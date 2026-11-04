#!/usr/bin/env python3
"""Rev 28 QA — squad tabstrip arrows (site) + technical-team flow (portal).

Serves site/ on :8095 and the Django backend on :8020 with a scratch DB,
then drives both with a real browser:

  A. mobile viewport  — squad strip shows arrows, next/prev switch squads,
                        active tab stays centred, no console errors
  B. desktop viewport — arrows never appear (sticky vertical list stays)
  C. portal           — login -> Technical team view -> empty state ->
                        add coach -> publish -> card updates ->
                        /api/coaches/ serves it -> hide -> gone again
"""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path('/home/z/my-project/work/sp-repo')
SITE = REPO / 'site'
DB = '/tmp/rev28-qa.sqlite3'
results = []


def check(name, ok, detail=''):
    print(('PASS' if ok else 'FAIL'), '-', name, detail)
    results.append(ok)


def wait_port(port, timeout=30):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                return True
        except OSError:
            time.sleep(0.4)
    return False


# ---- 1. backend on :8020 with a scratch database ------------------------
env = dict(os.environ,
           DJANGO_SETTINGS_MODULE='sporting_pearls_backend.settings',
           SP_ENV='local', DJANGO_SECRET_KEY='x' * 56, DB_PATH=DB,
           ALLOWED_HOSTS='localhost,127.0.0.1', CORS_ALLOW_ALL='1',
           DEBUG='1')
if os.path.exists(DB):
    os.remove(DB)
