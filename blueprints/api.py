import json
import base64
import io
import os
import pyotp
import qrcode
import requests
import bcrypt
import logging
from flask import Blueprint, request, jsonify, g, session, send_file, send_from_directory
from contextlib import closing
from werkzeug.utils import secure_filename
import sqlite3
import uuid

import database
import config_manager
from anx_library import process_anx_import_folder, update_anx_book_metadata, delete_anx_book, get_anx_user_dirs
from .main import download_calibre_book, send_email, get_calibre_auth, get_calibre_book_details, download_calibre_cover

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

def send_email_with_config(to_address, subject, body, config, attachment_content=None, attachment_filename=None):
    import smtplib
    from email.mime.application import MIMEApplication
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    
    logging.info(f"Attempting to send email to {to_address} via {config.get('SMTP_SERVER')}:{config.get('SMTP_PORT')}")
    
    if not all([config.get('SMTP_SERVER'), config.get('SMTP_PORT'), config.get('SMTP_USERNAME')]):
        logging.error("SMTP settings are incomplete.")
        return False, "SMTP 未完全配置。"
        
    msg = MIMEMultipart()
    msg['From'] = config['SMTP_USERNAME']
    msg['To'] = to_address
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    if attachment_content and attachment_filename:
        part = MIMEApplication(attachment_content, Name=attachment_filename)
        part['Content-Disposition'] = f'attachment; filename="{attachment_filename}"'
        msg.attach(part)
        
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
        
        server.set_debuglevel(1) # Log SMTP conversation
        
        if config.get('SMTP_PASSWORD'):
            logging.info(f"Logging in as {config['SMTP_USERNAME']}...")
            server.login(config['SMTP_USERNAME'], config['SMTP_PASSWORD'])
            
        logging.info("Sending email...")
        server.sendmail(config['SMTP_USERNAME'], to_address, msg.as_string())
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
        users = db.execute('SELECT id, username, is_admin FROM users').fetchall()
        return jsonify([dict(u) for u in users])

@api_bp.route('/users', methods=['POST'])
@admin_required_api
def add_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)
    if not username or not password:
        return jsonify({'error': '用户名和密码是必填项。'}), 400

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    with closing(database.get_db()) as db:
        try:
            db.execute(
                "INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                (username, hashed_pw, is_admin)
            )
            db.commit()
            return jsonify({'message': '用户已成功添加。'}), 201
        except database.sqlite3.IntegrityError:
            return jsonify({'error': '用户名已存在。'}), 409


