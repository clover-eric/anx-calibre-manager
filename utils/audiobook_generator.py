import asyncio
import os
import re
import logging
import io
from dataclasses import dataclass
from typing import Protocol, List, Tuple, Dict, Any
from abc import ABC, abstractmethod
from time import sleep

import ffmpeg
from ebooklib import epub
from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm
import edge_tts
from openai import OpenAI
from pydub import AudioSegment
from sentencex import segment

import config_manager
from utils.audiobook_tasks_db import get_tasks_to_cleanup, update_task_as_cleaned, get_all_successful_tasks
from utils.epub_chapter_parser import get_parsed_chapters
from utils.epub_meta import get_metadata
from utils.text import generate_audiobook_filename
import string

# --- 常量 ---
_PARAGRAPH_BREAK_MARKER = "_PARAGRAPH_BREAK_"

# --- 配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = "/audiobooks"
os.makedirs(OUTPUT_DIR, exist_ok=True)
CONCURRENT_TTS_REQUESTS = 5
MAX_TTS_RETRIES = 12

# --- 清理函数 ---
def cleanup_old_audiobooks():
    """根据全局设置清理旧的有声书文件。"""
    try:
        cleanup_days = int(config_manager.config.get('AUDIOBOOK_CLEANUP_DAYS', 7))
        if cleanup_days == 0:
            logger.info("Audiobook cleanup is disabled.")
            return

        logger.info(f"Starting cleanup of audiobooks older than {cleanup_days} days.")
        tasks_to_clean = get_tasks_to_cleanup(cleanup_days)
        count = 0
        for task in tasks_to_clean:
            if task['file_path'] and os.path.exists(task['file_path']):
                try:
                    os.remove(task['file_path'])
                    update_task_as_cleaned(task['task_id'])
                    logger.info(f"Cleaned up old audiobook: {task['file_path']}")
                    count += 1
                except OSError as e:
                    logger.error(f"Error removing file {task['file_path']}: {e}")
        logger.info(f"Cleanup complete. Removed {count} old audiobook files.")
    except Exception as e:
        logger.error(f"An error occurred during audiobook cleanup: {e}")

def cleanup_all_audiobooks():
    """手动触发，清理所有已生成的有声书文件。"""
    try:
        logger.info("Starting manual cleanup of all audiobooks.")
        tasks_to_clean = get_all_successful_tasks()
        count = 0
        for task in tasks_to_clean:
            if task['file_path'] and os.path.exists(task['file_path']):
                try:
                    os.remove(task['file_path'])
                    update_task_as_cleaned(task['task_id'])
                    logger.info(f"Cleaned up audiobook: {task['file_path']}")
                    count += 1
                except OSError as e:
                    logger.error(f"Error removing file {task['file_path']}: {e}")
        logger.info(f"Manual cleanup complete. Removed {count} audiobook files.")
        return count
    except Exception as e:
        logger.error(f"An error occurred during manual audiobook cleanup: {e}")
        return 0

# --- 从 epub_to_audiobook 移植的工具函数 ---

def split_long_sentence(sentence: str, max_chars: int) -> List[str]:
    punctuations = ['。', '！', '？', '. ', '! ', '? ', '；', ';', '，', ',', '：', ':', '）', ')', ']', '】', '}', '」', '』', '、', '—', '-', '–', ' ']
    parts = []
    remaining = sentence
    while remaining:
        if len(remaining) <= max_chars:
            parts.append(remaining)
            break
        best_split_idx = -1
        for p in punctuations:
            split_idx = remaining[:max_chars].rfind(p)
            if split_idx != -1:
                best_split_idx = split_idx + len(p)
                break
        if best_split_idx == -1:
            best_split_idx = max_chars
        parts.append(remaining[:best_split_idx])
        remaining = remaining[best_split_idx:]
    return parts

def is_punctuation_or_whitespace(s: str) -> bool:
    """检查字符串是否只包含标点符号、特殊符号和空白字符。"""
    # 定义一个更全面的标点和符号集合
    punctuation_and_symbols = string.punctuation + "。？！；，：、……“”‘’（）《》【】「」『』—"
    return all(char.isspace() or char in punctuation_and_symbols for char in s)

