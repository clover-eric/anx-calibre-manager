import os
import logging
import re
import sqlite3
from flask import Blueprint, jsonify, g, request, send_file, Response
from flask_babel import gettext as _
from contextlib import closing
import database
from utils.audio_metadata import extract_m4b_metadata
from anx_library import get_anx_user_dirs
from datetime import datetime
from utils.activity_logger import log_activity, ActivityType
from anx_library import get_anx_book_path, get_anx_user_dirs
from utils.epub_cfi_utils import get_cfi_for_chapter, get_chapter_from_cfi, get_total_chapters

logger = logging.getLogger(__name__)
audio_player_bp = Blueprint('audio_player', __name__, url_prefix='/api/audioplayer')

def get_db():
    return database.get_db()

@audio_player_bp.route('/list/<library_type>', methods=['GET'])
def get_audiobook_list(library_type):
    if g.user is None or g.user.id is None:
        return jsonify({'error': 'Authentication required'}), 401

    user_id = g.user.id
    
    with closing(get_db()) as db:
        cursor = db.cursor()
        if library_type == 'anx':
            cursor.execute("""
                SELECT task_id, book_id, library_type, file_path FROM audiobook_tasks
                WHERE user_id = ? AND library_type = 'anx' AND status = 'success'
            """, (user_id,))
        elif library_type == 'calibre':
            cursor.execute("""
                SELECT task_id, book_id, library_type, file_path, user_id FROM audiobook_tasks
                WHERE library_type = 'calibre' AND status = 'success'
            """)
        else:
            return jsonify({'error': 'Invalid library type'}), 400
        
        tasks = cursor.fetchall()

    audiobooks = []
    for task in tasks:
        if task['file_path'] and os.path.exists(task['file_path']):
            metadata = extract_m4b_metadata(task['file_path'])
            if metadata:
                chapters = metadata.get('chapters', [])
                chapter_count = len(chapters)
                total_duration = chapters[-1]['end'] if chapters else 0
                
                audiobooks.append({
                    'task_id': task['task_id'],
                    'book_id': task['book_id'],
                    'library_type': task['library_type'],
                    'user_id': task['user_id'] if 'user_id' in task.keys() else user_id,
                    'chapter_count': chapter_count,
                    'total_duration': total_duration,
                    **metadata
                })
    
    return jsonify(audiobooks)

@audio_player_bp.route('/stream/<task_id>')
def stream_audiobook(task_id):
    if g.user is None or g.user.id is None:
        return jsonify({'error': 'Authentication required'}), 401

    with closing(get_db()) as db:
        task = db.execute("SELECT file_path FROM audiobook_tasks WHERE task_id = ? AND status = 'success'", (task_id,)).fetchone()

    if not task or not task['file_path'] or not os.path.exists(task['file_path']):
        return jsonify({'error': 'Audiobook not found'}), 404

    file_path = task['file_path']
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get('Range', None)
    
    start = 0
    end = file_size - 1
    status_code = 200

    if range_header:
        range_match = re.search(r'bytes=(\d+)-(\d*)', range_header)
        if range_match:
            start = int(range_match.group(1))
            if range_match.group(2):
                end = int(range_match.group(2))
            status_code = 206 # Partial Content

    length = end - start + 1

    def generate_chunks():
        with open(file_path, 'rb') as f:
            f.seek(start)
            bytes_read = 0
            while bytes_read < length:
                chunk_size = min(4096, length - bytes_read)
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                bytes_read += len(chunk)
                yield chunk

    response = Response(generate_chunks(), status=status_code, mimetype='audio/mp4', direct_passthrough=True)
    response.headers.set('Content-Length', str(length))
    response.headers.set('Accept-Ranges', 'bytes')
    if range_header:
        response.headers.set('Content-Range', f'bytes {start}-{end}/{file_size}')

    return response