@api_bp.route('/users', methods=['PUT'])
@admin_required_api
def update_user():
    data = request.get_json()
    user_id = data.get('user_id')
    username = data.get('username')
    password = data.get('password')
    is_admin = data.get('is_admin', False)

    if not user_id or not username:
        return jsonify({'error': '用户 ID 和用户名是必填项。'}), 400

    with closing(database.get_db()) as db:
        if password:
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            db.execute(
                'UPDATE users SET username = ?, password_hash = ?, is_admin = ? WHERE id = ?',
                (username, hashed_pw, is_admin, user_id)
            )
        else:
            db.execute(
                'UPDATE users SET username = ?, is_admin = ? WHERE id = ?',
                (username, is_admin, user_id)
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
        db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        db.commit()
        return jsonify({'message': '用户已成功删除。'})


@api_bp.route('/user_settings', methods=['GET', 'POST'])
def user_settings_api():
    if request.method == 'POST':
        data = request.get_json()
        with closing(database.get_db()) as db:
            if 'new_password' in data and data['new_password']:
                hashed = bcrypt.hashpw(data['new_password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                db.execute('UPDATE users SET password_hash = ? WHERE id = ?', (hashed, g.user.id))
            priority_list = [v.strip() for v in data.get('send_format_priority', '').split(',')]
            db.execute('UPDATE users SET kindle_email = ?, send_format_priority = ? WHERE id = ?',
                       (data.get('kindle_email'), json.dumps(priority_list), g.user.id))
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
            'smtp_from_address': config_manager.config.get('SMTP_USERNAME')
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

@api_bp.route('/download_book/<int:book_id>', methods=['GET'])
def download_book_api(book_id):
    details = get_calibre_book_details(book_id)
    if not details:
        return jsonify({'error': '找不到书籍详情。'}), 404

    available_formats = [f.lower() for f in details.get('formats', [])]
    priority = json.loads(g.user.send_format_priority or '[]')
    
    format_to_download = None
    for p_format in priority:
        if p_format.lower() in available_formats:
            format_to_download = p_format.lower()
            break
    
    if not format_to_download:
        if available_formats:
            format_to_download = available_formats[0]
        else:
            return jsonify({'error': '该书籍没有任何可用格式。'}), 400

    content, filename = download_calibre_book(book_id, format_to_download)
    if content:
        return send_file(io.BytesIO(content), as_attachment=True, download_name=filename)
    
    return jsonify({'error': '无法下载书籍。'}), 404

@api_bp.route('/send_to_kindle/<int:book_id>', methods=['POST'])
def send_to_kindle_api(book_id):
    if not g.user.kindle_email: return jsonify({'error': '请先在用户设置中配置您的 Kindle 邮箱。'}), 400
    details = get_calibre_book_details(book_id)
    if not details: return jsonify({'error': '找不到书籍详情。'}), 404
    available_formats = [f.lower() for f in details.get('formats', [])]
    format_to_send = None
    priority = json.loads(g.user.send_format_priority or '[]')
    for p_format in priority:
        if p_format.lower() in available_formats:
            format_to_send = p_format.lower()
            break
            
    if not format_to_send:
        if available_formats:
            format_to_send = available_formats[0]
        else:
            return jsonify({'error': f'未找到可用格式: {", ".join(available_formats)}'}), 400
            
    additional_message = ""
    if format_to_send != 'epub' and 'epub' in available_formats:
        additional_message = f"注意: 此书以 {format_to_send.upper()} 格式发送。为获得最佳体验，建议在 Calibre 中将其转为 EPUB。"
        
    content, filename = download_calibre_book(book_id, format_to_send)
    if not content: return jsonify({'error': '下载书籍时出错。'}), 500
    subject = f"推送书籍: {details.get('title', 'N/A')}"
    body = f"附件是您请求的书籍。{additional_message}"
    success, message = send_email(g.user.kindle_email, subject, body, content, filename)
    if success:
        return jsonify({'message': message + (' ' + additional_message if additional_message else '')})
    else:
        return jsonify({'error': message}), 500

@api_bp.route('/push_to_anx/<int:book_id>', methods=['POST'])
def push_to_anx_api(book_id):
    details = get_calibre_book_details(book_id)
    if not details: return jsonify({'error': '找不到书籍详情。'}), 404
    
    available_formats = [f.lower() for f in details.get('formats', [])]
    priority = json.loads(g.user.send_format_priority or '[]')
    format_to_push = next((f for f in priority if f.lower() in available_formats), available_formats[0] if available_formats else None)

    if not format_to_push:
        return jsonify({'error': '未找到可推送的格式。'}), 400

    book_content, book_filename = download_calibre_book(book_id, format_to_push)
    if not book_content: return jsonify({'error': '下载书籍以进行推送时出错。'}), 500

    cover_content, _ = download_calibre_cover(book_id)

    dirs = get_anx_user_dirs(g.user.username)
    if not dirs:
        return jsonify({'error': '用户目录未配置。'}), 500
    
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
            
    result = process_anx_import_folder(g.user.username)
    
    return jsonify({
        'message': f"书籍 '{book_filename}' 推送完成。 "
                   f"已处理: {result.get('processed', 0)}, "
                   f"已跳过: {result.get('skipped', 0)}."
    })


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
@admin_required_api
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
    
    # Filter out any keys with None or empty values
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