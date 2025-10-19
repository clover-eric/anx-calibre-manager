"""
用户活动日志记录工具模块
用于统一记录所有用户活动，包括登录、登出、书籍操作等
"""
from datetime import datetime
from contextlib import closing
from flask import request, g
import database
import config_manager


import json

SENSITIVE_KEYWORDS = [
   'password', 'api_key', 'secret', 'token',
   'smtp_password', 'calibre_password', 'tts_api_key', 'llm_api_key'
]

def filter_sensitive_data(data):
   """
   递归地过滤字典中的敏感数据
   """
   if not isinstance(data, dict):
       return data
   
   clean_data = {}
   for key, value in data.items():
       if isinstance(value, dict):
           clean_data[key] = filter_sensitive_data(value)
       elif any(keyword in key.lower() for keyword in SENSITIVE_KEYWORDS):
           clean_data[key] = "[REDACTED]"
       else:
           clean_data[key] = value
   return clean_data

class ActivityType:
    """活动类型常量"""
    # 认证相关
    LOGIN_SUCCESS = 'login_success'
    LOGIN_FAILED = 'login_failed'
    LOGOUT = 'logout'
    REGISTER = 'register'
    
    # 书籍操作
    DOWNLOAD_BOOK = 'download_book'
    UPLOAD_BOOK = 'upload_book'
    DELETE_BOOK = 'delete_book'
    SEARCH_BOOKS = 'search_books'
    EDIT_METADATA = 'edit_metadata'
    
    # 推送操作
    PUSH_TO_KINDLE = 'push_to_kindle'
    PUSH_TO_ANX = 'push_to_anx'
    PUSH_ANX_TO_CALIBRE = 'push_anx_to_calibre'
    
    # 有声书操作
    GENERATE_AUDIOBOOK = 'generate_audiobook'
    DOWNLOAD_AUDIOBOOK = 'download_audiobook'
    DELETE_AUDIOBOOK = 'delete_audiobook'
    PLAY_AUDIOBOOK_UPDATE_PLAYING_PROGRESS = 'play_audiobook_update_playing_progress'
    PLAY_AUDIOBOOK_UPDATE_READING_TIME = 'play_audiobook_update_reading_time'
    
    # 在线阅读
    ONLINE_READING_UPDATE_READING_PROGRESS = 'update_reading_progress'
    ONLINE_READING_UPDATE_READING_TIME = 'update_reading_time'
    
    # LLM 对话
    LLM_CHAT_START = 'llm_chat_start'
    LLM_CHAT_MESSAGE = 'llm_chat_message'
    LLM_DELETE_SESSION = 'llm_delete_session'
    LLM_DELETE_MESSAGE = 'llm_delete_message'
    
    # MCP 相关
    MCP_TOKEN_GENERATE = 'mcp_token_generate'
    MCP_TOKEN_DELETE = 'mcp_token_delete'
    MCP_API_CALL = 'mcp_api_call'
    
    # 设置操作
    UPDATE_USER_SETTINGS = 'update_user_settings'
    UPDATE_GLOBAL_SETTINGS = 'update_global_settings'
    UPDATE_PASSWORD = 'update_password'
    ENABLE_2FA = 'enable_2fa'
    DISABLE_2FA = 'disable_2fa'
    
    # 用户管理
    CREATE_USER = 'create_user'
    UPDATE_USER = 'update_user'
    DELETE_USER = 'delete_user'
    LOCK_USER = 'lock_user'
    UNLOCK_USER = 'unlock_user'
    
    # 邀请码管理
    CREATE_INVITE_CODE = 'create_invite_code'
    DELETE_INVITE_CODE = 'delete_invite_code'
    USE_INVITE_CODE = 'use_invite_code'
    TOGGLE_INVITE_CODE = 'toggle_invite_code'
    
    # 服务配置管理
    CREATE_SERVICE_CONFIG = 'create_service_config'
    UPDATE_SERVICE_CONFIG = 'update_service_config'
    DELETE_SERVICE_CONFIG = 'delete_service_config'
    
    # 邮件操作
    TEST_SMTP = 'test_smtp'
    
    # KOReader 同步
    KOREADER_SYNC_PROGRESS = 'koreader_sync_progress'
    KOREADER_SYNC_READING_TIME = 'koreader_sync_reading_time'
    KOREADER_UPDATE_SUMMARY = 'koreader_update_summary'
    
    # 管理活动记录日志操作
    DELETE_USER_ACTIVITY_LOG = 'delete_user_activity_log'
    DELETE_ALL_ACTIVITY_LOGS = 'delete_all_activity_logs'


