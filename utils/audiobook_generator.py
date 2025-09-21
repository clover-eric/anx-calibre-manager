import asyncio
import os
import re
import logging
import io
import zipfile
from dataclasses import dataclass
from typing import Protocol, List, Tuple
from abc import ABC, abstractmethod
from time import sleep

import ffmpeg
from bs4 import BeautifulSoup
import ebooklib
from ebooklib import epub
from mutagen.mp4 import MP4, MP4Cover, MP4FreeForm
import edge_tts
from pydub import AudioSegment
from sentencex import segment

import config_manager
from utils.audiobook_tasks_db import get_tasks_to_cleanup, update_task_as_cleaned, get_all_successful_tasks

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
        paragraph_pause = AudioSegment.silent(duration=700) # 700ms 的段落停顿

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
                        break
                    except Exception as e:
                        logger.warning(f"EdgeTTS error on chunk {chunk_counter} (attempt {attempt + 1}/{MAX_TTS_RETRIES}): {e}")
                        if attempt < MAX_TTS_RETRIES - 1:
                            sleep(2 ** attempt)
                        else:
                            logger.error(f"Failed to generate audio for chunk after {MAX_TTS_RETRIES} retries.")
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
        
        combined.export(output_path, format="mp3")
        return os.path.exists(output_path) and os.path.getsize(output_path) > 0

# --- 有声书生成器 (主逻辑) ---

