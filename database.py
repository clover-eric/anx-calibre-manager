import sqlite3
import os
import json
from contextlib import closing
from config_manager import DATABASE_PATH

DEFAULT_FORMAT_PRIORITY = json.dumps(["azw3", "mobi", "epub", "fb2", "txt", "pdf"])

def get_db():
    """获取数据库连接"""
    db_dir = os.path.dirname(DATABASE_PATH)
    os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def update_schema_if_needed(db):
    """检查并添加新列，以实现简单的数据库迁移"""
    cursor = db.cursor()
    cursor.execute("PRAGMA table_info(users)")
    columns = [row['name'] for row in cursor.fetchall()]
    
    if 'kindle_email' not in columns:
        print("Migrating database: adding 'kindle_email' column to users table.")
        cursor.execute('ALTER TABLE users ADD COLUMN kindle_email TEXT')
        db.commit()

def create_schema():
    """
    创建数据库和表结构，并执行必要的迁移。
    """
    db_exists = os.path.exists(DATABASE_PATH)
    
    with closing(get_db()) as db:
        if not db_exists:
            print("Creating new database...")
            cursor = db.cursor()
            # Users Table
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    otp_secret TEXT,
                    send_format_priority TEXT,
                    kindle_email TEXT
                );
            ''')
            db.commit()
            print("Database tables created.")
        else:
            # 如果数据库已存在，检查是否需要更新 schema
            update_schema_if_needed(db)

if __name__ == '__main__':
    create_schema()
    print("Database schema checked/created/migrated.")