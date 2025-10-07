import asyncio
import threading
import uuid
import os
import tempfile
import sqlite3
from contextlib import closing
from flask import Blueprint, request, jsonify, g, send_file
from werkzeug.utils import secure_filename
from flask_babel import gettext as _

import config_manager
# 内部导入
from utils.audiobook_generator import AudiobookGenerator, TTSConfig, EdgeTTSProvider, OpenAITTSProvider
from .books import _get_processed_epub_for_book
from .calibre import get_calibre_book_details
from anx_library import get_anx_user_dirs
from utils.text import generate_audiobook_filename
from utils.covers import get_anx_cover_data, get_calibre_cover_data
import json
from utils.audiobook_tasks_db import (
    add_audiobook_task,
    update_audiobook_task,
    get_audiobook_task_by_id,
    get_audiobook_task_by_book,
    get_latest_task_for_book,
)
from utils.tts_static_data import EDGE_TTS_VOICES, OPENAI_TTS_VOICES

audiobook_bp = Blueprint('audiobook_api', __name__, url_prefix='/api/audiobook')

@audiobook_bp.route('/tts_voices', methods=['GET'])
def get_tts_voices():
    """Returns a list of supported voices for TTS providers."""
    return jsonify({
        'edge_tts': EDGE_TTS_VOICES,
        'openai_tts': OPENAI_TTS_VOICES
    })


