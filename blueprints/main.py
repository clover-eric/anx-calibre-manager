import math
import re
import requests
import io
import os
from flask import Blueprint, render_template, request, g, redirect, url_for, send_from_directory, send_file
from requests.auth import HTTPDigestAuth
from functools import wraps
import json

import config_manager
from database import get_db
from anx_library import get_anx_books
from utils import safe_title, safe_author

main_bp = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or g.user.id is None:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def get_calibre_auth():
    config = config_manager.config
    if config.get('CALIBRE_USERNAME') and config.get('CALIBRE_PASSWORD'):
        return HTTPDigestAuth(config['CALIBRE_USERNAME'], config['CALIBRE_PASSWORD'])
    return None

def get_calibre_books(search_query="", page=1, page_size=20):
    config = config_manager.config
    try:
        library_id = config_manager.config.get('CALIBRE_DEFAULT_LIBRARY_ID', 'Calibre_Library')
        offset = (page - 1) * page_size
        search_params = { 'query': search_query, 'num': page_size, 'offset': offset, 'library_id': library_id, 'sort': 'id', 'sort_order': 'desc' }
        headers = {'User-Agent': 'Mozilla/5.0'}
        search_response = requests.get(f"{config['CALIBRE_URL']}/ajax/search", params=search_params, auth=get_calibre_auth(), headers=headers)
        search_response.raise_for_status()
        search_data = search_response.json()
        book_ids = search_data.get('book_ids', [])
        total_books = search_data.get('total_num', 0)
        if not book_ids: return [], 0
        books_data = {}
        chunk_size = 100
        for i in range(0, len(book_ids), chunk_size):
            chunk = book_ids[i:i + chunk_size]
            if not chunk: continue
            requested_fields = 'all' # Request all fields to get format_metadata
            books_params = {'ids': ",".join(map(str, chunk)), 'library_id': config_manager.config.get('CALIBRE_DEFAULT_LIBRARY_ID', 'Calibre_Library'), 'fields': requested_fields}
            books_response = requests.get(f"{config['CALIBRE_URL']}/ajax/books", params=books_params, auth=get_calibre_auth(), headers=headers)
            books_response.raise_for_status()
            books_data.update(books_response.json())

        books = []
        for bid in book_ids:
            bid_str = str(bid)
            if bid_str in books_data:
                book_dict = books_data[bid_str]
                if book_dict: # Ensure book data is not None
                    book_dict['id'] = bid
                    books.append(book_dict)
        
        def format_bytes(size):
            if not size or size == 0: return "0B"
            power = 1024
            n = 0
            power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
            while size >= power and n < len(power_labels) -1 :
                size /= power
                n += 1
            return f"{size:.1f} {power_labels[n]}"

        for book in books:
            formats_with_sizes = []
            format_metadata = book.get('format_metadata', {})
            if isinstance(format_metadata, dict):
                for fmt, details in format_metadata.items():
                    size = details.get('size', 0)
                    formats_with_sizes.append(f"{fmt.upper()} ({format_bytes(size)})")
            
            book['formats_with_sizes'] = formats_with_sizes
            # Also keep the simple format list for other uses
            book['formats'] = list(format_metadata.keys()) if isinstance(format_metadata, dict) else []

        return books, total_books
    except requests.exceptions.RequestException as e:
        print(f"Error getting Calibre books: {e}")
        return [], 0

def format_reading_time(seconds):
    if not seconds or seconds == 0:
        return "0分钟"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{int(hours)}小时 {int(minutes)}分钟"
    return f"{int(minutes)}分钟"

@main_bp.route('/')
@login_required
def index():
    search_query = request.args.get('search', '')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 20, type=int)
    calibre_books, total_calibre_books = get_calibre_books(search_query, page, page_size)
    
    anx_books = get_anx_books(g.user.username)
    for book in anx_books:
        book['formatted_reading_time'] = format_reading_time(book['total_reading_time'])

    total_pages = math.ceil(total_calibre_books / page_size) if page_size > 0 else 0
    pagination = {'page': page, 'page_size': page_size, 'total_books': total_calibre_books, 'total_pages': total_pages}
    
    return render_template('index.html', 
                           calibre_books=calibre_books, 
                           anx_books=anx_books, 
                           search_query=search_query, 
                           pagination=pagination)
