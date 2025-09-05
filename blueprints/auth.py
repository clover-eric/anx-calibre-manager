import bcrypt
import re
import secrets
import string
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g, jsonify
from flask_babel import gettext as _
from contextlib import closing
import database
import config_manager

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if g.user and g.user.id: return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        otp_code = request.form.get('otp_code')
        with closing(database.get_db()) as db:
            user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash']):
            if user['otp_secret']:
                if not otp_code:
                    session['user_id_pending_2fa'] = user['id']
                    return jsonify({'require_2fa': True})
                
                import pyotp
                pending_user_id = session.get('user_id_pending_2fa')
                if not pending_user_id or pending_user_id != user['id']:
                    flash(_('Session invalid, please login again.'))
                    return redirect(url_for('auth.login'))

                if not pyotp.TOTP(user['otp_secret']).verify(otp_code):
                    return jsonify({'error': _('Two-factor authentication code is incorrect.')}), 401
            
            session.clear()
            session['user_id'] = user['id']
            session.permanent = True
            session.pop('user_id_pending_2fa', None)
            return jsonify({'success': True, 'redirect_url': url_for('main.index')})
        else:
            return jsonify({'error': _('Username or password is incorrect.')}), 401
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    lang = session.get('language')
    session.clear()
    flash(_('You have been logged out successfully.'))
    return redirect(url_for('auth.login', lang=lang))

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    with closing(database.get_db()) as db:
        if db.execute('SELECT COUNT(id) FROM users').fetchone()[0] > 0:
            return redirect(url_for('auth.login'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        language = request.form.get('language', 'en')
        if not username or not password:
            flash(_('Username and password cannot be empty.'))
            return render_template('setup.html')
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        with closing(database.get_db()) as db:
            db.execute("INSERT INTO users (username, password_hash, role, force_epub_conversion) VALUES (?, ?, 'admin', 1)", (username, hashed_password))
            db.commit()
        flash(_('Administrator account has been created, please login.'))
        return redirect(url_for('auth.login'))
    return render_template('setup.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    require_invite = config_manager.config.get('REQUIRE_INVITE_CODE', True)
    
    with closing(database.get_db()) as db:
        user_count = db.execute('SELECT COUNT(id) FROM users').fetchone()[0]
        if user_count == 0:
            return redirect(url_for('auth.setup'))
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            invite_code = data.get('invite_code', '').strip()
            username = data.get('username', '').strip()
            password = data.get('password', '')
            language = data.get('language', 'zh_Hans')
            
            if not username or not password:
                return jsonify({'error': _('Username and password cannot be empty')}), 400
            
            if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
                return jsonify({'error': _('Username can only contain letters, numbers and underscores, 3-50 characters long')}), 400
            
            if len(password) < 6:
                return jsonify({'error': _('Password must be at least 6 characters')}), 400
            
            with closing(database.get_db()) as db:
                existing_user = db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
                if existing_user:
                    return jsonify({'error': _('Username already exists')}), 400
                
                if require_invite:
                    if not invite_code:
                        return jsonify({'error': _('Please enter invite code')}), 400
                    
                    invite_record = db.execute('''
                        SELECT id, max_uses, current_uses, expires_at, is_active 
                        FROM invite_codes 
                        WHERE code = ? AND is_active = 1
                    ''', (invite_code,)).fetchone()
                    
                    if not invite_record:
                        return jsonify({'error': _('Invite code is invalid')}), 400
                    
                    if invite_record['max_uses'] > 0 and invite_record['current_uses'] >= invite_record['max_uses']:
                        return jsonify({'error': _('Invite code has reached usage limit')}), 400
                    
                    if invite_record['expires_at']:
                        expires_at = datetime.fromisoformat(invite_record['expires_at'].replace('Z', '+00:00'))
                        if datetime.now() > expires_at:
                            return jsonify({'error': _('Invite code has expired')}), 400
                
                import hashlib
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                kosync_userkey = hashlib.md5(password.encode('utf-8')).hexdigest()
                
                cursor = db.cursor()
                cursor.execute('''
                    INSERT INTO users (username, password_hash, role, language, force_epub_conversion, kosync_userkey)
                    VALUES (?, ?, 'user', ?, 1, ?)
                ''', (username, hashed_password, language, kosync_userkey))
                
                user_id = cursor.lastrowid
                
                from anx_library import initialize_anx_user_data
                success, message = initialize_anx_user_data(username)
                if not success:
                    print(f"Failed to initialize Anx data for new user {username}: {message}")
                
                if require_invite and 'invite_record' in locals() and invite_record:
                    new_uses = invite_record['current_uses'] + 1
                    cursor.execute('''
                        UPDATE invite_codes 
                        SET current_uses = ?, used_at = CURRENT_TIMESTAMP, used_by = ?
                        WHERE id = ?
                    ''', (new_uses, user_id, invite_record['id']))
                
                db.commit()
                
                return jsonify({
                    'success': True, 
                    'message': _('Registration successful! Please login.'),
                    'redirect_url': url_for('auth.login')
                })
                
        except Exception as e:
            print(f"Registration error: {e}")
            return jsonify({'error': _('An error occurred during registration')}), 500
    
    return render_template('register.html', require_invite_code=require_invite)

def generate_invite_code(length=8):
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    return ''.join(secrets.choice(chars) for _ in range(length))

@auth_bp.route('/admin/invite-codes', methods=['GET', 'POST'])
def manage_invite_codes():
    if not g.user or not g.user.is_admin:
        return jsonify({'error': _('Insufficient permissions')}), 403
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            action = data.get('action')
            
            if action == 'create':
                max_uses = int(data.get('max_uses', 1))
                expires_hours = data.get('expires_hours')
                custom_code = data.get('custom_code', '').strip()
                
                expires_at = None
                if expires_hours:
                    expires_at = datetime.now() + timedelta(hours=int(expires_hours))
                
                with closing(database.get_db()) as db:
                    if custom_code:
                        if not re.match(r'^[A-Z0-9]{4,20}$', custom_code):
                            return jsonify({'error': _('Custom invite code can only contain uppercase letters and numbers, 4-20 characters long')}), 400
                        
                        existing = db.execute('SELECT id FROM invite_codes WHERE code = ?', (custom_code,)).fetchone()
                        if existing:
                            return jsonify({'error': _('Invite code already exists')}), 400
                        
                        code = custom_code
                    else:
                        while True:
                            code = generate_invite_code()
                            existing = db.execute('SELECT id FROM invite_codes WHERE code = ?', (code,)).fetchone()
                            if not existing:
                                break
                    
                    db.execute('''
                        INSERT INTO invite_codes (code, created_by, max_uses, expires_at, is_active, current_uses, created_at) 
                        VALUES (?, ?, ?, ?, 1, 0, CURRENT_TIMESTAMP)
                    ''', (code, g.user.id, max_uses, expires_at.isoformat() if expires_at else None))
                    db.commit()
                
                return jsonify({'success': True, 'code': code})
            
            elif action == 'toggle':
                code_id = data.get('code_id')
                with closing(database.get_db()) as db:
                    db.execute('UPDATE invite_codes SET is_active = 1 - is_active WHERE id = ?', (code_id,))
                    db.commit()
                return jsonify({'success': True})
            
            elif action == 'delete':
                code_id = data.get('code_id')
                with closing(database.get_db()) as db:
                    db.execute('DELETE FROM invite_codes WHERE id = ?', (code_id,))
                    db.commit()
                return jsonify({'success': True})
                
        except Exception as e:
            print(f"Invite code management error: {e}")
            return jsonify({'error': _('Operation failed')}), 500
    
    # GET request for invite codes
    with closing(database.get_db()) as db:
        codes = db.execute('''
            SELECT ic.id, ic.code, u.username as created_by, ic.max_uses, ic.current_uses, 
                   ic.created_at, ic.expires_at, ic.is_active, GROUP_CONCAT(u2.username) as used_by_users
            FROM invite_codes ic
            LEFT JOIN users u ON ic.created_by = u.id
            LEFT JOIN users u2 ON ic.used_by = u2.id
            GROUP BY ic.id
            ORDER BY ic.created_at DESC
        ''').fetchall()
    
    return jsonify([dict(row) for row in codes])