import os
import requests
from contextlib import closing
import sqlite3

import config_manager
from utils.auth import get_calibre_auth
from anx_library import get_anx_user_dirs

def get_calibre_cover_data(book_id):
    """获取指定 Calibre 书籍的封面二进制数据"""
    config = config_manager.config
    url = f"{config['CALIBRE_URL']}/get/cover/{book_id}"
    try:
        response = requests.get(url, auth=get_calibre_auth(), stream=True)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"Error fetching cover for book {book_id}: {e}")
        return None

def get_anx_cover_data(username, book_id) -> bytes | None:
    """根据 book_id 从 Anx 数据库获取书籍封面数据"""
    dirs = get_anx_user_dirs(username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        return None
    
    with closing(sqlite3.connect(dirs["db_path"])) as db:
        db.row_factory = sqlite3.Row
        book_row = db.execute("SELECT cover_path FROM tb_books WHERE id = ?", (book_id,)).fetchone()
        if not book_row or not book_row['cover_path']:
            return None
        
        cover_full_path = os.path.join(dirs["workspace"], book_row['cover_path'])
        if os.path.exists(cover_full_path):
            with open(cover_full_path, 'rb') as f:
                return f.read()
    return None