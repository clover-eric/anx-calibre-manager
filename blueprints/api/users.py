import bcrypt
import hashlib
import shutil
import logging
import os
from flask import Blueprint, request, jsonify, g
from flask_babel import gettext as _
from contextlib import closing
import database
from anx_library import initialize_anx_user_data, get_anx_user_dirs
from utils.decorators import admin_required_api

users_bp = Blueprint('users', __name__, url_prefix='/api')

@users_bp.route('/users', methods=['GET'])
@admin_required_api
def get_users():
    with closing(database.get_db()) as db:
        users = db.execute('SELECT id, username, role FROM users').fetchall()
        return jsonify([dict(u) for u in users])

@users_bp.route('/users', methods=['POST'])
@admin_required_api
def add_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    if not username or not password:
        return jsonify({'error': _('Username and password are required.')}), 400

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    kosync_userkey = hashlib.md5(password.encode('utf-8')).hexdigest()
    with closing(database.get_db()) as db:
        try:
            db.execute(
                "INSERT INTO users (username, password_hash, role, kosync_userkey) VALUES (?, ?, ?, ?)",
                (username, hashed_pw, role, kosync_userkey)
            )
            db.commit()
            
            # Initialize Anx data structure for the new user
            success, message = initialize_anx_user_data(username)
            if not success:
                # Log the error, but don't fail the whole request since the user was created.
                logging.error(f"Failed to initialize Anx data for new user {username}: {message}")
                return jsonify({'message': _('User added successfully, but failed to initialize Anx directory: %(message)s', message=message)}), 201

            return jsonify({'message': _('User added and initialized successfully.')}), 201
        except database.sqlite3.IntegrityError:
            return jsonify({'error': _('Username already exists.')}), 409


@users_bp.route('/users', methods=['PUT'])
@admin_required_api
def update_user():
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')

    if not user_id or not username:
        return jsonify({'error': _('User ID and username are required.')}), 400

    with closing(database.get_db()) as db:
        if password:
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            kosync_userkey = hashlib.md5(password.encode('utf-8')).hexdigest()
            db.execute(
                'UPDATE users SET username = ?, password_hash = ?, role = ?, kosync_userkey = ? WHERE id = ?',
                (username, hashed_pw, role, kosync_userkey, user_id)
            )
        else:
            db.execute(
                'UPDATE users SET username = ?, role = ? WHERE id = ?',
                (username, role, user_id)
            )
        db.commit()
        return jsonify({'message': _('User updated successfully.')})

@users_bp.route('/users', methods=['DELETE'])
@admin_required_api
def delete_user():
    data = request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': _('User ID is required.')}), 400

    with closing(database.get_db()) as db:
        # First, get the username to delete their data directory
        user_to_delete = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
        
        if user_to_delete:
            username = user_to_delete['username']
            dirs = get_anx_user_dirs(username)
            if dirs and dirs.get('user_root') and os.path.exists(dirs['user_root']):
                try:
                    shutil.rmtree(dirs['user_root'])
                    logging.info(f"Successfully deleted WebDAV directory for user {username}")
                except Exception as e:
                    logging.error(f"Failed to delete WebDAV directory for user {username}: {e}")
                    # Don't block DB deletion, but return an error message
                    return jsonify({'error': _('Error deleting user data directory: %(error)s', error=e)}), 500
        
        # Now, delete the user from the database
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        return jsonify({'message': _('User and their data have been successfully deleted.')})