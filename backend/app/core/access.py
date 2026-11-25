"""Local demonstration API access control. Not federated-client authentication."""
from __future__ import annotations
import hashlib
import json
import time
from pathlib import Path
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.core.config import get_settings

bearer = HTTPBearer(auto_error=False)


def registry_path() -> Path:
    return Path(get_settings().access_registry_path).expanduser().resolve()


def require_access(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> str:
    denied = HTTPException(401, 'Missing, invalid, expired or revoked credential', headers={'WWW-Authenticate': 'Bearer'})
    if credentials is None or len(credentials.credentials) > 256:
        raise denied
    digest = hashlib.sha256(credentials.credentials.encode('utf-8')).hexdigest()
    try:
        entries = json.loads(registry_path().read_text(encoding='utf-8'))
        entry = entries.get(digest)
        if not isinstance(entry, dict):
            raise denied
        role = entry.get('role')
        expires = entry.get('expires_at')
        if (role not in ('viewer', 'operator') or entry.get('revoked') is not False
                or type(expires) not in (int, float) or not time.time() < expires < float('inf')):
            raise denied
    except HTTPException:
        raise
    except (OSError, ValueError, TypeError, AttributeError):
        raise HTTPException(503, 'Access registry unavailable') from None
    if request.method not in ('GET', 'HEAD') and role != 'operator':
        raise HTTPException(403, 'Operator permission required')
    return role
