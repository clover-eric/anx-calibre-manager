#!/usr/bin/env python3

import os
import re
import sys
import glob
import tempfile
import shutil
from ebooklib import epub
from lxml import etree

# ==============================================================================
#  CORE LOGIC
# ==============================================================================

def get_cfi_element_path(element: etree._Element) -> str:
    path_components = []
    curr = element
    while curr.getparent() is not None:
        parent = curr.getparent()
        index = (parent.index(curr) * 2) + 2
        component = f"/{index}"
        if 'id' in curr.attrib and curr.attrib['id']:
            component += f"[{curr.attrib['id']}]"
        path_components.append(component)
        curr = parent
    path_components.reverse()
    return "".join(path_components)

def get_cfi_path_parts(element: etree._Element) -> (str, str):
    prefix_components = []
    suffix_components = []
    curr = element

    # Build suffix from the element up to (but not including) the direct child of body
    while curr is not None and curr.getparent() is not None and etree.QName(curr.getparent().tag).localname.lower() != 'body':
        parent = curr.getparent()
        index = (parent.index(curr) * 2) + 2
        component = f"/{index}"
        if 'id' in curr.attrib and curr.attrib['id']:
            component += f"[{curr.attrib['id']}]"
        suffix_components.append(component)
        curr = parent
    
    # `curr` is now the direct child of `body`.
    # Build prefix starting from `body`'s child up to the root.
    while curr is not None and curr.getparent() is not None:
        parent = curr.getparent()
        index = (parent.index(curr) * 2) + 2
        component = f"/{index}"
        if 'id' in curr.attrib and curr.attrib['id']:
            component += f"[{curr.attrib['id']}]"
        prefix_components.append(component)
        curr = parent

    prefix_components.reverse()
    suffix_components.reverse()
    
    return "".join(prefix_components), "".join(suffix_components)


def resolve_custom_path(root: etree._Element, path: str) -> etree._Element | None:
    if not path:
        return root.find('.//body') if root.find('.//body') is not None else root

    try:
        # Add a '.' to make it a relative XPath query from the current node
        xpath_query = f".{path}" if path.startswith('/') else f"./{path}"
        
        # The lxml library can handle namespaces, but for simplicity here, we'll assume no namespace or use local-name()
        # This is a simplified approach. A more robust solution might need namespace mapping.
        xpath_query = re.sub(r'/(\w+)', r"/*[local-name()='\1']", xpath_query)
        
        # The custom path format is like /div[1]/p[2], which is already valid XPath.
        # We just need to handle the root and ensure it's a relative path.
        
        result = root.xpath(xpath_query)
        
        if result:
            return result[0]
        else:
            return None
    except etree.XPathError as e:
        print(f"XPath error for query '{xpath_query}': {e}")
        return None

def build_custom_element_path(target_element: etree._Element) -> str:
    path_components = []
    curr = target_element
    # Traverse up the DOM tree until the parent is <body> or None
    while curr is not None and curr.getparent() is not None and etree.QName(curr.getparent().tag).localname.lower() != 'body':
        parent = curr.getparent()
        tag_name = etree.QName(curr.tag).localname
        siblings_of_same_tag = parent.xpath(f"./*[local-name()='{tag_name}']")
        
        # Only add index if there is more than one sibling with the same tag name
        if len(siblings_of_same_tag) > 1:
            index_1_based = siblings_of_same_tag.index(curr) + 1
            path_components.append(f"{tag_name}[{index_1_based}]")
        else:
            path_components.append(tag_name)
        curr = parent

    # Handle the direct child of <body>
    if curr is not None and curr.getparent() is not None and etree.QName(curr.getparent().tag).localname.lower() == 'body':
        parent = curr.getparent()
        tag_name = etree.QName(curr.tag).localname
        siblings_of_same_tag = parent.xpath(f"./*[local-name()='{tag_name}']")
        if len(siblings_of_same_tag) > 1:
            index_1_based = siblings_of_same_tag.index(curr) + 1
            path_components.append(f"{tag_name}[{index_1_based}]")
        else:
            path_components.append(tag_name)

    path_components.reverse()
    
    if not path_components:
        return ""
        
    # Always prepend with /body/
    return "/body/" + "/".join(path_components)

