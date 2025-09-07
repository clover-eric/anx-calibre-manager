import json
import io
import os
import logging
import shutil
import subprocess
import tempfile
from flask import Blueprint, request, jsonify, g, send_file, send_from_directory
from flask_babel import gettext as _
from contextlib import closing
import sqlite3
import config_manager
from anx_library import (
    get_anx_user_dirs, 
    process_anx_import_folder, 
    update_anx_book_metadata,
    delete_anx_book
)
from .calibre import download_calibre_book, get_calibre_book_details, download_calibre_cover
from .email_service import send_email_with_config
from epub_fixer import fix_epub_for_kindle
from utils.text import random_english_text, safe_title, safe_author

books_bp = Blueprint('books', __name__, url_prefix='/api')

@books_bp.route('/download_anx_book/<int:book_id>', methods=['GET'])
def download_anx_book_api(book_id):
    dirs = get_anx_user_dirs(g.user.username)
    if not dirs or not os.path.exists(dirs["db_path"]):
        return jsonify({'error': _('Anx database not found.')}), 404
        
    try:
        with closing(sqlite3.connect(dirs["db_path"])) as db:
            db.row_factory = sqlite3.Row
            cursor = db.cursor()
            cursor.execute("SELECT file_path FROM tb_books WHERE id = ?", (book_id,))
            book_row = cursor.fetchone()
            if not book_row or not book_row['file_path']:
                return jsonify({'error': _('Book file with ID %(book_id)s not found.', book_id=book_id)}), 404
            
            data_dir = dirs["workspace"]
            return send_from_directory(data_dir, book_row['file_path'], as_attachment=True)
            
    except Exception as e:
        print(f"Error downloading anx book {book_id} for user {g.user.username}: {e}")
        return jsonify({'error': _('Error downloading book: %(error)s', error=e)}), 500

def _get_processed_epub_for_book(book_id, user_dict, filename_format='title - author'):
    """
    Core logic to get a processed EPUB for a book.
    It handles downloading, converting (if necessary), and fixing the EPUB.
    Returns a tuple: (content, filename, needs_conversion_flag) or (None, None, None) on error.
    """
    details = get_calibre_book_details(book_id)
    if not details:
        logging.error(f"Could not get details for book_id {book_id}")
        return None, None, False

    available_formats = [f.lower() for f in details.get('formats', [])]
    needs_conversion = False
    
    with tempfile.TemporaryDirectory() as temp_dir:
        epub_to_process_path = None
        
        # Check if EPUB already exists
        if 'epub' in available_formats:
            logging.info(f"Book ID {book_id} has EPUB format. Downloading directly.")
            content, filename = download_calibre_book(book_id, 'epub')
            if not content:
                logging.error(f"Failed to download existing EPUB for book_id {book_id}")
                return None, None, False
            
            epub_to_process_path = os.path.join(temp_dir, filename)
            with open(epub_to_process_path, 'wb') as f:
                f.write(content)
        else:
            # If no EPUB, convert from another format
            needs_conversion = True
            if not shutil.which('ebook-converter'):
                logging.error("ebook-converter not found, but conversion is needed.")
                return None, "CONVERTER_NOT_FOUND", False

            priority_str = user_dict.get('send_format_priority') or '[]'
            priority = json.loads(priority_str)
            format_to_convert = next((f for f in priority if f.lower() in available_formats), available_formats[0] if available_formats else None)

            if not format_to_convert:
                logging.error(f"No suitable format found to convert from for book_id {book_id}")
                return None, None, False

            logging.info(f"Book ID {book_id} needs conversion. Converting from {format_to_convert}.")
            original_content, original_filename = download_calibre_book(book_id, format_to_convert)
            if not original_content:
                logging.error(f"Failed to download source format {format_to_convert} for book_id {book_id}")
                return None, None, False

            source_path = os.path.join(temp_dir, original_filename)
            with open(source_path, 'wb') as f:
                f.write(original_content)

            base_name, _ = os.path.splitext(original_filename)
            epub_filename = f"{base_name}.epub"
            dest_path = os.path.join(temp_dir, epub_filename)

            try:
                logging.info(f"Running ebook-converter: {source_path} -> {dest_path}")
                subprocess.run(
                    ['ebook-converter', source_path, dest_path],
                    capture_output=True, text=True, check=True, timeout=300
                )
                epub_to_process_path = dest_path
            except Exception as e:
                logging.error(f"An unexpected error occurred during conversion for book_id {book_id}: {e}")
                return None, None, False

        if not epub_to_process_path or not os.path.exists(epub_to_process_path):
            logging.error(f"Could not find EPUB to process for book_id {book_id}")
            return None, None, False

        # --- Fix the EPUB ---
        logging.info(f"Processing EPUB with kindle-epub-fixer: {epub_to_process_path}")
        fixed_epub_path = fix_epub_for_kindle(epub_to_process_path, force_language='zh')
        
        with open(fixed_epub_path, 'rb') as f:
            content_to_send = f.read()

        # Sanitize title and authors for use in filename
        title = safe_title(details.get('title', 'Untitled'))
        
        if filename_format == 'title':
            filename_to_send = f"{title}.epub"
        else: # Default to 'title - author'
            authors = safe_author(" & ".join(details.get('authors', [])))
            if authors:
                filename_to_send = f"{title} - {authors}.epub"
            else:
                filename_to_send = f"{title}.epub"

        return content_to_send, filename_to_send, needs_conversion