class AudiobookGenerator:
    def __init__(self, tts_provider: BaseTTSProvider, update_progress_callback: Protocol):
        self.tts_provider = tts_provider
        self.update_progress = update_progress_callback
        self.book_language = "en" # 默认语言

    def _get_book_language(self, book: epub.EpubBook) -> str:
        try:
            lang_meta = book.get_metadata('DC', 'language')
            if lang_meta and lang_meta[0][0]:
                return lang_meta[0][0].split('-')[0] # 'en-US' -> 'en'
        except Exception:
            pass
        return "en"

    def _get_book_title(self, book: epub.EpubBook) -> str:
        try:
            if title_meta := book.get_metadata('DC', 'title'):
                return title_meta[0][0]
        except Exception as e:
            logger.error(f"Error extracting title: {e}")
        return "Untitled"

    def _get_epub_chapters(self, book: epub.EpubBook, epub_path: str) -> List[Tuple[str, str]]:
        """
        使用多级回退策略从 EPUB 文件中提取章节和内容。
        """
        logger.info("Attempting chapter extraction strategy: Level 1 (epub_to_audiobook logic)...")
        chapters = self._get_epub_chapters_level1(book)
        
        total_text_length = sum(len(content) for _, content in chapters)
        if chapters and total_text_length > 500:
            logger.info(f"Level 1 extraction successful. Found {len(chapters)} chapters with total length {total_text_length}.")
            return chapters

        logger.warning(f"Level 1 extraction yielded insufficient content (Chapters: {len(chapters)}, Length: {total_text_length}). Falling back to Level 2.")

        logger.info("Attempting chapter extraction strategy: Level 2 (zipfile + spine logic)...")
        chapters_level2 = self._get_epub_chapters_level2_spine(book, epub_path)

        total_text_length_level2 = sum(len(self._extract_text_from_html(content)) for _, content in chapters_level2)
        if chapters_level2 and total_text_length_level2 > total_text_length:
            logger.info(f"Level 2 extraction successful. Found {len(chapters_level2)} chapters with total length {total_text_length_level2}.")
            return chapters_level2

        logger.warning(f"Level 2 extraction was not better than Level 1. Returning original result.")
        return chapters

    def _get_epub_chapters_level1(self, book: epub.EpubBook) -> List[Tuple[str, str]]:
        """
        第一级提取策略：移植自 epub_to_audiobook 的核心逻辑。
        """
        chapters = []
        newline_mode = "double"
        remove_endnotes = True

        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            content = item.get_content()
            soup = BeautifulSoup(content, "lxml-xml")
            raw_text = soup.get_text(strip=False)

            if newline_mode == "double":
                cleaned_text = re.sub(r"[\n\r]{2,}", _PARAGRAPH_BREAK_MARKER, raw_text.strip())
            else:
                cleaned_text = re.sub(r"[\n\r]+", _PARAGRAPH_BREAK_MARKER, raw_text.strip())
            
            cleaned_text = re.sub(r'[\n\r]+', ' ', cleaned_text)
            cleaned_text = re.sub(r"\s+", " ", cleaned_text)

            if remove_endnotes:
                cleaned_text = re.sub(r'(?<=[a-zA-Z.,!?;”")])\d+', "", cleaned_text)
            cleaned_text = re.sub(r'\[\d+(\.\d+)?\]', '', cleaned_text)

            title = ""
            for level in ['h1', 'h2', 'h3', 'title']:
                if tag := soup.find(level):
                    title = tag.get_text().strip()
                    break
            if not title:
                title = item.get_name() or item.file_name

            if cleaned_text.strip():
                chapters.append((title, cleaned_text))
        
        return chapters

    def _get_epub_chapters_level2_spine(self, book: epub.EpubBook, epub_path: str) -> List[Tuple[str, str]]:
        """
        第二级提取策略：基于 zipfile 和 book.spine 的手动解析。
        """
        chapters = []
        if book.spine:
            logger.info("Extracting chapters from EPUB spine.")
            with zipfile.ZipFile(epub_path, 'r') as archive:
                toc_title_map = {}
                if book.toc:
                    toc_items = book.toc if isinstance(book.toc, (list, tuple)) else [book.toc]
                    for item in toc_items:
                        if isinstance(item, ebooklib.epub.Link):
                            toc_title_map[item.href.split('#')[0]] = item.title

                for item_id, _ in book.spine:
                    item = book.get_item_with_id(item_id)
                    if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                        file_name = item.file_name
                        title = toc_title_map.get(file_name, item.get_name() or file_name)
                        try:
                            content = archive.read(file_name).decode('utf-8', 'ignore')
                            chapters.append((title, content))
                        except KeyError:
                            logger.warning(f"File '{file_name}' not found in EPUB archive.")
                        except Exception as e:
                            logger.error(f"Error reading file '{file_name}' from EPUB: {e}")
        else:
            logger.warning("EPUB has no spine. Cannot use Level 2 extraction.")
        return chapters

    def _extract_text_from_html(self, html_content: str) -> str:
        """从HTML内容中稳健地提取和清理文本，并保留段落间隔。"""
        soup = BeautifulSoup(html_content, 'html.parser')
        # 移除不包含口头内容的标签
        for element in soup(["script", "style", "head", "title", "meta", "[document]"]):
            element.decompose()
        
        # 获取包含换行符的原始文本
        raw_text = soup.get_text(strip=False)
        
        # 1. 将两个或多个换行符（段落分隔）替换为特殊标记
        text_with_breaks = re.sub(r'[\n\r]{2,}', _PARAGRAPH_BREAK_MARKER, raw_text)
        # 2. 将剩余的单个换行符替换为空格
        text_no_single_newlines = re.sub(r'[\n\r]+', ' ', text_with_breaks)
        # 3. 清理多余的空白字符
        cleaned_text = re.sub(r'\s+', ' ', text_no_single_newlines).strip()
        
        return cleaned_text

    def _sanitize_text(self, text: str) -> str:
        """清理文本，移除多余的空白。"""
        return re.sub(r'\s+', ' ', text).strip()

    def _get_epub_cover_image(self, book: epub.EpubBook) -> bytes | None:
        try:
            if cover_items := list(book.get_items_of_type(ebooklib.ITEM_COVER)):
                return cover_items[0].get_content()
            for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                if 'cover' in item.get_name().lower():
                    return item.get_content()
        except Exception as e:
            logger.error(f"Error extracting cover: {e}")
        return None

    async def _generate_chapter_audio(self, semaphore: asyncio.Semaphore, index: int, title: str, content: str, book_id: str, is_full_book: bool = False) -> ChapterAudio | None:
        async with semaphore:
            try:
                progress = 10 + int(60 * (index / self.total_chapters))
                await self.update_progress("progress", {
                    "percentage": progress,
                    "status_key": "PROCESSING_CHAPTER",
                    "params": {"index": index + 1, "total": self.total_chapters}
                })

                text = self._extract_text_from_html(content) if not is_full_book else content
                
                if not text:
                    logger.warning(f"Chapter {index + 1} '{title}' is empty, skipping.")
                    return None

                temp_audio_path = os.path.join(OUTPUT_DIR, f"temp_{book_id}_{index:04d}.mp3")
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

    def _write_m4b_tags(self, book: epub.EpubBook, m4b_path: str, chapters_audio: List[ChapterAudio]):
        try:
            audio = MP4(m4b_path)
            
            # --- 标准元数据 ---
            if title_meta := book.get_metadata('DC', 'title'):
                audio["\xa9nam"] = [title_meta[0][0]]  # Title
            if creator_meta := book.get_metadata('DC', 'creator'):
                author_name = creator_meta[0][0]
                audio["\xa9ART"] = [author_name]  # Artist
                audio["aART"] = [author_name]   # Album Artist
            
            # --- 增强的元数据 ---
            if publisher_meta := book.get_metadata('DC', 'publisher'):
                audio["\xa9pub"] = [publisher_meta[0][0]]  # Publisher

            if date_meta := book.get_metadata('DC', 'date'):
                year_match = re.search(r'\d{4}', date_meta[0][0])
                if year_match:
                    audio["\xa9day"] = [year_match.group(0)]  # Year

            # Description - 优先使用 'description'，回退到 Calibre 可能使用的 'comments'
            if description_meta := book.get_metadata('DC', 'description'):
                audio["desc"] = [description_meta[0][0]]
            elif comments_meta := book.get_metadata('DC', 'comments'):
                 audio["desc"] = [comments_meta[0][0]]

            if subject_meta := book.get_metadata('DC', 'subject'):
                audio["\xa9gen"] = [s[0] for s in subject_meta]  # Genre

            if language_meta := book.get_metadata('DC', 'language'):
                audio["lang"] = [language_meta[0][0]] # Language

            # 提取 ISBN
            for identifier in book.get_metadata('DC', 'identifier'):
                try:
                    if 'scheme' in identifier[1] and identifier[1]['scheme'] == 'ISBN':
                        isbn_value = identifier[0]
                        # 使用一个非标准的 '----' atom 来存储 ISBN，某些播放器可能会识别
                        audio["----:com.apple.iTunes:ISBN"] = MP4FreeForm(isbn_value.encode('utf-8'))
                        break
                except (IndexError, KeyError):
                    continue

            audio["\xa9wrt"] = [self.tts_provider.config.voice]  # Composer/Narrator

            if cover_data := self._get_epub_cover_image(book):
                img_format = MP4Cover.FORMAT_JPEG if cover_data.startswith(b'\xff\xd8') else MP4Cover.FORMAT_PNG
                audio["covr"] = [MP4Cover(cover_data, imageformat=img_format)]

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

    async def generate(self, epub_path: str, book_id: str) -> str | None:
        # 在开始新任务前，执行一次自动清理
        cleanup_old_audiobooks()

        chapters = []
        try:
            await self.update_progress("start", {"status_key": "GENERATION_STARTED"})
            
            book = epub.read_epub(epub_path)
            self.book_language = self._get_book_language(book)

            await self.update_progress("progress", {"percentage": 5, "status_key": "PARSING_EPUB"})
            chapters = self._get_epub_chapters(book, epub_path)
            logger.info(f"DEBUG: Found {len(chapters)} chapters.")
            if not chapters:
                raise ValueError("CHAPTER_EXTRACTION_FAILED")
            self.total_chapters = len(chapters)
            
            book_title = self._get_book_title(book)
            sanitized_title = re.sub(r'[^\w\s-]', '', book_title).strip()
            sanitized_title = re.sub(r'[-\s]+', '_', sanitized_title)
            output_filename = f"{sanitized_title}_{book_id}.m4b"
            final_output_path = os.path.join(OUTPUT_DIR, output_filename)

            semaphore = asyncio.Semaphore(CONCURRENT_TTS_REQUESTS)
            tasks = [self._generate_chapter_audio(semaphore, i, title, content, book_id) for i, (title, content) in enumerate(chapters)]
            results = await asyncio.gather(*tasks)
            chapters_audio = [res for res in results if res is not None]

            # 如果所有章节都为空，则尝试将整本书作为一个章节处理
            if not chapters_audio and chapters:
                logger.warning("No valid text found in chapters. Attempting to process the entire book as a single chapter.")
                
                # 提取书中所有文档的纯文本内容
                full_book_text_content = ""
                for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                    html_content = item.get_content().decode('utf-8', 'ignore')
                    plain_text = self._extract_text_from_html(html_content)
                    if plain_text:
                        full_book_text_content += plain_text + " "

                if full_book_text_content.strip():
                    logger.debug(f"Fallback mode: full book text content (first 200 chars): {full_book_text_content.strip()[:200]}")
                    # 创建一个包含所有文本的伪章节
                    single_chapter_content_for_tts = [ (book_title, full_book_text_content.strip()) ]
                    self.total_chapters = 1 # 重置章节总数以便UI正确显示
                    
                    # 重新运行生成任务
                    tasks = [self._generate_chapter_audio(semaphore, i, title, content, book_id, is_full_book=True) for i, (title, content) in enumerate(single_chapter_content_for_tts)]
                    results = await asyncio.gather(*tasks)
                    chapters_audio = [res for res in results if res is not None]
                
                if not chapters_audio:
                    # 如果还是失败，则抛出原始错误
                    raise ValueError("CHAPTER_CONVERSION_FAILED")

            if not chapters_audio:
                raise ValueError("CHAPTER_CONVERSION_FAILED")

            await self.update_progress("progress", {"percentage": 75, "status_key": "MERGING_FILES"})
            
            # 使用 pydub 合并音频文件
            combined_audio = AudioSegment.empty()
            for chapter in sorted(chapters_audio, key=lambda c: c.index):
                try:
                    segment = AudioSegment.from_mp3(chapter.audio_path)
                    combined_audio += segment
                except Exception as e:
                    logger.warning(f"Could not process chapter audio file {chapter.audio_path}, skipping. Error: {e}")
            
            # 导出为 m4b (mp4) 格式
            # 注意：pydub 需要 ffmpeg 在后台支持 mp4 导出
            combined_audio.export(final_output_path, format="mp4", bitrate="64k")

            await self.update_progress("progress", {"percentage": 90, "status_key": "WRITING_METADATA"})
            self._write_m4b_tags(book, final_output_path, chapters_audio)

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
                temp_file = os.path.join(OUTPUT_DIR, f"temp_{book_id}_{i:04d}.mp3")
                if os.path.exists(temp_file): os.remove(temp_file)
            return None
