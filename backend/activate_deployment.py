"""Offline SQLite deployment of a verified experiment; run with server stopped."""
import argparse
import json
import math
import re
import shutil
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

FILES = ('global_model.pt', 'normalization.npz', 'metadata.json')


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def activate(root, db, eid, rows):
    models = root / 'models'
    candidate, latest = models / eid, models / 'latest'
    require(db.is_file(), 'Existing SQLite database not found')
    require(latest.is_dir() and all((latest / f).is_file() for f in FILES), 'Existing latest checkpoint incomplete')
    require(all((candidate / f).is_file() for f in FILES), 'Candidate incomplete')
    backup = root / 'deployment_backups' / (datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8])
    backup.mkdir(parents=True)
    shutil.copytree(latest, backup / 'latest')
    (backup / 'manifest.json').write_text(json.dumps({'database': str(db), 'experiment_id': eid}, indent=2), encoding='utf-8')
    stage = models / ('.stage_' + uuid.uuid4().hex)
    old = models / ('.previous_' + uuid.uuid4().hex)
    conn = sqlite3.connect(str(db), timeout=5)
    moved = False
    installed = False
    committed = False
    try:
        conn.execute('PRAGMA foreign_keys=ON')
        with sqlite3.connect(str(backup / 'database.sqlite3')) as dest:
            conn.backup(dest)
        require(conn.execute('PRAGMA quick_check').fetchone()[0] == 'ok', 'Database integrity check failed')
        conn.execute('BEGIN IMMEDIATE')
        scope = (eid, eid + '__%')
        # Escape underscore wildcard by comparing a literal prefix instead.
        where = 'model_type = ? OR substr(model_type,1,?) = ?'
        args = (eid, len(eid)+2, eid+'__')
        require(conn.execute('SELECT count(*) FROM metrics WHERE '+where,args).fetchone()[0] == 0, 'Experiment already imported; refusing duplicate activation')
        orgs = {r[0] for r in conn.execute('SELECT id FROM organizations')}
        require(all(r.org_id is None or r.org_id in orgs for r in rows), 'Unknown organisation in metric rows')
        keys = [(r.category,r.model_type,r.metric_name,r.org_id,r.round_number) for r in rows]
        require(len(keys)==len(set(keys)) and all(math.isfinite(r.metric_value) for r in rows), 'Invalid metric rows')
        conn.executemany('INSERT INTO metrics (timestamp,metric_name,metric_value,model_type,org_id,round_number,category) VALUES (?,?,?,?,?,?,?)', [(r.timestamp,r.metric_name,float(r.metric_value),r.model_type,r.org_id,r.round_number,r.category) for r in rows])
        require(conn.execute('SELECT count(*) FROM metrics WHERE '+where,args).fetchone()[0] == len(rows), 'Imported row count mismatch')
        selected = conn.execute("SELECT model_type FROM metrics WHERE category='experiment_metadata' AND metric_name='experiment_id' ORDER BY timestamp DESC LIMIT 1").fetchone()
        require(selected and selected[0]==eid, 'Dashboard would select a different experiment')
        shutil.copytree(candidate, stage)
        latest.rename(old); moved=True
        stage.rename(latest); installed=True
        require(json.loads((latest/'metadata.json').read_text(encoding='utf-8'))['experiment_id']==eid, 'Latest checkpoint mismatch')
        conn.commit(); committed=True
    except BaseException:
        if not committed:
            conn.rollback()
            if installed:
                shutil.rmtree(latest)
            if moved:
                old.rename(latest)
        print('Activation failed. Backup folder:', backup, file=sys.stderr)
        raise
    finally:
        conn.close()
        if stage.exists(): shutil.rmtree(stage)
    if old.exists(): shutil.rmtree(old)
    print('Backup folder:', backup)
    print('Imported metric rows:', len(rows))
    print('Active checkpoint:', eid)
    print('ACTIVATION PASSED')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('experiment_id')
    parser.add_argument('--confirm-offline', action='store_true', required=True, help='Confirm backend and other database writers are stopped')
    args=parser.parse_args()
    eid=args.experiment_id
    require(re.fullmatch(r'exp_\d{8}_\d{6}_[0-9a-f]{8}',eid), 'Invalid experiment ID')
    root=Path(__file__).resolve().parent
    # Re-run the existing full inference verification before changing anything.
    import subprocess
    subprocess.run([sys.executable,str(root/'prepare_deployment.py'),eid],cwd=root,check=True)
    from app.database.session import engine
    require(engine.url.get_backend_name()=='sqlite', 'This script supports SQLite only')
    require(engine.url.database and engine.url.database!=':memory:', 'Persistent database required')
    db=Path(engine.url.database).resolve()
    require(db == (root/'cyber20.db').resolve(), 'Unexpected database location; refusing activation')
    from app.database.seed import build_experiment_rows
    results=json.loads((root/f'{eid}_results.json').read_text(encoding='utf-8'))
    require(results['exported_mode']=='non_iid', 'Only the agreed Non-IID candidate is supported')
    rows=build_experiment_rows(results,deployment_mode='non_iid')
    activate(root,db,eid,rows)


if __name__=='__main__': main()