be = subprocess.Popen([sys.executable, 'manage.py', 'migrate', '--noinput'],
                      cwd=REPO / 'backend', env=env,
                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
be.wait()
subprocess.run([sys.executable, 'manage.py', 'shell', '-c',
                "from django.contrib.auth.models import User;"
                "User.objects.filter(username='qa').delete();"
                "User.objects.create_superuser('qa','qa@example.com','qa-pass-123')"],
               cwd=REPO / 'backend', env=env, check=True,
               stdout=subprocess.DEVNULL)
subprocess.run([sys.executable, 'manage.py', 'import_roster'],
               cwd=REPO / 'backend', env=env, check=True,
               stdout=subprocess.DEVNULL)
runserver = subprocess.Popen(
    [sys.executable, 'manage.py', 'runserver', '127.0.0.1:8020', '--noreload'],
    cwd=REPO / 'backend', env=env,
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---- 2. static site on :8095 --------------------------------------------
site_srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8095',
                             '--bind', '127.0.0.1', '--directory', str(SITE)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    ok_be = wait_port(8020)
    ok_site = wait_port(8095)
    check('servers up (backend :8020, site :8095)', ok_be and ok_site)

    with sync_playwright() as pw:
        browser = pw.chromium.launch()

        # ---- A. mobile tabstrip -----------------------------------------
        ctx = browser.new_context(viewport={'width': 390, 'height': 844})
        page = ctx.new_page()
        errors = []
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.on('pageerror', lambda e: errors.append(str(e)))
        # the local test origin is not in the live backend's CORS list —
        # fulfil those calls locally so the console stays clean
        page.route('**sporting-pearlsorg.onrender.com**', lambda r: r.fulfill(
            status=200, content_type='application/json',
            body='{"ok":true,"squads":[],"count":0,"coaches":[]}'))
        page.goto('http://127.0.0.1:8095/the-squad.html', wait_until='networkidle',
                  timeout=45000)
        page.wait_for_timeout(600)
        prev, nxt = page.locator('#tabPrev'), page.locator('#tabNext')
        check('mobile: arrows are visible', prev.is_visible() and nxt.is_visible())
        check('mobile: right edge fade hints at more squads',
              'can-right' in (page.locator('.tabstrip').get_attribute('class') or ''))
        check('mobile: prev disabled at first squad', prev.is_disabled())
        nxt.click()
        page.wait_for_timeout(900)
        check('mobile: next arrow switches to U14',
              page.locator('#pmTeam').inner_text().strip() == 'U14 Development Squad')
        check('mobile: prev enabled after moving', not prev.is_disabled())
        # active tab should now be scrolled into view (carousel-aligned)
        box_tab = page.locator('.tab.active').bounding_box()
        box_track = page.locator('#teamTabs').bounding_box()
        inview = box_tab and box_track and \
            box_tab['x'] >= box_track['x'] - 6 and \
            box_tab['x'] + box_tab['width'] <= box_track['x'] + box_track['width'] + 6
        check('mobile: active squad fully in view', bool(inview),
              f"tab {box_tab and round(box_tab['x'])}..{box_tab and round(box_tab['x']+box_tab['width'])} "
              f"track {box_track and round(box_track['x'])}..{box_track and round(box_track['x']+box_track['width'])}")
        for _ in range(4):
            if nxt.is_enabled():
                nxt.click()
                page.wait_for_timeout(700)
        page.wait_for_timeout(600)
        check('mobile: reached Féminin (last squad)',
              page.locator('#pmTeam').inner_text().strip() == 'Sporting Pearls Féminin')
        check('mobile: next disabled at last squad', nxt.is_disabled())
        check('mobile: zero console errors', not errors, errors[:2])
        ctx.close()

        # ---- B. desktop: arrows never appear ---------------------------
        ctx = browser.new_context(viewport={'width': 1400, 'height': 900})
        page = ctx.new_page()
        page.goto('http://127.0.0.1:8095/the-squad.html', wait_until='networkidle',
                  timeout=45000)
        check('desktop: arrows hidden',
              not page.locator('#tabPrev').is_visible()
              and not page.locator('#tabNext').is_visible())
        cols = page.evaluate(
            "getComputedStyle(document.getElementById('teamTabs')).flexDirection")
        check('desktop: sticky vertical list kept', cols == 'column', cols)
        check('desktop: all five tabs visible at once',
              page.locator('.tab:visible').count() == 5)
        ctx.close()

        # ---- C. portal technical-team flow ------------------------------
        ctx = browser.new_context(viewport={'width': 1280, 'height': 900})
        page = ctx.new_page()
        errors = []
        page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
        page.goto('http://127.0.0.1:8020/portal/login/', wait_until='networkidle')
        page.fill('input[name="username"]', 'qa')
        page.fill('input[name="password"]', 'qa-pass-123')
        page.click('button[type="submit"]')
        page.wait_for_url('**/portal/**', timeout=15000)
        page.wait_for_load_state('networkidle')
        check('portal: staff login works', '/portal/' in page.url)

        page.click('.nav-item[data-view="coaches"]')
        page.wait_for_timeout(400)
        check('portal: Technical team view appears',
              page.locator('#view-coaches.active').count() == 1)
        check('portal: view title switched',
              'Technical team' in page.locator('#tb-title-h').inner_text())
        check('portal: empty state shown before first coach',
              page.locator('#co-empty').is_visible())

        # add a coach
        page.click('#btn-add-coach')
        page.wait_for_timeout(300)
        page.fill('#ca-name', 'Josephat Okello')
        page.fill('#ca-role', 'Head Coach')
        page.select_option('#ca-squad', 'U14')
        page.fill('#ca-bio', 'CAF A licence, 12 seasons with the Pearls.')
        page.check('#ca-pub')
        page.click('#ca-save')
        page.wait_for_timeout(1600)          # toast + auto reload
        page.wait_for_load_state('networkidle')
        card = page.locator('.co-card[data-name="Josephat Okello"]')
        check('portal: coach card appears after add', card.count() == 1)
        check('portal: card shows Live on site',
              'Live on site' in card.inner_text())
        check('portal: empty state gone', not page.locator('#co-empty').is_visible())

        # the public API serves the published coach (squad arrives as the
        # display label — that is what the website card prints)
        api = page.request.get('http://127.0.0.1:8020/api/coaches/').json()
        check('api: published coach served',
              api.get('count') == 1 and
              api['coaches'][0]['name'] == 'Josephat Okello' and
              'U14' in api['coaches'][0]['squad'],
              str(api)[:120])

        # edit the coach
        card.locator('.co-act[data-act="edit"]').click()
        page.wait_for_timeout(300)
        page.fill('#ce-role', 'Head Coach & Technical Director')
        page.click('#ce-save')
        page.wait_for_timeout(500)
        check('portal: edit updates the card in place',
              'Technical Director' in
              page.locator('.co-card[data-name="Josephat Okello"]').inner_text())

        # hide -> draft, api count back to zero
        page.locator('.co-card[data-name="Josephat Okello"] '
                     '.co-act[data-act="toggle"]').click()
        page.wait_for_timeout(500)
        api = page.request.get('http://127.0.0.1:8020/api/coaches/').json()
        check('api: hidden coach vanishes from the website feed',
              api.get('count') == 0, str(api)[:80])
        check('portal: card flips to Draft',
              'Draft' in
              page.locator('.co-card[data-name="Josephat Okello"]').inner_text())
        check('portal: zero console errors', not errors, errors[:2])
        ctx.close()
        browser.close()
finally:
    runserver.terminate()
    site_srv.terminate()
    for p in (runserver, site_srv):
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()

print()
if all(results):
    print('RESULT: ALL REV 28 CHECKS PASSED.')
    sys.exit(0)
print('RESULT: %d check(s) FAILED.' % results.count(False))
sys.exit(1)
