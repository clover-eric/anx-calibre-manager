"""
用户活动 API (非管理员)
"""
from flask import Blueprint, jsonify, g
from flask_babel import gettext as _
from contextlib import closing
import database
from utils.activity_logger import ActivityType
from ..main import login_required

user_activities_user_bp = Blueprint('user_activities_user', __name__, url_prefix='/api/user')

@user_activities_user_bp.route('/pushed-books', methods=['GET'])
@login_required
def get_pushed_to_anx_books():
    """
    获取当前用户已推送到 Anx 的 Calibre 书籍ID列表
    """
    if not g.user:
        return jsonify({'error': _('User not logged in')}), 401

    try:
        with closing(database.get_db()) as db:
            activities = db.execute('''
                SELECT DISTINCT book_id
                FROM user_activity_log
                WHERE user_id = ? 
                  AND activity_type = ? 
                  AND library_type = 'calibre' 
                  AND success = 1
                  AND book_id IS NOT NULL
            ''', (g.user.id, ActivityType.PUSH_TO_ANX)).fetchall()
            
            pushed_book_ids = [row['book_id'] for row in activities]
            return jsonify(pushed_book_ids)
            
    except Exception as e:
        print(f"Error getting pushed to anx books: {e}")
        return jsonify({'error': _('Failed to load pushed book list')}), 500