import os
import ebookmeta
from PIL import Image, ImageDraw, ImageFont
import ebooklib
from ebooklib import epub
from mobi_header import MobiHeader
from .epub_meta import _get_epub_cover_image
import struct
from pypdf import PdfReader

def extract_ebook_metadata(file_path):
    """
    Extracts metadata (title, author, cover) from an ebook file using a multi-strategy approach.
    Returns a dictionary with 'title', 'author', and 'cover' (bytes).
    """
    _unused, ext = os.path.splitext(file_path)
    ext = ext.lower()

    try:
        if ext == '.epub':
            book = epub.read_epub(file_path)
            return {
                'title': book.get_metadata('DC', 'title')[0][0] if book.get_metadata('DC', 'title') else 'Unknown Title',
                'author': ', '.join(c[0] for c in book.get_metadata('DC', 'creator')) if book.get_metadata('DC', 'creator') else 'Unknown Author',
                'cover': _get_epub_cover_image(book)
            }
        elif ext in ['.mobi', '.azw3']:
            mh = MobiHeader(file_path)
            cover_data = None
            
            # First, try to get cover by name 'cover'
            cover_value = mh.get_exth_value_by_name('cover')
            if cover_value:
                cover_data = cover_value.get('data') if isinstance(cover_value, dict) else cover_value
            
            # If not found, try to get by 'Cover Offset'
            if not cover_data:
                cover_offset_val = mh.get_exth_value_by_name('Cover Offset')
                if cover_offset_val:
                    cover_offset = struct.unpack('>L', cover_offset_val)[0]
                    first_image_index = mh.metadata[108]['value']
                    cover_record_index = first_image_index + cover_offset
                    if 0 <= cover_record_index < len(mh.palm_doc.records):
                        cover_data = mh.palm_doc.records[cover_record_index]

            title = mh.get_exth_value_by_name('Updated Title') or mh.get_exth_value_by_name('Title') or 'Unknown Title'
            author = mh.get_exth_value_by_name('Author') or 'Unknown Author'

            return {
                'title': title,
                'author': author,
                'cover': cover_data
            }
        elif ext == '.fb2':
            metadata = ebookmeta.get_metadata(file_path)
            return {
                'title': metadata.title if metadata.title else 'Unknown Title',
                'author': ', '.join(metadata.author_list) if metadata.author_list else 'Unknown Author',
                'cover': metadata.cover_image_data
            }
        elif ext == '.pdf':
            reader = PdfReader(file_path)
            meta = reader.metadata
            cover = None
            if reader.pages and reader.pages[0].images:
                cover = reader.pages[0].images[0].data

            title = meta.title
            author = meta.author

            # Clean up null characters
            if title:
                title = title.replace('\x00', '')
            if author:
                author = author.replace('\x00', '')
           
            return {
                'title': title or 'Unknown Title',
                'author': author or 'Unknown Author',
                'cover': cover
            }
           
            return {
                'title': title,
                'author': author,
                'cover': cover
            }
    except Exception as e:
        print(f"Error extracting metadata from {file_path} using {ext} strategy: {e}")
    
    return None

import re

def _contains_chinese(text):
    """Check if the text contains Chinese characters."""
    return re.search(r'[\u4e00-\u9fff]', text)

def _draw_text_with_wrapping(draw, text, font, max_lines, y_pos, width, is_title=False):
    """A helper function to draw wrapped and centered text."""
    # Determine characters per line based on language and type (title/author)
    if _contains_chinese(text):
        chars_per_line = 4 if is_title else 6
    else:
        chars_per_line = 7 if is_title else 10

    lines = []
    for i in range(0, len(text), chars_per_line):
        lines.append(text[i:i+chars_per_line])
    
    lines = lines[:max_lines] # Truncate to max_lines
    
    # Calculate total height of the text block for vertical centering
    line_spacing = 10 # Extra pixels between lines
    line_heights = [font.getbbox(line)[3] - font.getbbox(line)[1] for line in lines]
    total_text_height = sum(line_heights) + (len(lines) - 1) * line_spacing
    
    # Adjust y_pos to be the top of the text block
    current_y = y_pos - total_text_height / 2
    
    for i, line in enumerate(lines):
        # Get bounding box for horizontal centering
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]
        
        x_pos = (width - text_width) / 2
        draw.text((x_pos, current_y), line, font=font, fill=(0, 0, 0))
        current_y += line_heights[i] + line_spacing
    return current_y

def generate_cover_image(title, author, width=600, height=800):
    """
    Generates a fallback cover image with the book's title and author.
    """
    # Create a blank image with a random soft color
    import random
    r = random.randint(180, 220)
    g = random.randint(180, 220)
    b = random.randint(180, 220)
    image = Image.new('RGB', (width, height), color = (r, g, b))
    draw = ImageDraw.Draw(image)

    # Use a default font
    try:
        # Try to use a common sans-serif font
        font_title = ImageFont.truetype("wqy-microhei.ttc", 140)
        font_author = ImageFont.truetype("wqy-microhei.ttc", 100)
        font_watermark = ImageFont.truetype("wqy-microhei.ttc", 30)
    except IOError:
        # Fallback to default font if not found
        font_title = ImageFont.load_default()
        font_author = ImageFont.load_default()
        font_watermark = ImageFont.load_default()

    # Add text to image
    title_y_pos = height / 3
    title_bottom_y = _draw_text_with_wrapping(draw, title, font_title, 4, title_y_pos, width, is_title=True)
    
    # Adjust author position based on title height
    author_y_pos = title_bottom_y + 50 # Add 50px spacing
    _draw_text_with_wrapping(draw, author, font_author, 1, author_y_pos, width)
    
    # Add watermark
    watermark_text_line1 = "Cover Generated by"
    watermark_text_line2 = "Anx Calibre Manager"
    draw.text((width - 10, height - 40), watermark_text_line1, font=font_watermark, anchor="rs", fill=(0, 0, 0, 128))
    draw.text((width - 10, height - 10), watermark_text_line2, font=font_watermark, anchor="rs", fill=(0, 0, 0, 128))


    # Save image to a bytes buffer
    import io
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()
    
    return img_byte_arr

def process_uploaded_ebook(file_path, original_filename=None):
    """
    A robust function to get metadata and cover for an uploaded ebook.
    If cover is not found, it generates a fallback.
    """
    filename_to_use = original_filename or os.path.basename(file_path)
    _unused, ext = os.path.splitext(filename_to_use)
    ext = ext.lower()

    metadata = {
        'title': 'Unknown Title',
        'author': 'Unknown Author',
        'cover': None
    }

    extracted_meta = extract_ebook_metadata(file_path)
    if extracted_meta:
        metadata.update(extracted_meta)
    
    # Fallback to filename ONLY if the title is still unknown
    if not metadata.get('title') or metadata['title'] == 'Unknown Title':
        base_filename = os.path.splitext(filename_to_use)[0]
        separator = ' - '
        if separator in base_filename:
            parts = base_filename.split(separator, 1)
            metadata['title'] = parts[0].strip()
            # Also update the author if it was unknown
            if not metadata.get('author') or metadata['author'] == 'Unknown Author':
                metadata['author'] = parts[1].strip()
        else:
            metadata['title'] = base_filename
    
    # If there's no cover, generate one
    if not metadata['cover']:
        metadata['cover'] = generate_cover_image(metadata['title'], metadata['author'])

    return metadata