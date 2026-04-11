"""
User authentication is disabled. The decorator remains as a no-op so route
definitions stay unchanged; it does not enforce credentials.
"""
from functools import wraps


def require_auth(storage):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)

        return decorated_function

    return decorator
