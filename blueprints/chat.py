from flask import Blueprint, render_template, request, g
from flask_babel import gettext as _
from contextlib import closing
import database
from utils.decorators import login_required

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat_player')
@login_required
def chat_player():
    # --- Data for the left panel (session lists) ---
    with closing(database.get_db()) as db:
        base_query = """
            SELECT id, book_id, book_type, book_title, updated_at
            FROM llm_chat_sessions
            WHERE user_id = ? AND book_type = ?
            ORDER BY updated_at DESC
        """
        calibre_sessions = db.execute(base_query, (g.user.id, 'calibre')).fetchall()
        anx_sessions = db.execute(base_query, (g.user.id, 'anx')).fetchall()

    # --- Data for potentially auto-loading a chat in the right panel ---
    # This allows direct linking to a conversation
    initial_chat = {
        'book_id': request.args.get('book_id', type=int),
        'book_type': request.args.get('book_type'),
        'book_title': request.args.get('book_title')
    }
    
    # Determine the default active library tab
    # If a specific book is requested, activate its library tab. Otherwise, default to 'calibre'.
    active_library = initial_chat.get('book_type') or 'calibre'
    theme = g.user.theme if hasattr(g.user, 'theme') and g.user.theme else 'auto'

    return render_template('chat_player.html',
                           calibre_sessions=calibre_sessions,
                           anx_sessions=anx_sessions,
                           initial_chat=initial_chat,
                           active_library=active_library,
                           theme=theme)