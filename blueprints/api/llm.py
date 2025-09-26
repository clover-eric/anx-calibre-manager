import requests
import uuid
from flask import Blueprint, request, jsonify, g
from flask_babel import gettext as _
from contextlib import closing
import database

# Use a try-except block for cleaner optional import
try:
    from blueprints.mcp import get_calibre_entire_book_content, get_anx_entire_book_content
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

llm_bp = Blueprint('llm', __name__, url_prefix='/api/llm')

def login_required_api(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or g.user.id is None:
            return jsonify({'error': _('Authentication required.')}), 401
        return f(*args, **kwargs)
    return decorated_function

@llm_bp.route('/history', methods=['GET'])
@login_required_api
def get_chat_history():
    book_id = request.args.get('book_id', type=int)
    book_type = request.args.get('book_type')

    if not book_id or not book_type:
        return jsonify({'error': _('Book ID and type are required.')}), 400

    with closing(database.get_db()) as db:
        session = db.execute(
            'SELECT id FROM llm_chat_sessions WHERE user_id = ? AND book_id = ? AND book_type = ? ORDER BY created_at DESC LIMIT 1',
            (g.user.id, book_id, book_type)
        ).fetchone()

        if not session:
            return jsonify({'error': _('No history found for this book.')}), 404

        messages = db.execute(
            'SELECT role, content FROM llm_chat_messages WHERE session_id = ? ORDER BY created_at ASC',
            (session['id'],)
        ).fetchall()

    return jsonify({
        'session_id': session['id'],
        'messages': [dict(msg) for msg in messages]
    })

@llm_bp.route('/chat', methods=['POST'])
@login_required_api
def chat_with_book():
    if not MCP_AVAILABLE:
        return jsonify({'error': _('MCP module is not available, cannot process book content.')}), 501

    data = request.get_json()
    session_id = data.get('session_id')
    book_id = data.get('book_id')
    book_type = data.get('book_type')
    book_title = data.get('book_title')
    user_message = data.get('message')

    if not all([book_id, book_type, book_title, user_message]):
        return jsonify({'error': _('Missing required fields.')}), 400

    with closing(database.get_db()) as db:
        cursor = db.cursor()
        # Session management
        if not session_id:
            session_id = str(uuid.uuid4())
            cursor.execute(
                'INSERT INTO llm_chat_sessions (id, user_id, book_id, book_type, book_title) VALUES (?, ?, ?, ?, ?)',
                (session_id, g.user.id, book_id, book_type, book_title)
            )
        
        # Save user message
        cursor.execute(
            'INSERT INTO llm_chat_messages (session_id, role, content) VALUES (?, ?, ?)',
            (session_id, 'user', user_message)
        )
        db.commit()

    # --- Get book content ---
    # This is a long-running operation

    # First, handle invalid book type to simplify logic below.
    if book_type not in ['calibre', 'anx']:
        return jsonify({'error': _('Invalid book type.')}), 400

    # mcp.py's functions expect g.user to be a dict-like object (like sqlite3.Row),
    # but in this web context, it's a User class instance. We must create a temporary,
    # compatible dict for ALL calls into mcp.py, and restore the original g.user afterwards.
    original_user = g.user
    g.user = {key: getattr(original_user, key, None) for key in
              ['id', 'username', 'language', 'kindle_email', 'anx_token', 'anx_url']}

    content_result = {}
    try:
        if book_type == 'calibre':
            content_result = get_calibre_entire_book_content(book_id)
        elif book_type == 'anx':
            content_result = get_anx_entire_book_content(book_id)
    finally:
        # CRITICAL: Restore g.user to prevent side effects in the rest of the request.
        g.user = original_user

    if 'error' in content_result:
        return jsonify({'error': _('Failed to get book content: %(error)s', error=content_result['error'])}), 500
    
    book_content = content_result.get('full_text', '')
    if not book_content:
        return jsonify({'error': _('Could not extract text from the book.')}), 500

    # --- Call LLM ---
    if not all([g.user.llm_base_url, g.user.llm_api_key, g.user.llm_model]):
        return jsonify({'error': _('LLM settings are not configured in user settings.')}), 412

    headers = {'Authorization': f'Bearer {g.user.llm_api_key}', 'Content-Type': 'application/json'}
    endpoint = g.user.llm_base_url
    if not endpoint.endswith('/'):
        endpoint += '/'
    endpoint += 'chat/completions'

    system_prompt = f"You are a helpful assistant. The user is asking about the book '{book_title}'. Here is the full text of the book:\n\n---BOOK CONTENT---\n{book_content}\n---END BOOK CONTENT---"
    
    payload = {
        "model": g.user.llm_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=300)
        response.raise_for_status()
        llm_response_data = response.json()
        model_response = llm_response_data['choices'][0]['message']['content']
    except Exception as e:
        return jsonify({'error': _('Failed to communicate with LLM provider: %(error)s', error=str(e))}), 500

    # Save model response
    with closing(database.get_db()) as db:
        db.execute(
            'INSERT INTO llm_chat_messages (session_id, role, content) VALUES (?, ?, ?)',
            (session_id, 'model', model_response)
        )
        db.commit()

    return jsonify({'session_id': session_id, 'response': model_response})


@llm_bp.route('/models', methods=['POST'])
@login_required_api
def get_llm_models():
    data = request.get_json()
    base_url = data.get('base_url')
    api_key = data.get('api_key')

    if not base_url or not api_key:
        return jsonify({'error': _('Base URL and API Key are required.')}), 400

    headers = {'Authorization': f'Bearer {api_key}'}
    if not base_url.endswith('/'):
        base_url += '/'
    models_url = f"{base_url}models"

    try:
        response = requests.get(models_url, headers=headers, timeout=10)
        response.raise_for_status()
        models_data = response.json()
        
        if 'data' in models_data and isinstance(models_data['data'], list):
            model_ids = sorted([model['id'] for model in models_data['data'] if 'id' in model])
            return jsonify(model_ids)
        else:
            return jsonify({'error': _('Unexpected response format from model provider.')}), 500

    except requests.exceptions.RequestException as e:
        error_message = str(e)
        if '401' in error_message:
            return jsonify({'error': _('Authentication error. Please check your API Key.')}), 401
        elif '404' in error_message:
             return jsonify({'error': _('Invalid API endpoint. Please check your Base URL.')}), 404
        else:
            return jsonify({'error': _('Could not connect to the model provider: %(error)s', error=error_message)}), 500
    except Exception as e:
        return jsonify({'error': _('An unexpected error occurred: %(error)s', error=str(e))}), 500

@llm_bp.route('/session/<session_id>', methods=['DELETE'])
@login_required_api
def delete_chat_session(session_id):
    with closing(database.get_db()) as db:
        # Security check: Ensure the session belongs to the current user
        session = db.execute(
            'SELECT id FROM llm_chat_sessions WHERE id = ? AND user_id = ?',
            (session_id, g.user.id)
        ).fetchone()

        if not session:
            return jsonify({'error': _('Session not found or permission denied.')}), 404

        # ON DELETE CASCADE will handle messages in llm_chat_messages table
        db.execute('DELETE FROM llm_chat_sessions WHERE id = ?', (session_id,))
        db.commit()

    return jsonify({'success': True, 'message': _('Chat session deleted successfully.')})