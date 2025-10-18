import json
from flask import Blueprint, request, jsonify, g
from flask_babel import gettext as _
from contextlib import closing
import database

service_configs_bp = Blueprint('service_configs', __name__, url_prefix='/api/service_configs')

@service_configs_bp.route('/<string:config_type>', methods=['GET'])
def get_configs(config_type):
    if config_type not in ['tts', 'llm']:
        return jsonify({'error': _('Invalid config type specified.')}), 400

    with closing(database.get_db()) as db:
        configs = db.execute(
            "SELECT id, profile_name, config_data FROM user_service_configs WHERE user_id = ? AND config_type = ? ORDER BY profile_name",
            (g.user.id, config_type)
        ).fetchall()
    
    results = [{'id': row['id'], 'profile_name': row['profile_name'], 'config_data': json.loads(row['config_data'])} for row in configs]
    return jsonify(results)

@service_configs_bp.route('', methods=['POST'])
def create_config():
    data = request.get_json()
    config_type = data.get('config_type')
    profile_name = data.get('profile_name')
    config_data = data.get('config_data')

    if not all([config_type, profile_name, config_data]):
        return jsonify({'error': _('Missing required fields.')}), 400
    
    if config_type not in ['tts', 'llm']:
        return jsonify({'error': _('Invalid config type specified.')}), 400

    try:
        with closing(database.get_db()) as db:
            cursor = db.cursor()
            cursor.execute(
                "INSERT INTO user_service_configs (user_id, config_type, profile_name, config_data) VALUES (?, ?, ?, ?)",
                (g.user.id, config_type, profile_name, json.dumps(config_data))
            )
            new_id = cursor.lastrowid
            db.commit()
        return jsonify({'id': new_id, 'message': _('Configuration profile saved successfully.')}), 201
    except Exception as e:
        # Assuming UNIQUE constraint violation is the most common error
        return jsonify({'error': _('A profile with this name already exists.')}), 409

@service_configs_bp.route('/<int:config_id>', methods=['PUT'])
def update_config(config_id):
    data = request.get_json()
    profile_name = data.get('profile_name')
    config_data = data.get('config_data')

    if not all([profile_name, config_data]):
        return jsonify({'error': _('Missing required fields.')}), 400

    try:
        with closing(database.get_db()) as db:
            db.execute(
                "UPDATE user_service_configs SET profile_name = ?, config_data = ? WHERE id = ? AND user_id = ?",
                (profile_name, json.dumps(config_data), config_id, g.user.id)
            )
            db.commit()
        return jsonify({'message': _('Configuration profile updated successfully.')})
    except Exception as e:
        return jsonify({'error': _('A profile with this name already exists.')}), 409

@service_configs_bp.route('/<int:config_id>', methods=['DELETE'])
def delete_config(config_id):
    with closing(database.get_db()) as db:
        db.execute("DELETE FROM user_service_configs WHERE id = ? AND user_id = ?", (config_id, g.user.id))
        db.commit()
    return jsonify({'message': _('Configuration profile deleted successfully.')})