@audio_player_bp.route('/progress/<task_id>', methods=['GET', 'POST'])
def handle_progress(task_id):
    if g.user is None or g.user.id is None:
        return jsonify({'error': 'Authentication required'}), 401
    
    user_id = g.user.id

    with closing(get_db()) as db:
        if request.method == 'POST':
            data = request.get_json()
            current_time = data.get('currentTime')
            total_duration = data.get('totalDuration')
            playback_rate = data.get('playbackRate', 1.0)
            chapter_index = data.get('chapterIndex')
            is_user_action = data.get('isUserAction', False)

            if current_time is None or total_duration is None:
                return jsonify({'error': 'Invalid progress data'}), 400

            progress_ms = int(float(current_time) * 1000)
            duration_ms = int(float(total_duration) * 1000)

            db.execute("""
                INSERT INTO audiobook_progress (user_id, task_id, progress_ms, duration_ms, playback_rate, chapter_index, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, task_id) DO UPDATE SET
                progress_ms = excluded.progress_ms,
                duration_ms = excluded.duration_ms,
                playback_rate = excluded.playback_rate,
                chapter_index = excluded.chapter_index,
                updated_at = CURRENT_TIMESTAMP
            """, (user_id, task_id, progress_ms, duration_ms, playback_rate, chapter_index))
            db.commit()

            task = db.execute("SELECT book_id, library_type FROM audiobook_tasks WHERE task_id = ?", (task_id,)).fetchone()
            if task and task['library_type'] == 'anx' and chapter_index is not None:
                try:
                    book_id = task['book_id']
                    epub_path = get_anx_book_path(g.user.username, book_id)
                    epubcfi = get_cfi_for_chapter(epub_path, chapter_index)
                    if epubcfi:
                        total_chapters = get_total_chapters(epub_path)
                        percentage = ((chapter_index + 1) / total_chapters) * 100 if total_chapters > 0 else 0
                        dirs = get_anx_user_dirs(g.user.username)
                        if dirs and os.path.exists(dirs["db_path"]):
                            with closing(sqlite3.connect(dirs["db_path"])) as anx_db:
                                current_time_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                                anx_db.execute("UPDATE tb_books SET last_read_position = ?, reading_percentage = ?, update_time = ? WHERE id = ?", (epubcfi, percentage, current_time_str, book_id))
                                anx_db.commit()
                except Exception as e:
                    logger.error(f"Failed to update Anx DB for book {task['book_id']}: {e}")

            if is_user_action:
                log_activity(ActivityType.PLAY_AUDIOBOOK_UPDATE_PLAYING_PROGRESS, task_id=task_id, success=True)
                if task and task['library_type'] == 'anx':
                    log_activity(ActivityType.PLAY_AUDIOBOOK_UPDATE_READING_PROGRESS, book_id=task['book_id'], library_type='anx', success=True)

            return jsonify({'message': _('Progress updated')})
        else:  # GET
            progress = db.execute("SELECT progress_ms, playback_rate, chapter_index FROM audiobook_progress WHERE user_id = ? AND task_id = ?", (user_id, task_id)).fetchone()
            task = db.execute("SELECT book_id, library_type, file_path FROM audiobook_tasks WHERE task_id = ?", (task_id,)).fetchone()

            if not task or not task['file_path'] or not os.path.exists(task['file_path']):
                return jsonify({'currentTime': 0, 'totalDuration': 0, 'playbackRate': 1.0, 'chapterIndex': 0})

            metadata = extract_m4b_metadata(task['file_path'])
            total_duration_sec = metadata.get('duration', 0) if metadata else 0
            
            saved_time_sec = 0
            saved_rate = 1.0
            audiobook_chapter_index = 0
            if progress:
                saved_time_sec = (int(progress['progress_ms']) / 1000.0) if progress['progress_ms'] else 0
                saved_rate = float(progress['playback_rate']) if progress['playback_rate'] else 1.0
                audiobook_chapter_index = int(progress['chapter_index']) if progress['chapter_index'] else 0

            final_time_sec = saved_time_sec
            final_chapter_index = audiobook_chapter_index

            if task['library_type'] == 'anx':
                try:
                    dirs = get_anx_user_dirs(g.user.username)
                    if dirs and os.path.exists(dirs["db_path"]):
                        with closing(sqlite3.connect(dirs["db_path"])) as anx_db:
                            anx_book = anx_db.execute("SELECT last_read_position FROM tb_books WHERE id = ?", (task['book_id'],)).fetchone()
                            if anx_book and anx_book[0]:
                                epub_path = get_anx_book_path(g.user.username, task['book_id'])
                                reader_chapter_index = get_chapter_from_cfi(epub_path, anx_book[0])
                                if reader_chapter_index > audiobook_chapter_index:
                                    final_chapter_index = reader_chapter_index
                                    final_time_sec = 0 # Start from beginning of chapter
                except Exception as e:
                    logger.error(f"Failed to get Anx progress for book {task['book_id']}: {e}")

            if total_duration_sec > 0 and final_time_sec > total_duration_sec:
                final_time_sec = 0

            return jsonify({
                'currentTime': final_time_sec,
                'totalDuration': total_duration_sec,
                'playbackRate': saved_rate,
                'chapterIndex': final_chapter_index
            })

@audio_player_bp.route('/log_listen_time', methods=['POST'])
def log_listen_time():
    if g.user is None or g.user.id is None:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    book_id = data.get('book_id')
    listen_duration_seconds = data.get('listen_duration_seconds')
    is_user_action = data.get('isUserAction', False)  # 标记是否为用户主动操作

    if not book_id or not listen_duration_seconds:
        return jsonify({'error': 'book_id and listen_duration_seconds are required.'}), 400

    try:
        listen_duration = int(listen_duration_seconds)
        if listen_duration <= 0:
            return jsonify({'message': 'Duration must be positive.'})
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid listen_duration_seconds.'}), 400

    dirs = get_anx_user_dirs(g.user.username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        return jsonify({'error': 'Anx library not found.'}), 404

    date_str = datetime.utcnow().strftime('%Y-%m-%d')

    with closing(sqlite3.connect(dirs["db_path"])) as db:
        cursor = db.cursor()
        
        # Check if a record for this book and date already exists
        cursor.execute("SELECT id, reading_time FROM tb_reading_time WHERE book_id = ? AND date = ?", (book_id, date_str))
        existing_record = cursor.fetchone()

        if existing_record:
            new_reading_time = existing_record[1] + listen_duration
            cursor.execute("UPDATE tb_reading_time SET reading_time = ? WHERE id = ?", (new_reading_time, existing_record[0]))
        else:
            cursor.execute("INSERT INTO tb_reading_time (book_id, date, reading_time) VALUES (?, ?, ?)", (book_id, date_str, listen_duration))
        
        db.commit()
        
        # 只在用户主动操作时记录活动日志
        if is_user_action:
            log_activity(ActivityType.PLAY_AUDIOBOOK_UPDATE_READING_TIME, book_id=book_id, library_type='anx', success=True, detail=f'{listen_duration}s')

    return jsonify({'message': 'Listen time logged successfully.'})

