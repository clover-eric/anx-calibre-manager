"""
用户活动管理 API
提供用户活动统计、详情查询和用户账户管理功能
"""
from datetime import datetime, timedelta, timezone
from flask import Blueprint, request, jsonify, g
from flask_babel import gettext as _
from contextlib import closing
import database
from utils.decorators import admin_required_api
from utils.activity_logger import log_activity, ActivityType, get_user_activities, get_activity_statistics

user_activities_bp = Blueprint('user_activities', __name__, url_prefix='/api/admin')


@user_activities_bp.route('/user-activities', methods=['GET'])
@admin_required_api
def get_user_activities_summary():
    """
    获取用户活动概览
    返回所有用户的活动统计信息
    """
    try:
        with closing(database.get_db()) as db:
            # 获取所有用户基本信息
            users = db.execute('''
                SELECT id, username, role, last_login_at, last_login_ip,
                       account_locked_until, failed_login_attempts
                FROM users
                ORDER BY last_login_at DESC NULLS LAST
            ''').fetchall()
            
            user_list = []
            for user in users:
                user_id = user['id']
                username = user['username']
                
                # 统计该用户的登录次数
                login_count = db.execute('''
                    SELECT COUNT(*) as count
                    FROM user_activity_log
                    WHERE user_id = ? AND activity_type = ? AND success = 1
                ''', (user_id, ActivityType.LOGIN_SUCCESS)).fetchone()['count']
                
                # 统计该用户的总活动次数
                activity_count = db.execute('''
                    SELECT COUNT(*) as count
                    FROM user_activity_log
                    WHERE user_id = ?
                ''', (user_id,)).fetchone()['count']
                
                # 获取最后一次登录失败信息
                last_failed_login = db.execute('''
                    SELECT created_at, ip_address, failure_reason
                    FROM user_activity_log
                    WHERE user_id = ? AND activity_type = ? AND success = 0
                    ORDER BY created_at DESC
                    LIMIT 1
                ''', (user_id, ActivityType.LOGIN_FAILED)).fetchone()
                
                # 获取各类活动的最后操作时间
                last_activities = {}
                activity_types = [
                    ActivityType.DOWNLOAD_BOOK,
                    ActivityType.UPLOAD_BOOK,
                    ActivityType.SEARCH_BOOKS,
                    ActivityType.ONLINE_READING_UPDATE_READING_PROGRESS,
                    ActivityType.PUSH_TO_KINDLE,
                    ActivityType.GENERATE_AUDIOBOOK
                ]
                
                for act_type in activity_types:
                    last_act = db.execute('''
                        SELECT created_at
                        FROM user_activity_log
                        WHERE user_id = ? AND activity_type = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                    ''', (user_id, act_type)).fetchone()
                    if last_act:
                        last_activities[act_type] = last_act['created_at']
                
                # 判断账户状态
                is_locked = False
                locked_until = None
                lock_reason = None
                if user['account_locked_until']:
                    locked_until_dt = datetime.fromisoformat(user['account_locked_until'])
                    if datetime.now() < locked_until_dt:
                        is_locked = True
                        locked_until = user['account_locked_until']
                        
                        # 查询锁定原因
                        lock_log = db.execute('''
                            SELECT detail FROM user_activity_log
                            WHERE user_id = ? AND activity_type = ? AND success = 1
                            ORDER BY created_at DESC
                            LIMIT 1
                        ''', (user_id, ActivityType.LOCK_USER)).fetchone()
                        
                        if lock_log and 'Reason:' in lock_log['detail']:
                            try:
                                # 解析 'Account locked until ... Reason: ...' 格式的字符串
                                reason_part = lock_log['detail'].split('Reason:')[1].strip()
                                lock_reason = reason_part
                            except IndexError:
                                lock_reason = _('Reason not specified')
                        elif lock_log:
                            lock_reason = lock_log['detail'] # Fallback for other lock-related messages
                        else:
                            # Fallback for locks without a specific log entry (e.g., automatic locks)
                            lock_reason = _('Account locked due to multiple failed login attempts.')

                
                user_list.append({
                    'id': user_id,
                    'username': username,
                    'role': user['role'],
                    'last_login': user['last_login_at'],
                    'last_login_ip': user['last_login_ip'],
                    'login_count': login_count,
                    'activity_count': activity_count,
                    'is_locked': is_locked,
                    'locked_until': locked_until,
                    'lock_reason': lock_reason,
                    'failed_login_attempts': user['failed_login_attempts'],
                    'last_failed_login': dict(last_failed_login) if last_failed_login else None,
                    'last_activities': last_activities
                })
            
            # 全局统计信息
            total_users = len(users)
            
            # 今天活跃用户数
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            active_today = db.execute('''
                SELECT COUNT(DISTINCT user_id) as count
                FROM user_activity_log
                WHERE created_at >= ?
            ''', (today_start,)).fetchone()['count']
            
            # 总登录次数
            total_logins = db.execute('''
                SELECT COUNT(*) as count
                FROM user_activity_log
                WHERE activity_type = ? AND success = 1
            ''', (ActivityType.LOGIN_SUCCESS,)).fetchone()['count']
            
            # 总活动次数
            total_activities = db.execute('''
                SELECT COUNT(*) as count
                FROM user_activity_log
            ''').fetchone()['count']
            
            # 获取全局各事件统计
            global_stats = get_activity_statistics()
            
            return jsonify({
                'stats': {
                    'total_users': total_users,
                    'active_today': active_today,
                    'total_logins': total_logins,
                    'total_activities': total_activities
                },
                'users': user_list,
                'global_activity_stats': global_stats
            })
    
    except Exception as e:
        print(f"Error getting user activities: {e}")
        return jsonify({'error': _('Failed to load user activities')}), 500


