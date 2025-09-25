import functools
import json
import os
import re
import requests
import shutil
import subprocess
import tempfile
from flask import Blueprint, request, jsonify, g
from contextlib import closing
import database
import config_manager
import ebooklib
from ebooklib import epub
from lxml import etree, html
from epub_fixer import fix_epub_for_kindle

# Import necessary functions from other modules
from .main import get_calibre_books
# Rename the original function to avoid conflicts
from .api.calibre import get_calibre_book_details as get_raw_calibre_book_details
from .api.books import _push_calibre_to_anx_logic, _send_to_kindle_logic, _get_processed_epub_for_book
from anx_library import get_anx_books, get_anx_book_details
from utils.epub_utils import _get_text_from_html, _extract_toc_from_epub, _process_entire_epub, _count_words
from blueprints.api.audiobook import generate_audiobook_route
from utils.audiobook_tasks_db import get_latest_task_for_book
 
mcp_bp = Blueprint('mcp', __name__, url_prefix='/mcp')
 
def token_required(f):
    """Decorator to require a valid MCP token."""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.args.get('token')
        if not token:
            return jsonify({'error': 'Missing token'}), 401

        token = token.strip()

        with closing(database.get_db()) as db:
            token_data = db.execute('SELECT * FROM mcp_tokens WHERE token = ?', (token,)).fetchone()
        
        if not token_data:
            return jsonify({'error': 'Invalid token'}), 403
        
        with closing(database.get_db()) as db:
            user = db.execute('SELECT * FROM users WHERE id = ?', (token_data['user_id'],)).fetchone()
        
        if not user:
             return jsonify({'error': 'User not found for token'}), 403

        g.user = user
        return f(*args, **kwargs)
    return decorated_function

# --- Data Formatting for MCP ---

def format_calibre_book_data_for_mcp(book_data):
    """Formats and filters Calibre book data specifically for MCP tool output."""
    if not book_data:
        return None

    book_id = book_data.get('application_id') or book_data.get('id')
    if book_id is None:
        return None

    # Define the fields that are useful for a person reading the output.
    return {
        'book_id': book_id,
        'title': book_data.get('title', 'N/A'),
        'authors': book_data.get('authors', []),
        'tags': book_data.get('tags', []),
        'series': book_data.get('series', ''),
        'publisher': book_data.get('publisher', ''),
        'pubdate': (book_data.get('pubdate') or '').split('T')[0],
        'comments': book_data.get('comments', ''),
        'rating': book_data.get('rating', 0),
        'formats': list(book_data.get('format_metadata', {}).keys())
    }

# --- Tool Implementations ---

def search_calibre_books(search_expression: str, limit: int = 20):
    """
    根据一个搜索表达式在 Calibre 书库中搜索书籍。
    该函数直接使用 Calibre 强大的搜索查询语言。
    """
    books, _unused = get_calibre_books(search_query=search_expression, page=1, page_size=limit)
    return [format_calibre_book_data_for_mcp(book) for book in books if book]

def get_recent_calibre_books(limit: int = 20):
    books, _unused = get_calibre_books(page=1, page_size=limit)
    return [format_calibre_book_data_for_mcp(book) for book in books if book]

def get_calibre_book_details(book_id: int):
    """Wrapper for getting and formatting book details."""
    raw_details = get_raw_calibre_book_details(book_id)
    return format_calibre_book_data_for_mcp(raw_details)

def get_recent_anx_books(limit: int = 20):
    books = get_anx_books(g.user['username'])
    return books[:limit]

def push_calibre_book_to_anx(book_id: int):
    return _push_calibre_to_anx_logic(dict(g.user), book_id)

def send_calibre_book_to_kindle(book_id: int):
    return _send_to_kindle_logic(dict(g.user), book_id)

