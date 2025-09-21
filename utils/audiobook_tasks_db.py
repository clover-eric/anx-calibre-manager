import json
from contextlib import closing
from database import get_db

def add_audiobook_task(task_id, user_id, book_id, library_type, status="queued", status_key="QUEUED", percentage=0):
    """向 audiobook_tasks 表中添加一个新任务"""
    with closing(get_db()) as db:
        db.execute(
            """
            INSERT INTO audiobook_tasks (task_id, user_id, book_id, library_type, status, status_key, percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, user_id, book_id, library_type, status, status_key, percentage)
        )
        db.commit()

def update_audiobook_task(task_id, status, status_key=None, status_params=None, percentage=None, file_path=None):
    """更新 audiobook_tasks 表中现有任务的状态"""
    with closing(get_db()) as db:
        # 构建更新语句
        fields = []
        params = []
        
        fields.append("status = ?")
        params.append(status)
        
        if status_key is not None:
            fields.append("status_key = ?")
            params.append(status_key)
        if status_params is not None:
            fields.append("status_params = ?")
            params.append(json.dumps(status_params))
        if percentage is not None:
            fields.append("percentage = ?")
            params.append(percentage)
        if file_path is not None:
            fields.append("file_path = ?")
            params.append(file_path)
            
        params.append(task_id)
        
        query = f"UPDATE audiobook_tasks SET {', '.join(fields)} WHERE task_id = ?"
        
        db.execute(query, tuple(params))
        db.commit()


def get_audiobook_task_by_id(task_id):
    """通过 task_id 从数据库中获取任务"""
    with closing(get_db()) as db:
        task = db.execute("SELECT * FROM audiobook_tasks WHERE task_id = ?", (task_id,)).fetchone()
        return task

def get_audiobook_task_by_book(user_id, book_id, library_type):
    """检查特定用户和书籍是否已存在活动任务"""
    with closing(get_db()) as db:
        # 仅查找未完成或未出错的任务
        task = db.execute(
            "SELECT * FROM audiobook_tasks WHERE user_id = ? AND book_id = ? AND library_type = ? AND status NOT IN ('success', 'error', 'cleaned')",
            (user_id, book_id, library_type)
        ).fetchone()
        return task

def get_latest_task_for_book(user_id, book_id, library_type):
    """
    获取特定书籍的最新**活动**任务（即未被清理的任务）。
    对于 Calibre 库，任务是共享的，不检查 user_id。
    对于 Anx 库，任务是用户私有的，会检查 user_id。
    """
    with closing(get_db()) as db:
        # 基础查询语句，排除了已被清理的任务
        query = """
            SELECT * FROM audiobook_tasks
            WHERE book_id = ? AND TRIM(library_type) = TRIM(?) AND status != 'cleaned'
        """
        params = [book_id, library_type]

        # 如果是 anx 库，则添加用户限制
        if library_type.strip().lower() == 'anx':
            query += " AND user_id = ?"
            params.append(user_id)

        # 添加排序和限制
        query += " ORDER BY updated_at DESC LIMIT 1"

        task = db.execute(query, tuple(params)).fetchone()
        return task

def get_tasks_to_cleanup(age_in_days=7):
    """获取所有在指定天数前成功完成的任务"""
    with closing(get_db()) as db:
        tasks = db.execute(
            "SELECT * FROM audiobook_tasks WHERE status = 'success' AND updated_at <= date('now', '-' || ? || ' days')",
            (age_in_days,)
        ).fetchall()
        return tasks

def update_task_as_cleaned(task_id):
    """将任务标记为已清理"""
    with closing(get_db()) as db:
        db.execute(
            "UPDATE audiobook_tasks SET status = 'cleaned', file_path = NULL WHERE task_id = ?",
            (task_id,)
        )
        db.commit()

def get_all_successful_tasks():
    """获取所有状态为 'success' 的任务"""
    with closing(get_db()) as db:
        tasks = db.execute("SELECT * FROM audiobook_tasks WHERE status = 'success'").fetchall()
        return tasks