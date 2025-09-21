import sqlite3
import os
import json
import fcntl
import time
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
    
    if 'role' not in columns and 'is_admin' in columns:
        print("Migrating database: adding 'role' column and migrating from 'is_admin'.")
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        cursor.execute("UPDATE users SET role = 'admin' WHERE is_admin = 1")
        # We can drop the old column if we want, but it's safer to leave it for now.
        cursor.execute('ALTER TABLE users DROP COLUMN is_admin')
        db.commit()

    if 'kindle_email' not in columns:
        print("Migrating database: adding 'kindle_email' column to users table.")
        cursor.execute('ALTER TABLE users ADD COLUMN kindle_email TEXT')
        db.commit()

    if 'theme' not in columns:
        print("Migrating database: adding 'theme' column to users table.")
        cursor.execute("ALTER TABLE users ADD COLUMN theme TEXT DEFAULT 'auto'")
        db.commit()

    if 'force_epub_conversion' not in columns:
        print("Migrating database: adding 'force_epub_conversion' column to users table.")
        cursor.execute('ALTER TABLE users ADD COLUMN force_epub_conversion INTEGER NOT NULL DEFAULT 1')
        db.commit()

    if 'kosync_userkey' not in columns:
        print("Migrating database: adding 'kosync_userkey' column to users table.")
        cursor.execute('ALTER TABLE users ADD COLUMN kosync_userkey TEXT')
        db.commit()

    # 检查 mcp_tokens 表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mcp_tokens'")
    if cursor.fetchone() is None:
        print("Migrating database: creating 'mcp_tokens' table.")
        create_mcp_tokens_table(cursor)
        db.commit()

    # 检查 invite_codes 表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='invite_codes'")
    if cursor.fetchone() is None:
        print("Migrating database: creating 'invite_codes' table.")
        create_invite_codes_table(cursor)
        db.commit()

    if 'stats_enabled' not in columns:
        print("Migrating database: adding 'stats_enabled' column to users table.")
        cursor.execute('ALTER TABLE users ADD COLUMN stats_enabled INTEGER NOT NULL DEFAULT 1')
        db.commit()

    if 'stats_public' not in columns:
        print("Migrating database: adding 'stats_public' column to users table.")
        cursor.execute('ALTER TABLE users ADD COLUMN stats_public INTEGER NOT NULL DEFAULT 0')
        db.commit()

    if 'language' not in columns:
        print("Migrating database: adding 'language' column to users table.")
        cursor.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'zh_Hans'")
        db.commit()

    # Add TTS settings columns
    tts_columns = {
        'tts_provider': "TEXT DEFAULT 'edge'",
        'tts_voice': "TEXT DEFAULT 'zh-CN-YunjianNeural'",
        'tts_api_key': "TEXT",
        'tts_base_url': "TEXT",
        'tts_model': "TEXT",
        'tts_rate': "TEXT DEFAULT '+0%'",
        'tts_volume': "TEXT DEFAULT '+0%'",
        'tts_pitch': "TEXT DEFAULT '+0Hz'"
    }
    for col, col_type in tts_columns.items():
        if col not in columns:
            print(f"Migrating database: adding '{col}' column to users table.")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
            db.commit()

    # 检查 audiobook_tasks 表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audiobook_tasks'")
    if cursor.fetchone() is None:
        print("Migrating database: creating 'audiobook_tasks' table.")
        create_audiobook_tasks_table(cursor)
        db.commit()
    else:
        # 如果表已存在，检查是否需要迁移 message -> status_key
        cursor.execute("PRAGMA table_info(audiobook_tasks)")
        task_columns = [row['name'] for row in cursor.fetchall()]
        if 'message' in task_columns:
            print("Migrating database: altering 'audiobook_tasks' table from message to status_key/status_params.")
            # 使用 ALTER TABLE RENAME COLUMN (SQLite 3.25.0+)
            cursor.execute("ALTER TABLE audiobook_tasks RENAME COLUMN message TO status_key")
            cursor.execute("ALTER TABLE audiobook_tasks ADD COLUMN status_params TEXT")
            db.commit()
        elif 'status_key' not in task_columns:
             # 兼容非常旧的、没有 message 列的版本
             cursor.execute("ALTER TABLE audiobook_tasks ADD COLUMN status_key TEXT")
             cursor.execute("ALTER TABLE audiobook_tasks ADD COLUMN status_params TEXT")
             db.commit()


def create_audiobook_tasks_table(cursor):
    """创建有声书任务表的辅助函数"""
    cursor.execute('''
        CREATE TABLE audiobook_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            book_id INTEGER NOT NULL,
            library_type TEXT NOT NULL,
            status TEXT NOT NULL,
            status_key TEXT,
            status_params TEXT,
            percentage INTEGER,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
    ''')
    # 创建触发器以自动更新 updated_at
    cursor.execute('''
        CREATE TRIGGER update_audiobook_tasks_updated_at
        AFTER UPDATE ON audiobook_tasks
        FOR EACH ROW
        BEGIN
            UPDATE audiobook_tasks SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
        END;
    ''')

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

def create_invite_codes_table(cursor):
    """创建邀请码表的辅助函数"""
    cursor.execute('''
        CREATE TABLE invite_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            used_at TIMESTAMP NULL,
            used_by INTEGER NULL,
            expires_at TIMESTAMP NULL,
            max_uses INTEGER DEFAULT 1,
            current_uses INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE CASCADE,
            FOREIGN KEY (used_by) REFERENCES users (id) ON DELETE SET NULL
        );
    ''')

def create_schema():
    """
    创建数据库和表结构，并执行必要的迁移。
    使用文件锁来防止多进程并发问题。
    """
    lock_path = DATABASE_PATH + '.lock'
    with open(lock_path, 'w') as lock_file:
        try:
            # 尝试获取锁，如果失败则等待
            fcntl.flock(lock_file, fcntl.LOCK_EX)
            
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
                            role TEXT NOT NULL DEFAULT 'user',
                            otp_secret TEXT,
                            send_format_priority TEXT,
                            kindle_email TEXT,
                            theme TEXT DEFAULT 'auto',
                            force_epub_conversion INTEGER NOT NULL DEFAULT 1,
                            kosync_userkey TEXT,
                            stats_enabled INTEGER NOT NULL DEFAULT 1,
                            stats_public INTEGER NOT NULL DEFAULT 0,
                            language TEXT DEFAULT 'zh_Hans',
                            tts_provider TEXT DEFAULT 'edge',
                            tts_voice TEXT DEFAULT 'zh-CN-YunjianNeural',
                            tts_api_key TEXT,
                            tts_base_url TEXT,
                            tts_model TEXT,
                            tts_rate TEXT DEFAULT '+0%',
                            tts_volume TEXT DEFAULT '+0%',
                            tts_pitch TEXT DEFAULT '+0Hz'
                        );
                    ''')
                    # MCP Tokens Table
                    create_mcp_tokens_table(cursor)
                    create_invite_codes_table(cursor)
                    create_audiobook_tasks_table(cursor)
                    db.commit()
                    print("Database tables created.")
                else:
                    # 如果数据库已存在，检查是否需要更新 schema
                    update_schema_if_needed(db)
        finally:
            # 确保锁被释放
            fcntl.flock(lock_file, fcntl.LOCK_UN)

if __name__ == '__main__':
    create_schema()
    print("Database schema checked/created/migrated.")