def _get_processed_epub_for_anx_book(id: int, username: str):
    book_details = get_anx_book_details(username, id)
    if not book_details:
        return None, "BOOK_NOT_FOUND", False

    file_path = book_details.get('file_path')
    if not file_path:
        return None, "FILE_PATH_MISSING", False

    from anx_library import get_anx_user_dirs
    dirs = get_anx_user_dirs(username)
    if not dirs:
        return None, "USER_DIR_NOT_FOUND", False

    full_file_path = os.path.join(dirs['base'], 'data', file_path)
    if not os.path.exists(full_file_path):
        return None, "FILE_NOT_FOUND", False

    needs_conversion = not full_file_path.lower().endswith('.epub')

    with tempfile.TemporaryDirectory() as temp_dir:
        epub_to_process_path = None
        
        if not needs_conversion:
            epub_to_process_path = os.path.join(temp_dir, os.path.basename(full_file_path))
            shutil.copy2(full_file_path, epub_to_process_path)
        else:
            if not shutil.which('ebook-converter'):
                return None, "CONVERTER_NOT_FOUND", False

            base_name, _unused = os.path.splitext(os.path.basename(full_file_path))
            epub_filename = f"{base_name}.epub"
            dest_path = os.path.join(temp_dir, epub_filename)

            try:
                subprocess.run(
                    ['ebook-converter', full_file_path, dest_path],
                    capture_output=True, text=True, check=True, timeout=300
                )
                epub_to_process_path = dest_path
            except Exception:
                return None, "CONVERSION_FAILED", False

        if not epub_to_process_path or not os.path.exists(epub_to_process_path):
            return None, "PROCESSING_FAILED", False

        fixed_epub_path = fix_epub_for_kindle(epub_to_process_path, force_language='zh')
        
        with open(fixed_epub_path, 'rb') as f:
            content_to_send = f.read()

        final_filename = os.path.basename(fixed_epub_path)
        return content_to_send, final_filename, needs_conversion

def get_calibre_epub_table_of_contents(book_id: int):
    user_dict = dict(g.user)
    epub_content, epub_filename, _unused = _get_processed_epub_for_book(book_id, user_dict)

    if epub_filename == 'CONVERTER_NOT_FOUND':
        return {'error': '此书需要转换为 EPUB 格式，但当前环境缺少 `ebook-converter` 工具。'}
    if not epub_content:
        return {'error': '无法获取或处理书籍的 EPUB 文件。'}

    with tempfile.NamedTemporaryFile(suffix='.epub', delete=True) as temp_file:
        temp_file.write(epub_content)
        temp_file.flush()
        
        try:
            book = epub.read_epub(temp_file.name)
            toc_items = _extract_toc_from_epub(book)
            # Add chapter numbers for user convenience
            for i, item in enumerate(toc_items):
                item['chapter_number'] = i + 1

            book_details = get_raw_calibre_book_details(book_id)
            return {
                "book_id": book_id,
                "book_title": book_details.get('title', 'N/A'),
                "total_chapters": len(toc_items),
                "chapters": toc_items
            }
        except Exception as e:
            return {"error": f"解析 EPUB 文件时出错: {str(e)}"}

def get_anx_epub_table_of_contents(id: int):
    epub_content, epub_filename, _unused = _get_processed_epub_for_anx_book(id, g.user['username'])

    if epub_filename == 'CONVERTER_NOT_FOUND':
        return {'error': '此书需要转换为 EPUB 格式，但当前环境缺少 `ebook-converter` 工具。'}
    if not epub_content:
        return {'error': f'无法获取或处理书籍的 EPUB 文件。错误代码: {epub_filename}'}

    with tempfile.NamedTemporaryFile(suffix='.epub', delete=True) as temp_file:
        temp_file.write(epub_content)
        temp_file.flush()
        
        try:
            book = epub.read_epub(temp_file.name)
            toc_items = _extract_toc_from_epub(book)
            for i, item in enumerate(toc_items):
                item['chapter_number'] = i + 1

            book_details = get_anx_book_details(g.user['username'], id)
            return {
                "id": id,
                "book_title": book_details.get('title', 'N/A'),
                "total_chapters": len(toc_items),
                "chapters": toc_items
            }
        except Exception as e:
            return {"error": f"解析 EPUB 文件时出错: {str(e)}"}