def get_anx_book_path(username, book_id):
    """根据 book_id 获取 Anx 书籍的完整文件路径"""
    dirs = get_anx_user_dirs(username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        raise FileNotFoundError("Anx database not found.")
    
    with closing(sqlite3.connect(dirs["db_path"])) as db:
        db.row_factory = sqlite3.Row
        book_row = db.execute("SELECT file_path FROM tb_books WHERE id = ?", (book_id,)).fetchone()
        if not book_row or not book_row['file_path']:
            raise FileNotFoundError(f"Anx book file with ID {book_id} not found.")
        
        return os.path.join(dirs["workspace"], book_row['file_path'])


def get_anx_book_details(username, book_id):
    """根据 book_id 获取 Anx 书籍的标题和作者"""
    dirs = get_anx_user_dirs(username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        return None, None
    
    with closing(sqlite3.connect(dirs["db_path"])) as db:
        db.row_factory = sqlite3.Row
        book_row = db.execute("SELECT title, author FROM tb_books WHERE id = ?", (book_id,)).fetchone()
        if not book_row:
            return None, None
        return book_row['title'], book_row['author']


def get_calibre_book_as_temp_file(user_dict, book_id):
    """获取 Calibre 书籍的 EPUB 内容并存入临时文件"""
    language = (user_dict.get('language') or 'zh').split('_')[0]
    content, filename, _ = _get_processed_epub_for_book(book_id, user_dict, language=language)
    
    if filename == 'CONVERTER_NOT_FOUND':
        raise RuntimeError("ebook-converter tool is missing.")
    if not content or not filename:
        raise FileNotFoundError(f"Could not get or process Calibre book ID {book_id}.")

    # 创建一个临时文件来保存 EPUB 内容
    # 注意：需要确保这个文件在任务结束后被删除
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".epub")
    temp_file.write(content)
    temp_file.close()
    return temp_file.name


def run_async_task(target, *args, **kwargs):
    """在一个新的事件循环中运行异步任务的线程目标函数，并可选地在之后清理一个临时文件。"""
    temp_file_to_clean = kwargs.pop('temp_file_to_clean', None)
    try:
        asyncio.run(target(*args, **kwargs))
    except Exception as e:
        print(f"异步任务线程中发生错误: {e}")
    finally:
        # 清理临时文件
        if temp_file_to_clean and os.path.exists(temp_file_to_clean):
            os.remove(temp_file_to_clean)
            print(f"已清理临时文件: {temp_file_to_clean}")


@audiobook_bp.route('/generate', methods=['POST'])
def generate_audiobook_route():
    """
    启动一个有声书生成任务。
    需要 'book_id' 和 'library' ('anx' 或 'calibre') 在 POST 请求的 form data 中。
    """
    form_data = request.form
    if 'book_id' not in form_data or 'library' not in form_data:
        return jsonify({"error": _("'book_id' or 'library' is missing from the request")}), 400

    book_id = int(form_data['book_id'])
    library = form_data['library']
    
    # 检查是否已有正在进行的任务
    existing_task = get_audiobook_task_by_book(g.user.id, book_id, library)
    if existing_task:
        return jsonify({
            "error": _("A task for this book is already in progress."),
            "task_id": existing_task['task_id']
        }), 409

    task_id = str(uuid.uuid4())
    add_audiobook_task(task_id, g.user.id, book_id, library)

    async def update_progress_callback(status, data):
        """
        用于更新任务状态的回调函数。
        它只将原始的 status_key 和 params 存入数据库，翻译操作推迟到 API 查询时进行。
        """
        update_audiobook_task(
            task_id,
            status,
            status_key=data.get("status_key"),
            status_params=data.get("params"),
            percentage=data.get("percentage"),
            file_path=data.get("path")
        )

    try:
        # 1. 加载TTS配置 (用户设置优先，全局配置其次)
        tts_config_data = {}
        tts_fields = [
            'tts_provider', 'tts_voice', 'tts_api_key', 'tts_base_url',
            'tts_model', 'tts_rate', 'tts_volume', 'tts_pitch'
        ]
        for field in tts_fields:
            user_value = getattr(g.user, field, None)
            if user_value is not None and user_value != '':
                tts_config_data[field.replace('tts_', '')] = user_value # 移除前缀以匹配TTSConfig
            else:
                default_key = f"DEFAULT_{field.upper()}"
                tts_config_data[field.replace('tts_', '')] = config_manager.config.get(default_key)

        # 从配置数据中分离出 provider，因为它不属于 TTSConfig
        provider = tts_config_data.pop('provider', 'edge_tts') # 默认为 edge_tts
        
        tts_config = TTSConfig(**tts_config_data)
        
        # 根据 provider 实例化不同的提供者
        if provider == 'openai_tts':
            tts_provider = OpenAITTSProvider(tts_config)
        else: # 默认为 edge_tts
            tts_provider = EdgeTTSProvider(tts_config)

        # 2. 获取书籍文件路径
        book_path_or_temp_file = None
        if library == 'anx':
            book_path_or_temp_file = get_anx_book_path(g.user.username, book_id)
        elif library == 'calibre':
            user_dict = {
                'username': g.user.username,
                'kindle_email': g.user.kindle_email,
                'send_format_priority': g.user.send_format_priority,
                'force_epub_conversion': g.user.force_epub_conversion,
                'language': g.user.language
            }
            book_path_or_temp_file = get_calibre_book_as_temp_file(user_dict, book_id)
        else:
            return jsonify({"error": _("Invalid 'library' type")}), 400

        # 3. 在后台线程中运行生成任务
        generator = AudiobookGenerator(tts_provider, update_progress_callback)
        
        # 准备传递给生成器的参数
        generator_kwargs = {}
        if library == 'anx':
            cover_data = get_anx_cover_data(g.user.username, book_id)
            if cover_data:
                generator_kwargs['cover_image_data'] = cover_data
        elif library == 'calibre':
            cover_data = get_calibre_cover_data(book_id)
            if cover_data:
                generator_kwargs['cover_image_data'] = cover_data

        # 检查是否使用了临时文件，以便在任务结束后清理
        if "tmp" in book_path_or_temp_file:
            # 这个特殊的 kwarg 是给 run_async_task 用的，而不是 generator.generate
            generator_kwargs['temp_file_to_clean'] = book_path_or_temp_file

        # 检查是否使用了临时文件，以便在任务结束后清理
        temp_file_to_clean = None
        if "tmp" in book_path_or_temp_file:
            temp_file_to_clean = book_path_or_temp_file
        
        # 将 temp_file_to_clean 单独传递给 run_async_task
        run_async_kwargs = {'temp_file_to_clean': temp_file_to_clean}

        user_dict_for_thread = {
            'id': g.user.id,
            'username': g.user.username,
            'kindle_email': g.user.kindle_email,
            'send_format_priority': g.user.send_format_priority,
            'force_epub_conversion': g.user.force_epub_conversion,
            'language': g.user.language
        }
        thread = threading.Thread(
            target=run_async_task,
            args=(generator.generate, str(book_id), library, user_dict_for_thread),
            # 修复：移除错误的 kwargs 重置，并正确合并外部封面数据和临时文件清理参数
            kwargs={**generator_kwargs, **run_async_kwargs}
        )
        thread.daemon = True
        thread.start()

        return jsonify({"task_id": task_id})

    except (FileNotFoundError, RuntimeError) as e:
        error_message = _("File error: %(error)s") % {'error': str(e)}
        update_audiobook_task(task_id, "error", status_key="FILE_ERROR", status_params={"error": str(e)})
        return jsonify({"error": error_message}), 404
    except Exception as e:
        error_message = _("An unknown error occurred while starting the task: %(error)s") % {'error': str(e)}
        update_audiobook_task(task_id, "error", status_key="UNKNOWN_ERROR", status_params={"error": str(e)})
        return jsonify({"error": error_message}), 500


@audiobook_bp.route('/status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """获取指定任务ID的状态。"""
    task = get_audiobook_task_by_id(task_id)
    if not task:
        return jsonify({"error": _("Task not found")}), 404
    
    # 直接返回原始任务数据，翻译由前端处理
    return jsonify(dict(task))


@audiobook_bp.route('/status_for_book', methods=['GET'])
def get_task_status_for_book():
    """获取特定书籍的活动任务状态。"""
    book_id = request.args.get('book_id', type=int)
    library_type = request.args.get('library')

    if not book_id or not library_type:
        return jsonify({"error": _("'book_id' or 'library' is missing from the request")}), 400

    task = get_latest_task_for_book(g.user.id, book_id, library_type)

    if not task:
        return jsonify({}) # 返回一个空对象表示没有活动任务
    
    # 直接返回原始任务数据，翻译由前端处理
    return jsonify(dict(task))


@audiobook_bp.route('/download/<task_id>', methods=['GET'])
def download_audiobook(task_id):
    """下载生成的有声书文件。"""
    task = get_audiobook_task_by_id(task_id)

    if not task:
        return jsonify({"error": _("Task not found")}), 404

    # 安全检查：对于非 Calibre 库的书籍，确保任务属于当前用户
    if task['library_type'] != 'calibre' and task['user_id'] != g.user.id:
        return jsonify({"error": _("Forbidden")}), 403

    # 检查任务是否成功完成
    if task['status'] != 'success':
        return jsonify({"error": _("Audiobook is not ready for download")}), 400

    # 检查文件路径是否存在
    file_path = task['file_path']
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": _("File not found on server")}), 404

    try:
        # 使用新的工具函数构造一致的文件名
        title, author = None, None
        if task['library_type'] == 'anx':
            title, author = get_anx_book_details(g.user.username, task['book_id'])
        elif task['library_type'] == 'calibre':
            details = get_calibre_book_details(task['book_id'])
            if details:
                title = details.get('title', 'Untitled')
                author = " & ".join(details.get('authors', ['Unknown']))

        if title and author:
            download_name = generate_audiobook_filename(
                title=title,
                author=author,
                book_id=task['book_id'],
                library_type=task['library_type'],
                username=g.user.username if task['library_type'] == 'anx' else None
            )
        else:
            # 如果无法获取元数据，则回退到原始文件名
            download_name = os.path.basename(file_path)

        return send_file(file_path, as_attachment=True, download_name=download_name)
    except Exception as e:
        return jsonify({"error": _("Could not send file: %(error)s") % {'error': str(e)}}), 500

@audiobook_bp.route('/delete/<task_id>', methods=['DELETE'])
def delete_audiobook(task_id):
    if g.user is None or g.user.id is None:
        return jsonify({'error': 'Authentication required'}), 401

    with closing(database.get_db()) as db:
        cursor = db.cursor()
        cursor.execute("SELECT * FROM audiobook_tasks WHERE task_id = ?", (task_id,))
        task = cursor.fetchone()

        if not task:
            return jsonify({'error': 'Task not found'}), 404

        # Permission Check
        is_owner = task['user_id'] == g.user.id
        is_maintainer = g.user.is_maintainer

        if task['library_type'] == 'anx' and not is_owner:
            return jsonify({'error': 'Permission denied to delete this Anx audiobook'}), 403
        
        if task['library_type'] == 'calibre' and not is_maintainer:
            return jsonify({'error': 'Only maintainers can delete Calibre audiobooks'}), 403

        # Proceed with deletion
        try:
            # 1. Delete the file
            if task['file_path'] and os.path.exists(task['file_path']):
                os.remove(task['file_path'])
            
            # 2. Delete progress records for this task (all users)
            cursor.execute("DELETE FROM audiobook_progress WHERE task_id = ?", (task_id,))

            # 3. Delete the task record
            cursor.execute("DELETE FROM audiobook_tasks WHERE task_id = ?", (task_id,))
            
            db.commit()
            
            return jsonify({'message': 'Audiobook deleted successfully'})

        except Exception as e:
            db.rollback()
            # Consider adding logging here
            return jsonify({'error': 'An error occurred during deletion'}), 500