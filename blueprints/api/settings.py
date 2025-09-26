import json
import bcrypt
import hashlib
from flask import Blueprint, request, jsonify, g, session
from flask_babel import gettext as _
from contextlib import closing
import database
import config_manager
from utils.audiobook_generator import cleanup_all_audiobooks

settings_bp = Blueprint('settings', __name__, url_prefix='/api')

# Helper for decorators
def admin_required_api(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or not g.user.is_admin:
            return jsonify({'error': _('Administrator permission required.')}), 403
        return f(*args, **kwargs)
    return decorated_function

@settings_bp.route('/user_settings', methods=['GET', 'POST'])
def user_settings_api():
    if request.method == 'POST':
        data = request.get_json()
        with closing(database.get_db()) as db:
            # Start building the update query
            updates = []
            params = []

            # Password update
            if data.get('new_password'):
                hashed = bcrypt.hashpw(data['new_password'].encode('utf-8'), bcrypt.gensalt())
                kosync_userkey = hashlib.md5(data['new_password'].encode('utf-8')).hexdigest()
                updates.append("password_hash = ?")
                updates.append("kosync_userkey = ?")
                params.extend([hashed, kosync_userkey])

            # Other fields
            field_map = {
                'kindle_email': 'kindle_email',
                'theme': 'theme',
                'language': 'language',
                'tts_provider': 'tts_provider',
                'tts_voice': 'tts_voice',
                'tts_api_key': 'tts_api_key',
                'tts_base_url': 'tts_base_url',
                'tts_model': 'tts_model',
                'tts_rate': 'tts_rate',
                'tts_volume': 'tts_volume',
                'tts_pitch': 'tts_pitch',
                'llm_provider': 'llm_provider',
                'llm_api_key': 'llm_api_key',
                'llm_base_url': 'llm_base_url',
                'llm_model': 'llm_model'
            }
            for key, column in field_map.items():
                if key in data:
                    updates.append(f"{column} = ?")
                    params.append(data[key])
            
            if 'send_format_priority' in data:
                priority_list = [v.strip() for v in data.get('send_format_priority', '').split(',')]
                updates.append("send_format_priority = ?")
                params.append(json.dumps(priority_list))

            # Boolean fields
            bool_fields = ['force_epub_conversion', 'stats_enabled', 'stats_public']
            for field in bool_fields:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if updates:
                query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
                params.append(g.user.id)
                db.execute(query, tuple(params))
                db.commit()
                
                # 如果更新了语言设置，同步更新session中的语言
                if 'language' in data:
                    session['language'] = data['language']

        return jsonify({'success': True, 'message': _('User settings updated.')})
    else: # GET
        priority_str = g.user.send_format_priority
        if priority_str:
            priority = json.loads(priority_str)
        else:
            default_priority_str = config_manager.config.get('DEFAULT_FORMAT_PRIORITY', 'azw3,mobi,epub,fb2,txt,pdf')
            priority = [item.strip() for item in default_priority_str.split(',')]
        user_settings = {
            'username': g.user.username,
            'kindle_email': g.user.kindle_email,
            'send_format_priority': priority,
            'has_2fa': bool(g.user.otp_secret),
            'smtp_from_address': config_manager.config.get('SMTP_USERNAME'),
            'theme': g.user.theme or 'auto',
            'force_epub_conversion': bool(g.user.force_epub_conversion),
            'stats_enabled': bool(g.user.stats_enabled),
            'stats_public': bool(g.user.stats_public),
            'language': g.user.language
        }
        
        # Load TTS settings, falling back to global defaults
        tts_fields = [
            'tts_provider', 'tts_voice', 'tts_api_key', 'tts_base_url',
            'tts_model', 'tts_rate', 'tts_volume', 'tts_pitch'
        ]
        for field in tts_fields:
            user_value = getattr(g.user, field, None)
            if user_value is not None and user_value != '':
                user_settings[field] = user_value
            else:
                default_key = f"DEFAULT_{field.upper()}"
                user_settings[field] = config_manager.config.get(default_key)

        # Load LLM settings, falling back to global defaults
        llm_fields = [
            'llm_provider', 'llm_api_key', 'llm_base_url', 'llm_model'
        ]
        for field in llm_fields:
            user_value = getattr(g.user, field, None)
            if user_value is not None and user_value != '':
                user_settings[field] = user_value
            else:
                default_key = f"DEFAULT_{field.upper()}"
                user_settings[field] = config_manager.config.get(default_key)
        
        return jsonify(user_settings)

@settings_bp.route('/global_settings', methods=['GET', 'POST'])
@admin_required_api
def global_settings_api():
    if request.method == 'POST':
        data = request.get_json()
        # Handle checkbox boolean value
        data['CALIBRE_ADD_DUPLICATES'] = data.get('CALIBRE_ADD_DUPLICATES') == 'true'
        config_manager.config.save_config(data)
        return jsonify({'message': _('Global settings updated.')})
    else: # GET
        return jsonify(config_manager.config.get_all())

@settings_bp.route('/admin/cleanup_audiobooks', methods=['POST'])
@admin_required_api
def cleanup_audiobooks_api():
    """手动触发清理所有已生成的有声书文件。"""
    try:
        cleaned_count = cleanup_all_audiobooks()
        return jsonify({'success': True, 'message': _('%(count)s audiobook files have been cleaned up.', count=cleaned_count)})
    except Exception as e:
        return jsonify({'error': _('An error occurred during cleanup: %(error)s', error=str(e))}), 500