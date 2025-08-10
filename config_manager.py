import os
import json

# Use separate, standard directories for config and data.
# These are intended to be mounted as separate volumes in Docker.
CONFIG_DIR = os.environ.get('CONFIG_DIR', '/config')
WEBDAV_DIR = os.environ.get('WEBDAV_DIR', '/webdav')

CONFIG_FILE = os.path.join(CONFIG_DIR, 'settings.json')
DATABASE_PATH = os.path.join(CONFIG_DIR, 'app.db')

# Define default configuration and environment variable mappings
DEFAULT_CONFIG = {
    # Global Calibre related settings
    'CALIBRE_URL': {'env': 'CALIBRE_URL', 'default': 'http://localhost:8081'},
    'CALIBRE_USERNAME': {'env': 'CALIBRE_USERNAME', 'default': ''},
    'CALIBRE_PASSWORD': {'env': 'CALIBRE_PASSWORD', 'default': ''},
    
    # Global application security settings
    'SECRET_KEY': {'env': 'SECRET_KEY', 'default': ''}, # Will be generated on first load
    'LOGIN_MAX_ATTEMPTS': {'env': 'LOGIN_MAX_ATTEMPTS', 'default': 5},

    # WebDAV root directory
    'WEBDAV_ROOT': {'env': 'WEBDAV_ROOT', 'default': WEBDAV_DIR},

    # Default format priority
    'DEFAULT_FORMAT_PRIORITY': {'env': 'DEFAULT_FORMAT_PRIORITY', 'default': 'azw3,mobi,epub,fb2,txt,pdf'},

    # SMTP (Mail sending) settings
    'SMTP_SERVER': {'env': 'SMTP_SERVER', 'default': ''},
    'SMTP_PORT': {'env': 'SMTP_PORT', 'default': 587},
    'SMTP_USERNAME': {'env': 'SMTP_USERNAME', 'default': ''},
    'SMTP_PASSWORD': {'env': 'SMTP_PASSWORD', 'default': ''},
    'SMTP_ENCRYPTION': {'env': 'SMTP_ENCRYPTION', 'default': 'ssl'}, # 'ssl', 'starttls', or 'none'
}

# Initialize config as a dictionary first to avoid NameError during initial load
config = {}

def load_config():
    """
    Loads the global configuration.
    Priority: Config file > Environment variables > Default values
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_from_file = json.load(f)
        except (json.JSONDecodeError, IOError):
            config_from_file = {}
    else:
        config_from_file = {}

    loaded_config = {}
    for key, values in DEFAULT_CONFIG.items():
        # Priority 1: Config file
        if key in config_from_file:
            loaded_config[key] = config_from_file[key]
        # Priority 2: Environment variables
        elif os.environ.get(values['env']):
            val = os.environ.get(values['env'])
            if key in ['LOGIN_MAX_ATTEMPTS', 'SMTP_PORT']:
                try:
                    loaded_config[key] = int(val)
                except (ValueError, TypeError):
                    loaded_config[key] = values['default']
            else:
                loaded_config[key] = val
        # Priority 3: Default values
        else:
            loaded_config[key] = values['default']
            
    # Ensure SECRET_KEY always exists and is valid
    if not loaded_config.get('SECRET_KEY'):
        loaded_config['SECRET_KEY'] = os.urandom(24).hex()
        # Save immediately to persist the key
        save_config({'SECRET_KEY': loaded_config['SECRET_KEY']})

    return loaded_config

def save_config(new_config):
    """
    Saves the global configuration to a file and updates the in-memory config.
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    current_config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                current_config = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    for key, value in new_config.items():
        if key in DEFAULT_CONFIG:
            # Skip empty password fields to avoid clearing them
            if key in ['CALIBRE_PASSWORD', 'SMTP_PASSWORD'] and not value:
                continue

            if key in ['LOGIN_MAX_ATTEMPTS', 'SMTP_PORT'] and value is not None:
                try:
                    current_config[key] = int(value)
                except (ValueError, TypeError):
                    pass
            elif key == 'SMTP_ENCRYPTION':
                current_config[key] = value.lower() if value in ['ssl', 'tls', 'none'] else 'tls'
            else:
                current_config[key] = value

    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_config, f, indent=4, ensure_ascii=False)
        
        # Update in-memory config
        config.update(current_config)
        
        return True, "Global configuration saved successfully."
    except IOError as e:
        return False, f"Failed to save config file: {e}"

# Load the configuration when the module is loaded
config.update(load_config())