import re
import secrets
import string
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g
from flask_babel import gettext as _
from contextlib import closing
import database

invite_bp = Blueprint('invite', __name__, url_prefix='/api')

def generate_invite_code(length=8):
    chars = string.ascii_uppercase + string.digits
    chars = chars.replace('0', '').replace('O', '').replace('1', '').replace('I', '')
    return ''.join(secrets.choice(chars) for _ in range(length))

@invite_bp.route('/admin/invite-codes', methods=['GET', 'POST'])
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