def _get_chapter_content_logic(book_id, chapter_number, get_epub_content_func, get_details_func):
    """通用逻辑：使用高性能函数获取指定章节的内容。"""
    epub_content, epub_filename, _ = get_epub_content_func()
    if 'error' in (epub_filename or {}): return epub_filename
    if not epub_content: return {'error': f'无法获取或处理书籍的 EPUB 文件。代码: {epub_filename}'}

    with tempfile.NamedTemporaryFile(suffix='.epub', delete=True) as temp_file:
        temp_file.write(epub_content)
        temp_file.flush()
        processed_data = _process_entire_epub(temp_file.name)

    if 'error' in processed_data:
        return processed_data

    total_chapters = processed_data.get('total_chapters', 0)
    if not (1 <= chapter_number <= total_chapters):
        return {"error": f"章节号 {chapter_number} 无效，有效范围: 1-{total_chapters}"}

    chapter_data = processed_data['processed_chapters'][chapter_number - 1]
    
    book_details = get_details_func(book_id)
    return {
        'book_id': book_id,
        'book_title': book_details.get('title', 'N/A'),
        'chapter_number': chapter_number,
        'chapter_title': chapter_data.get('title', 'N/A'),
        'content': chapter_data.get('html_content', '')
    }

def get_calibre_epub_chapter_content(book_id: int, chapter_number: int):
    """获取指定 Calibre 书籍的指定章节完整内容。"""
    user_dict = dict(g.user)
    get_epub_func = lambda: _get_processed_epub_for_book(book_id, user_dict)
    return _get_chapter_content_logic(book_id, chapter_number, get_epub_func, get_raw_calibre_book_details)

def get_anx_epub_chapter_content(id: int, chapter_number: int):
    """获取指定 Anx 书籍的指定章节完整内容。"""
    get_epub_func = lambda: _get_processed_epub_for_anx_book(id, g.user['username'])
    get_details_func = lambda book_id: get_anx_book_details(g.user['username'], book_id)
    return _get_chapter_content_logic(id, chapter_number, get_epub_func, get_details_func)

def _get_entire_book_content_logic(book_id, get_epub_content_func, get_details_func):
    """通用逻辑：使用高性能函数获取整本书的纯文本内容。"""
    epub_content, epub_filename, _ = get_epub_content_func()
    if 'error' in (epub_filename or {}): return epub_filename
    if not epub_content: return {'error': f'无法获取或处理书籍的 EPUB 文件。代码: {epub_filename}'}

    with tempfile.NamedTemporaryFile(suffix='.epub', delete=True) as temp_file:
        temp_file.write(epub_content)
        temp_file.flush()
        processed_data = _process_entire_epub(temp_file.name)

    if 'error' in processed_data:
        return processed_data

    full_text_parts = []
    for chapter in processed_data.get('processed_chapters', []):
        text_content = _get_text_from_html(chapter.get('html_content', ''))
        full_text_parts.append(f"--- Chapter {chapter.get('chapter_number')}: {chapter.get('title', '')} ---\n\n{text_content}\n\n")
    
    book_details = get_details_func(book_id)
    return {
        'book_id': book_id,
        'book_title': book_details.get('title', 'N/A'),
        'full_text': "".join(full_text_parts)
    }

def _get_book_word_count_statistics_logic(book_id, get_epub_content_func, get_details_func):
    """通用逻辑：使用高性能函数获取书籍的字数统计信息。"""
    epub_content, epub_filename, _ = get_epub_content_func()
    if 'error' in (epub_filename or {}): return epub_filename
    if not epub_content: return {'error': f'无法获取或处理书籍的 EPUB 文件。代码: {epub_filename}'}

    with tempfile.NamedTemporaryFile(suffix='.epub', delete=True) as temp_file:
        temp_file.write(epub_content)
        temp_file.flush()
        processed_data = _process_entire_epub(temp_file.name)

    if 'error' in processed_data:
        return processed_data

    stats = []
    total_word_count = 0
    for chapter in processed_data.get('processed_chapters', []):
        text_content = _get_text_from_html(chapter.get('html_content', ''))
        word_count = _count_words(text_content)
        
        stats.append({
            'chapter_number': chapter.get('chapter_number'),
            'chapter_title': chapter.get('title', 'N/A'),
            'word_count': word_count
        })
        total_word_count += word_count
    
    book_details = get_details_func(book_id)
    return {
        'book_id': book_id,
        'book_title': book_details.get('title', 'N/A'),
        'total_word_count': total_word_count,
        'chapter_statistics': stats
    }

