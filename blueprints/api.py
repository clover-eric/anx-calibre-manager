import json
import base64
import io
import os
import pyotp
import qrcode
import requests
import bcrypt
import logging
import re
import secrets
import shutil
import subprocess
import tempfile
import mimetypes
import hashlib
from flask import Blueprint, request, jsonify, g, session, send_file, send_from_directory
from contextlib import closing
from werkzeug.utils import secure_filename
import sqlite3
import uuid
from functools import lru_cache
from urllib.parse import quote

import database
import config_manager
from anx_library import (
    process_anx_import_folder, 
    update_anx_book_metadata, 
    delete_anx_book, 
    get_anx_user_dirs,
    initialize_anx_user_data
)
from .main import download_calibre_book, get_calibre_auth, get_calibre_book_details, download_calibre_cover
from epub_fixer import fix_epub_for_kindle
from utils import random_english_text, create_calibre_mail, safe_title, safe_author

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Helper for decorators
def admin_required_api(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or not g.user.is_admin:
            return jsonify({'error': '需要管理员权限。'}), 403
        return f(*args, **kwargs)
    return decorated_function

def maintainer_required_api(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or not g.user.is_maintainer:
            return jsonify({'error': '需要维护者或管理员权限。'}), 403
        return f(*args, **kwargs)
    return decorated_function

def send_email_with_config(to_address, subject, body, config, attachment_content=None, attachment_filename=None):
    import smtplib
    
    logging.info(f"Attempting to send email to {to_address} via {config.get('SMTP_SERVER')}:{config.get('SMTP_PORT')}")
    
    if not all([config.get('SMTP_SERVER'), config.get('SMTP_PORT'), config.get('SMTP_USERNAME')]):
        logging.error("SMTP settings are incomplete.")
        return False, "SMTP 未完全配置。"
        
    from_address = config['SMTP_USERNAME']
    
    attachment_type = None
    if attachment_filename:
        attachment_type, _ = mimetypes.guess_type(attachment_filename)
        if attachment_type is None:
            # Fallback for unknown types
            attachment_type = 'application/octet-stream'
            logging.warning(f"Could not guess mimetype for {attachment_filename}, falling back to {attachment_type}")

    # Use Calibre's mail creation logic
    msg = create_calibre_mail(
        from_=from_address,
        to=to_address,
        subject=subject,
        text=body,
        attachment_data=attachment_content,
        attachment_name=attachment_filename,
        attachment_type=attachment_type
    )
        
    try:
        server = None
        encryption = config.get('SMTP_ENCRYPTION', 'none').lower()
        port = int(config['SMTP_PORT'])
        
        logging.info(f"Connecting to SMTP server with encryption: {encryption} on port {port}")
        if encryption == 'ssl':
            server = smtplib.SMTP_SSL(config['SMTP_SERVER'], port)
        else:
            server = smtplib.SMTP(config['SMTP_SERVER'], port)
            if encryption == 'starttls':
                logging.info("Starting TLS...")
                server.starttls()
        
        #server.set_debuglevel(1) # Log SMTP conversation
        
        if config.get('SMTP_PASSWORD'):
            logging.info(f"Logging in as {config['SMTP_USERNAME']}...")
            server.login(config['SMTP_USERNAME'], config['SMTP_PASSWORD'])
            
        logging.info("Sending email...")
        server.send_message(msg, from_address, [to_address])
        logging.info("Email sent successfully.")
        server.quit()
        return True, "邮件发送成功。"
    except Exception as e:
        logging.error(f"Failed to send email: {e}", exc_info=True)
        return False, f"邮件发送失败: {e}"

@api_bp.route('/download_anx_book/<int:book_id>', methods=['GET'])
def download_anx_book_api(book_id):
    dirs = get_anx_user_dirs(g.user.username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        return jsonify({'error': 'Anx 数据库未找到。'}), 404
        
    try:
        with closing(sqlite3.connect(dirs["db_path"])) as db:
            db.row_factory = sqlite3.Row
            cursor = db.cursor()
            cursor.execute("SELECT file_path FROM tb_books WHERE id = ?", (book_id,))
            book_row = cursor.fetchone()
            if not book_row or not book_row['file_path']:
                return jsonify({'error': f'未找到 ID 为 {book_id} 的书籍文件。'}), 404
            
            data_dir = dirs["workspace"]
            return send_from_directory(data_dir, book_row['file_path'], as_attachment=True)
            
    except Exception as e:
        print(f"Error downloading anx book {book_id} for user {g.user.username}: {e}")
        return jsonify({'error': f'下载书籍时出错: {e}'}), 500


@api_bp.route('/users', methods=['GET'])
@admin_required_api
def get_users():
    with closing(database.get_db()) as db:
        users = db.execute('SELECT id, username, role FROM users').fetchall()
        return jsonify([dict(u) for u in users])

@api_bp.route('/users', methods=['POST'])
@admin_required_api
def add_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    if not username or not password:
        return jsonify({'error': '用户名和密码是必填项。'}), 400

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
                return jsonify({'message': f'用户已成功添加，但初始化 Anx 目录失败: {message}'}), 201

            return jsonify({'message': '用户已成功添加并初始化。'}), 201
        except database.sqlite3.IntegrityError:
            return jsonify({'error': '用户名已存在。'}), 409


@api_bp.route('/users', methods=['PUT'])
@admin_required_api
def update_user():
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')

    if not user_id or not username:
        return jsonify({'error': '用户 ID 和用户名是必填项。'}), 400

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
        return jsonify({'message': '用户已成功更新。'})

@api_bp.route('/users', methods=['DELETE'])
@admin_required_api
def delete_user():
    data = request.get_json()
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': '用户 ID 是必填项。'}), 400

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
                    return jsonify({'error': f'删除用户数据目录时出错: {e}'}), 500
        
        # Now, delete the user from the database
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        return jsonify({'message': '用户及其数据已成功删除。'})


@api_bp.route('/user_settings', methods=['GET', 'POST'])
def user_settings_api():
    if request.method == 'POST':
        data = request.get_json()
        with closing(database.get_db()) as db:
            if 'new_password' in data and data['new_password']:
                new_password = data['new_password']
                hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
                kosync_userkey = hashlib.md5(new_password.encode('utf-8')).hexdigest()
                db.execute('UPDATE users SET password_hash = ?, kosync_userkey = ? WHERE id = ?', (hashed, kosync_userkey, g.user.id))
            priority_list = [v.strip() for v in data.get('send_format_priority', '').split(',')]
            # Handle checkbox boolean value
            force_conversion = data.get('force_epub_conversion', False)
            stats_enabled = data.get('stats_enabled', False)
            stats_public = data.get('stats_public', False)
            db.execute('UPDATE users SET kindle_email = ?, send_format_priority = ?, theme = ?, force_epub_conversion = ?, stats_enabled = ?, stats_public = ? WHERE id = ?',
                       (data.get('kindle_email'), json.dumps(priority_list), data.get('theme', 'auto'), force_conversion, stats_enabled, stats_public, g.user.id))
            db.commit()
        return jsonify({'message': '用户设置已更新。'})
    else: # GET
        priority_str = g.user.send_format_priority
        if priority_str:
            priority = json.loads(priority_str)
        else:
            default_priority_str = config_manager.config.get('DEFAULT_FORMAT_PRIORITY', 'azw3,mobi,epub,fb2,txt,pdf')
            priority = [item.strip() for item in default_priority_str.split(',')]
        return jsonify({
            'username': g.user.username,
            'kindle_email': g.user.kindle_email,
            'send_format_priority': priority,
            'has_2fa': bool(g.user.otp_secret),
            'smtp_from_address': config_manager.config.get('SMTP_USERNAME'),
            'theme': g.user.theme or 'auto',
            'force_epub_conversion': bool(g.user.force_epub_conversion),
            'stats_enabled': bool(g.user.stats_enabled),
            'stats_public': bool(g.user.stats_public)
        })

@api_bp.route('/global_settings', methods=['GET', 'POST'])
@admin_required_api
def global_settings_api():
    if request.method == 'POST':
        data = request.get_json()
        # Handle checkbox boolean value
        data['CALIBRE_ADD_DUPLICATES'] = data.get('CALIBRE_ADD_DUPLICATES') == 'true'
        config_manager.save_config(data)
        return jsonify({'message': '全局设置已更新。'})
    else: # GET
        return jsonify(config_manager.config)

@api_bp.route('/test_smtp', methods=['POST'])
@admin_required_api
def test_smtp_api():
    data = request.get_json()
    to_address = data.get('to_address')
    if not to_address:
        return jsonify({'error': '测试收件箱地址是必填项。'}), 400
    
    test_config = {
        'SMTP_SERVER': data.get('SMTP_SERVER'),
        'SMTP_PORT': data.get('SMTP_PORT'),
        'SMTP_USERNAME': data.get('SMTP_USERNAME'),
        'SMTP_PASSWORD': data.get('SMTP_PASSWORD'),
        'SMTP_ENCRYPTION': data.get('SMTP_ENCRYPTION'),
    }
    
    subject = "Anx Calibre Manager SMTP Test"
    body = "This is a test email from Anx Calibre Manager. If you received this, your SMTP settings are correct!"
    
    success, message = send_email_with_config(to_address, subject, body, test_config)
    
    if success:
        return jsonify({'message': f"测试邮件已成功发送到 {to_address}。"})
    else:
        return jsonify({'error': f"发送测试邮件失败: {message}"}), 500

@api_bp.route('/2fa/setup', methods=['POST'])
def setup_2fa():
    if g.user.otp_secret: return jsonify({'error': '2FA 已启用。'}), 400
    secret = pyotp.random_base32()
    session['2fa_secret_pending'] = secret
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=g.user.username, issuer_name='AnxCalibreManager')
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf)
    qr_code_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return jsonify({'secret': secret, 'qr_code': f'data:image/png;base64,{qr_code_b64}'})

@api_bp.route('/2fa/verify', methods=['POST'])
def verify_2fa():
    otp_code = request.json.get('otp_code')
    secret = session.get('2fa_secret_pending')
    if not secret: return jsonify({'error': '未找到待处理的 2FA 设置请求。'}), 400
    if pyotp.TOTP(secret).verify(otp_code):
        with closing(database.get_db()) as db:
            db.execute('UPDATE users SET otp_secret = ? WHERE id = ?', (secret, g.user.id))
            db.commit()
        session.pop('2fa_secret_pending', None)
        return jsonify({'message': '2FA 已成功启用！'})
    else:
        return jsonify({'error': '验证码错误。'}), 400

@api_bp.route('/2fa/disable', methods=['POST'])
def disable_2fa():
    with closing(database.get_db()) as db:
        db.execute('UPDATE users SET otp_secret = NULL WHERE id = ?', (g.user.id,))
        db.commit()
    return jsonify({'message': '2FA 已禁用。'})

def _get_processed_epub_for_book(book_id, user_dict, filename_format='title - author'):
    """
    Core logic to get a processed EPUB for a book.
    It handles downloading, converting (if necessary), and fixing the EPUB.
    Returns a tuple: (content, filename, needs_conversion_flag) or (None, None, None) on error.
    """
    details = get_calibre_book_details(book_id)
    if not details:
        logging.error(f"Could not get details for book_id {book_id}")
        return None, None, False

    available_formats = [f.lower() for f in details.get('formats', [])]
    needs_conversion = False
    
    with tempfile.TemporaryDirectory() as temp_dir:
        epub_to_process_path = None
        
        # Check if EPUB already exists
        if 'epub' in available_formats:
            logging.info(f"Book ID {book_id} has EPUB format. Downloading directly.")
            content, filename = download_calibre_book(book_id, 'epub')
            if not content:
                logging.error(f"Failed to download existing EPUB for book_id {book_id}")
                return None, None, False
            
            epub_to_process_path = os.path.join(temp_dir, filename)
            with open(epub_to_process_path, 'wb') as f:
                f.write(content)
        else:
            # If no EPUB, convert from another format
            needs_conversion = True
            if not shutil.which('ebook-converter'):
                logging.error("ebook-converter not found, but conversion is needed.")
                # This case will be handled by the calling function to return a specific error message
                return None, "CONVERTER_NOT_FOUND", False

            priority_str = user_dict.get('send_format_priority') or '[]'
            priority = json.loads(priority_str)
            format_to_convert = next((f for f in priority if f.lower() in available_formats), available_formats[0] if available_formats else None)

            if not format_to_convert:
                logging.error(f"No suitable format found to convert from for book_id {book_id}")
                return None, None, False

            logging.info(f"Book ID {book_id} needs conversion. Converting from {format_to_convert}.")
            original_content, original_filename = download_calibre_book(book_id, format_to_convert)
            if not original_content:
                logging.error(f"Failed to download source format {format_to_convert} for book_id {book_id}")
                return None, None, False

            source_path = os.path.join(temp_dir, original_filename)
            with open(source_path, 'wb') as f:
                f.write(original_content)

            base_name, _ = os.path.splitext(original_filename)
            epub_filename = f"{base_name}.epub"
            dest_path = os.path.join(temp_dir, epub_filename)

            try:
                logging.info(f"Running ebook-converter: {source_path} -> {dest_path}")
                subprocess.run(
                    ['ebook-converter', source_path, dest_path],
                    capture_output=True, text=True, check=True, timeout=300
                )
                epub_to_process_path = dest_path
            except Exception as e:
                logging.error(f"An unexpected error occurred during conversion for book_id {book_id}: {e}")
                return None, None, False

        if not epub_to_process_path or not os.path.exists(epub_to_process_path):
            logging.error(f"Could not find EPUB to process for book_id {book_id}")
            return None, None, False

        # --- Fix the EPUB ---
        logging.info(f"Processing EPUB with kindle-epub-fixer: {epub_to_process_path}")
        fixed_epub_path = fix_epub_for_kindle(epub_to_process_path, force_language='zh')
        
        with open(fixed_epub_path, 'rb') as f:
            content_to_send = f.read()

        # Sanitize title and authors for use in filename
        title = safe_title(details.get('title', 'Untitled'))
        
        if filename_format == 'title':
            filename_to_send = f"{title}.epub"
        else: # Default to 'title - author'
            authors = safe_author(" & ".join(details.get('authors', [])))
            if authors:
                filename_to_send = f"{title} - {authors}.epub"
            else:
                filename_to_send = f"{title}.epub"

        return content_to_send, filename_to_send, needs_conversion


@api_bp.route('/download_book/<int:book_id>', methods=['GET'])
def download_book_api(book_id):
    if g.user.force_epub_conversion:
        logging.info(f"Force EPUB conversion is ON for user {g.user.username} for book {book_id}")
        user_dict = {
        'username': g.user.username,
        'kindle_email': g.user.kindle_email,
        'send_format_priority': g.user.send_format_priority,
        'force_epub_conversion': g.user.force_epub_conversion
    }
        content, filename, _ = _get_processed_epub_for_book(book_id, user_dict)
        
        if filename == 'CONVERTER_NOT_FOUND':
            return jsonify({'error': '此书需要转换为 EPUB 格式，但当前环境缺少 `ebook-converter` 工具。'}), 412
        if content and filename:
            return send_file(io.BytesIO(content), as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': '无法处理或转换书籍。'}), 500
    else:
        # Original logic
        details = get_calibre_book_details(book_id)
        if not details:
            return jsonify({'error': '找不到书籍详情。'}), 404

        available_formats = [f.lower() for f in details.get('formats', [])]
        priority = json.loads(g.user.send_format_priority or '[]')
        
        format_to_download = next((p_format.lower() for p_format in priority if p_format.lower() in available_formats), None)
        
        if not format_to_download:
            if available_formats:
                format_to_download = available_formats[0]
            else:
                return jsonify({'error': '该书籍没有任何可用格式。'}), 400

        content, filename = download_calibre_book(book_id, format_to_download)
        if content:
            return send_file(io.BytesIO(content), as_attachment=True, download_name=filename)
        
        return jsonify({'error': '无法下载书籍。'}), 404

def _send_to_kindle_logic(user_dict, book_id):
    """Core logic to send a Calibre book to a user's Kindle. Expects user as a dict."""
    if not user_dict.get('kindle_email'):
        return {'success': False, 'error': '请先在用户设置中配置您的 Kindle 邮箱。'}

    # Kindle always requires a processed EPUB
    content_to_send, filename_to_send, needs_conversion = _get_processed_epub_for_book(book_id, user_dict, filename_format='title')

    if filename_to_send == 'CONVERTER_NOT_FOUND':
        return {'success': False, 'error': '此书需要转换为 EPUB 格式，但当前环境缺少 `ebook-converter` 工具。请将其安装到系统 PATH 中。', 'code': 'CONVERTER_NOT_FOUND'}
    
    if not content_to_send:
        return {'success': False, 'error': '无法获取或处理书籍的 EPUB 文件。'}

    # Per Calibre's logic for Kindle, use random English text for subject and body
    subject = random_english_text(min_words_per_sentence=3, max_words_per_sentence=9, max_num_sentences=1).rstrip('.')
    body = random_english_text()
    success, message = send_email_with_config(
        user_dict['kindle_email'], 
        subject, 
        body, 
        config_manager.config, # Use the global config
        content_to_send, 
        filename_to_send
    )

    if success:
        return {'success': True, 'message': message, 'needs_conversion': needs_conversion}
    else:
        return {'success': False, 'error': message}

@api_bp.route('/send_to_kindle/<int:book_id>', methods=['POST'])
def send_to_kindle_api(book_id):
    user_dict = {
        'username': g.user.username,
        'kindle_email': g.user.kindle_email,
        'send_format_priority': g.user.send_format_priority,
        'force_epub_conversion': g.user.force_epub_conversion
    }
    result = _send_to_kindle_logic(user_dict, book_id)
    if result['success']:
        return jsonify({'message': result['message'], 'needs_conversion': result.get('needs_conversion', False)})
    else:
        if result.get('code') == 'CONVERTER_NOT_FOUND':
            return jsonify({'error': result['error']}), 412 # Precondition Failed
        if 'Kindle 邮箱' in result.get('error', ''):
            return jsonify({'error': result['error']}), 400
        return jsonify({'error': result['error']}), 500

def _push_calibre_to_anx_logic(user_dict, book_id):
    """Core logic to push a Calibre book to a user's Anx library. Expects user as a dict."""
    book_content, book_filename = None, None

    if user_dict.get('force_epub_conversion'):
        logging.info(f"Force EPUB conversion is ON for user {user_dict['username']} for book {book_id} push to Anx.")
        content, filename, _ = _get_processed_epub_for_book(book_id, user_dict)
        if filename == 'CONVERTER_NOT_FOUND':
            return {'success': False, 'error': '此书需要转换为 EPUB 格式，但当前环境缺少 `ebook-converter` 工具。'}
        book_content, book_filename = content, filename
    else:
        # Original logic
        details = get_calibre_book_details(book_id)
        if not details:
            return {'success': False, 'error': '找不到书籍详情。'}
        available_formats = [f.lower() for f in details.get('formats', [])]
        priority_str = user_dict.get('send_format_priority') or '[]'
        priority = json.loads(priority_str)
        format_to_push = next((f for f in priority if f.lower() in available_formats), available_formats[0] if available_formats else None)

        if not format_to_push:
            return {'success': False, 'error': '未找到可推送的格式。'}
        
        book_content, book_filename = download_calibre_book(book_id, format_to_push)

    if not book_content:
        return {'success': False, 'error': '下载或处理书籍时出错。'}

    cover_content, _ = download_calibre_cover(book_id)

    dirs = get_anx_user_dirs(user_dict['username'])
    if not dirs:
        return {'success': False, 'error': '用户目录未配置。'}

    import_dir = dirs["import"]
    os.makedirs(import_dir, exist_ok=True)

    book_file_path = os.path.join(import_dir, book_filename)
    with open(book_file_path, 'wb') as f:
        f.write(book_content)

    if cover_content:
        base_name, _ = os.path.splitext(book_filename)
        cover_filename = f"{base_name}.jpg"
        cover_file_path = os.path.join(import_dir, cover_filename)
        with open(cover_file_path, 'wb') as f:
            f.write(cover_content)

    result = process_anx_import_folder(user_dict['username'])
    
    return {
        'success': True,
        'message': f"书籍 '{book_filename}' 推送完成。 "
                   f"已处理: {result.get('processed', 0)}, "
                   f"已跳过: {result.get('skipped', 0)}."
    }

@api_bp.route('/push_to_anx/<int:book_id>', methods=['POST'])
def push_to_anx_api(book_id):
    user_dict = {
        'username': g.user.username,
        'kindle_email': g.user.kindle_email,
        'send_format_priority': g.user.send_format_priority,
        'force_epub_conversion': g.user.force_epub_conversion
    }
    result = _push_calibre_to_anx_logic(user_dict, book_id)
    if result['success']:
        return jsonify({'message': result['message']})
    else:
        return jsonify({'error': result['error']}), 500


@api_bp.route('/upload_to_calibre', methods=['POST'])
def upload_to_calibre_api():
    if 'books' not in request.files:
        return jsonify({'error': '没有文件部分。'}), 400
    
    files = request.files.getlist('books')
    if not files or files[0].filename == '':
        return jsonify({'error': '没有选择文件。'}), 400

    results = []
    for file in files:
        if file:
            filename = file.filename
            
            job_id = str(uuid.uuid4())
            
            library_id = config_manager.config.get('CALIBRE_DEFAULT_LIBRARY_ID', 'Calibre_Library') 
            
            add_duplicates = config_manager.config.get('CALIBRE_ADD_DUPLICATES', False)
            add_duplicates_flag = 'y' if add_duplicates else 'n' 

            encoded_filename = requests.utils.quote(filename) 

            url = f"{config_manager.config['CALIBRE_URL']}/cdb/add-book/{job_id}/{add_duplicates_flag}/{encoded_filename}/{library_id}"
            
            try:
                headers = {'Content-Type': file.mimetype} if file.mimetype else {}
                
                # We must read the file content into memory before passing it to requests,
                # as the file object will be closed after the first iteration.
                file.seek(0)
                file_content = file.read()
                
                response = requests.post(url, data=file_content, auth=get_calibre_auth(), headers=headers)
                response.raise_for_status()
                
                res_json = response.json()
                if res_json.get('book_id'):
                    results.append({'success': True, 'filename': filename, 'message': f"书籍 '{res_json.get('title')}' 已成功上传, ID: {res_json['book_id']}."})
                else:
                    results.append({'success': False, 'filename': filename, 'error': '上传失败，书籍可能已存在。', 'details': res_json.get('duplicates')})
            except requests.exceptions.HTTPError as e:
                error_message = f"Calibre 服务器返回错误: {e.response.status_code} - {e.response.text}"
                results.append({'success': False, 'filename': filename, 'error': error_message})
            except requests.exceptions.RequestException as e:
                results.append({'success': False, 'filename': filename, 'error': f'连接 Calibre 服务器出错: {e}'})
    
    return jsonify(results)

@api_bp.route('/update_calibre_book/<int:book_id>', methods=['POST'])
@maintainer_required_api
def update_calibre_book_api(book_id):
    data = request.get_json()
    
    # Prepare the 'changes' dictionary
    changes = {
        'title': data.get('title'),
        'authors': data.get('authors'),
        'rating': data.get('rating'),
        'comments': data.get('comments'),
        'publisher': data.get('publisher'),
        'tags': data.get('tags'),
        '#library': data.get('#library'),
        '#readdate': data.get('#readdate'),
        'pubdate': data.get('pubdate')
    }
    
    # Filter out any keys with None values, but keep empty strings as they represent a deliberate clearing of a field.
    changes = {k: v for k, v in changes.items() if v is not None}

    # If authors is a string, split it into a list as required by Calibre
    if 'authors' in changes and isinstance(changes['authors'], str):
        changes['authors'] = [a.strip() for a in changes['authors'].split('&')]

    # Handle date fields: Calibre expects a special string for undefined/cleared dates.
    UNDEFINED_DATE_ISO = '0101-01-01T00:00:00+00:00'
    for date_field in ['pubdate', '#readdate']:
        if date_field in changes and changes[date_field] == '':
            changes[date_field] = UNDEFINED_DATE_ISO

    if not changes:
        return jsonify({'error': '没有提供任何要更新的字段。'}), 400

    payload = {'changes': changes}
    
    library_id = config_manager.config.get('CALIBRE_DEFAULT_LIBRARY_ID', 'Calibre_Library')
    url = f"{config_manager.config['CALIBRE_URL']}/cdb/set-fields/{book_id}/{library_id}"
    
    try:
        response = requests.post(url, json=payload, auth=get_calibre_auth())
        response.raise_for_status()
        
        try:
            result = response.json()
            # The cdb endpoint returns the updated metadata for the book
            if str(book_id) in result:
                return jsonify({'message': '元数据更新成功。', 'updated_metadata': result[str(book_id)]})
            else:
                 return jsonify({'error': 'Calibre 返回了未知响应。', 'details': result}), 500
        except json.JSONDecodeError:
            return jsonify({'error': f'Calibre 返回了无效的 JSON 响应: {response.text}'}), 500
                
    except requests.exceptions.HTTPError as e:
        return jsonify({'error': f'连接 Calibre 服务器出错: {e.response.status_code} {e.response.reason}', 'details': e.response.text}), 500
    except requests.exceptions.RequestException as e:
        return jsonify({'error': f'连接 Calibre 服务器出错: {e}'}), 500

@api_bp.route('/edit_anx_metadata', methods=['POST'])
def edit_anx_metadata_api():
    data = request.get_json()
    book_id = data.pop('id', None)
    if not book_id:
        return jsonify({'error': '缺少书籍 ID。'}), 400

    success, message = update_anx_book_metadata(g.user.username, book_id, data)

    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 500

@api_bp.route('/delete_anx_book/<int:book_id>', methods=['DELETE'])
def delete_anx_book_api(book_id):
    success, message = delete_anx_book(g.user.username, book_id)
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 500

# --- MCP Token Management ---
@api_bp.route('/mcp_tokens', methods=['GET'])
def get_mcp_tokens():
    with closing(database.get_db()) as db:
        tokens = db.execute('SELECT id, token, created_at FROM mcp_tokens WHERE user_id = ?', (g.user.id,)).fetchall()
        return jsonify([dict(row) for row in tokens])

@api_bp.route('/mcp_tokens', methods=['POST'])
def create_mcp_token():
    new_token = secrets.token_hex(16)
    with closing(database.get_db()) as db:
        db.execute('INSERT INTO mcp_tokens (user_id, token) VALUES (?, ?)', (g.user.id, new_token))
        db.commit()
    return jsonify({'message': '新令牌已生成。', 'token': new_token})

@api_bp.route('/mcp_tokens/<int:token_id>', methods=['DELETE'])
def delete_mcp_token(token_id):
    with closing(database.get_db()) as db:
        # Ensure the token belongs to the current user before deleting
        db.execute('DELETE FROM mcp_tokens WHERE id = ? AND user_id = ?', (token_id, g.user.id))
        db.commit()
    return jsonify({'message': '令牌已删除。'})


# --- Completions API ---
@lru_cache(maxsize=16)
def get_all_items_for_field(library_id, field):
    """
    Fetches all items for a given field from the Calibre server.
    Results are cached to avoid repeated requests for the same field.
    """
    encoded_field = quote(field)
    url = f"{config_manager.config['CALIBRE_URL']}/interface-data/field-names/{encoded_field}?library_id={library_id}"
    try:
        response = requests.get(url, auth=get_calibre_auth())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"Could not fetch completions for field '{field}': {e}")
        return []

@api_bp.route('/calibre/completions', methods=['GET'])
@maintainer_required_api
def calibre_completions_api():
    field = request.args.get('field')
    query = request.args.get('query', '').lower()
    
    if not field:
        return jsonify({'error': 'Field parameter is required.'}), 400

    supported_fields = ['authors', 'publisher', 'tags', '#library']
    if field not in supported_fields:
        return jsonify({'error': f"Completions not supported for field: {field}"}), 400

    library_id = config_manager.config.get('CALIBRE_DEFAULT_LIBRARY_ID', 'Calibre_Library')
    
    all_items = get_all_items_for_field(library_id, field)
    
    if not query:
        # Return a small subset if query is empty
        return jsonify(all_items[:20])

    filtered_items = [item for item in all_items if query in item.lower()]
    
    return jsonify(filtered_items[:20]) # Return max 20 results

@api_bp.route('/download_koreader_plugin', methods=['GET'])
def download_koreader_plugin():
    # The zip file is created in the static directory by the Dockerfile
    return send_from_directory('static', 'anx-calibre-manager-koreader-plugin.zip', as_attachment=True)
