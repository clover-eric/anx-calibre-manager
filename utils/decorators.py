from functools import wraps
from flask import g, jsonify
from flask_babel import gettext as _

def admin_required_api(f):
    """Decorator to require admin privileges for an API endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or not g.user.is_admin:
            return jsonify({'error': _('Administrator permission required.')}), 403
        return f(*args, **kwargs)
    return decorated_function

def maintainer_required_api(f):
    """Decorator to require maintainer or admin privileges for an API endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or not g.user.is_maintainer:
            return jsonify({'error': _('Maintainer or administrator permission required.')}), 403
        return f(*args, **kwargs)
    return decorated_function