def get_calibre_entire_book_content(book_id: int):
    """获取指定 Calibre 书籍的完整纯文本内容。"""
    user_dict = dict(g.user)
    get_epub_func = lambda: _get_processed_epub_for_book(book_id, user_dict)
    return _get_entire_book_content_logic(book_id, get_epub_func, get_raw_calibre_book_details)

def get_anx_entire_book_content(id: int):
    """获取指定 Anx 书籍的完整纯文本内容。"""
    get_epub_func = lambda: _get_processed_epub_for_anx_book(id, g.user['username'])
    get_details_func = lambda book_id: get_anx_book_details(g.user['username'], book_id)
    return _get_entire_book_content_logic(id, get_epub_func, get_details_func)

def get_calibre_book_word_count_statistics(book_id: int):
    """获取指定 Calibre 书籍的字数统计信息（分章节和总计）。"""
    user_dict = dict(g.user)
    get_epub_func = lambda: _get_processed_epub_for_book(book_id, user_dict)
    return _get_book_word_count_statistics_logic(book_id, get_epub_func, get_raw_calibre_book_details)

def get_anx_book_word_count_statistics(id: int):
    """获取指定 Anx 书籍的字数统计信息（分章节和总计）。"""
    get_epub_func = lambda: _get_processed_epub_for_anx_book(id, g.user['username'])
    get_details_func = lambda book_id: get_anx_book_details(g.user['username'], book_id)
    return _get_book_word_count_statistics_logic(id, get_epub_func, get_details_func)


def generate_audiobook(book_id: int, library_type: str):
    """
    为指定的书籍生成有声书。
    :param book_id: 书籍的 ID
    :param library_type: 书库类型，'anx' 或 'calibre'
    """
    existing_task = get_latest_task_for_book(g.user['id'], book_id, library_type)
    if existing_task and existing_task['status'] not in ['error', 'completed']:
        return {'status': 'already_in_progress', 'task_id': existing_task['task_id']}

    from flask import current_app
    from types import SimpleNamespace
    
    # 正确的方法是使用 `data` 参数传递表单数据
    form_data = {'book_id': str(book_id), 'library': library_type}

    # 捕获外部作用域的 g.user (sqlite3.Row) 并将其转换为支持属性访问的对象
    user_dict = dict(g.user)
    user_object_for_context = SimpleNamespace(**user_dict)

    with current_app.test_request_context(method='POST', data=form_data):
        # 在测试上下文中，g 对象是全新的，所以需要重新赋值
        g.user = user_object_for_context

        response = generate_audiobook_route()

    # generate_audiobook_route 可能会返回一个 Response 对象，或者一个 (Response, status_code) 的元组
    response_obj = response
    if isinstance(response, tuple):
        response_obj = response[0]

    # 检查响应是否是 JSON 格式
    if hasattr(response_obj, 'is_json') and response_obj.is_json:
        return response_obj.get_json()
    else:
        status_code = response[1] if isinstance(response, tuple) else response_obj.status_code
        # 如果不是 JSON，可能是一个重定向或错误页面，我们需要处理它
        if status_code >= 200 and status_code < 400:
             # 假设成功，但没有 JSON 返回。检查数据库中的任务以确认。
             # 这是一个简化的处理方式，理想情况下应该从响应头等信息获取任务ID
             return {"status": "started_no_json_response", "message": "Request accepted, but no JSON response. Check status later."}
        else:
             return {"error": f"Failed with status code {status_code}", "response_data": response_obj.get_data(as_text=True)}


def get_audiobook_generation_status(task_id: str):
    """
    获取有声书生成任务的状态和进度。
    :param task_id: 任务的 ID
    """
    from utils.audiobook_tasks_db import get_audiobook_task_by_id
    task = get_audiobook_task_by_id(task_id) # get_audiobook_task_by_id 不需要 user_id
    if not task:
        return {'error': 'Task not found.'}
    
    # 安全检查：对于 Anx 库的书籍，确保任务属于当前用户
    if task['library_type'] == 'anx' and task['user_id'] != g.user['id']:
        return {'error': 'Task not found for this user.'}

    return dict(task)


