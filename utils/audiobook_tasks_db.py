from contextlib import closing
from database import get_db

def add_audiobook_task(task_id, user_id, book_id, library_type, status="queued", message="Task queued", percentage=0):
    """向 audiobook_tasks 表中添加一个新任务"""
    with closing(get_db()) as db:
        db.execute(
            """
            INSERT INTO audiobook_tasks (task_id, user_id, book_id, library_type, status, message, percentage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (task_id, user_id, book_id, library_type, status, message, percentage)
        )
        db.commit()

def update_audiobook_task(task_id, status, message=None, percentage=None, file_path=None):
    """更新 audiobook_tasks 表中现有任务的状态"""
    with closing(get_db()) as db:
        # 构建更新语句
        fields = []
        params = []
        
        fields.append("status = ?")
        params.append(status)
        
        if message is not None:
            fields.append("message = ?")
            params.append(message)
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
    """根据 book_id 和 library_type 获取一个用户的最新任务，无论状态如何。"""
    with closing(get_db()) as db:
        # 使用 TRIM() 来消除 library_type 字段中可能存在的前后空格，增强查询的健壮性
        task = db.execute("""
            SELECT * FROM audiobook_tasks
            WHERE user_id = ? AND book_id = ? AND TRIM(library_type) = TRIM(?)
            ORDER BY updated_at DESC
            LIMIT 1
        """, (user_id, book_id, library_type)).fetchone()
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