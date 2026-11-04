#!/usr/bin/env python3
"""Rev 26 check — every squad must be 4-2-3-1 end to end: seed JSON -> DB -> public API.

Run from anywhere: paths are derived from the repo layout.
Scratch DB lives in /tmp so it never touches a real database.
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CANDIDATE = os.path.dirname(SCRIPT_DIR)
BASE = _CANDIDATE if os.path.exists(os.path.join(_CANDIDATE, 'backend', 'manage.py')) \
    else '/home/z/my-project/work/sp-repo'
SCRATCH_DB = '/tmp/rev26-check.sqlite3'

os.environ['DJANGO_SETTINGS_MODULE'] = 'sporting_pearls_backend.settings'
os.environ['SP_ENV'] = 'local'
os.environ['DJANGO_SECRET_KEY'] = 'x' * 56
os.environ['DB_PATH'] = SCRATCH_DB
sys.path.insert(0, os.path.join(BASE, 'backend'))

if os.path.exists(SCRATCH_DB):
    os.remove(SCRATCH_DB)

import django  # noqa: E402
django.setup()

from django.core.management import call_command  # noqa: E402

failures = []


def check(name, ok, detail=''):
    print(('PASS' if ok else 'FAIL'), '-', name, detail)
    if not ok:
        failures.append(name)


OLD_FORMS = ('4-4-2', '4-3-3', '3-5-2')

# 1) Seed JSON -------------------------------------------------------------
with open(os.path.join(BASE, 'backend', 'player_seed.json'), encoding='utf-8') as fh:
    seed_doc = json.load(fh)
seed = seed_doc['squads']
check('seed: 5 squads', len(seed) == 5, str(len(seed)))
check('seed: every squad 4-2-3-1', all(s.get('form') == '4-2-3-1' for s in seed))
check('seed: no old formations', all(s.get('form') not in OLD_FORMS for s in seed))

# 2) Migrate + import into scratch DB -------------------------------------
call_command('migrate', verbosity=0)
call_command('import_roster', verbosity=0)

from submissions.models import Squad, Player  # noqa: E402

check('DB: 5 squads', Squad.objects.count() == 5, str(Squad.objects.count()))
check('DB: every squad 4-2-3-1',
      not Squad.objects.exclude(formation='4-2-3-1').exists())
check('DB: 50 players', Player.objects.count() == 50, str(Player.objects.count()))

# 3) Public API ------------------------------------------------------------
from django.test import Client  # noqa: E402

client = Client()
resp = client.get('/api/players/')
check('API /api/players/ -> 200', resp.status_code == 200, str(resp.status_code))
body = resp.content.decode('utf-8')
check('API: 4-2-3-1 present', '4-2-3-1' in body)
check('API: no old formations', all(f not in body for f in OLD_FORMS))

resp2 = client.get('/api/health/')
check('API /api/health/ -> 200', resp2.status_code == 200, str(resp2.status_code))

print()
if failures:
    print('RESULT: %d FAILURE(S): %s' % (len(failures), ', '.join(failures)))
    sys.exit(1)
print('RESULT: ALL CHECKS PASSED — Rev 26 is fully 4-2-3-1.')