def get_audiobook_status_by_book(book_id: int, library_type: str):
    """
    通过 book_id 和 library_type 获取书籍的最新有声书任务状态。
    :param book_id: 书籍的 ID
    :param library_type: 书库类型，'anx' 或 'calibre'
    """
    task = get_latest_task_for_book(g.user['id'], book_id, library_type)
    if not task:
        return {'status': 'not_found', 'message': 'No active or completed task found for this book.'}
    return dict(task)


# --- Main MCP Endpoint ---

TOOLS = {
    'generate_audiobook': {
        'function': generate_audiobook,
        'params': {'book_id': int, 'library_type': str},
        'description': "为指定的书籍生成有声书。library_type 必须是 'anx' 或 'calibre'。"
    },
    'get_audiobook_generation_status': {
        'function': get_audiobook_generation_status,
        'params': {'task_id': str},
        'description': '通过任务 ID 获取有声书生成任务的状态和进度。'
    },
    'get_audiobook_status_by_book': {
        'function': get_audiobook_status_by_book,
        'params': {'book_id': int, 'library_type': str},
        'description': "通过书籍 ID 和库类型（'anx' 或 'calibre'）获取最新的有声书任务状态。"
    },
    'search_calibre_books': {
        'function': search_calibre_books,
        'params': {'search_expression': str, 'limit': int},
        'description': """使用 Calibre 的搜索语法搜索书籍。支持简单的模糊搜索和高级的字段查询。
基础搜索 (模糊匹配): 直接提供关键词即可。例如: "三体"
高级搜索 (构建复杂查询):
- 字段搜索: field_name:"value"。例如: title:"Pride and Prejudice" 或 author:Austen。常用字段: title, authors, tags, series, publisher, pubdate, comments, rating, date, series, size, formats, last_modified。自定义字段示例(库，已读日期): #library:"My Lib", #readdate:>=2023-01-15 (以 # 开头)。
- 布尔运算符: 使用 AND, OR, NOT (或 &, |, !) 组合条件。例如: tags:fiction AND tags:classic 或 title:history NOT author:Jones。
- 比较运算符: 对数字或日期字段使用 <, >, <=, >=, =。例如: pubdate:>2020-01-01 或 rating:>=4。
- 通配符: * 匹配任意字符序列, ? 匹配单个字符。例如: title:hist* 或 author:Sm?th。
- 正则表达式: field_name:~"regex"。例如: title:~"war.*peace"。"""
    },
    'get_recent_calibre_books': {
        'function': get_recent_calibre_books,
        'params': {'limit': int},
        'description': '获取最近添加到 Calibre 书库的书籍列表。'
    },
    'get_calibre_book_details': {
        'function': get_calibre_book_details,
        'params': {'book_id': int},
        'description': '获取指定 ID 的 Calibre 书籍的详细信息。'
    },
    'get_recent_anx_books': {
        'function': get_recent_anx_books,
        'params': {'limit': int},
        'description': '获取当前用户的 Anx 书库（正在看的书库）中最近的书籍列表。'
    },
    'get_anx_book_details': {
        'function': get_anx_book_details,
        'params': {'id': int},
        'description': '获取指定 ID 的 Anx 书籍（正在看的书库）的详细信息。'
    },
    'push_calibre_book_to_anx': {
        'function': push_calibre_book_to_anx,
        'params': {'book_id': int},
        'description': '将指定的 Calibre 书籍推送到当前用户的 Anx 书库（正在看的书库）。'
    },
    'send_calibre_book_to_kindle': {
        'function': send_calibre_book_to_kindle,
        'params': {'book_id': int},
        'description': '将指定的 Calibre 书籍发送到当前用户配置的 Kindle 邮箱。'
    },
    'get_calibre_epub_table_of_contents': {
        'function': get_calibre_epub_table_of_contents,
        'params': {'book_id': int},
        'description': '获取指定 Calibre 书籍的目录章节列表。如果书籍不是 EPUB 格式，会自动尝试转换。'
    },
    'get_calibre_epub_chapter_content': {
        'function': get_calibre_epub_chapter_content,
        'params': {'book_id': int, 'chapter_number': int},
        'description': '获取指定 Calibre 书籍的指定章节完整内容。如果书籍不是 EPUB 格式，会自动尝试转换。'
    },
    'get_anx_epub_table_of_contents': {
        'function': get_anx_epub_table_of_contents,
        'params': {'id': int},
        'description': '获取指定 Anx 书库（正在看的书库）中书籍的目录章节列表。如果书籍不是 EPUB 格式，会自动尝试转换。'
    },
    'get_anx_epub_chapter_content': {
        'function': get_anx_epub_chapter_content,
        'params': {'id': int, 'chapter_number': int},
        'description': '获取指定 Anx 书库（正在看的书库）中书籍的指定章节完整内容。如果书籍不是 EPUB 格式，会自动尝试转换。'
    },
    'get_calibre_entire_book_content': {
        'function': get_calibre_entire_book_content,
        'params': {'book_id': int},
        'description': '获取指定 Calibre 书籍的完整纯文本内容（保留段落格式）。'
    },
    'get_anx_entire_book_content': {
        'function': get_anx_entire_book_content,
        'params': {'id': int},
        'description': '获取指定 Anx 书籍的完整纯文本内容（保留段落格式）。'
    },
    'get_calibre_book_word_count_statistics': {
        'function': get_calibre_book_word_count_statistics,
        'params': {'book_id': int},
        'description': '获取指定 Calibre 书籍的字数统计信息（分章节和总计）。对于中文等语言统计字数，对于英文等语言统计单词数。'
    },
    'get_anx_book_word_count_statistics': {
        'function': get_anx_book_word_count_statistics,
        'params': {'id': int},
        'description': '获取指定 Anx 书籍的字数统计信息（分章节和总计）。对于中文等语言统计字数，对于英文等语言统计单词数。'
    }
}

