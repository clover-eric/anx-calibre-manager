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
    """检查并添加新列或表，以实现简单的数据库迁移"""
    cursor = db.cursor()
    
    # 检查 users 表的列
    cursor.execute("PRAGMA table_info(users)")
    columns = [row['name'] for row in cursor.fetchall()]
    
    if 'kindle_email' not in columns:
        print("Migrating database: adding 'kindle_email' column to users table.")
        cursor.execute('ALTER TABLE users ADD COLUMN kindle_email TEXT')
        db.commit()

    if 'theme' not in columns:
        print("Migrating database: adding 'theme' column to users table.")
        cursor.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'auto'")
        db.commit()

    # 检查 mcp_tokens 表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mcp_tokens'")
    if cursor.fetchone() is None:
        print("Migrating database: creating 'mcp_tokens' table.")
        create_mcp_tokens_table(cursor)
        db.commit()


def create_mcp_tokens_table(cursor):
    """创建 mcp_tokens 表的辅助函数"""
    cursor.execute('''
        CREATE TABLE mcp_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
    ''')

def create_schema():
    """
    创建数据库和表结构，并执行必要的迁移。
    """
    db_exists = os.path.exists(DATABASE_PATH)
    
    with closing(get_db()) as db:
        cursor = db.cursor()
        if not db_exists:
            print("Creating new database...")
            # Users Table
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    is_admin INTEGER NOT NULL DEFAULT 0,
                    otp_secret TEXT,
                    send_format_priority TEXT,
                    kindle_email TEXT,
                    theme TEXT DEFAULT 'auto'
                );
            ''')
            # MCP Tokens Table
            create_mcp_tokens_table(cursor)
            db.commit()
            print("Database tables created.")
        else:
            # 如果数据库已存在，检查是否需要更新 schema
            update_schema_if_needed(db)

if __name__ == '__main__':
    create_schema()
    print("Database schema checked/created/migrated.")