@user_activities_bp.route('/user-activities/by-type/<event_type>', methods=['GET'])
@admin_required_api
def get_activities_by_type(event_type):
    """
    获取特定事件类型的所有活动记录
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        with closing(database.get_db()) as db:
            activities = db.execute('''
                SELECT id, created_at, username, success, failure_reason,
                       book_title, library_type, detail, ip_address
                FROM user_activity_log
                WHERE activity_type = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (event_type, limit, offset)).fetchall()
            
            return jsonify([{
                'id': act['id'],
                'timestamp': act['created_at'],
                'username': act['username'],
                'success': bool(act['success']),
                'failure_reason': act['failure_reason'],
                'book_title': act['book_title'],
                'library_type': act['library_type'],
                'detail': act['detail'],
                'ip_address': act['ip_address']
            } for act in activities])
    
    except Exception as e:
        print(f"Error getting activities by type: {e}")
        return jsonify({'error': _('Failed to load activities')}), 500


@user_activities_bp.route('/user-activities/<username>', methods=['GET'])
@admin_required_api
def get_user_activity_details(username):
    """
    获取特定用户的详细活动记录
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        activity_type = request.args.get('activity_type', None)
        
        activities = get_user_activities(
            username=username,
            activity_type=activity_type,
            limit=limit,
            offset=offset
        )
        
        return jsonify([{
            'id': act['id'],
            'timestamp': act['created_at'],
            'activity_type': act['activity_type'],
            'success': bool(act['success']),
            'failure_reason': act['failure_reason'],
            'book_title': act['book_title'],
            'library_type': act['library_type'],
            'detail': act['detail'],
            'ip_address': act['ip_address']
        } for act in activities])
    
    except Exception as e:
        print(f"Error getting user activity details: {e}")
        return jsonify({'error': _('Failed to load activity details')}), 500


@user_activities_bp.route('/user-activities/stats/events', methods=['GET'])
@admin_required_api
def get_event_statistics():
    """
    获取各类事件的全局统计信息
    用于图表展示
    """
    try:
        days = request.args.get('days', 30, type=int)
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with closing(database.get_db()) as db:
            # 按事件类型统计
            event_stats = db.execute('''
                SELECT 
                    activity_type,
                    COUNT(*) as total_count,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failure_count
                FROM user_activity_log
                WHERE created_at >= ?
                GROUP BY activity_type
                ORDER BY total_count DESC
            ''', (start_date,)).fetchall()
            
            # 按日期统计活动趋势
            daily_stats = db.execute('''
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM user_activity_log
                WHERE created_at >= ?
                GROUP BY DATE(created_at)
                ORDER BY date
            ''', (start_date,)).fetchall()
            
            return jsonify({
                'event_stats': [dict(row) for row in event_stats],
                'daily_stats': [dict(row) for row in daily_stats]
            })
    
    except Exception as e:
        print(f"Error getting event statistics: {e}")
        return jsonify({'error': _('Failed to load event statistics')}), 500


