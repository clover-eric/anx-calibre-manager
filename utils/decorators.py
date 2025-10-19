from functools import wraps
from flask import g, jsonify, redirect, url_for, request
from flask_babel import gettext as _

def login_required(f):
    """Decorator to require login for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or g.user.id is None:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

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

def login_required_api(f):
    """Decorator to require login for an API endpoint."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None or g.user.id is None:
            return jsonify({'error': _('Authentication required.')}), 401
        return f(*args, **kwargs)
    return decorated_function