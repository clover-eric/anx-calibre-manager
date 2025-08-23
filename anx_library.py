import os
import sqlite3
import hashlib
import re
import shutil
from contextlib import closing
from datetime import datetime
from config_manager import config
from anx_db_schema import ANX_DB_SCHEMA

def initialize_anx_user_data(username):
    """Creates the necessary directory structure and initializes an empty Anx database for a new user."""
    dirs = get_anx_user_dirs(username)
    if not dirs:
        print(f"Could not get user directories for {username}. WEBDAV_ROOT might be missing.")
        return False, f"无法为用户 {username} 获取目录结构。"

    try:
        # Create all necessary directories
        # The full structure is /webdav/<user>/anx/data/file, etc.
        os.makedirs(dirs["file"], exist_ok=True)
        os.makedirs(dirs["cover"], exist_ok=True)
        os.makedirs(dirs["import"], exist_ok=True)
        os.makedirs(dirs["already_in"], exist_ok=True)

        # Initialize the database only if it doesn't exist
        if not os.path.exists(dirs["db_path"]):
            with closing(sqlite3.connect(dirs["db_path"])) as db:
                cursor = db.cursor()
                cursor.executescript(ANX_DB_SCHEMA)
                current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("""
                    INSERT INTO tb_groups (id, name, parent_id, is_deleted, create_time, update_time)
                    VALUES (0, 'Root', NULL, 0, ?, ?)
                """, (current_time, current_time))
                db.commit()
        
        return True, "用户 Anx 数据目录和数据库已成功初始化。"
    except Exception as e:
        print(f"Error initializing Anx data for user {username}: {e}")
        return False, f"初始化用户 Anx 数据时出错: {e}"

def get_anx_user_dirs(username):
    """Gets all the relevant directory paths for a user's Anx library."""
    webdav_root = config.get("WEBDAV_ROOT")
    if not webdav_root or not username:
        return None
    safe_username = os.path.basename(username)
    user_root = os.path.join(webdav_root, safe_username)
    base_dir = os.path.join(user_root, 'anx')
    
    return {
        "user_root": user_root,
        "base": base_dir,
        "db_path": os.path.join(base_dir, "database7.db"),
        "import": os.path.join(base_dir, "import"),
        "workspace": os.path.join(base_dir, "data"),
        "file": os.path.join(base_dir, "data", "file"),
        "cover": os.path.join(base_dir, "data", "cover"),
        "already_in": os.path.join(base_dir, "alreadyin"),
    }

