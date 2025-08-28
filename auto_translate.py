import polib
from googletrans import Translator
import sys
import asyncio

async def translate_entries(entries, translator, api_target_lang):
    """Asynchronously translates a list of polib entries."""
    for i, entry in enumerate(entries):
        try:
            # Simple rate limiting to avoid API issues
            if i > 0 and i % 5 == 0:
                await asyncio.sleep(1)

            # Skip fuzzy entries as they might have been manually edited
            if 'fuzzy' in entry.flags:
                continue

            translation = await translator.translate(entry.msgid, dest=api_target_lang)
            entry.msgstr = translation.text
            print(f'"{entry.msgid}" -> "{entry.msgstr}"')
        except Exception as e:
            print(f"Error translating '{entry.msgid}': {e}")
            # Fallback to original text on error to avoid empty strings
            entry.msgstr = entry.msgid

def translate_po_file(target_lang):
    """
    Translates a .po file for the given target language.
    It reads from the source .po file and fills in empty msgstr entries.
    """
    po_file_path = f'translations/{target_lang}/LC_MESSAGES/messages.po'
    
    # The googletrans library expects 'zh-cn' for Simplified Chinese,
    # but our directory is 'zh_CN'. We'll adjust the API call parameter.
    api_target_lang = 'zh-cn' if target_lang == 'zh_CN' else target_lang

    try:
        po = polib.pofile(po_file_path)
    except IOError:
        print(f"PO file for {target_lang} not found at {po_file_path}. Skipping.")
        return

    translator = Translator()
    
    print(f"Translating to {target_lang}...")
    
    entries_to_translate = [entry for entry in po if not entry.msgstr]
    
    if not entries_to_translate:
        print(f"No new strings to translate for {target_lang}.")
        return

    # Run the async translation process
    asyncio.run(translate_entries(entries_to_translate, translator, api_target_lang))

    po.save(po_file_path)
    print(f"Translation complete for {target_lang}. Saved to {po_file_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_languages = sys.argv[1:]
        for lang in target_languages:
            translate_po_file(lang)
    else:
        print("Usage: python auto_translate.py <lang_code_1> <lang_code_2> ...")
        print("Example: python auto_translate.py zh_CN es fr")