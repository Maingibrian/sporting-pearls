#!/usr/bin/env python3
"""Phase 0 QA — T1..T7: settings fail-closed production guard.

Portable kit version (Phase 5): paths resolve relative to this file
(scripts/ inside the repo), and the interpreter is whatever Python is
running the script — so it works on a laptop (`python scripts/phase0_guard_tests.py`)
and in CI (dependencies from backend/requirements.txt installed first).

Each case boots `sporting_pearls_backend.settings` in a clean subprocess
with a controlled environment (no .env present in the source tree), then
asserts the expected outcome:
  * FAIL cases: process exits non-zero with ImproperlyConfigured
  * PASS cases: 'BOOT-OK' is printed
"""
import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / 'backend'
VENV_PY = BACKEND / '.venv' / 'bin' / 'python'
PY = str(VENV_PY) if VENV_PY.exists() else sys.executable

GOOD = {
    'DJANGO_SECRET_KEY': 'x' * 64,
    'DEBUG': '0',
    'ALLOWED_HOSTS': 'example.org,www.example.org',
    'CORS_ALLOW_ALL': '0',
    'SESSION_COOKIE_SECURE': '1',
    'CSRF_COOKIE_SECURE': '1',
}

RESULTS = []


def run(name, expect, env_overrides):
    env = {k: v for k, v in GOOD.items()}
    env.update(env_overrides)
    env['PYTHONPATH'] = str(BACKEND)
    proc = subprocess.run(
        [PY, '-c',
         "import sporting_pearls_backend.settings; print('BOOT-OK')"],
        cwd=str(BACKEND), env=env, capture_output=True, text=True, timeout=60)
    booted = 'BOOT-OK' in proc.stdout
    ok = (booted and expect == 'PASS') or (not booted and expect == 'FAIL')
    detail = (proc.stdout + proc.stderr).strip().splitlines()
    reason = next((ln for ln in detail if '  - ' in ln or 'BOOT-OK' in ln), '')
    RESULTS.append((name, expect, 'PASS' if ok else '**FAIL**', reason[:110]))
    return ok


def main():
    # T1 DEBUG
    run('T1a DEBUG=1 under production', 'FAIL', {'SP_ENV': 'production', 'DEBUG': '1'})
    # T2 wildcard / empty hosts
    run('T2a ALLOWED_HOSTS=*', 'FAIL', {'SP_ENV': 'production', 'ALLOWED_HOSTS': '*'})
    run('T2b ALLOWED_HOSTS empty', 'FAIL', {'SP_ENV': 'production', 'ALLOWED_HOSTS': ''})
    # T3 wildcard CORS
    run('T3a CORS_ALLOW_ALL=1', 'FAIL', {'SP_ENV': 'production', 'CORS_ALLOW_ALL': '1'})
    # T4 secret key
    run('T4a key missing', 'FAIL', {'SP_ENV': 'production', 'DJANGO_SECRET_KEY': ''})
    run('T4b key = known placeholder', 'FAIL',
        {'SP_ENV': 'production', 'DJANGO_SECRET_KEY': 'django-insecure-change-me-in-production'})
    run('T4c key too short (30 chars)', 'FAIL',
        {'SP_ENV': 'production', 'DJANGO_SECRET_KEY': 'y' * 30})
    # T5 insecure cookies
    run('T5a SESSION_COOKIE_SECURE=0', 'FAIL',
        {'SP_ENV': 'production', 'SESSION_COOKIE_SECURE': '0'})
    run('T5b CSRF_COOKIE_SECURE=0', 'FAIL',
        {'SP_ENV': 'production', 'CSRF_COOKIE_SECURE': '0'})
    # T6 fully hardened env boots
    run('T6a hardened env boots', 'PASS', {'SP_ENV': 'production'})
    # T7 development mode stays permissive (wildcards + weak key + no SP_ENV)
    run('T7a dev mode, no SP_ENV, wildcards+weak key', 'PASS',
        {'DJANGO_SECRET_KEY': 'weak', 'ALLOWED_HOSTS': '*', 'CORS_ALLOW_ALL': '1',
         'SESSION_COOKIE_SECURE': '0', 'CSRF_COOKIE_SECURE': '0'})
    # T7b: SP_ENV=development explicitly is also permissive
    run('T7b SP_ENV=development explicit', 'PASS',
        {'SP_ENV': 'development', 'DJANGO_SECRET_KEY': 'weak'})

    # T6b: manage.py check under a fully hardened production env
    env = {k: v for k, v in GOOD.items()}
    env.update({'SP_ENV': 'production', 'PYTHONPATH': str(BACKEND)})
    proc = subprocess.run([PY, 'manage.py', 'check'], cwd=str(BACKEND),
                          env=env, capture_output=True, text=True, timeout=120)
    ok = proc.returncode == 0 and 'hard security checks passed' in (proc.stdout + proc.stderr)
    RESULTS.append(('T6b manage.py check (production env)', 'PASS',
                    'PASS' if ok else '**FAIL**',
                    'checks passed + guard message printed' if ok else proc.stderr[-110:]))

    # T7c: manage.py check in development (source tree default)
    proc = subprocess.run([PY, 'manage.py', 'check'], cwd=str(BACKEND),
                          capture_output=True, text=True, timeout=120)
    ok = proc.returncode == 0
    RESULTS.append(('T7c manage.py check (dev, no env)', 'PASS',
                    'PASS' if ok else '**FAIL**', proc.stdout.strip()[-110:]))

    print(f"\n{'CASE':<44} {'EXPECT':<7} {'RESULT':<9} REASON")
    print('-' * 110)
    all_ok = True
    for name, expect, got, reason in RESULTS:
        print(f'{name:<44} {expect:<7} {got:<9} {reason}')
        if got == '**FAIL**':
            all_ok = False
    print('-' * 110)
    print('ALL GUARD TESTS PASS' if all_ok else 'SOME TESTS FAILED')
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    main()