def get_anx_books(username):
    """Fetches all non-deleted books for a user from their Anx database."""
    dirs = get_anx_user_dirs(username)
    db_path = dirs["db_path"] if dirs else None
    
    if not db_path or not os.path.exists(db_path):
        print(f"ANX DB not found for user {username} at {db_path}")
        return []

    books = []
    try:
        with closing(sqlite3.connect(db_path)) as db:
            db.row_factory = sqlite3.Row
            cursor = db.cursor()
            query = """
                SELECT
                    b.*,
                    COALESCE(SUM(rt.reading_time), 0) as total_reading_time,
                    COALESCE(COUNT(DISTINCT n.id), 0) as note_count
                FROM
                    tb_books b
                LEFT JOIN
                    tb_reading_time rt ON b.id = rt.book_id
                LEFT JOIN
                    tb_notes n ON b.id = n.book_id
                WHERE
                    b.is_deleted = 0
                GROUP BY
                    b.id
                ORDER BY
                    b.update_time DESC
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                books.append(dict(row))
    except Exception as e:
        print(f"Error reading Anx database for user {username}: {e}")
        return []
    
    return books

def get_anx_book_details(username, book_id):
    """Fetches the details for a single Anx book by its ID."""
    all_books = get_anx_books(username)
    for book in all_books:
        if book['id'] == book_id:
            return book
    return None

def _calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def process_anx_import_folder(username):
    """Processes files in a user's Anx import folder and adds them to the database."""
    dirs = get_anx_user_dirs(username)
    if not dirs:
        return {"error": "User directories not configured."}

    for path in [dirs["import"], dirs["file"], dirs["cover"], dirs["already_in"]]:
        os.makedirs(path, exist_ok=True)

    processed_count = 0
    skipped_count = 0
    
    for filename in os.listdir(dirs["import"]):
        file_path = os.path.join(dirs["import"], filename)
        if not os.path.isfile(file_path):
            continue

        base_name, extension = os.path.splitext(filename)
        extension = extension[1:].lower()
        
        allowed_extensions = ["epub", "mobi", "azw3", "pdf", "txt"]
        if extension not in allowed_extensions:
            shutil.move(file_path, os.path.join(dirs["already_in"], filename))
            continue

        title, author = base_name, "Unknown Author"
        match = re.match(r'^(.*) - (.*)$', base_name)
        if match:
            title, author = match.groups()
            
        file_md5 = _calculate_md5(file_path)

        with closing(sqlite3.connect(dirs["db_path"])) as db:
            cursor = db.cursor()
            cursor.execute("SELECT id, is_deleted FROM tb_books WHERE file_md5 = ?", (file_md5,))
            existing = cursor.fetchone()

            if existing:
                existing_id, is_deleted = existing
                # If the book was soft-deleted, reactivate it
                if is_deleted == 1:
                    print(f"Reactivating deleted book with MD5: {file_md5}")
                    
                    # Move new book file into place
                    dest_file_path = os.path.join(dirs["file"], filename)
                    shutil.move(file_path, dest_file_path)
                    file_relative_path = 'file/' + filename

                    # Move new cover file into place
                    cover_filename = f"{base_name}.jpg"
                    cover_path = os.path.join(dirs["import"], cover_filename)
                    cover_relative_path = ""
                    if os.path.exists(cover_path):
                        dest_cover_path = os.path.join(dirs["cover"], cover_filename)
                        shutil.move(cover_path, dest_cover_path)
                        cover_relative_path = 'cover/' + cover_filename

                    # Update the database record
                    current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
                    cursor.execute("""
                        UPDATE tb_books
                        SET is_deleted = 0,
                            update_time = ?,
                            file_path = ?,
                            cover_path = ?
                        WHERE id = ?
                    """, (current_time, file_relative_path, cover_relative_path, existing_id))
                    db.commit()
                    processed_count += 1
                else:
                    # It's a true duplicate, skip it
                    shutil.move(file_path, os.path.join(dirs["already_in"], filename))
                    skipped_count += 1
                
                continue

            # New book
            dest_file_path = os.path.join(dirs["file"], filename)
            shutil.move(file_path, dest_file_path)

            cover_filename = f"{base_name}.jpg"
            cover_path = os.path.join(dirs["import"], cover_filename)
            cover_relative_path = ""
            if os.path.exists(cover_path):
                dest_cover_path = os.path.join(dirs["cover"], cover_filename)
                shutil.move(cover_path, dest_cover_path)
                cover_relative_path = 'cover/' + cover_filename
            
            current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            file_relative_path = 'file/' + filename

            cursor.execute("""
                INSERT INTO tb_books (
                    title, author, cover_path, file_path, file_md5, create_time, update_time, 
                    is_deleted, last_read_position, reading_percentage, rating, group_id, description
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                title, author, cover_relative_path, file_relative_path, file_md5, 
                current_time, current_time, 0, '', 0.0, 0.0, 0, ''
            ))
            db.commit()
            processed_count += 1
            
    return {"processed": processed_count, "skipped": skipped_count}


def update_anx_book_metadata(username, book_id, data):
    """Updates the metadata for a specific book in a user's Anx database."""
    dirs = get_anx_user_dirs(username)
    db_path = dirs["db_path"] if dirs else None
    
    if not db_path or not os.path.exists(db_path):
        return False, "Anx 数据库未找到。"

    allowed_fields = ['title', 'author', 'rating', 'description']
    update_data = {key: data[key] for key in data if key in allowed_fields}
    
    if not update_data:
        return False, "没有提供有效数据进行更新。"

    update_data['update_time'] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    set_clause = ", ".join([f"{key} = ?" for key in update_data.keys()])
    values = list(update_data.values())
    values.append(book_id)
    query = f"UPDATE tb_books SET {set_clause} WHERE id = ?"

    try:
        with closing(sqlite3.connect(db_path)) as db:
            cursor = db.cursor()
            cursor.execute(query, tuple(values))
            db.commit()
            if cursor.rowcount == 0:
                return False, f"未找到 ID 为 {book_id} 的书籍。"
            return True, "元数据更新成功。"
    except Exception as e:
        print(f"Error updating Anx database for user {username}: {e}")
        return False, f"更新数据库时出错: {e}"

def delete_anx_book(username, book_id):
    """Deletes a book from a user's Anx library by marking it as deleted and removing files."""
    dirs = get_anx_user_dirs(username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        return False, "Anx 数据库未找到。"

    try:
        with closing(sqlite3.connect(dirs["db_path"])) as db:
            db.row_factory = sqlite3.Row
            cursor = db.cursor()
            
            cursor.execute("SELECT file_path, cover_path FROM tb_books WHERE id = ?", (book_id,))
            book_files = cursor.fetchone()
            
            if not book_files:
                return False, f"未找到 ID 为 {book_id} 的书籍。"

            current_time = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            cursor.execute("UPDATE tb_books SET is_deleted = 1, update_time = ? WHERE id = ?", (current_time, book_id))
            db.commit()

            if book_files['file_path']:
                file_to_delete = os.path.join(dirs["base"], 'data', book_files['file_path'])
                if os.path.exists(file_to_delete):
                    os.remove(file_to_delete)
            
            if book_files['cover_path']:
                cover_to_delete = os.path.join(dirs["base"], 'data', book_files['cover_path'])
                if os.path.exists(cover_to_delete):
                    os.remove(cover_to_delete)

            return True, "书籍已成功删除。"
    except Exception as e:
        print(f"Error deleting book {book_id} for user {username}: {e}")
        return False, f"删除书籍时出错: {e}"
