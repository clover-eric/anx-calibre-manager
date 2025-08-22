import bcrypt
import hashlib
import sqlite3
from flask import Blueprint, request, jsonify, g
from contextlib import closing
import database
from anx_library import get_anx_user_dirs
from utils import convert_koreader_progress
import os
import json
from datetime import datetime
import logging

koreader_bp = Blueprint('koreader', __name__, url_prefix='/koreader')

@koreader_bp.before_request
def log_request_info():
    logging.info('KOReader Sync Request:')
    logging.info('Headers: %s', request.headers)
    logging.info('Body: %s', request.get_data())

@koreader_bp.after_request
def log_response_info(response):
    logging.info('KOReader Sync Response:')
    logging.info('Status: %s', response.status)
    logging.info('Body: %s', response.get_data())
    return response

@koreader_bp.route('/', methods=['GET'])
def server_info():
    return jsonify({
        'server': 'AnxCalibreManager',
        'version': '1.0.0'
    })

def get_user_by_username(username):
    with closing(database.get_db()) as db:
        return db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

def get_user_from_auth_headers():
    username = request.headers.get('X-Auth-User')
    userkey = request.headers.get('X-Auth-Key')

    if not username or not userkey:
        return None

    user = get_user_by_username(username)
    if not user or not user['kosync_userkey']:
        return None

    if user['kosync_userkey'] == userkey:
        return user
    return None

@koreader_bp.route('/users/auth', methods=['GET'])
def auth_user():
    user = get_user_from_auth_headers()
    if user:
        return jsonify({'message': 'Authentication successful.'})
    else:
        return jsonify({'message': 'Invalid credentials.'}), 401

@koreader_bp.route('/users/create', methods=['POST'])
def create_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'message': 'Username and password are required.'}), 400

    user = get_user_by_username(username)
    if not user:
        return jsonify({'message': 'User not found in AnxCalibreManager.'}), 404

    password_hash = user['password_hash']
    if isinstance(password_hash, str):
        password_hash = password_hash.encode('utf-8')

    if bcrypt.checkpw(password.encode('utf-8'), password_hash):
        userkey = hashlib.md5(password.encode('utf-8')).hexdigest()
        with closing(database.get_db()) as db:
            db.execute("UPDATE users SET kosync_userkey = ? WHERE id = ?", (userkey, user['id']))
            db.commit()
        return jsonify({'userkey': userkey}), 201
    else:
        return jsonify({'message': 'Invalid credentials.'}), 401

@koreader_bp.route('/syncs/progress/<string:document>', methods=['GET'])
def get_progress(document):
    user = get_user_from_auth_headers()
    if not user:
        return jsonify({'message': 'Authentication required.'}), 401

    dirs = get_anx_user_dirs(user['username'])
    if not dirs or not os.path.exists(dirs["db_path"]):
        return jsonify({'message': 'Anx library not found.'}), 404

    with closing(sqlite3.connect(dirs["db_path"])) as db:
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tb_books WHERE file_md5 = ? AND is_deleted = 0", (document,))
        book = cursor.fetchone()

        if not book:
            return jsonify({'message': 'Document not found.'}), 404

        cfi = book['last_read_position']
        if not cfi:
            return jsonify({'message': 'No progress found for this document.'}), 404
        
        epub_path = os.path.join(dirs['workspace'], book['file_path'])
        xpointer, err = convert_koreader_progress('from-cfi', epub_path, cfi)

        if err:
            return jsonify({'message': f'Failed to convert progress: {err}'}), 500

        update_time_str = book['update_time']
        dt_object = None
        try:
            dt_object = datetime.strptime(update_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError:
            try:
                dt_object = datetime.strptime(update_time_str, '%Y-%m-%dT%H:%M:%S.%f')
            except ValueError:
                return jsonify({'message': f'Failed to parse timestamp: {update_time_str}'}), 500
        
        return jsonify({
            'percentage': book['reading_percentage'],
            'progress': xpointer,
            'device': 'AnxCalibreManager',
            'timestamp': int(dt_object.timestamp())
        })

@koreader_bp.route('/syncs/progress', methods=['PUT'])
def update_progress():
    user = get_user_from_auth_headers()
    if not user:
        return jsonify({'message': 'Authentication required.'}), 401

    data = request.get_json()
    document_digest = data.get('document')
    xpointer = data.get('progress')
    percentage = data.get('percentage')

    if not document_digest or not xpointer or percentage is None:
        return jsonify({'message': 'Document, progress and percentage are required.'}), 400

    dirs = get_anx_user_dirs(user['username'])
    if not dirs or not os.path.exists(dirs["db_path"]):
        return jsonify({'message': 'Anx library not found.'}), 404

    with closing(sqlite3.connect(dirs["db_path"])) as db:
        db.row_factory = sqlite3.Row
        cursor = db.cursor()
        cursor.execute("SELECT * FROM tb_books WHERE file_md5 = ? AND is_deleted = 0", (document_digest,))
        book = cursor.fetchone()

        if not book:
            return jsonify({'message': 'Document not found.'}), 404

        epub_path = os.path.join(dirs['workspace'], book['file_path'])
        cfi, err = convert_koreader_progress('to-cfi', epub_path, xpointer)

        if err:
            return jsonify({'message': f'Failed to convert progress: {err}'}), 500

        current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')
        cursor.execute("""
            UPDATE tb_books
            SET last_read_position = ?, reading_percentage = ?, update_time = ?
            WHERE id = ?
        """, (cfi, percentage, current_time, book['id']))
        db.commit()

        return jsonify({'message': 'Progress updated successfully.'})
