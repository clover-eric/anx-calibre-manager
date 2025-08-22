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
    current_element = root
    parts = path.split('/')[1:]
    
    pattern = r"(\w+)\[(\d+)\]"

    for part in parts:
        if current_element is None:
            return None
        
        match_bracket = re.match(pattern, part)
        if match_bracket:
            tag_name, index = match_bracket.group(1), int(match_bracket.group(2)) - 1
        else:
            tag_name, index = part, 0
        
        children = current_element.xpath(f"./*[local-name()='{tag_name}']")
        
        if 0 <= index < len(children):
            current_element = children[index]
        else:
            return None
    return current_element

def build_custom_element_path(target_element: etree._Element) -> str:
    path_components = []
    curr = target_element
    while curr is not None and curr.getparent() is not None and etree.QName(curr.getparent().tag).localname.lower() != 'body':
        parent = curr.getparent()
        tag_name = etree.QName(curr.tag).localname
        siblings_of_same_tag = parent.xpath(f"./*[local-name()='{tag_name}']")
        index_1_based = siblings_of_same_tag.index(curr) + 1
        path_components.append(f"{tag_name}[{index_1_based}]")
        curr = parent
    if curr is not None and curr.getparent() is not None:
        parent = curr.getparent()
        tag_name = etree.QName(curr.tag).localname
        if etree.QName(parent.tag).localname.lower() == 'body':
            siblings_of_same_tag = parent.xpath(f"./*[local-name()='{tag_name}']")
            index_1_based = siblings_of_same_tag.index(curr) + 1
            path_components.append(f"{tag_name}[{index_1_based}]")
    path_components.reverse()
    if not path_components: return ""
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

    if element_cfi_part.count(',') >= 2:
        last_comma_index = element_cfi_part.rfind(',')
        element_cfi_part = element_cfi_part[:last_comma_index]

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
            result_path += f"/text().{offset}"
        return result_path

def generate_cfi_from_custom_pointer(ebook_path: str, custom_pointer: str) -> str:
    pattern = r"/body/DocFragment\[(\d+)\](.*?)(?:/text\(\)\.(\d+))?$"
    
    match = re.search(pattern, custom_pointer)
    
    if not match:
        return f"错误: 在输入中找不到有效的定位符模式: '{custom_pointer}'"

    doc_index_str, element_path, offset = match.groups()
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
        
        if offset:
            element_cfi_path = get_cfi_element_path(target_element)
            final_cfi = f"epubcfi({spine_cfi_step}!{element_cfi_path}:{offset})"
        else:
            element_cfi_path = get_cfi_element_path(target_element)
            final_cfi = f"epubcfi({spine_cfi_step}!{element_cfi_path})"
            
        return final_cfi