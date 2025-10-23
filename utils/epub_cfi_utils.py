# -*- coding: utf-8 -*-
import ebooklib
from ebooklib import epub
import re
import logging
from functools import lru_cache
from .epub_utils import _extract_toc_from_epub

logger = logging.getLogger(__name__)

@lru_cache(maxsize=32)
def _get_book(epub_path: str):
    """Cached function to read an EPUB file."""
    try:
        return epub.read_epub(epub_path)
    except Exception as e:
        logger.error(f"Failed to read and cache EPUB file at {epub_path}: {e}")
        return None

@lru_cache(maxsize=32)
def _get_toc_to_spine_map(epub_path: str):
    """
    Creates a mapping from the TOC item index to the corresponding spine index.
    This is the key to ensuring consistency with audiobook chapter generation.
    """
    book = _get_book(epub_path)
    if not book:
        return {}

    toc_items = _extract_toc_from_epub(book)
    spine_hrefs = [item.get_name() for item_id, _ in book.spine if (item := book.get_item_with_id(item_id))]
    
    mapping = {}
    for toc_index, toc_item in enumerate(toc_items):
        toc_href = toc_item['href'].split('#')[0]
        
        found_spine_index = -1
        for spine_index, spine_href in enumerate(spine_hrefs):
            if toc_href.endswith(spine_href):
                found_spine_index = spine_index
                break
        
        if found_spine_index != -1:
            mapping[toc_index] = found_spine_index
            
    return mapping

def get_cfi_for_chapter(epub_path: str, chapter_index: int) -> str:
    """
    Generates an EPUB CFI for a given audiobook chapter index by mapping it to the correct spine item.
    """
    book = _get_book(epub_path)
    if not book or not book.spine:
        return ""

    toc_to_spine_map = _get_toc_to_spine_map(epub_path)
    spine_index = toc_to_spine_map.get(chapter_index)

    if spine_index is None or not (0 <= spine_index < len(book.spine)):
        logger.warning(f"Could not map chapter index {chapter_index} to a valid spine item for {epub_path}.")
        return ""

    cfi_path_component = (spine_index + 1) * 2
    item_id = book.spine[spine_index][0]
    
    return f"epubcfi(/6/{cfi_path_component}[{item_id}])"

def get_chapter_from_cfi(epub_path: str, cfi: str) -> int:
    """
    Parses an EPUB CFI to determine the audiobook chapter index.
    """
    if not cfi:
        return 0

    match = re.search(r'epubcfi\(/6/(\d+)', cfi)
    if not match:
        return 0

    try:
        path_component = int(match.group(1))
        if path_component > 0 and path_component % 2 == 0:
            spine_index = (path_component // 2) - 1
            
            toc_to_spine_map = _get_toc_to_spine_map(epub_path)
            # Invert the map to find the toc_index from a spine_index
            spine_to_toc_map = {v: k for k, v in toc_to_spine_map.items()}
            
            return spine_to_toc_map.get(spine_index, 0)
        return 0
    except (ValueError, IndexError) as e:
        logger.error(f"Failed to parse chapter from CFI '{cfi}': {e}")
        return 0

def get_total_chapters(epub_path: str) -> int:
    """
    Gets the total number of chapters based on the extracted TOC, consistent with audiobook generation.
    """
    book = _get_book(epub_path)
    if not book:
        return 0
    return len(_extract_toc_from_epub(book))