def split_text(text: str, max_chars: int, language: str) -> List[str]:
    if not text: return []
    if max_chars <= 0: raise ValueError("max_chars must be positive")
    
    sentences = list(segment(language, text))
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        space = " " if current_chunk else ""
        if len(current_chunk) + len(space) + len(sentence) <= max_chars:
            current_chunk += space + sentence
        elif len(sentence) > max_chars:
            if current_chunk: chunks.append(current_chunk)
            sentence_chunks = split_long_sentence(sentence, max_chars)
            chunks.extend(sentence_chunks[:-1])
            current_chunk = sentence_chunks[-1]
        else:
            if current_chunk: chunks.append(current_chunk)
            current_chunk = sentence
    if current_chunk: chunks.append(current_chunk)
    return chunks

# --- 数据类 ---

@dataclass
class TTSConfig:
    voice: str = "zh-CN-YunjianNeural"
    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None

@dataclass
class ChapterAudio:
    index: int
    title: str
    audio_path: str
    duration_ms: int

# --- TTS 实现 (移植自 epub_to_audiobook) ---

class CommWithPauses:
    def __init__(self, text: str, voice_name: str, **kwargs) -> None:
        self.full_text = text
        self.voice_name = voice_name
        self.kwargs = kwargs
        self.file = io.BytesIO()

    async def get_audio_segment(self) -> AudioSegment:
        temp_chunk = io.BytesIO()
        communicate = edge_tts.Communicate(self.full_text, self.voice_name, **self.kwargs)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                temp_chunk.write(chunk["data"])
        
        temp_chunk.seek(0)
        try:
            return AudioSegment.from_mp3(temp_chunk)
        except Exception:
            return AudioSegment.silent(0, 24000)

class BaseTTSProvider(ABC):
    def __init__(self, config: TTSConfig):
        self.config = config

    @abstractmethod
    async def text_to_speech(self, text: str, output_path: str, language: str) -> bool:
        pass

class EdgeTTSProvider(BaseTTSProvider):
    async def text_to_speech(self, text: str, output_path: str, language: str) -> bool:
        max_chars = 1800 if language.startswith("zh") else 3000
        
        # 按段落标记分割文本
        paragraphs = text.split(_PARAGRAPH_BREAK_MARKER)
        
        segments: list[AudioSegment] = []
        paragraph_pause = AudioSegment.silent(duration=1500) # 1500ms 的段落停顿
        sentence_pause = AudioSegment.silent(duration=900)  # 900ms 的句子停顿

        # 预先计算总块数以提供更准确的日志
        total_chunks = sum(len(split_text(p, max_chars, language)) for p in paragraphs if p.strip())
        if total_chunks == 0: total_chunks = 1 # 避免除以零
        chunk_counter = 0

        for para_idx, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            text_chunks = split_text(paragraph, max_chars, language)
            
            for i, chunk in enumerate(text_chunks):
                chunk_counter += 1
                
                # 在发送到 TTS 之前，跳过只包含标点或空白的块
                if is_punctuation_or_whitespace(chunk):
                    logger.info(f"Skipping chunk {chunk_counter}/{total_chunks} as it contains only punctuation/whitespace.")
                    continue

                logger.info(f"Generating audio for chunk {chunk_counter}/{total_chunks}...")
                for attempt in range(MAX_TTS_RETRIES):
                    try:
                        communicate = CommWithPauses(
                            text=chunk,
                            voice_name=self.config.voice,
                            rate=self.config.rate,
                            volume=self.config.volume,
                            pitch=self.config.pitch,
                            proxy=None
                        )
                        segment = await communicate.get_audio_segment()
                        segments.append(segment)
                        # 如果不是段落的最后一个句子块，则添加句子停顿
                        if i < len(text_chunks) - 1:
                            segments.append(sentence_pause)
                        break
                    except Exception as e:
                        # 增强日志：当 TTS 失败时，记录下导致失败的具体文本块内容
                        logger.warning(f"EdgeTTS error on chunk {chunk_counter} (attempt {attempt + 1}/{MAX_TTS_RETRIES}): {e}")
                        logger.warning(f"Problematic chunk content: {chunk!r}") # 使用 !r 来显示原始字符串表示
                        if attempt < MAX_TTS_RETRIES - 1:
                            sleep(2 ** attempt)
                        else:
                            logger.error(f"Failed to generate audio for chunk after {MAX_TTS_RETRIES} retries. Content: {chunk!r}")
                            return False
            
            # 在每个段落（除了最后一个）之后添加停顿
            if para_idx < len(paragraphs) - 1:
                segments.append(paragraph_pause)

        if not segments:
            logger.warning("No audio segments were generated.")
            return False

        combined = AudioSegment.empty()
        for seg in segments:
            combined += seg
        
        combined.export(output_path, format="ipod", codec="aac")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0

