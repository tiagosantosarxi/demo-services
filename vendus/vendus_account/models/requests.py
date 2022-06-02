from base64 import b64encode

from requests.auth import AuthBase, to_native_string


def _basic_auth_key(key):
    """Returns a Basic Auth string."""

    if isinstance(key, str):
        key = key.encode('latin1')

    authstr = 'Basic ' + to_native_string(
        b64encode(b'%s' % key).strip()
    )

    return authstr


class HTTPBasicAuthKey(AuthBase):
    """Attaches HTTP Basic Authentication with Key to the given Request object."""

    def __init__(self, key):
        self.key = key

    def __eq__(self, other):
        return all([
            self.key == getattr(other, 'key', None),
        ])

    def __ne__(self, other):
        return not self == other

    def __call__(self, r):
        r.headers['Authorization'] = _basic_auth_key(self.key)
        return r
