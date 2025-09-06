import os
import hashlib
import cfi_converter

def convert_koreader_progress(direction, epub_path, progress):
    """
    Calls the cfi_converter.py script to convert progress between xpointer and epubcfi.
    direction: 'to-cfi' or 'from-cfi'
    epub_path: Absolute path to the EPUB file.
    progress: The progress string to convert.
    """
    if not os.path.exists(epub_path):
        return None, f"EPUB file not found at {epub_path}"

    try:
        if direction == 'to-cfi':
            result = cfi_converter.generate_cfi_from_custom_pointer(epub_path, progress)
        elif direction == 'from-cfi':
            result = cfi_converter.generate_custom_pointer_from_cfi(epub_path, progress)
        else:
            return None, f"Invalid conversion direction: {direction}"

        if result.startswith('错误:'):
            return None, result
        return result, None
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"

def calculate_koreader_partial_md5(filepath):
    """
    Calculates the partial MD5 checksum of a file using KOReader's algorithm.
    """
    if not os.path.exists(filepath):
        return None, f"File not found at {filepath}"

    try:
        md5 = hashlib.md5()
        step = 1024
        size = 1024

        with open(filepath, "rb") as f:
            for i in range(-1, 11):
                # In Lua, lshift(step, 2*i) is equivalent to step * (2**(2*i))
                # However, for i = -1, 2*i = -2, and 2**-2 = 0.25.
                # We need to handle this correctly in Python.
                if i == -1:
                    offset = int(step * 0.25)
                else:
                    offset = step * (2**(2*i))
                
                f.seek(offset)
                sample = f.read(size)
                if sample:
                    md5.update(sample)
                else:
                    break
        return md5.hexdigest(), None
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"