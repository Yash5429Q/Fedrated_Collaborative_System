"""Single-administrator local credential management. Never commit the registry."""
import argparse
import hashlib
import json
import os
import secrets
import tempfile
import time
from pathlib import Path
from app.core.access import registry_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    issue = sub.add_parser('issue')
    issue.add_argument('role', choices=['viewer', 'operator'])
    issue.add_argument('--minutes', type=int, default=60)
    revoke = sub.add_parser('revoke')
    revoke.add_argument('credential_id')
    sub.add_parser('list')
    args = parser.parse_args()
    path = registry_path()
    entries = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not isinstance(entries, dict):
        raise SystemExit('Invalid registry')
    if args.action == 'list':
        for key, row in entries.items():
            print(key, row['role'], 'revoked' if row['revoked'] else 'expired' if row['expires_at'] <= time.time() else 'active')
        return
    if args.action == 'issue':
        if not 1 <= args.minutes <= 1440:
            parser.error('minutes must be between 1 and 1440')
        token = secrets.token_urlsafe(32)
        key = hashlib.sha256(token.encode()).hexdigest()
        entries[key] = {'role': args.role, 'expires_at': time.time() + args.minutes * 60, 'revoked': False}
    else:
        key = args.credential_id
        if key not in entries:
            parser.error('unknown credential ID')
        entries[key]['revoked'] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
    print('Credential ID:', key)
    if args.action == 'issue':
        print('Bearer token (shown once; keep private):', token)
    else:
        print('Revoked')

if __name__ == '__main__':
    main()