@books_bp.route('/download_book/<int:book_id>', methods=['GET'])
def download_book_api(book_id):
    if g.user.force_epub_conversion:
        logging.info(f"Force EPUB conversion is ON for user {g.user.username} for book {book_id}")
        user_dict = {
            'username': g.user.username,
            'kindle_email': g.user.kindle_email,
            'send_format_priority': g.user.send_format_priority,
            'force_epub_conversion': g.user.force_epub_conversion
        }
        content, filename, needs_conversion = _get_processed_epub_for_book(book_id, user_dict)
        
        if filename == 'CONVERTER_NOT_FOUND':
            return jsonify({'error': _('This book needs to be converted to EPUB, but the `ebook-converter` tool is missing in the current environment.')}), 412
        if content and filename:
            return send_file(io.BytesIO(content), as_attachment=True, download_name=filename)
        else:
            return jsonify({'error': _('Unable to process or convert the book.')}), 500
    else:
        # Original logic
        details = get_calibre_book_details(book_id)
        if not details:
            return jsonify({'error': _('Book details not found.')}), 404

        available_formats = [f.lower() for f in details.get('formats', [])]
        priority = json.loads(g.user.send_format_priority or '[]')
        
        format_to_download = next((p_format.lower() for p_format in priority if p_format.lower() in available_formats), None)
        
        if not format_to_download:
            if available_formats:
                format_to_download = available_formats[0]
            else:
                return jsonify({'error': _('This book has no available formats.')}), 400

        content, filename = download_calibre_book(book_id, format_to_download)
        if content:
            return send_file(io.BytesIO(content), as_attachment=True, download_name=filename)
        
        return jsonify({'error': _('Unable to download the book.')}), 404

def _send_to_kindle_logic(user_dict, book_id):
    """Core logic to send a Calibre book to a user's Kindle. Expects user as a dict."""
    if not user_dict.get('kindle_email'):
        return {'success': False, 'error': _('Please configure your Kindle email in user settings first.')}

    # Kindle always requires a processed EPUB
    content_to_send, filename_to_send, needs_conversion = _get_processed_epub_for_book(book_id, user_dict, filename_format='title')

    if filename_to_send == 'CONVERTER_NOT_FOUND':
        return {'success': False, 'error': _('This book needs to be converted to EPUB, but the `ebook-converter` tool is missing. Please install it in the system PATH.'), 'code': 'CONVERTER_NOT_FOUND'}
    
    if not content_to_send:
        return {'success': False, 'error': _('Unable to get or process the EPUB file for the book.')}

    # Per Calibre's logic for Kindle, use random English text for subject and body
    subject = random_english_text(min_words_per_sentence=3, max_words_per_sentence=9, max_num_sentences=1).rstrip('.')
    body = random_english_text()
    success, message = send_email_with_config(
        user_dict['kindle_email'], 
        subject, 
        body, 
        config_manager.config, # Use the global config
        content_to_send, 
        filename_to_send
    )

    if success:
        return {'success': True, 'message': message, 'needs_conversion': needs_conversion}
    else:
        return {'success': False, 'error': message}

