import os
import re
import ebooklib
from ebooklib import epub
from lxml import etree, html

def _get_text_from_html(html_string):
    """Safely extracts plain text from an HTML string, preserving paragraphs and newlines."""
    if not html_string:
        return ""
    try:
        doc = html.fromstring(html_string)
        
        # Remove script and style tags completely
        for bad in doc.xpath("//script | //style"):
            bad.getparent().remove(bad)

        # Replace <br> with a newline
        for br in doc.xpath(".//br"):
            br.tail = "\n" + (br.tail or "")

        # Add newlines after paragraphs and other block elements
        for p in doc.xpath(".//p | .//div | .//h1 | .//h2 | .//h3 | .//h4"):
            p.tail = "\n\n" + (p.tail or "")

        text = doc.text_content()
        
        # Clean up excessive whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()
    except Exception:
        return "" # Fallback for malformed content

def _extract_toc_from_epub(book):
    """Extracts a flat list of TOC items from a pre-loaded ebooklib book object."""
    toc_items = []
    if hasattr(book, 'toc') and book.toc:
        for item in book.toc:
            if isinstance(item, tuple):
                section, children = item
                if hasattr(section, 'title') and hasattr(section, 'href'):
                    toc_items.append({'title': section.title, 'href': section.href})
                for child in children:
                    if hasattr(child, 'title') and hasattr(child, 'href'):
                        toc_items.append({'title': child.title, 'href': child.href})
            else:
                if hasattr(item, 'title') and hasattr(item, 'href'):
                    toc_items.append({'title': item.title, 'href': item.href})

    # Fallback to spine if TOC is empty or malformed
    if not toc_items:
        for item_id, _ in book.spine:
            item = book.get_item_with_id(item_id)
            if item and (item.get_type() == ebooklib.ITEM_DOCUMENT or item.media_type in ['application/xhtml+xml', 'text/html']):
                title = os.path.splitext(os.path.basename(item.get_name()))[0]
                toc_items.append({'title': title, 'href': item.get_name()})
    return toc_items

def _process_entire_epub(epub_path):
    """
    Reads an EPUB file once and processes its entire structure and content.
    Handles cross-file chapters and anchor-based chapters correctly.
    This is the performant core function for all content/word count operations.
    """
    try:
        book = epub.read_epub(epub_path)
    except Exception as e:
        return {"error": f"Failed to read or parse EPUB file: {e}"}

    toc_items = _extract_toc_from_epub(book)
    if not toc_items:
        return {"error": "Could not extract a valid Table of Contents from the book."}

    spine_hrefs = [book.get_item_with_id(item_id).get_name() for item_id, _ in book.spine if book.get_item_with_id(item_id)]
    
    processed_chapters = []

    for i, chapter_info in enumerate(toc_items):
        chapter_number = i + 1
        
        href_parts = chapter_info['href'].split('#')
        start_href = href_parts[0]
        start_anchor = href_parts[1] if len(href_parts) > 1 else None

        next_chapter_start_href = None
        next_anchor_in_same_file = None
        if chapter_number < len(toc_items):
            next_chapter_info = toc_items[chapter_number]
            next_href_parts = next_chapter_info['href'].split('#')
            next_chapter_start_href = next_href_parts[0]
            if next_chapter_start_href == start_href and len(next_href_parts) > 1:
                next_anchor_in_same_file = next_href_parts[1]

        try:
            start_index = spine_hrefs.index(start_href)
        except ValueError:
            # Skip this chapter if its start file isn't in the spine
            processed_chapters.append({
                "chapter_number": chapter_number,
                "title": chapter_info['title'],
                "html_content": "<!-- Error: Chapter file not found in spine -->"
            })
            continue

        end_index = len(spine_hrefs)
        if next_chapter_start_href and next_chapter_start_href != start_href:
            if next_chapter_start_href in spine_hrefs:
                end_index = spine_hrefs.index(next_chapter_start_href)
        elif next_anchor_in_same_file:
            # If the next chapter is just another anchor in the same file,
            # the content is only in the start_href file.
            end_index = start_index + 1
        else:
            # If this is the last chapter in the TOC, read until the end of the spine.
            end_index = len(spine_hrefs)

        full_content_html = ""
        for j in range(start_index, end_index):
            item_href = spine_hrefs[j]
            item = book.get_item_with_href(item_href)
            if item and (item.get_type() == ebooklib.ITEM_DOCUMENT or item.media_type in ['application/xhtml+xml', 'text/html']):
                try:
                    parser = etree.HTMLParser()
                    doc = etree.fromstring(item.get_content(), parser)
                    # Use a namespace-agnostic XPath to find the body tag, making it more robust
                    body_nodes = doc.xpath('//*[local-name()="body"]')
                    
                    if body_nodes:
                        body = body_nodes[0]
                        # Anchor-based slicing logic
                        content_nodes = []
                        if not start_anchor:
                            content_nodes = body.getchildren()
                        else:
                            # Find the start node. Use a robust XPath.
                            start_node = body.xpath(f".//*[@id='{start_anchor}']")
                            if not start_node:
                                content_nodes = body.getchildren() # Fallback if anchor not found
                            else:
                                start_node = start_node[0]
                                current_node = start_node
                                while current_node is not None:
                                    if next_anchor_in_same_file:
                                        # Check if the current node itself is the next anchor
                                        if current_node.get('id') == next_anchor_in_same_file:
                                            break
                                        # Check if any descendant is the next anchor
                                        if current_node.xpath(f".//*[@id='{next_anchor_in_same_file}']"):
                                            break
                                    content_nodes.append(current_node)
                                    current_node = current_node.getnext()
                        
                        inner_html_parts = [etree.tostring(node, encoding='unicode', method='html') for node in content_nodes]
                        full_content_html += "".join(inner_html_parts).strip()
                    else:
                        # Fallback if body is not found (e.g., malformed HTML)
                        full_content_html += item.get_content().decode('utf-8', 'ignore')
                except Exception:
                    # Fallback to raw content on parsing error
                    full_content_html += item.get_content().decode('utf-8', 'ignore')
        
        processed_chapters.append({
            "chapter_number": chapter_number,
            "title": chapter_info['title'],
            "html_content": full_content_html
        })

    return {
        "total_chapters": len(toc_items),
        "chapters": toc_items,
        "processed_chapters": processed_chapters
    }

def _count_words(text):
    """根据语言智能统计字数或词数。"""
    cjk_chars = re.findall(r'[\u4e00-\u9fff]', text)
    latin_words = re.findall(r'\b[a-zA-Z0-9]+\b', text)
    
    if len(cjk_chars) > len(latin_words):
        return len(text) # For CJK, count all characters
    else:
        return len(latin_words) # For Latin-based, count words