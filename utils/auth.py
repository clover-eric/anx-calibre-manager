from requests.auth import HTTPDigestAuth
import config_manager

def get_calibre_auth():
    config = config_manager.config
    if config.get('CALIBRE_USERNAME') and config.get('CALIBRE_PASSWORD'):
        return HTTPDigestAuth(config['CALIBRE_USERNAME'], config['CALIBRE_PASSWORD'])
    return None