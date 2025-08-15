import os
import re
import zipfile
import logging
from xml.dom import minidom
import tempfile

class EPUBFixer:
    """
    A class to fix common issues in EPUB files that might cause problems with
    Amazon's Send-to-Kindle service.
    Adapted from https://github.com/innocenat/kindle-epub-fix
    """
    def __init__(self):
        self.fixed_problems = []
        self.files = {}
        self.binary_files = {}
        self.entries = []

    def read_epub(self, epub_path):
        """Read EPUB file contents into memory."""
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            self.entries = zip_ref.namelist()
            for filename in self.entries:
                ext = filename.split('.')[-1].lower()
                if filename == 'mimetype' or ext in ['html', 'xhtml', 'htm', 'xml', 'svg', 'css', 'opf', 'ncx']:
                    self.files[filename] = zip_ref.read(filename).decode('utf-8')
                else:
                    self.binary_files[filename] = zip_ref.read(filename)

    def fix_encoding(self):
        """Add UTF-8 encoding declaration if missing from (x)html files."""
        encoding_declaration = '<?xml version="1.0" encoding="utf-8"?>'
        regex = r'^<\?xml\s+version=["\'][\d.]+["\']\s+encoding=["\'][a-zA-Z\d\-\.]+["\'].*?\?>'

        for filename, content in self.files.items():
            ext = filename.split('.')[-1].lower()
            if ext in ['html', 'xhtml']:
                stripped_content = content.lstrip()
                if not re.match(regex, stripped_content, re.IGNORECASE):
                    self.files[filename] = encoding_declaration + '\n' + stripped_content
                    self.fixed_problems.append(f"Added missing UTF-8 encoding declaration to {filename}")

    def fix_body_id_link(self):
        """Fix linking to body ID showing up as an unresolved hyperlink."""
        body_id_list = []
        for filename, content in self.files.items():
            ext = filename.split('.')[-1].lower()
            if ext in ['html', 'xhtml']:
                try:
                    dom = minidom.parseString(content)
                    body_elements = dom.getElementsByTagName('body')
                    if body_elements and body_elements[0].hasAttribute('id'):
                        body_id = body_elements[0].getAttribute('id')
                        if body_id:
                            link_target = os.path.basename(filename) + '#' + body_id
                            body_id_list.append((link_target, os.path.basename(filename)))
                except Exception:
                    continue # Ignore parsing errors

        if not body_id_list:
            return

        for filename in self.files:
            for src, target in body_id_list:
                if src in self.files[filename]:
                    self.files[filename] = self.files[filename].replace(src, target)
                    self.fixed_problems.append(f"Replaced body ID link target '{src}' with '{target}' in {filename}")

    def fix_book_language(self, default_language='en', force_language=None):
        """Fix language field not defined, not one of the Amazon-allowed languages, or force a specific language."""
        allowed_languages = {
            'af', 'gsw', 'ar', 'eu', 'nb', 'br', 'ca', 'zh', 'kw', 'co', 'da', 'nl', 'stq', 'en', 'fi', 'fr', 'fy', 'gl',
            'de', 'gu', 'hi', 'is', 'ga', 'it', 'ja', 'lb', 'mr', 'ml', 'gv', 'frr', 'nn', 'pl', 'pt', 'oc', 'rm',
            'sco', 'gd', 'es', 'sv', 'ta', 'cy', 'afr', 'ara', 'eus', 'baq', 'nob', 'bre', 'cat', 'zho', 'chi', 'cor',
            'cos', 'dan', 'nld', 'dut', 'eng', 'fin', 'fra', 'fre', 'fry', 'glg', 'deu', 'ger', 'guj', 'hin', 'isl',
            'ice', 'gle', 'ita', 'jpn', 'ltz', 'mar', 'mal', 'glv', 'nor', 'nno', 'por', 'oci', 'roh', 'gla', 'spa',
            'swe', 'tam', 'cym', 'wel'
        }

        container_content = self.files.get('META-INF/container.xml')
        if not container_content:
            return

        try:
            container_xml = minidom.parseString(container_content)
            opf_filename = next(
                rf.getAttribute('full-path') for rf in container_xml.getElementsByTagName('rootfile')
                if rf.getAttribute('media-type') == 'application/oebps-package+xml'
            )
        except (Exception, StopIteration):
            return

        opf_content = self.files.get(opf_filename)
        if not opf_content:
            return

        try:
            opf = minidom.parseString(opf_content)
            metadata_list = opf.getElementsByTagName('metadata')
            if not metadata_list:
                return
            metadata = metadata_list[0]
            
            language_tags = opf.getElementsByTagName('dc:language')
            original_language = None
            language_to_set = None
            
            if force_language:
                language_to_set = force_language
                if not language_tags:
                    self.fixed_problems.append(f"No dc:language tag found. Creating and forcing to '{language_to_set}'.")
                    lang_tag = opf.createElement('dc:language')
                    lang_tag.appendChild(opf.createTextNode(language_to_set))
                    metadata.appendChild(lang_tag)
                else:
                    lang_tag = language_tags[0]
                    original_language = lang_tag.firstChild.nodeValue if lang_tag.firstChild else ''
                    if original_language != language_to_set:
                         self.fixed_problems.append(f"Forcing language from '{original_language}' to '{language_to_set}'.")
                         lang_tag.firstChild.nodeValue = language_to_set
            else:
                if not language_tags:
                    language_to_set = default_language
                    self.fixed_problems.append(f"No dc:language tag found. Setting to default: '{default_language}'")
                    lang_tag = opf.createElement('dc:language')
                    lang_tag.appendChild(opf.createTextNode(language_to_set))
                    metadata.appendChild(lang_tag)
                else:
                    lang_tag = language_tags[0]
                    original_language = lang_tag.firstChild.nodeValue if lang_tag.firstChild else ''
                    simplified_lang = original_language.split('-')[0].lower()
                    if simplified_lang not in allowed_languages:
                        language_to_set = default_language
                        self.fixed_problems.append(f"Unsupported language '{original_language}'. Changed to '{default_language}'")
                        lang_tag.firstChild.nodeValue = language_to_set
                    else:
                        language_to_set = original_language

            if original_language != language_to_set:
                self.files[opf_filename] = opf.toxml(encoding='utf-8').decode('utf-8')

        except Exception as e:
            logging.warning(f"Could not parse or modify OPF file '{opf_filename}': {e}")

    def fix_stray_img(self):
        """Remove stray <img> tags (those without a src attribute)."""
        for filename, content in self.files.items():
            ext = filename.split('.')[-1].lower()
            if ext in ['html', 'xhtml']:
                try:
                    dom = minidom.parseString(content)
                    stray_imgs = [img for img in dom.getElementsByTagName('img') if not img.getAttribute('src')]
                    if stray_imgs:
                        for img in stray_imgs:
                            if img.parentNode:
                                img.parentNode.removeChild(img)
                        self.files[filename] = dom.toxml(encoding='utf-8').decode('utf-8')
                        self.fixed_problems.append(f"Removed {len(stray_imgs)} stray image tag(s) in {filename}")
                except Exception:
                    continue # Ignore parsing errors

    def write_epub(self, output_path):
        """Write the modified contents to a new EPUB file."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
            # mimetype must be the first file and uncompressed
            if 'mimetype' in self.files:
                zip_ref.writestr('mimetype', self.files['mimetype'], compress_type=zipfile.ZIP_STORED)
            
            sorted_files = sorted(self.files.items(), key=lambda item: item[0] != 'mimetype')

            for filename, content in sorted_files:
                if filename != 'mimetype':
                    zip_ref.writestr(filename, content.encode('utf-8'))

            for filename, content in self.binary_files.items():
                zip_ref.writestr(filename, content)

    def process(self, input_path, output_path, default_language='en', force_language=None):
        """
        Run all fixing procedures on an EPUB file.
        """
        self.read_epub(input_path)
        
        self.fix_body_id_link()
        self.fix_book_language(default_language, force_language)
        self.fix_stray_img()
        self.fix_encoding() # Run this last as other steps might alter XML content

        if self.fixed_problems:
            logging.info(f"EPUB Fixer found and fixed {len(self.fixed_problems)} issues in '{os.path.basename(input_path)}'.")
            for problem in self.fixed_problems:
                logging.info(f"  - {problem}")
            self.write_epub(output_path)
            return True
        else:
            logging.info(f"EPUB Fixer found no issues in '{os.path.basename(input_path)}'.")
            # If no changes, we don't need to re-write the file.
            return False

def fix_epub_for_kindle(epub_path, default_language='en', force_language=None):
    """
    A wrapper function that takes an EPUB file path, fixes it for Kindle,
    and returns the path to the fixed file. The fixed file is placed in a
    temporary directory. If no fixes are needed, returns the original path.
    
    :param epub_path: Path to the input EPUB file.
    :param default_language: Default language to set if not specified or invalid.
    :param force_language: If set, forces the book language to the specified code (e.g., 'en', 'zh').
    :return: Path to the fixed EPUB file, or original path if no fixes were applied.
    """
    fixer = EPUBFixer()
    
    # Create a temporary file for the output to avoid overwriting the original
    temp_dir = tempfile.gettempdir()
    output_filename = "fixed-" + os.path.basename(epub_path)
    output_path = os.path.join(temp_dir, output_filename)
    
    try:
        fixes_applied = fixer.process(epub_path, output_path, default_language, force_language)
        if fixes_applied:
            return output_path
        else:
            # No changes were made, so no need for the new file.
            if os.path.exists(output_path):
                os.remove(output_path)
            return epub_path
    except Exception as e:
        logging.error(f"An error occurred while fixing EPUB '{epub_path}': {e}", exc_info=True)
        # Clean up temporary file on error
        if os.path.exists(output_path):
            os.remove(output_path)
        # Return original path on failure
        return epub_path