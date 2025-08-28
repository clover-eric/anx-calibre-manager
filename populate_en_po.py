import polib

# The path to your English .po file
po_file_path = 'translations/en/LC_MESSAGES/messages.po'

# Load the .po file
po = polib.pofile(po_file_path)

# Iterate through each entry and copy msgid to msgstr if msgstr is empty
for entry in po:
    if not entry.msgstr:
        # For multi-line msgid, polib handles the concatenation correctly
        entry.msgstr = entry.msgid

# Save the changes back to the file
po.save(po_file_path)

print(f"Successfully populated empty msgstr fields in {po_file_path}")