class OpenAITTSProvider(BaseTTSProvider):
    def __init__(self, config: TTSConfig):
        super().__init__(config)
        self.client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            max_retries=4
        )

    def _convert_rate_to_speed(self, rate: str) -> float:
        """Converts rate like '+10%' to speed like 1.1."""
        try:
            rate_val = float(rate.strip('%')) / 100
            return max(0.25, min(4.0, 1.0 + rate_val))
        except ValueError:
            return 1.0

    async def text_to_speech(self, text: str, output_path: str, language: str) -> bool:
        max_chars = 1800  # OpenAI has a 4096 character limit, 1800 is a safe chunk size
        
        paragraphs = text.split(_PARAGRAPH_BREAK_MARKER)
        
        segments: list[AudioSegment] = []
        paragraph_pause = AudioSegment.silent(duration=500)
        sentence_pause = AudioSegment.silent(duration=300)

        total_chunks = sum(len(split_text(p, max_chars, language)) for p in paragraphs if p.strip())
        if total_chunks == 0: total_chunks = 1
        chunk_counter = 0

        speed = self._convert_rate_to_speed(self.config.rate)

        for para_idx, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            text_chunks = split_text(paragraph, max_chars, language)
            
            for chunk in text_chunks:
                chunk_counter += 1
                logger.info(f"Generating audio for chunk {chunk_counter}/{total_chunks} via OpenAI...")
                try:
                    response = self.client.audio.speech.create(
                        model=self.config.model or "tts-1",
                        voice=self.config.voice or "alloy",
                        speed=speed,
                        input=chunk,
                        response_format="mp3",
                    )
                    
                    audio_data = io.BytesIO(response.content)
                    segment = AudioSegment.from_mp3(audio_data)
                    segments.append(segment)
                    # 如果不是段落的最后一个句子块，则添加句子停顿
                    if i < len(text_chunks) - 1:
                        segments.append(sentence_pause)

                except Exception as e:
                    logger.error(f"OpenAI TTS error on chunk {chunk_counter}: {e}")
                    return False
            
            if para_idx < len(paragraphs) - 1:
                segments.append(paragraph_pause)

        if not segments:
            logger.warning("No audio segments were generated by OpenAI.")
            return False

        combined = AudioSegment.empty()
        for seg in segments:
            combined += seg
        
        combined.export(output_path, format="ipod", codec="aac")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0

# --- 有声书生成器 (主逻辑) ---

