import functools
import json
from flask import Blueprint, request, jsonify, g
from contextlib import closing
import database

# Import necessary functions from other modules
from .main import get_calibre_books, get_calibre_book_details
from .api import _push_calibre_to_anx_logic, _send_to_kindle_logic
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

# --- Tool Implementations ---

def search_calibre_books(query: str, limit: int = 20):
    books, _ = get_calibre_books(search_query=query, page=1, page_size=limit)
    return books

def get_recent_calibre_books(limit: int = 20):
    books, _ = get_calibre_books(page=1, page_size=limit)
    return books

def get_recent_anx_books(limit: int = 20):
    books = get_anx_books(g.user['username'])
    return books[:limit]

def push_calibre_book_to_anx(book_id: int):
    return _push_calibre_to_anx_logic(g.user, book_id)

def send_calibre_book_to_kindle(book_id: int):
    return _send_to_kindle_logic(g.user, book_id)

# --- Main MCP Endpoint ---

TOOLS = {
    'search_calibre_books': {
        'function': search_calibre_books,
        'params': {'query': str, 'limit': int},
        'description': '根据关键词搜索 Calibre 书库，并返回书籍列表。'
    },
    'get_recent_calibre_books': {
        'function': get_recent_calibre_books,
        'params': {'limit': int},
        'description': '获取最近添加到 Calibre 书库的书籍列表。'
    },
    'get_calibre_book_details': {
        'function': get_calibre_book_details,
        'params': {'book_id': int},
        'description': '获取指定 ID 的 Calibre 书籍的详细信息，包括所有元数据字段。'
    },
    'get_recent_anx_books': {
        'function': get_recent_anx_books,
        'params': {'limit': int},
        'description': '获取当前用户的 Anx 书库中最近的书籍列表。'
    },
    'get_anx_book_details': {
        'function': get_anx_book_details,
        'params': {'book_id': int},
        'description': '获取指定 ID 的 Anx 书籍的详细信息。'
    },
    'push_calibre_book_to_anx': {
        'function': push_calibre_book_to_anx,
        'params': {'book_id': int},
        'description': '将指定的 Calibre 书籍推送到当前用户的 Anx 书库。'
    },
    'send_calibre_book_to_kindle': {
        'function': send_calibre_book_to_kindle,
        'params': {'book_id': int},
        'description': '将指定的 Calibre 书籍发送到当前用户配置的 Kindle 邮箱。'
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