@main_bp.route('/sw.js')
def service_worker():
    return send_from_directory('static', 'sw.js')

@main_bp.route('/settings')
@login_required
def settings_page():
    return render_template('settings.html')

@main_bp.route('/calibre_cover/<int:book_id>')
@login_required
def calibre_cover(book_id):
    cover_content, _ = download_calibre_cover(book_id)
    if cover_content:
        return send_file(io.BytesIO(cover_content), mimetype='image/jpeg')
    return redirect("https://via.placeholder.com/150x220.png?text=Cover+Error")


@main_bp.route('/anx_cover/<path:cover_path>')
@login_required
def anx_cover(cover_path):
    webdav_root = config_manager.config.get("WEBDAV_ROOT")
    if not webdav_root:
        return redirect("https://via.placeholder.com/150x220.png?text=Cover+Error")
    
    safe_username = os.path.basename(g.user.username)
    full_data_dir = os.path.join(webdav_root, safe_username, 'anx', 'data')
    return send_from_directory(full_data_dir, cover_path)

@main_bp.route('/anx_cover_public/<username>/<path:cover_path>')
def anx_cover_public(username, cover_path):
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()

    # Allow access if the user is logged in and accessing their own cover, or if the stats are public
    is_owner = g.user and hasattr(g.user, 'username') and g.user.username == username
    if not (user and (user['stats_public'] or is_owner)):
        return redirect("https://via.placeholder.com/150x220.png?text=Cover+Error")

    webdav_root = config_manager.config.get("WEBDAV_ROOT")
    if not webdav_root:
        return redirect("https://via.placeholder.com/150x220.png?text=Cover+Error")

    safe_username = os.path.basename(user['username'])
    full_data_dir = os.path.join(webdav_root, safe_username, 'anx', 'data')
    
    if not os.path.exists(os.path.join(full_data_dir, cover_path)):
        return redirect("https://via.placeholder.com/150x220.png?text=Cover+Error")

    return send_from_directory(full_data_dir, cover_path)
# --- Helper Functions (for use in API blueprint) ---

def get_calibre_book_details(book_id):
    config = config_manager.config
    try:
        response = requests.get(f"{config['CALIBRE_URL']}/ajax/book/{book_id}?fields=all", auth=get_calibre_auth())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting book details for {book_id}: {e}")
        return None

def download_calibre_cover(book_id):
    config = config_manager.config
    url = f"{config['CALIBRE_URL']}/get/cover/{book_id}"
    try:
        response = requests.get(url, auth=get_calibre_auth(), stream=True)
        response.raise_for_status()
        # Assume JPG, which is Calibre's default for covers
        return response.content, "cover.jpg"
    except requests.exceptions.RequestException as e:
        print(f"Error fetching cover for book {book_id}: {e}")
        return None, None

def download_calibre_book(book_id, download_format='mobi'):
    details = get_calibre_book_details(book_id)
    if not details: return None, None
    title = safe_title(details.get('title', 'Unknown Title'))
    authors = safe_author(" & ".join(details.get('authors', ['Unknown Author'])))
    if authors:
        filename = f"{title} - {authors}.{download_format}"
    else:
        filename = f"{title}.{download_format}"
    
    config = config_manager.config
    try:
        url = f"{config['CALIBRE_URL']}/get/{download_format.lower()}/{book_id}"
        response = requests.get(url, auth=get_calibre_auth(), stream=True)
        response.raise_for_status()
        return response.content, filename
    except requests.exceptions.RequestException as e:
        print(f"Error downloading book {book_id} in format {download_format} from URL {url}: {e}")
        return None, None