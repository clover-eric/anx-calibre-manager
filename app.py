import logging
import os
import bcrypt
from flask import Flask, g, redirect, url_for, request
from contextlib import closing
import database
import config_manager
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from werkzeug.middleware.proxy_fix import ProxyFix
from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.fs_dav_provider import FilesystemProvider
from wsgidav.dc.base_dc import BaseDomainController

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class User:
    def __init__(self, row):
        if row:
            for key in row.keys():
                setattr(self, key, row[key])
        else:
            self.id = None
            self.is_admin = False

class AnxDomainController(BaseDomainController):
    def __init__(self, wsgidav_app, config):
        super().__init__(wsgidav_app, config)
        self.realm = "AnxCalibreManager"

    def get_domain_realm(self, path_info, environ):
        return self.realm

    def require_authentication(self, realm, environ):
        return True

    def supports_http_digest_auth(self):
        return False

    def digest_auth_user(self, realm, user_name, environ):
        return False # Not implemented

    def basic_auth_user(self, realm, user_name, password, environ):
        """Authenticate user and authorize access to their own directory."""
        db = database.get_db()
        user = db.execute("SELECT password_hash FROM users WHERE username = ?", (user_name,)).fetchone()
        db.close()

        if not user or not user['password_hash']:
            logging.warning(f"WebDAV auth failed: user '{user_name}' not found.")
            return False

        password_hash = user['password_hash']
        if isinstance(password_hash, str):
            password_hash = password_hash.encode('utf-8')

        if not bcrypt.checkpw(password.encode('utf-8'), password_hash):
            logging.warning(f"WebDAV auth failed: incorrect password for user '{user_name}'.")
            return False

        # Authorization: Check if the user is accessing their own directory.
        # The path_info from the environ is relative to the mount point,
        # so it will be like '/<username>/<path>'
        path_info = environ.get('PATH_INFO', '')
        path_parts = path_info.strip('/').split('/')
        
        if not path_parts or path_parts[0] != user_name:
            logging.warning(f"WebDAV auth failed: user '{user_name}' attempted to access path '{path_info}'.")
            return False
        
        logging.info(f"WebDAV auth successful for user '{user_name}'.")
        # Create user directory if it doesn't exist
        webdav_root = self.wsgidav_app.config["provider_mapping"]["/"].root_folder_path
        user_dir = os.path.join(webdav_root, user_name)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            logging.info(f"Created WebDAV directory for user '{user_name}' at {user_dir}")

        return True


def create_app():
    app = Flask(__name__)
    
    app.config.from_mapping(config_manager.config)
    app.secret_key = app.config['SECRET_KEY']
    
    # Set session lifetime from config
    from datetime import timedelta
    session_lifetime_days = app.config.get('SESSION_LIFETIME_DAYS', 7)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=int(session_lifetime_days))

    database.create_schema()

    from blueprints.main import main_bp
    from blueprints.auth import auth_bp
    from blueprints.api import api_bp
    from blueprints.mcp import mcp_bp
    from blueprints.kosync import kosync_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(mcp_bp)
    app.register_blueprint(kosync_bp)

    @app.before_request
    def before_request_handler():
        g.user = get_current_user()
        # Pass the app context to g for the MCP endpoint to use
        g.app = app
        with closing(database.get_db()) as db:
            user_count = db.execute('SELECT COUNT(id) FROM users').fetchone()[0]
            if user_count == 0 and request.endpoint and not request.endpoint.startswith('auth.') and not request.endpoint == 'static':
                 return redirect(url_for('auth.setup'))

    def get_current_user():
        from flask import session
        user_row = None
        if 'user_id' in session:
            with closing(database.get_db()) as db:
                user_row = db.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],)).fetchone()
        return User(user_row)

    # --- WebDAV Setup (with WsgiDAV) ---
    webdav_root = config_manager.config.get("WEBDAV_ROOT", "/webdav")
    if not os.path.exists(webdav_root):
        os.makedirs(webdav_root)

    provider = FilesystemProvider(webdav_root)

    config = {
        "provider_mapping": {"/": provider},
        "http_authenticator": {
            "domain_controller": AnxDomainController,
            "accept_basic": True,
            "accept_digest": False,
            "default_to_digest": False,
        },
        "verbose": 1,
        "logging": {
            "enable": False,
        },
        "dir_browser": {"enable": True},
        "mount_path": "/webdav",
    }
    dav_app = WsgiDAVApp(config)
    # Combine the main app and the WebDAV app
    dispatcher = DispatcherMiddleware(app.wsgi_app, {
        '/webdav': dav_app
    })

    # Apply ProxyFix to the combined application to handle headers from the reverse proxy
    app.wsgi_app = ProxyFix(dispatcher, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    return app

if __name__ == '__main__':
    from cheroot import wsgi
    
    app = create_app()
    
    port = int(os.environ.get("PORT", 5000))
    server = wsgi.Server(('0.0.0.0', port), app)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
