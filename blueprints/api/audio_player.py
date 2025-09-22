import os
from flask import Blueprint, jsonify, g, request, send_file, Response
from contextlib import closing
import database
from utils.audio_metadata import extract_m4b_metadata

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
                WHERE user_id = ? AND status = 'success'
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

    return send_file(task['file_path'], mimetype='audio/mp4')

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
            
            if current_time is None or total_duration is None:
                return jsonify({'error': 'Invalid progress data'}), 400

            db.execute("""
                INSERT INTO audiobook_progress (user_id, task_id, current_time, total_duration)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, task_id) DO UPDATE SET
                current_time = excluded.current_time,
                total_duration = excluded.total_duration,
                updated_at = CURRENT_TIMESTAMP
            """, (user_id, task_id, current_time, total_duration))
            db.commit()
            return jsonify({'message': 'Progress updated'})
        else: # GET
            progress = db.execute("SELECT current_time, total_duration FROM audiobook_progress WHERE user_id = ? AND task_id = ?", (user_id, task_id)).fetchone()
            if progress:
                return jsonify({'currentTime': progress['current_time'], 'totalDuration': progress['total_duration']})
            else:
                return jsonify({'currentTime': 0, 'totalDuration': 0})
