import base64
import io
import pyotp
import qrcode
from flask import Blueprint, request, jsonify, g, session
from flask_babel import gettext as _
from contextlib import closing
import database

auth_2fa_bp = Blueprint('auth_2fa', __name__, url_prefix='/api')

@auth_2fa_bp.route('/2fa/setup', methods=['POST'])
def setup_2fa():
    if g.user.otp_secret: 
        return jsonify({'error': _('2FA is already enabled.')}), 400
    secret = pyotp.random_base32()
    session['2fa_secret_pending'] = secret
    uri = pyotp.totp.TOTP(secret).provisioning_uri(name=g.user.username, issuer_name='AnxCalibreManager')
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf)
    qr_code_b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    return jsonify({'secret': secret, 'qr_code': f'data:image/png;base64,{qr_code_b64}'})

@auth_2fa_bp.route('/2fa/verify', methods=['POST'])
def verify_2fa():
    otp_code = request.json.get('otp_code')
    secret = session.get('2fa_secret_pending')
    if not secret: 
        return jsonify({'error': _('No pending 2FA setup request found.')}), 400
    if pyotp.TOTP(secret).verify(otp_code):
        with closing(database.get_db()) as db:
            db.execute('UPDATE users SET otp_secret = ? WHERE id = ?', (secret, g.user.id))
            db.commit()
        session.pop('2fa_secret_pending', None)
        return jsonify({'message': _('2FA has been successfully enabled!')})
    else:
        return jsonify({'error': _('Incorrect verification code.')}), 400

@auth_2fa_bp.route('/2fa/disable', methods=['POST'])
def disable_2fa():
    with closing(database.get_db()) as db:
        db.execute('UPDATE users SET otp_secret = NULL WHERE id = ?', (g.user.id,))
        db.commit()
    return jsonify({'message': _('2FA has been disabled.')})