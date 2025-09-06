import sys
import socket
import uuid as _uuid
from email.message import EmailMessage
from email.utils import formatdate, parseaddr
import encodings.idna

def decode_fqdn(fqdn):
    if isinstance(fqdn, bytes):
        enc = 'mbcs' if sys.platform == 'win32' else 'utf-8'
        try:
            fqdn = fqdn.decode(enc)
        except Exception:
            fqdn = ''
    return fqdn

def safe_localhost():
    try:
        fqdn = decode_fqdn(socket.getfqdn())
    except UnicodeDecodeError:
        fqdn = 'localhost.localdomain' # Fallback
    if '.' in fqdn and fqdn != '.':
        try:
            local_hostname = str(idna.ToASCII(fqdn))
        except Exception:
            local_hostname = 'localhost.localdomain'
    else:
        addr = '127.0.0.1'
        try:
            addr = socket.gethostbyname(socket.gethostname())
        except socket.gaierror:
            pass
        local_hostname = '[%s]' % addr
    return local_hostname

def get_msgid_domain(from_):
    try:
        from_email = parseaddr(from_)[1]
        msgid_domain = from_email.partition('@')[2].strip()
        msgid_domain = msgid_domain.rstrip('>').strip()
    except Exception:
        msgid_domain = ''
    return msgid_domain or safe_localhost()

def create_calibre_mail(from_, to, subject, text=None, attachment_data=None,
                 attachment_type=None, attachment_name=None):
    assert text or attachment_data

    outer = EmailMessage()
    outer['From'] = from_
    outer['To'] = to
    outer['Subject'] = subject
    outer['Date'] = formatdate(localtime=True)
    outer['Message-Id'] = f"<{_uuid.uuid4()}@{get_msgid_domain(from_)}>"
    outer.preamble = 'You will not see this in a MIME-aware mail reader.\n'

    if text is not None:
        if isinstance(text, bytes):
            text = text.decode('utf-8', 'replace')
        outer.set_content(text)

    if attachment_data is not None:
        assert attachment_data and attachment_name
        try:
            maintype, subtype = attachment_type.split('/', 1)
        except Exception:
            maintype, subtype = 'application', 'octet-stream'
        if isinstance(attachment_data, str):
            attachment_data = attachment_data.encode('utf-8')
        outer.add_attachment(attachment_data, maintype=maintype, subtype=subtype, filename=attachment_name)

    return outer