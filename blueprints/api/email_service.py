import smtplib
import logging
import mimetypes
from flask import Blueprint, request, jsonify, g
from flask_babel import gettext as _
import config_manager
from utils.email import create_calibre_mail
from utils.decorators import admin_required_api
from utils.activity_logger import log_activity, ActivityType

email_bp = Blueprint('email', __name__, url_prefix='/api')

def send_email_with_config(to_address, subject, body, config, attachment_content=None, attachment_filename=None):
    """
    Send email using provided configuration
    """
    logging.info(f"Attempting to send email to {to_address} via {config.get('SMTP_SERVER')}:{config.get('SMTP_PORT')}")
    
    if not all([config.get('SMTP_SERVER'), config.get('SMTP_PORT'), config.get('SMTP_USERNAME')]):
        logging.error("SMTP settings are incomplete.")
        return False, _("SMTP is not fully configured.")
        
    from_address = config['SMTP_USERNAME']
    
    attachment_type = None
    if attachment_filename:
        attachment_type, _unused = mimetypes.guess_type(attachment_filename)
        if attachment_type is None:
            # Fallback for unknown types
            attachment_type = 'application/octet-stream'
            logging.warning(f"Could not guess mimetype for {attachment_filename}, falling back to {attachment_type}")

    # Use Calibre's mail creation logic
    msg = create_calibre_mail(
        from_=from_address,
        to=to_address,
        subject=subject,
        text=body,
        attachment_data=attachment_content,
        attachment_name=attachment_filename,
        attachment_type=attachment_type
    )
        
    try:
        server = None
        encryption = config.get('SMTP_ENCRYPTION', 'none').lower()
        port = int(config['SMTP_PORT'])
        
        logging.info(f"Connecting to SMTP server with encryption: {encryption} on port {port}")
        if encryption == 'ssl':
            server = smtplib.SMTP_SSL(config['SMTP_SERVER'], port)
        else:
            server = smtplib.SMTP(config['SMTP_SERVER'], port)
            if encryption == 'starttls':
                logging.info("Starting TLS...")
                server.starttls()
        
        #server.set_debuglevel(1) # Log SMTP conversation
        
        if config.get('SMTP_PASSWORD'):
            logging.info(f"Logging in as {config['SMTP_USERNAME']}...")
            server.login(config['SMTP_USERNAME'], config['SMTP_PASSWORD'])
            
        logging.info("Sending email...")
        server.send_message(msg, from_address, [to_address])
        logging.info("Email sent successfully.")
        server.quit()
        return True, _("Email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}", exc_info=True)
        return False, _("Failed to send email: %(error)s", error=e)

@email_bp.route('/test_smtp', methods=['POST'])
@admin_required_api
def test_smtp_api():
    data = request.get_json()
    to_address = data.get('to_address')
    if not to_address:
        return jsonify({'error': _('Test recipient email address is required.')}), 400
    
    test_config = {
        'SMTP_SERVER': data.get('SMTP_SERVER'),
        'SMTP_PORT': data.get('SMTP_PORT'),
        'SMTP_USERNAME': data.get('SMTP_USERNAME'),
        'SMTP_PASSWORD': data.get('SMTP_PASSWORD'),
        'SMTP_ENCRYPTION': data.get('SMTP_ENCRYPTION'),
    }
    
    subject = "Anx Calibre Manager SMTP Test"
    body = "This is a test email from Anx Calibre Manager. If you received this, your SMTP settings are correct!"
    
    success, message = send_email_with_config(to_address, subject, body, test_config)
    
    if success:
        log_activity(ActivityType.TEST_SMTP, success=True, detail=_('Test email sent to %(email)s', email=to_address))
        return jsonify({'message': _("Test email successfully sent to %(email)s.", email=to_address)})
    else:
        log_activity(ActivityType.TEST_SMTP, success=False, failure_reason=_("Failed to send test email: %(message)s", message=message))
        return jsonify({'error': _("Failed to send test email: %(message)s", message=message)}), 500