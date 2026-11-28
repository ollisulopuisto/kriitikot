"""Content-address local assets so cached files cannot mix page releases."""
from hashlib import sha256
from pathlib import Path


def asset_url(static_root, filename):
    version = sha256((Path(static_root) / filename).read_bytes()).hexdigest()[:16]
    return f'static/{filename}?v={version}'