@user_activities_bp.route('/users/<int:user_id>/lock', methods=['POST'])
@admin_required_api
def lock_user(user_id):
    """
    封锁用户账户
    """
    try:
        data = request.get_json()
        duration_minutes = data.get('duration_minutes', 30)
        reason = data.get('reason', _('Locked by administrator'))
        
        locked_until_str = ""
        if duration_minutes > 0:
            locked_until = (datetime.now() + timedelta(minutes=duration_minutes))
            locked_until_str = locked_until.isoformat()
        else:
            # 永久锁定 (设置为一个非常遥远的未来)
            locked_until = datetime(9999, 12, 31, 23, 59, 59)
            locked_until_str = locked_until.isoformat()

        with closing(database.get_db()) as db:
            user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return jsonify({'error': _('User not found')}), 404
            
            db.execute('''
                UPDATE users 
                SET account_locked_until = ?
                WHERE id = ?
            ''', (locked_until_str, user_id))
            db.commit()
            
            lock_time_detail = _('permanently') if duration_minutes <= 0 else locked_until.strftime('%Y-%m-%d %H:%M:%S')
            
            log_activity(
                ActivityType.LOCK_USER,
                username=user['username'],
                user_id=user_id,
                success=True,
                detail=_('Account locked %(time)s. Reason: %(reason)s',
                        time=lock_time_detail, reason=reason)
            )
            
            return jsonify({
                'message': _('User account locked successfully'),
                'locked_until': locked_until_str
            })
    
    except Exception as e:
        print(f"Error locking user: {e}")
        return jsonify({'error': _('Failed to lock user account')}), 500


@user_activities_bp.route('/users/<int:user_id>/unlock', methods=['POST'])
@admin_required_api
def unlock_user(user_id):
    """
    解封用户账户
    """
    try:
        with closing(database.get_db()) as db:
            user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return jsonify({'error': _('User not found')}), 404
            
            db.execute('''
                UPDATE users 
                SET account_locked_until = NULL,
                    failed_login_attempts = 0
                WHERE id = ?
            ''', (user_id,))
            db.commit()
            
            log_activity(
                ActivityType.UNLOCK_USER,
                username=user['username'],
                user_id=user_id,
                success=True,
                detail=_('Account unlocked by administrator')
            )
            
            return jsonify({'message': _('User account unlocked successfully')})
    
    except Exception as e:
        print(f"Error unlocking user: {e}")
        return jsonify({'error': _('Failed to unlock user account')}), 500


@user_activities_bp.route('/users/<int:user_id>/reset-failed-attempts', methods=['POST'])
@admin_required_api
def reset_failed_attempts(user_id):
    """
    重置用户的失败登录尝试次数
    """
    try:
        with closing(database.get_db()) as db:
            user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return jsonify({'error': _('User not found')}), 404
            
            db.execute('''
                UPDATE users 
                SET failed_login_attempts = 0
                WHERE id = ?
            ''', (user_id,))
            db.commit()
            
            log_activity(
                ActivityType.UPDATE_USER,
                username=user['username'],
                user_id=user_id,
                success=True,
                detail=_('Failed login attempts reset by administrator')
            )
            
            return jsonify({'message': _('Failed login attempts reset successfully')})
    
    except Exception as e:
        print(f"Error resetting failed attempts: {e}")
        return jsonify({'error': _('Failed to reset login attempts')}), 500


@user_activities_bp.route('/users/<int:user_id>/activities', methods=['DELETE'])
@admin_required_api
def delete_user_activities(user_id):
    """
    删除单个用户的所有活动记录
    """
    try:
        with closing(database.get_db()) as db:
            user = db.execute('SELECT username FROM users WHERE id = ?', (user_id,)).fetchone()
            if not user:
                return jsonify({'error': _('User not found')}), 404
            
            db.execute('DELETE FROM user_activity_log WHERE user_id = ?', (user_id,))
            db.commit()
            
            log_activity(
                ActivityType.DELETE_USER_ACTIVITY_LOG,
                user_id=g.user.id,
                success=True,
                detail=_('Administrator %(admin)s deleted all activity logs for user: %(username)s',
                         admin=g.user.username, username=user['username'])
            )
            
            return jsonify({'message': _('Successfully deleted all activities for user %(username)s', username=user['username'])})
    
    except Exception as e:
        print(f"Error deleting user activities: {e}")
        return jsonify({'error': _('Failed to delete user activities')}), 500


@user_activities_bp.route('/user-activities/all', methods=['DELETE'])
@admin_required_api
def delete_all_activities():
    """
    删除所有用户的活动记录
    """
    try:
        with closing(database.get_db()) as db:
            db.execute('DELETE FROM user_activity_log')
            db.commit()
            
            log_activity(
                ActivityType.DELETE_ALL_ACTIVITY_LOGS,
                user_id=g.user.id,
                success=True,
                detail=_('Administrator %(admin)s deleted all user activity logs', admin=g.user.username)
            )
            
            return jsonify({'message': _('Successfully deleted all user activity logs')})
    
    except Exception as e:
        print(f"Error deleting all activities: {e}")
        return jsonify({'error': _('Failed to delete all user activities')}), 500