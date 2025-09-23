import os
import logging
import re
from flask import Blueprint, jsonify, g, request, send_file, Response
from contextlib import closing
import database
from utils.audio_metadata import extract_m4b_metadata

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
            
            if current_time is None or total_duration is None:
                return jsonify({'error': 'Invalid progress data'}), 400

            progress_ms = int(float(current_time) * 1000)
            duration_ms = int(float(total_duration) * 1000)
            
            db.execute("""
                INSERT INTO audiobook_progress (user_id, task_id, progress_ms, duration_ms, playback_rate, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, task_id) DO UPDATE SET
                progress_ms = excluded.progress_ms,
                duration_ms = excluded.duration_ms,
                playback_rate = excluded.playback_rate,
                updated_at = CURRENT_TIMESTAMP
            """, (user_id, task_id, progress_ms, duration_ms, playback_rate))
            
            db.commit()
            return jsonify({'message': 'Progress and playback rate updated'})
        else:  # GET
            progress = db.execute("SELECT progress_ms, playback_rate FROM audiobook_progress WHERE user_id = ? AND task_id = ?", (user_id, task_id)).fetchone()
            task = db.execute("SELECT file_path FROM audiobook_tasks WHERE task_id = ?", (task_id,)).fetchone()

            if not task or not task['file_path'] or not os.path.exists(task['file_path']):
                return jsonify({'currentTime': 0, 'totalDuration': 0, 'playbackRate': 1.0})

            metadata = extract_m4b_metadata(task['file_path'])
            total_duration_sec = metadata.get('duration', 0) if metadata else 0
            saved_time_sec = 0
            saved_rate = 1.0

            if progress:
                if progress['progress_ms'] is not None:
                    try:
                        saved_time_sec = int(progress['progress_ms']) / 1000.0
                    except (ValueError, TypeError):
                        saved_time_sec = 0.0
                
                if progress['playback_rate'] is not None:
                    saved_rate = float(progress['playback_rate'])

                if total_duration_sec > 0 and saved_time_sec > total_duration_sec:
                    saved_time_sec = 0

            return jsonify({
                'currentTime': saved_time_sec,
                'totalDuration': total_duration_sec,
                'playbackRate': saved_rate
            })