@books_bp.route('/send_to_kindle/<int:book_id>', methods=['POST'])
def send_to_kindle_api(book_id):
    user_dict = {
        'username': g.user.username,
        'kindle_email': g.user.kindle_email,
        'send_format_priority': g.user.send_format_priority,
        'force_epub_conversion': g.user.force_epub_conversion
    }
    result = _send_to_kindle_logic(user_dict, book_id)
    if result['success']:
        return jsonify({'message': result['message'], 'needs_conversion': result.get('needs_conversion', False)})
    else:
        if result.get('code') == 'CONVERTER_NOT_FOUND':
            return jsonify({'error': result['error']}), 412 # Precondition Failed
        if 'Kindle 邮箱' in result.get('error', ''):
            return jsonify({'error': result['error']}), 400
        return jsonify({'error': result['error']}), 500

def _push_calibre_to_anx_logic(user_dict, book_id):
    """Core logic to push a Calibre book to a user's Anx library. Expects user as a dict."""
    book_content, book_filename = None, None

    if user_dict.get('force_epub_conversion'):
        logging.info(f"Force EPUB conversion is ON for user {user_dict['username']} for book {book_id} push to Anx.")
        content, filename, _unused = _get_processed_epub_for_book(book_id, user_dict)
        if filename == 'CONVERTER_NOT_FOUND':
            return {'success': False, 'error': _('This book needs to be converted to EPUB, but the `ebook-converter` tool is missing.')}
        book_content, book_filename = content, filename
    else:
        # Original logic
        details = get_calibre_book_details(book_id)
        if not details:
            return {'success': False, 'error': _('Book details not found.')}
        available_formats = [f.lower() for f in details.get('formats', [])]
        priority_str = user_dict.get('send_format_priority') or '[]'
        priority = json.loads(priority_str)
        format_to_push = next((f for f in priority if f.lower() in available_formats), available_formats[0] if available_formats else None)

        if not format_to_push:
            return {'success': False, 'error': _('No pushable format found.')}
        
        book_content, book_filename = download_calibre_book(book_id, format_to_push)

    if not book_content:
        return {'success': False, 'error': _('Error downloading or processing the book.')}

    cover_content, _unused = download_calibre_cover(book_id)

    dirs = get_anx_user_dirs(user_dict['username'])
    if not dirs:
        return {'success': False, 'error': _('User directory not configured.')}

    import_dir = dirs["import"]
    os.makedirs(import_dir, exist_ok=True)

    book_file_path = os.path.join(import_dir, book_filename)
    with open(book_file_path, 'wb') as f:
        f.write(book_content)

    if cover_content:
        base_name, _unused = os.path.splitext(book_filename)
        cover_filename = f"{base_name}.jpg"
        cover_file_path = os.path.join(import_dir, cover_filename)
        with open(cover_file_path, 'wb') as f:
            f.write(cover_content)

    result = process_anx_import_folder(user_dict['username'])
    
    return {
        'success': True,
        'message': _("Book '%(filename)s' pushed. Processed: %(processed)s, Skipped: %(skipped)s.",
                     filename=book_filename,
                     processed=result.get('processed', 0),
                     skipped=result.get('skipped', 0))
    }

@books_bp.route('/push_to_anx/<int:book_id>', methods=['POST'])
def push_to_anx_api(book_id):
    user_dict = {
        'username': g.user.username,
        'kindle_email': g.user.kindle_email,
        'send_format_priority': g.user.send_format_priority,
        'force_epub_conversion': g.user.force_epub_conversion
    }
    result = _push_calibre_to_anx_logic(user_dict, book_id)
    if result['success']:
        return jsonify({'message': result['message']})
    else:
        return jsonify({'error': result['error']}), 500

@books_bp.route('/edit_anx_metadata', methods=['POST'])
def edit_anx_metadata_api():
    data = request.get_json()
    book_id = data.pop('id', None)
    if not book_id:
        return jsonify({'error': _('Missing book ID.')}), 400

    success, message = update_anx_book_metadata(g.user.username, book_id, data)

    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 500

@books_bp.route('/delete_anx_book/<int:book_id>', methods=['DELETE'])
def delete_anx_book_api(book_id):
    success, message = delete_anx_book(g.user.username, book_id)
    if success:
        return jsonify({'message': message})
    else:
        return jsonify({'error': message}), 500