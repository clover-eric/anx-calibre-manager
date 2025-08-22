import bcrypt
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g, jsonify
from contextlib import closing
import database

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
        
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
            if user['otp_secret']:
                if not otp_code:
                    session['user_id_pending_2fa'] = user['id']
                    return jsonify({'require_2fa': True})
                
                import pyotp
                pending_user_id = session.get('user_id_pending_2fa')
                if not pending_user_id or pending_user_id != user['id']:
                    flash('会话无效，请重新登录。')
                    return redirect(url_for('auth.login'))

                if not pyotp.TOTP(user['otp_secret']).verify(otp_code):
                    return jsonify({'error': '两步验证码错误。'}), 401
            
            session.clear()
            session['user_id'] = user['id']
            session.permanent = True
            session.pop('user_id_pending_2fa', None)
            return jsonify({'success': True, 'redirect_url': url_for('main.index')})
        else:
            return jsonify({'error': '用户名或密码错误。'}), 401
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('您已成功登出。')
    return redirect(url_for('auth.login'))

@auth_bp.route('/setup', methods=['GET', 'POST'])
def setup():
    with closing(database.get_db()) as db:
        if db.execute('SELECT COUNT(id) FROM users').fetchone()[0] > 0:
            return redirect(url_for('auth.login'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash('用户名和密码不能为空。')
            return render_template('setup.html')
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        with closing(database.get_db()) as db:
            db.execute('INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)', (username, hashed_password, 1))
            db.commit()
        flash('管理员账户已创建，请登录。')
        return redirect(url_for('auth.login'))
    return render_template('setup.html')