def resolve_cfi_element_path(root: etree._Element, cfi_path: str) -> etree._Element:
    current_element = root
    steps = re.split(r'[/,]', cfi_path)
    traversed_path = []
    for step in steps:
        if not step: continue
        step_num_str = step.split('[')[0]
        if step_num_str.isdigit():
            step_num = int(step_num_str)
            if step_num % 2 == 0:
                child_index = (step_num // 2) - 1
                children = list(current_element)
                
                if 0 <= child_index < len(children):
                    current_element = children[child_index]
                    traversed_path.append(step)
                else:
                    error_msg = (
                        f"路径解析失败: 在CFI步骤 '{step}' 处中断。\n"
                        f"  - 已成功遍历路径: '{'/'.join(traversed_path)}'\n"
                        f"  - 失败原因: 尝试访问第 {child_index + 1} 个子元素 (索引 {child_index})，"
                        f"但当前元素 <{current_element.tag}> 只有 {len(children)} 个子元素。"
                    )
                    raise ValueError(error_msg)
    return current_element


class EbookProcessor:
    def __init__(self, ebook_path):
        self.ebook_path = ebook_path
        self.file_ext = os.path.splitext(ebook_path)[1].lower()
        self.temp_dir = None
        self.spine_items = []

    def __enter__(self):
        if not os.path.exists(self.ebook_path):
            raise FileNotFoundError(f"电子书文件未找到: {self.ebook_path}")
        if self.file_ext == '.epub':
            self._process_epub()
        else:
            raise ValueError(f"不支持的文件格式: '{self.file_ext}'")
        return self

    def _process_epub(self):
        book = epub.read_epub(self.ebook_path)
        for item_tuple in book.spine:
            item_id = item_tuple[0]
            spine_item = book.get_item_with_id(item_id)
            if spine_item:
                self.spine_items.append({'href': spine_item.get_name(), 'content': spine_item.get_content()})

    def get_spine_item(self, index):
        return self.spine_items[index] if 0 <= index < len(self.spine_items) else None

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir)

def generate_custom_pointer_from_cfi(ebook_path: str, cfi_string: str) -> str:
    clean_cfi = cfi_string.strip("'\"")
    if not clean_cfi.lower().startswith("epubcfi(") or not clean_cfi.endswith(")"):
        return f"错误: CFI 必须以 'epubcfi(' 开始并以 ')' 结束。"
    inner_content = clean_cfi[8:-1]
    parts = inner_content.split('!', 1)
    if len(parts) != 2:
        return f"错误: CFI 必须包含一个 '!' 分隔符。"
    spine_cfi_part, element_cfi_part = parts

    # Handle CFI ranges, e.g., epubcfi(/6/8!/4/6,/122/2/1:359,/132/2/1:23)
    # We only care about the start of the range.
    # The format is /common_path,start_path,end_path
    range_parts = element_cfi_part.split(',')
    if len(range_parts) == 3:
        common_path = range_parts[0]
        start_path = range_parts[1]
        
        # Reconstruct the full path for the start of the range
        if common_path.endswith('/'):
            common_path = common_path[:-1]
        if not start_path.startswith('/'):
            start_path = '/' + start_path
        
        element_cfi_part = common_path + start_path

    offset = None
    path_part = element_cfi_part
    if ':' in element_cfi_part:
        path_part, offset = element_cfi_part.split(':', 1)

    spine_match = re.match(r"/6/(\d+)", spine_cfi_part)
    if not spine_match:
        return f"错误: 无效的 CFI spine 路径部分: '{spine_cfi_part}'"
    spine_cfi_num = int(spine_match.group(1))
    spine_index = (spine_cfi_num - 2) // 2
    with EbookProcessor(ebook_path) as book:
        target_item = book.get_spine_item(spine_index)
        if not target_item:
            return f"错误: CFI 中的 spine 索引 [{spine_index}] 超出范围。"
        root = etree.fromstring(target_item['content'], etree.XMLParser(recover=True))
        target_element = resolve_cfi_element_path(root, path_part)
        custom_element_path = build_custom_element_path(target_element)
        doc_fragment_index = spine_index + 1
        
        result_path = f"/body/DocFragment[{doc_fragment_index}]{custom_element_path}"
        if offset and offset.isdigit():
            is_text_offset = False
            last_step_match = re.search(r"/(\d+)(?:\[.*?\])?$", path_part)
            if last_step_match:
                last_step_index = int(last_step_match.group(1))
                # In CFI, odd numbers indicate text nodes, even numbers indicate element nodes.
                if last_step_index % 2 != 0:
                    is_text_offset = True

            if is_text_offset:
                # last_step_index is the CFI step (e.g., 1, 3, 5...)
                # Convert it back to a 1-based XPath index for text()[]
                text_node_xpath_index = (last_step_index + 1) // 2
                if text_node_xpath_index > 1:
                    result_path += f"/text()[{text_node_xpath_index}].{offset}"
                else:
                    result_path += f"/text().{offset}"  # Omit [1] for simplicity
            else:
                result_path += f".{offset}"
        return result_path

