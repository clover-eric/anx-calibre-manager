# -*- coding: utf-8 -*-
import sys
import os

# Add the project root to the Python path to allow imports
# This assumes the script is run from the 'anx-calibre-manager' directory
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

try:
    from utils.epub_cfi_utils import get_total_chapters, get_cfi_for_chapter, get_chapter_from_cfi
    from utils.epub_utils import _extract_toc_from_epub # Needed for total chapters
except ImportError as e:
    print(f"Error: Could not import necessary modules. Make sure you are running this script")
    print(f"from the 'anx-calibre-manager' directory. Details: {e}")
    sys.exit(1)

def verify_conversion(epub_path):
    """
    Tests the round-trip conversion for every chapter in the given EPUB file.
    """
    if not os.path.exists(epub_path):
        print(f"Error: EPUB file not found at '{epub_path}'")
        return

    print(f"--- Verifying CFI conversion for: {epub_path} ---")

    total_chapters = get_total_chapters(epub_path)
    if total_chapters == 0:
        print("Could not find any chapters in the book.")
        return

    print(f"Found {total_chapters} chapters (based on TOC). Starting verification...\n")

    mismatch_count = 0
    for chapter_index in range(total_chapters):
        # 1. Convert chapter index to CFI
        cfi = get_cfi_for_chapter(epub_path, chapter_index)
        
        if not cfi:
            print(f"Chapter {chapter_index:03d}: [FAIL] -> Could not generate CFI.")
            mismatch_count += 1
            continue

        # 2. Convert CFI back to chapter index
        converted_index = get_chapter_from_cfi(epub_path, cfi)

        # 3. Compare and print results
        status = "OK" if chapter_index == converted_index else "FAIL"
        if status == "FAIL":
            mismatch_count += 1
        
        print(f"Chapter {chapter_index:03d}: [{status}] -> CFI: {cfi} -> Converted Index: {converted_index}")

    print("\n--- Verification Complete ---")
    if mismatch_count == 0:
        print(f"Success! All {total_chapters} chapters converted correctly.")
    else:
        print(f"Failure: {mismatch_count} out of {total_chapters} chapters did not convert correctly.")

    print("\n--- Special Test for Range CFI ---")
    range_cfi = "epubcfi(/6/40!/4,/18/1:137,/24/1:161)"
    print(f"Testing CFI: {range_cfi}")
    range_chapter_index = get_chapter_from_cfi(epub_path, range_cfi)
    print(f"Resulting Chapter Index: {range_chapter_index}")
    # You can manually verify if this index is correct for your book.

if __name__ == "__main__":
    # Set the path to your target EPUB file here
    target_epub_path = "./a.epub"
    verify_conversion(target_epub_path)