class AudiobookGenerator:
    def __init__(self, tts_provider: BaseTTSProvider, update_progress_callback: Protocol):
        self.tts_provider = tts_provider
        self.update_progress = update_progress_callback
        self.book_language = "en" # 默认语言

    async def _generate_chapter_audio(self, semaphore: asyncio.Semaphore, index: int, title: str, content: str, book_id: str) -> ChapterAudio | None:
        async with semaphore:
            try:
                progress = 10 + int(60 * ((index + 1) / self.total_chapters))
                await self.update_progress("progress", {
                    "percentage": progress,
                    "status_key": "PROCESSING_CHAPTER",
                    "params": {"index": index + 1, "total": self.total_chapters}
                })

                # 将标准的段落分隔符 (\n\n) 转换回 TTS 处理器使用的内部标记。
                text = content.replace('\n\n', f' {_PARAGRAPH_BREAK_MARKER} ')
                
                if not text.strip():
                    logger.warning(f"Chapter {index + 1} '{title}' is empty after processing, skipping.")
                    return None

                temp_audio_path = os.path.join(OUTPUT_DIR, f"temp_{book_id}_{index:04d}.m4a")
                success = await self.tts_provider.text_to_speech(text, temp_audio_path, self.book_language)

                if not success:
                    logger.error(f"Failed to generate audio for chapter '{title}'.")
                    return None

                probe = ffmpeg.probe(temp_audio_path)
                duration_ms = int(float(probe['format']['duration']) * 1000)
                return ChapterAudio(index, title, temp_audio_path, duration_ms)
            except Exception as e:
                logger.error(f"Error processing chapter {index+1} ('{title}'): {e}")
                return None

    def _write_m4b_tags(self, book_meta: Dict[str, Any], m4b_path: str, chapters_audio: List[ChapterAudio], cover_image_data: bytes | None = None):
        try:
            audio = MP4(m4b_path)
            
            # --- 标准元数据 ---
            if title := book_meta.get('title'):
                audio["\xa9nam"] = [title]
            
            authors = book_meta.get('authors', [])
            if authors:
                author_name = authors[0]
                audio["\xa9ART"] = [author_name]
                audio["aART"] = [author_name]
            
            # --- 增强的元数据 ---
            if publisher := book_meta.get('publisher'):
                audio["\xa9pub"] = [publisher]

            UNDEFINED_DATE_ISO = '0101-01-01T00:00:00+00:00'
            if pubdate := book_meta.get('pubdate'):
                pubdate_str = str(pubdate).strip()
                # 检查是否为 Calibre 的未定义日期或 Anx/EPUB 内部的无效年份，如果是则跳过
                if UNDEFINED_DATE_ISO not in pubdate_str and pubdate_str not in ['0101', '101']:
                    # pubdate 可能已经是年份字符串，或者包含年份的字符串
                    year_match = re.search(r'\d{4}', pubdate_str)
                    if year_match:
                        # 再次检查匹配到的年份是否有效
                        year_val = year_match.group(0)
                        if year_val not in ['0101', '101']:
                            audio["\xa9day"] = [year_val]

            # Description - 使用 'comments' 键，因为 get_metadata 已经处理了回退逻辑
            if comments := book_meta.get('comments'):
                 audio["desc"] = [comments]

            if tags := book_meta.get('tags'):
                audio["\xa9gen"] = tags

            if language := book_meta.get('language'):
                audio["lang"] = [language]

            # 提取 ISBN
            if isbn := book_meta.get('isbn'):
                audio["----:com.apple.iTunes:ISBN"] = MP4FreeForm(isbn.encode('utf-8'))

            audio["\xa9wrt"] = [self.tts_provider.config.voice]  # Composer/Narrator

            # --- 封面处理 ---
            # 优先使用外部传入的封面数据（例如从 Anx 数据库直接读取的）
            final_cover_data = cover_image_data
            if not final_cover_data:
                # 如果没有外部封面，则使用从 get_metadata 获取的封面
                final_cover_data = book_meta.get('cover_image_data')

            if final_cover_data:
                img_format = MP4Cover.FORMAT_JPEG if final_cover_data.startswith(b'\xff\xd8') else MP4Cover.FORMAT_PNG
                audio["covr"] = [MP4Cover(final_cover_data, imageformat=img_format)]

            # --- 章节元数据 ---
            # mutagen 使用 Nero 格式的章节标签
            # See: https://github.com/quodlibet/mutagen/blob/master/mutagen/mp4/_chapters.py
            # See: https://github.com/Jens-Christian-Korth/m4b-util/blob/master/m4b_util/helpers.py
            if chapters_audio:
                chapter_times = []
                current_time_ms = 0
                for chapter in sorted(chapters_audio, key=lambda c: c.index):
                    chapter_times.append(current_time_ms)
                    current_time_ms += chapter.duration_ms

                toc = []
                for i, start_time in enumerate(chapter_times):
                    title = sorted(chapters_audio, key=lambda c: c.index)[i].title
                    toc.append((start_time, title))

                # 创建 Nero 章节字符串
                nero_chapters = ""
                for i, (start, title) in enumerate(toc):
                    # 时间格式: HH:MM:SS.ms
                    hours, remainder = divmod(start, 3600000)
                    minutes, remainder = divmod(remainder, 60000)
                    seconds, milliseconds = divmod(remainder, 1000)
                    time_str = f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"
                    nero_chapters += f"CHAPTER{i+1}={time_str}\nCHAPTER{i+1}NAME={title}\n"
                
                # 将章节数据写入 '----' atom
                audio["----:com.apple.iTunes:chapters"] = MP4FreeForm(nero_chapters.encode("utf-8"))

            audio.save()
        except Exception as e:
            logger.error(f"Error writing M4B tags: {e}")

    async def generate(self, book_id: str, library_type: str, user_dict: dict, cover_image_data: bytes | None = None) -> str | None:
        # 在开始新任务前，执行一次自动清理
        cleanup_old_audiobooks()

        chapters = []
        try:
            await self.update_progress("start", {"status_key": "GENERATION_STARTED"})
            
            await self.update_progress("progress", {"percentage": 5, "status_key": "PARSING_EPUB"})
            chapters = get_parsed_chapters(library_type, int(book_id), user_dict)
            book_meta = get_metadata(library_type, int(book_id), user_dict)
            
            logger.info(f"DEBUG: Found {len(chapters)} chapters from unified parser.")
            if not chapters:
                raise ValueError("CHAPTER_EXTRACTION_FAILED")
            self.total_chapters = len(chapters)
            
            self.book_language = book_meta.get('language', 'en').split('-')[0]
            book_title = book_meta.get('title', 'Untitled')
            book_author = (book_meta.get('authors') or ['Unknown Author'])[0]
            
            output_filename = generate_audiobook_filename(
                title=book_title,
                author=book_author,
                book_id=book_id,
                library_type=library_type,
                username=user_dict.get('username')
            )
            final_output_path = os.path.join(OUTPUT_DIR, output_filename)

            semaphore = asyncio.Semaphore(CONCURRENT_TTS_REQUESTS)
            tasks = [self._generate_chapter_audio(semaphore, i, title, content, book_id) for i, (title, content) in enumerate(chapters)]
            results = await asyncio.gather(*tasks)
            chapters_audio = [res for res in results if res is not None]

            # 如果所有章节都为空，则尝试将整本书作为一个章节处理
            if not chapters_audio and chapters:
                logger.warning("No valid text found in chapters. Attempting to process the entire book as a single chapter.")
                
                full_book_text_content = "\n\n".join([content for _, content in chapters])

                if full_book_text_content.strip():
                    logger.debug(f"Fallback mode: full book text content (first 200 chars): {full_book_text_content.strip()[:200]}")
                    # 创建一个包含所有文本的伪章节
                    single_chapter_content_for_tts = [ (book_title, full_book_text_content.strip()) ]
                    self.total_chapters = 1 # 重置章节总数以便UI正确显示
                    
                    # 重新运行生成任务
                    tasks = [self._generate_chapter_audio(semaphore, i, title, content, book_id) for i, (title, content) in enumerate(single_chapter_content_for_tts)]
                    results = await asyncio.gather(*tasks)
                    chapters_audio = [res for res in results if res is not None]
                
                if not chapters_audio:
                    # 如果还是失败，则抛出原始错误
                    raise ValueError("CHAPTER_CONVERSION_FAILED")

            if not chapters_audio:
                raise ValueError("CHAPTER_CONVERSION_FAILED")

            await self.update_progress("progress", {"percentage": 75, "status_key": "MERGING_FILES"})
            
            # --- 使用 ffmpeg concat 进行高效合并 ---
            concat_list_path = os.path.join(OUTPUT_DIR, f"concat_list_{book_id}.txt")
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for chapter in sorted(chapters_audio, key=lambda c: c.index):
                    # 使用正确的引号处理可能包含特殊字符的路径
                    f.write(f"file '{os.path.abspath(chapter.audio_path)}'\n")

            try:
                # 只执行一步：使用 acodec='copy' 快速无损合并
                logger.info("Merging audio files with fast, lossless concatenation...")
                (
                    ffmpeg
                    .input(concat_list_path, format='concat', safe=0)
                    .output(final_output_path, acodec='copy')
                    .run(overwrite_output=True, quiet=True)
                )
                logger.info(f"Successfully merged audio files into {final_output_path}")

            except ffmpeg.Error as e:
                logger.error(f"ffmpeg concat failed. Stderr: {e.stderr.decode('utf8')}")
                raise ValueError("MERGE_FILES_FAILED") from e
            finally:
                # 确保 concat_list 文件被删除
                if os.path.exists(concat_list_path):
                    os.remove(concat_list_path)

            await self.update_progress("progress", {"percentage": 90, "status_key": "WRITING_METADATA"})
            self._write_m4b_tags(book_meta, final_output_path, chapters_audio, cover_image_data=cover_image_data)

            await self.update_progress("progress", {"percentage": 98, "status_key": "CLEANING_UP"})
            for chapter in chapters_audio:
                os.remove(chapter.audio_path)

            await self.update_progress("success", {"status_key": "GENERATION_SUCCESS", "path": final_output_path, "percentage": 100})
            return final_output_path

        except Exception as e:
            logger.exception("A critical error occurred during audiobook generation.")
            # 将异常类型作为key，消息作为参数，以便在API层进行翻译
            error_key = str(e) if isinstance(e, ValueError) else "UNKNOWN_ERROR"
            await self.update_progress("error", {"status_key": error_key, "params": {"error": str(e)}})
            for i in range(len(chapters)):
                temp_file = os.path.join(OUTPUT_DIR, f"temp_{book_id}_{i:04d}.m4a")
                if os.path.exists(temp_file): os.remove(temp_file)
            return None