def get_input_schema(params):
    properties = {}
    required = []
    for name, type_hint in params.items():
        json_type = "string"
        if type_hint == int:
            json_type = "integer"
        elif type_hint == float:
            json_type = "number"
        elif type_hint == bool:
            json_type = "boolean"
        
        properties[name] = {"type": json_type, "description": ""} # Placeholder description
        required.append(name)
        
    return {"type": "object", "properties": properties, "required": required}


@mcp_bp.route('', methods=['POST'])
@token_required
def mcp_endpoint():
    """Main MCP endpoint, compliant with JSON-RPC 2.0 and MCP Lifecycle."""
    try:
        data = request.get_json()
        if not data or 'jsonrpc' not in data or data['jsonrpc'] != '2.0':
            return jsonify({"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": None}), 400
        
        req_id = data.get('id')
        method = data.get('method')
        params = data.get('params', {})

        if method == 'initialize':
            return jsonify({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "anx-calibre-manager", "version": "0.1.0"}
                }
            })
        
        if method == 'notifications/initialized':
            return "", 204

        if method == 'tools/list':
            tool_list = [{"name": name, "description": info['description'], "inputSchema": get_input_schema(info['params'])} for name, info in TOOLS.items()]
            return jsonify({"jsonrpc": "2.0", "id": req_id, "result": {"tools": tool_list}})

        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})

            if not tool_name or tool_name not in TOOLS:
                return jsonify({"jsonrpc": "2.0", "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"}, "id": req_id}), 404

            tool_info = TOOLS[tool_name]
            tool_function = tool_info['function']
            
            # 创建一个只包含目标函数所需参数的新字典，以避免意外的关键字参数错误
            expected_params = tool_info.get('params', {}).keys()
            filtered_arguments = {k: v for k, v in arguments.items() if k in expected_params}

            if tool_name == 'get_anx_book_details':
                if 'id' in arguments:
                    # 'id' is the expected param, but the function needs 'book_id'
                    filtered_arguments['book_id'] = arguments.get('id')
                    if 'id' in filtered_arguments:
                        del filtered_arguments['id']
                filtered_arguments['username'] = g.user['username']

            try:
                result = tool_function(**filtered_arguments)
                result_text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": result_text}], "isError": False}
                })
            except Exception as e:
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": f"Error executing tool {tool_name}: {str(e)}"}], "isError": True}
                })
        else:
            return jsonify({"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": req_id}), 404

    except Exception as e:
        return jsonify({"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Internal error: {str(e)}"}, "id": None}), 500