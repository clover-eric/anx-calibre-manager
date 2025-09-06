import secrets
from flask import Blueprint, request, jsonify, g
from flask_babel import gettext as _
from contextlib import closing
import database

tokens_bp = Blueprint('tokens', __name__, url_prefix='/api')

# --- MCP Token Management ---
@tokens_bp.route('/mcp_tokens', methods=['GET'])
def get_mcp_tokens():
    with closing(database.get_db()) as db:
        tokens = db.execute('SELECT id, token, created_at FROM mcp_tokens WHERE user_id = ?', (g.user.id,)).fetchall()
        return jsonify([dict(row) for row in tokens])

@tokens_bp.route('/mcp_tokens', methods=['POST'])
def create_mcp_token():
    new_token = secrets.token_hex(16)
    with closing(database.get_db()) as db:
        db.execute('INSERT INTO mcp_tokens (user_id, token) VALUES (?, ?)', (g.user.id, new_token))
        db.commit()
    return jsonify({'message': _('New token generated.'), 'token': new_token})

@tokens_bp.route('/mcp_tokens/<int:token_id>', methods=['DELETE'])
def delete_mcp_token(token_id):
    with closing(database.get_db()) as db:
        # Ensure the token belongs to the current user before deleting
        db.execute('DELETE FROM mcp_tokens WHERE id = ? AND user_id = ?', (token_id, g.user.id))
        db.commit()
    return jsonify({'message': _('Token deleted.')})