def generate_cfi_from_custom_pointer(ebook_path: str, custom_pointer: str) -> str:
    # This pattern handles both formats:
    # 1. /body/DocFragment[4]/body/div[3]/p[69]/span/text().23
    # 2. /body/DocFragment[4]/body/div[1].0
    pattern = r"/body/DocFragment\[(\d+)\](.*?)(?:/text\(\)(?:\[(\d+)\])?\.(\d+)|\.(\d+))?$"
    
    match = re.search(pattern, custom_pointer)
    
    if not match:
        return f"错误: 在输入中找不到有效的定位符模式: '{custom_pointer}'"

    doc_index_str, element_path, text_node_index_str, offset_with_text, offset_direct = match.groups()
    
    offset_str = offset_with_text if offset_with_text is not None else offset_direct
    
    # Clean up element_path if it incorrectly captured part of the offset
    if offset_direct and element_path.endswith(f".{offset_direct}"):
         element_path = element_path[:-len(f".{offset_direct}")]

    doc_index = int(doc_index_str) - 1
    
    with EbookProcessor(ebook_path) as book:
        target_item = book.get_spine_item(doc_index)
        if not target_item:
            return f"错误: DocFragment 索引 [{doc_index + 1}] 超出范围。"
        
        root = etree.fromstring(target_item['content'], etree.XMLParser(recover=True))
        
        target_element = resolve_custom_path(root, element_path)
        
        if target_element is None:
            return f"错误: 内部路径 '{element_path}' 在文档 '{target_item['href']}' 中无法定位。"

        spine_cfi_step = f"/6/{(doc_index * 2) + 2}"
        element_cfi_path = get_cfi_element_path(target_element)

        if offset_str is not None:
            offset = int(offset_str)
            # Case 1: Pointer is to a text node offset, e.g., /text()[2].23
            if offset_with_text is not None:
                text_node_cfi_step = 1  # Default to the first text node (/1)
                if text_node_index_str and text_node_index_str.isdigit():
                    # Convert 1-based XPath index to CFI odd-numbered step
                    # e.g., text()[1] -> /1, text()[2] -> /3, etc.
                    text_node_index = int(text_node_index_str)
                    text_node_cfi_step = (text_node_index * 2) - 1
                
                final_cfi = f"epubcfi({spine_cfi_step}!{element_cfi_path}/{text_node_cfi_step}:{offset})"
            # Case 2: Pointer is to an element offset, e.g., div[1].0
            elif offset_direct is not None:
                final_cfi = f"epubcfi({spine_cfi_step}!{element_cfi_path}:{offset})"
            else:
                 # Fallback, should not happen if regex is correct
                 final_cfi = f"epubcfi({spine_cfi_step}!{element_cfi_path})"
        else:
            final_cfi = f"epubcfi({spine_cfi_step}!{element_cfi_path})"
            
        return final_cfi