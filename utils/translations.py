import os
from flask_babel import get_locale
from babel.support import Translations

def get_js_translations():
    """
    Returns a dictionary of all available translations for JavaScript.
    Automatically extracts all translations from the current locale's catalog.
    This is more maintainable than manually maintaining a list.
    """
    try:
        # 获取当前语言
        locale = str(get_locale())
        
        # 构建翻译文件路径
        translations_dir = os.path.join(os.path.dirname(__file__), '..', 'translations')
        mo_path = os.path.join(translations_dir, locale, 'LC_MESSAGES', 'messages.mo')
        
        # 如果翻译文件不存在，返回空字典（将使用原始英文）
        if not os.path.exists(mo_path):
            return {}
        
        # 加载翻译目录
        translations = Translations.load(translations_dir, [locale])
        
        # 提取所有翻译对
        js_translations = {}
        if translations and hasattr(translations, '_catalog'):
            for msgid, msgstr in translations._catalog.items():
                # 跳过空字符串和元数据
                if msgid and isinstance(msgid, str) and msgstr and isinstance(msgstr, str):
                    js_translations[msgid] = msgstr
        
        return js_translations
        
    except Exception as e:
        # 如果出现任何错误，返回空字典，JavaScript将使用原始文本
        print(f"Warning: Failed to load JavaScript translations: {e}")
        return {}