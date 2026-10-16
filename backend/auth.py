"""Optional HTTP Basic authentication configured through the environment."""
import os
import secrets
from functools import wraps
from flask import Response, request


def _unauthorized(message='Authentication required'):
    return Response(
        message,
        401,
        {'WWW-Authenticate': 'Basic realm="App Watch", charset="UTF-8"'},
    )


def require_auth(storage):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            expected_username = os.getenv('BASIC_AUTH_USERNAME', '')
            expected_password = os.getenv('BASIC_AUTH_PASSWORD', '')

            # Authentication is opt-in and remains disabled when both values are empty.
            if not expected_username and not expected_password:
                return f(*args, **kwargs)

            # Fail closed if only half of the credentials were configured.
            if not expected_username or not expected_password:
                return _unauthorized('Basic authentication is not configured correctly')

            credentials = request.authorization
            username_matches = secrets.compare_digest(
                (credentials.username if credentials and credentials.username else '').encode('utf-8'),
                expected_username.encode('utf-8'),
            )
            password_matches = secrets.compare_digest(
                (credentials.password if credentials and credentials.password else '').encode('utf-8'),
                expected_password.encode('utf-8'),
            )
            if not username_matches or not password_matches:
                return _unauthorized()

            return f(*args, **kwargs)

        return decorated_function

    return decorator
