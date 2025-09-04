import functools
import json
import os
import requests
import shutil
import subprocess
import tempfile
from flask import Blueprint, request, jsonify, g
from contextlib import closing
import database
import config_manager
from ebooklib import epub
from lxml import etree, html
from epub_fixer import fix_epub_for_kindle

# Import necessary functions from other modules
from .main import get_calibre_books
# Rename the original function to avoid conflicts
from .main import get_calibre_book_details as get_raw_calibre_book_details
from .api import _push_calibre_to_anx_logic, _send_to_kindle_logic, _get_processed_epub_for_book
from anx_library import get_anx_books, get_anx_book_details

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

    book_id = book_data.get('id')
    if book_id is None:
        return None

    # Define the fields that are useful for a person reading the output.
    return {
        'id': book_id,
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
    books, _ = get_calibre_books(search_query=search_expression, page=1, page_size=limit)
    return [format_calibre_book_data_for_mcp(book) for book in books if book]

def get_recent_calibre_books(limit: int = 20):
    books, _ = get_calibre_books(page=1, page_size=limit)
    return [format_calibre_book_data_for_mcp(book) for book in books if book]

def get_calibre_book_details(book_id: int):
    """Wrapper for getting and formatting book details."""
    raw_details = get_raw_calibre_book_details(book_id)
    return format_calibre_book_data_for_mcp(raw_details)

def get_recent_anx_books(limit: int = 20):
    books = get_anx_books(g.user['username'])
    return books[:limit]

# --- EPUB Parsing Helpers ---

def _extract_toc_from_epub(epub_path):
    """Extracts the table of contents from an EPUB file."""
    book = epub.read_epub(epub_path)
    toc_items = []
    
    if hasattr(book, 'toc') and book.toc:
        chapter_num = 1
        for item in book.toc:
            if isinstance(item, tuple):
                section, children = item
                if hasattr(section, 'title') and hasattr(section, 'href'):
                    toc_items.append({"chapter_number": chapter_num, "title": section.title, "href": section.href})
                    chapter_num += 1
                for child in children:
                    if hasattr(child, 'title') and hasattr(child, 'href'):
                        toc_items.append({"chapter_number": chapter_num, "title": f"  {child.title}", "href": child.href})
                        chapter_num += 1
            else:
                if hasattr(item, 'title') and hasattr(item, 'href'):
                    toc_items.append({"chapter_number": chapter_num, "title": item.title, "href": item.href})
                    chapter_num += 1
    
    if not toc_items:
        chapter_num = 1
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item and item.get_type() == epub.ITEM_DOCUMENT:
                title = os.path.splitext(os.path.basename(item.get_name()))[0]
                toc_items.append({"chapter_number": chapter_num, "title": title, "href": item.get_name()})
                chapter_num += 1
    return toc_items

def _extract_content_from_epub(epub_path, chapter_number):
    """Extracts the content of a specific chapter from an EPUB file."""
    book = epub.read_epub(epub_path)
    
    chapter_items = []
    if hasattr(book, 'toc') and book.toc:
        for item in book.toc:
            if isinstance(item, tuple):
                section, children = item
                if hasattr(section, 'title') and hasattr(section, 'href'):
                    chapter_items.append((section.title, section.href))
                for child in children:
                    if hasattr(child, 'title') and hasattr(child, 'href'):
                        chapter_items.append((child.title, child.href))
            else:
                if hasattr(item, 'title') and hasattr(item, 'href'):
                    chapter_items.append((item.title, item.href))
    
    if not chapter_items:
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item and item.get_type() == epub.ITEM_DOCUMENT:
                title = os.path.splitext(os.path.basename(item.get_name()))[0]
                chapter_items.append((title, item.get_name()))
    
    if not (1 <= chapter_number <= len(chapter_items)):
        return {"error": f"章节号 {chapter_number} 无效，有效范围: 1-{len(chapter_items)}"}
    
    chapter_title, chapter_href = chapter_items[chapter_number - 1]
    clean_href = chapter_href.split('#')[0]
    
    target_item = book.get_item_with_href(clean_href)
    if not target_item:
        for item in book.get_items():
            if item.get_name() == clean_href:
                target_item = item
                break
    
    if not target_item:
        return {"error": f"无法找到章节文件: {clean_href}"}
    
    content = target_item.get_content().decode('utf-8', 'ignore')
    try:
        doc = html.fromstring(content)
        etree.strip_elements(doc, 'script', 'style')
        text_content = '\n'.join(line.strip() for line in doc.text_content().split('\n') if line.strip())
    except:
        text_content = content
        
    return {
        "chapter_title": chapter_title,
        "chapter_href": chapter_href,
        "content": text_content
    }

def push_calibre_book_to_anx(book_id: int):
    # The logic function expects a dictionary. g.user is a sqlite3.Row, which is dict-like.
    # To be safe and explicit, we convert it to a standard dict.
    return _push_calibre_to_anx_logic(dict(g.user), book_id)

def send_calibre_book_to_kindle(book_id: int):
    # The logic function expects a dictionary.
    return _send_to_kindle_logic(dict(g.user), book_id)

def _get_processed_epub_for_anx_book(book_id: int, username: str):
    """
    Core logic to get a processed EPUB for an Anx book.
    It handles converting (if necessary) and fixing the EPUB from a local file path.
    Returns a tuple: (content, filename, needs_conversion_flag) or (None, None, None) on error.
    """
    book_details = get_anx_book_details(username, book_id)
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
            # If it's already an EPUB, we still copy it to the temp dir for uniform processing
            epub_to_process_path = os.path.join(temp_dir, os.path.basename(full_file_path))
            shutil.copy2(full_file_path, epub_to_process_path)
        else:
            if not shutil.which('ebook-converter'):
                return None, "CONVERTER_NOT_FOUND", False

            base_name, _ = os.path.splitext(os.path.basename(full_file_path))
            epub_filename = f"{base_name}.epub"
            dest_path = os.path.join(temp_dir, epub_filename)

            try:
                subprocess.run(
                    ['ebook-converter', full_file_path, dest_path],
                    capture_output=True, text=True, check=True, timeout=300
                )
                epub_to_process_path = dest_path
            except Exception as e:
                # Consider logging the error e
                return None, "CONVERSION_FAILED", False

        if not epub_to_process_path or not os.path.exists(epub_to_process_path):
            return None, "PROCESSING_FAILED", False

        # Fix the EPUB
        fixed_epub_path = fix_epub_for_kindle(epub_to_process_path, force_language='zh')
        
        with open(fixed_epub_path, 'rb') as f:
            content_to_send = f.read()

        final_filename = os.path.basename(fixed_epub_path)
        return content_to_send, final_filename, needs_conversion

def get_calibre_epub_table_of_contents(book_id: int):
    """
    获取指定 Calibre 书籍的 EPUB 目录章节列表（包含章节序号和标题）。
    如果书籍不是 EPUB 格式，会尝试自动转换。
    """
    user_dict = dict(g.user)
    epub_content, epub_filename, _ = _get_processed_epub_for_book(book_id, user_dict)

    if epub_filename == 'CONVERTER_NOT_FOUND':
        return {'error': '此书需要转换为 EPUB 格式，但当前环境缺少 `ebook-converter` 工具。'}
    if not epub_content:
        return {'error': '无法获取或处理书籍的 EPUB 文件。'}

    import tempfile
    temp_epub_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            temp_file.write(epub_content)
            temp_epub_path = temp_file.name
        
        toc_items = _extract_toc_from_epub(temp_epub_path)
        
        book_details = get_raw_calibre_book_details(book_id)
        return {
            "book_id": book_id,
            "book_title": book_details.get('title', '') if book_details else 'N/A',
            "total_chapters": len(toc_items),
            "chapters": toc_items
        }
    except Exception as e:
        return {"error": f"解析 EPUB 文件时出错: {str(e)}"}
    finally:
        if temp_epub_path and os.path.exists(temp_epub_path):
            os.unlink(temp_epub_path)

def get_calibre_epub_chapter_content(book_id: int, chapter_number: int):
    """
    获取指定 Calibre 书籍的指定章节完整内容。
    如果书籍不是 EPUB 格式，会尝试自动转换。
    """
    user_dict = dict(g.user)
    epub_content, epub_filename, _ = _get_processed_epub_for_book(book_id, user_dict)

    if epub_filename == 'CONVERTER_NOT_FOUND':
        return {'error': '此书需要转换为 EPUB 格式，但当前环境缺少 `ebook-converter` 工具。'}
    if not epub_content:
        return {'error': '无法获取或处理书籍的 EPUB 文件。'}

    import tempfile
    temp_epub_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            temp_file.write(epub_content)
            temp_epub_path = temp_file.name
        
        content_result = _extract_content_from_epub(temp_epub_path, chapter_number)
        if "error" in content_result:
            return content_result
        
        book_details = get_raw_calibre_book_details(book_id)
        return {
            "book_id": book_id,
            "book_title": book_details.get('title', '') if book_details else 'N/A',
            "chapter_number": chapter_number,
            **content_result
        }
    except Exception as e:
        return {"error": f"获取章节内容时出错: {str(e)}"}
    finally:
        if temp_epub_path and os.path.exists(temp_epub_path):
            os.unlink(temp_epub_path)

def get_anx_epub_table_of_contents(book_id: int):
    """
    获取指定 Anx 书库（正在看的书库）中书籍的目录章节列表（包含章节序号和标题）。
    如果书籍不是 EPUB 格式，会尝试自动转换。
    """
    epub_content, epub_filename, _ = _get_processed_epub_for_anx_book(book_id, g.user['username'])

    if epub_filename == 'CONVERTER_NOT_FOUND':
        return {'error': '此书需要转换为 EPUB 格式，但当前环境缺少 `ebook-converter` 工具。'}
    if not epub_content:
        return {'error': f'无法获取或处理书籍的 EPUB 文件。错误代码: {epub_filename}'}

    temp_epub_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            temp_file.write(epub_content)
            temp_epub_path = temp_file.name
        
        toc_items = _extract_toc_from_epub(temp_epub_path)
        
        book_details = get_anx_book_details(g.user['username'], book_id)
        return {
            "book_id": book_id,
            "book_title": book_details.get('title', '') if book_details else 'N/A',
            "total_chapters": len(toc_items),
            "chapters": toc_items
        }
    except Exception as e:
        return {"error": f"解析 EPUB 文件时出错: {str(e)}"}
    finally:
        if temp_epub_path and os.path.exists(temp_epub_path):
            os.unlink(temp_epub_path)

def get_anx_epub_chapter_content(book_id: int, chapter_number: int):
    """
    获取指定 Anx 书库（正在看的书库）中书籍的指定章节完整内容。
    如果书籍不是 EPUB 格式，会尝试自动转换。
    """
    epub_content, epub_filename, _ = _get_processed_epub_for_anx_book(book_id, g.user['username'])

    if epub_filename == 'CONVERTER_NOT_FOUND':
        return {'error': '此书需要转换为 EPUB 格式，但当前环境缺少 `ebook-converter` 工具。'}
    if not epub_content:
        return {'error': f'无法获取或处理书籍的 EPUB 文件。错误代码: {epub_filename}'}

    temp_epub_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.epub', delete=False) as temp_file:
            temp_file.write(epub_content)
            temp_epub_path = temp_file.name
        
        content_result = _extract_content_from_epub(temp_epub_path, chapter_number)
        if "error" in content_result:
            return content_result
        
        book_details = get_anx_book_details(g.user['username'], book_id)
        return {
            "book_id": book_id,
            "book_title": book_details.get('title', '') if book_details else 'N/A',
            "chapter_number": chapter_number,
            **content_result
        }
    except Exception as e:
        return {"error": f"获取章节内容时出错: {str(e)}"}
    finally:
        if temp_epub_path and os.path.exists(temp_epub_path):
            os.unlink(temp_epub_path)

# --- Main MCP Endpoint ---

TOOLS = {
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
        'params': {'book_id': int},
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
        'params': {'book_id': int},
        'description': '获取指定 Anx 书库（正在看的书库）中书籍的目录章节列表。如果书籍不是 EPUB 格式，会自动尝试转换。'
    },
    'get_anx_epub_chapter_content': {
        'function': get_anx_epub_chapter_content,
        'params': {'book_id': int, 'chapter_number': int},
        'description': '获取指定 Anx 书库（正在看的书库）中书籍的指定章节完整内容。如果书籍不是 EPUB 格式，会自动尝试转换。'
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
        # For simplicity, let's make all params optional for now, 
        # as we don't have default values specified in a structured way.
        # required.append(name)
        
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
            # Respond with server capabilities
            return jsonify({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05", # Echoing a recent version
                    "capabilities": {
                        "tools": {
                            "listChanged": False # We don't support dynamic tool changes
                        }
                    },
                    "serverInfo": {
                        "name": "anx-calibre-manager",
                        "version": "0.1.0"
                    }
                }
            })
        
        if method == 'notifications/initialized':
            # Client is ready, we can just acknowledge this.
            # No response is needed for notifications.
            return "", 204

        if method == 'tools/list':
            tool_list = []
            for name, info in TOOLS.items():
                tool_list.append({
                    "name": name,
                    "description": info['description'],
                    "inputSchema": get_input_schema(info['params'])
                })
            return jsonify({"jsonrpc": "2.0", "id": req_id, "result": {"tools": tool_list}})

        elif method == 'tools/call':
            tool_name = params.get('name')
            arguments = params.get('arguments', {})

            if not tool_name or tool_name not in TOOLS:
                return jsonify({"jsonrpc": "2.0", "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"}, "id": req_id}), 404

            tool_info = TOOLS[tool_name]
            tool_function = tool_info['function']
            
            if tool_name == 'get_anx_book_details':
                arguments['username'] = g.user['username']

            try:
                result = tool_function(**arguments)
                result_text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
                
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": result_text}],
                        "isError": False
                    }
                })
            except Exception as e:
                return jsonify({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error executing tool {tool_name}: {str(e)}"}],
                        "isError": True
                    }
                })
        else:
            return jsonify({"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": req_id}), 404

    except Exception as e:
        return jsonify({"jsonrpc": "2.0", "error": {"code": -32603, "message": f"Internal error: {str(e)}"}, "id": None}), 500