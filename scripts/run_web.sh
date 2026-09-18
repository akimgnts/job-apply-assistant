#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ ! -x .venv/bin/python ]]; then
  python3.11 -m venv .venv
fi
if ! .venv/bin/python -c 'import sys; assert sys.version_info[:2] == (3, 11)' 2>/dev/null; then
  echo 'Le lancement local nécessite un environnement .venv Python 3.11.' >&2
  exit 1
fi
if ! .venv/bin/python - <<'PY'
import importlib.metadata
import re
from pathlib import Path
for line in Path('requirements.txt').read_text().splitlines():
    requirement = line.strip()
    if requirement and not requirement.startswith('#'):
        importlib.metadata.version(re.split(r'[<>=!~\[; ]', requirement)[0])
PY
then
  .venv/bin/python -m pip install -r requirements.txt
fi

exec .venv/bin/python - "$@" <<'PY'
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

parser = argparse.ArgumentParser(description='Lancer Job Apply en local.')
parser.add_argument('--import-snapshot', action='store_true', help='Importer les archives datées du dépôt.')
args = parser.parse_args()
load_dotenv(Path.cwd() / '.env', override=False)
os.environ.setdefault('DATABASE_URL', 'sqlite:///' + str(Path.cwd() / 'data' / 'web_workspace.sqlite3'))
if make_url(os.environ['DATABASE_URL']).get_backend_name() == 'sqlite':
    from app.web.bootstrap import initialize_local
    result = initialize_local(os.environ['DATABASE_URL'], with_snapshot=args.import_snapshot)
    print('Espace local initialisé :', result, flush=True)
elif args.import_snapshot:
    parser.error("L'import de démarrage est réservé à SQLite local.")
else:
    print('Base configurée conservée ; aucune initialisation ni migration automatique.', flush=True)
port = int(os.environ.get('PORT', '8000'))
os.execv(sys.executable, [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)])
PY
