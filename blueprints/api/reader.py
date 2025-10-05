from flask import Blueprint, jsonify, g, request
from contextlib import closing
import sqlite3
import os
from anx_library import get_anx_user_dirs
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
reader_bp = Blueprint('reader', __name__, url_prefix='/api/reader')

@reader_bp.route('/progress/anx/<int:book_id>', methods=['GET'])
def get_anx_progress(book_id):
    if g.user is None:
        return jsonify({'error': 'Authentication required'}), 401

    dirs = get_anx_user_dirs(g.user.username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        return jsonify({'error': 'Anx library not found.'}), 404

    with closing(sqlite3.connect(dirs["db_path"])) as db:
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        cursor.execute("SELECT last_read_position, reading_percentage FROM tb_books WHERE id = ? AND is_deleted = 0", (book_id,))
        book = cursor.fetchone()

        if not book:
            return jsonify({'error': 'Book not found.'}), 404

        return jsonify({
            'cfi': book['last_read_position'],
            'percentage': book['reading_percentage']
        })

@reader_bp.route('/progress/anx/<int:book_id>', methods=['POST'])
def save_anx_progress(book_id):
    if g.user is None:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    cfi = data.get('cfi')
    percentage = data.get('percentage')
    reading_time_seconds = data.get('reading_time_seconds')

    if cfi is None or percentage is None:
        return jsonify({'error': 'CFI and percentage are required.'}), 400

    dirs = get_anx_user_dirs(g.user.username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        return jsonify({'error': 'Anx library not found.'}), 404

    with closing(sqlite3.connect(dirs["db_path"])) as db:
        cursor = db.cursor()
        current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')
        
        # Update reading progress
        cursor.execute("""
            UPDATE tb_books
            SET last_read_position = ?, reading_percentage = ?, update_time = ?
            WHERE id = ? AND is_deleted = 0
        """, (cfi, percentage, current_time, book_id))

        if cursor.rowcount == 0:
            logger.warning(f"Attempted to save progress for non-existent book_id {book_id} for user {g.user.username}")
            return jsonify({'error': 'Book not found or no update was made.'}), 404

        # Update reading time
        if reading_time_seconds and int(reading_time_seconds) > 0:
            date_str = datetime.utcnow().strftime('%Y-%m-%d')
            duration = int(reading_time_seconds)
            
            cursor.execute("SELECT id, reading_time FROM tb_reading_time WHERE book_id = ? AND date = ?", (book_id, date_str))
            existing_record = cursor.fetchone()

            if existing_record:
                new_reading_time = existing_record[1] + duration
                cursor.execute("UPDATE tb_reading_time SET reading_time = ? WHERE id = ?", (new_reading_time, existing_record[0]))
            else:
                cursor.execute("INSERT INTO tb_reading_time (book_id, date, reading_time) VALUES (?, ?, ?)", (book_id, date_str, duration))
            

        db.commit()

    return jsonify({'message': 'Progress and reading time saved successfully.'})