def log_activity(
    activity_type,
    username=None,
    user_id=None,
    success=True,
    failure_reason=None,
    book_id=None,
    book_title=None,
    library_type=None,
    task_id=None,
    detail=None
):
    """
    记录用户活动日志
    
    Args:
        activity_type: 活动类型 (使用 ActivityType 中的常量)
        username: 用户名 (如果未提供，尝试从 g.user 获取)
        user_id: 用户ID (如果未提供，尝试从 g.user 获取)
        success: 操作是否成功 (默认 True)
        failure_reason: 失败原因 (仅在 success=False 时使用)
        book_id: 书籍ID (用于书籍相关操作)
        book_title: 书籍标题
        library_type: 库类型 ('calibre' 或 'anx')
        task_id: 任务ID (用于有声书等异步任务)
        detail: 其他详细信息 (JSON字符串或普通文本)
    """
    try:
        # 检查是否启用了活动日志记录
        if not config_manager.config.get('ENABLE_ACTIVITY_LOG', False):
            return
        
        # 尝试从 g 对象获取用户信息
        if username is None and hasattr(g, 'user') and g.user:
            username = g.user.username
            user_id = g.user.id
        
        # 如果仍然没有用户名，使用 'anonymous'
        if username is None:
            username = 'anonymous'
        
        # 获取请求信息
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')[:500]  # 限制长度
        
        # 过滤和处理 detail 字段
        detail_to_log = detail
        if isinstance(detail, dict):
            clean_detail = filter_sensitive_data(detail)
            detail_to_log = json.dumps(clean_detail, ensure_ascii=False)

        # 插入日志记录
        with closing(database.get_db()) as db:
            db.execute('''
                INSERT INTO user_activity_log (
                    user_id, username, activity_type, success, failure_reason,
                    book_id, book_title, library_type, task_id, detail,
                    ip_address, user_agent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, username, activity_type, int(success), failure_reason,
                book_id, book_title, library_type, task_id, detail_to_log,
                ip_address, user_agent
            ))
            db.commit()
    except Exception as e:
        # 记录日志失败不应该影响主业务流程
        print(f"Failed to log activity: {e}")


def get_user_activities(user_id=None, username=None, activity_type=None, 
                        limit=100, offset=0, start_date=None, end_date=None):
    """
    查询用户活动日志
    
    Args:
        user_id: 用户ID (可选)
        username: 用户名 (可选)
        activity_type: 活动类型 (可选)
        limit: 返回记录数量限制
        offset: 偏移量 (用于分页)
        start_date: 开始日期 (可选)
        end_date: 结束日期 (可选)
    
    Returns:
        活动日志记录列表
    """
    with closing(database.get_db()) as db:
        query = 'SELECT * FROM user_activity_log WHERE 1=1'
        params = []
        
        if user_id is not None:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        if username is not None:
            query += ' AND username = ?'
            params.append(username)
        
        if activity_type is not None:
            query += ' AND activity_type = ?'
            params.append(activity_type)
        
        if start_date is not None:
            query += ' AND created_at >= ?'
            params.append(start_date)
        
        if end_date is not None:
            query += ' AND created_at <= ?'
            params.append(end_date)
        
        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor = db.execute(query, params)
        return cursor.fetchall()


def get_activity_statistics(user_id=None, start_date=None, end_date=None):
    """
    获取活动统计信息
    
    Args:
        user_id: 用户ID (可选，不提供则统计所有用户)
        start_date: 开始日期 (可选)
        end_date: 结束日期 (可选)
    
    Returns:
        统计信息字典
    """
    with closing(database.get_db()) as db:
        query = '''
            SELECT 
                activity_type,
                COUNT(*) as count,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failure_count
            FROM user_activity_log
            WHERE 1=1
        '''
        params = []
        
        if user_id is not None:
            query += ' AND user_id = ?'
            params.append(user_id)
        
        if start_date is not None:
            query += ' AND created_at >= ?'
            params.append(start_date)
        
        if end_date is not None:
            query += ' AND created_at <= ?'
            params.append(end_date)
        
        query += ' GROUP BY activity_type'
        
        cursor = db.execute(query, params)
        results = cursor.fetchall()
        
        return {
            row['activity_type']: {
                'total': row['count'],
                'success': row['success_count'],
                'failure': row['failure_count']
            }
            for row in results
        }


def get_recent_login_attempts(username, minutes=30):
    """
    获取最近的登录尝试记录
    
    Args:
        username: 用户名
        minutes: 时间范围（分钟）
    
    Returns:
        登录尝试记录列表
    """
    with closing(database.get_db()) as db:
        cursor = db.execute('''
            SELECT * FROM user_activity_log
            WHERE username = ? 
            AND activity_type IN (?, ?)
            AND created_at >= datetime('now', '-' || ? || ' minutes')
            ORDER BY created_at DESC
        ''', (username, ActivityType.LOGIN_SUCCESS, ActivityType.LOGIN_FAILED, minutes))
        return cursor.fetchall()