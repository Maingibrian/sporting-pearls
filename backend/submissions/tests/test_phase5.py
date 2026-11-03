"""Phase 5 tests — healthz probe, media auth-gating (R17), dashboard
asset route, and the tightened CSP surface.

Context (PRODUCTION-READINESS.md §4 / change log rev 16):
  * /media/ was served by django.views.static.serve UNAUTHENTICATED —
    any unpublished player photo was one guessable path away. It is now
    portal.media_serve: published players' photos stay public (the
    squad pages embed them, media-consented), everything else requires
    a staff session or the owning guardian.
  * The portal dashboard's inline <script> moved to
    /portal/assets/dash.js (allow-listed, staff-only).
  * /healthz/ (and '') checks database readiness, leaks no internals.
"""
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from parents.models import Guardian, GuardianPlayer
from submissions.models import Player, Squad

BACKEND_DIR = Path(__file__).resolve().parents[2]

# a real 1x1 PNG
PNG_1PX = bytes.fromhex(
    '89504e470d0a1a0a0000000d494844520000000100000001080600000'
    '01f15c4890000000d49444154789c626001000000ffff030000060005'
    '57bfabd40000000049454e44ae426082')


def _make_player(ref, published, photo_name):
    squad, _ = Squad.objects.get_or_create(
        key='u15', defaults={'code': 'U15', 'label': 'U15'})
    p = Player(squad=squad, ref=ref, first_name='Test', last_name='Player',
               is_published=published)
    p.photo = photo_name          # set the stored name without a file write
    p.save()
    return p


class HealthzTests(TestCase):

    def test_healthz_ok_on_both_paths(self):
        for url in ('/healthz/', '/'):
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertTrue(r.json()['ok'])
            self.assertEqual(r.json()['service'], 'sporting-pearls-backend')

    def test_healthz_reports_503_when_db_down(self):
        from django.db import connection
        with mock.patch.object(connection, 'cursor') as cur:
            cur.side_effect = RuntimeError('db gone')
            r = self.client.get('/healthz/')
        self.assertEqual(r.status_code, 503)
        self.assertFalse(r.json()['ok'])
        # no internals leaked
        self.assertNotIn(b'db gone', r.content)


class MediaGateTests(TestCase):
    """R17: /media/ is authenticated except for published players."""

    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        (Path(self.tmp) / 'players').mkdir()
        for name in ('pub.png', 'priv.png', 'orphan.png'):
            (Path(self.tmp) / 'players' / name).write_bytes(PNG_1PX)
        (Path(self.tmp) / 'secret.txt').write_text('not a photo', encoding='utf-8')

        self.pub = _make_player('U15-01', True, 'players/pub.png')
        self.priv = _make_player('U15-02', False, 'players/priv.png')
        # orphan.png belongs to no player row

        self.staff = User.objects.create_user('staff1', password='x' * 20,
                                              is_staff=True)
        self.g1 = User.objects.create_user('guard1@example.com',
                                           password='x' * 20)
        self.guardian1 = Guardian.objects.create(user=self.g1, full_name='G One')
        GuardianPlayer.objects.create(guardian=self.guardian1, player=self.priv)
        self.g2 = User.objects.create_user('guard2@example.com',
                                           password='x' * 20)
        self.guardian2 = Guardian.objects.create(user=self.g2, full_name='G Two')
        GuardianPlayer.objects.create(guardian=self.guardian2,
                                      player=self.pub)  # different child only

    def test_published_photo_is_public(self):
        with override_settings(MEDIA_ROOT=self.tmp):
            r = self.client.get('/media/players/pub.png')
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r['Content-Type'], 'image/png')

    def test_unpublished_photo_anonymous_404(self):
        with override_settings(MEDIA_ROOT=self.tmp):
            r = self.client.get('/media/players/priv.png')
            self.assertEqual(r.status_code, 404)

    def test_unpublished_photo_staff_200(self):
        self.client.force_login(self.staff)
        with override_settings(MEDIA_ROOT=self.tmp):
            r = self.client.get('/media/players/priv.png')
            self.assertEqual(r.status_code, 200)

    def test_unpublished_photo_owning_guardian_200(self):
        self.client.force_login(self.g1)
        with override_settings(MEDIA_ROOT=self.tmp):
            r = self.client.get('/media/players/priv.png')
            self.assertEqual(r.status_code, 200)

    def test_unpublished_photo_other_guardian_404(self):
        """Guardian of a DIFFERENT child gets the same 404 as a stranger."""
        self.client.force_login(self.g2)
        with override_settings(MEDIA_ROOT=self.tmp):
            r = self.client.get('/media/players/priv.png')
            self.assertEqual(r.status_code, 404)

    def test_orphan_file_staff_only(self):
        """A file belonging to no player row is gated (fail closed)."""
        with override_settings(MEDIA_ROOT=self.tmp):
            self.assertEqual(
                self.client.get('/media/players/orphan.png').status_code, 404)
        self.client.force_login(self.staff)
        with override_settings(MEDIA_ROOT=self.tmp):
            self.assertEqual(
                self.client.get('/media/players/orphan.png').status_code, 200)

    def test_non_players_path_gated(self):
        with override_settings(MEDIA_ROOT=self.tmp):
            self.assertEqual(
                self.client.get('/media/secret.txt').status_code, 404)
        self.client.force_login(self.staff)
        with override_settings(MEDIA_ROOT=self.tmp):
            r = self.client.get('/media/secret.txt')
            self.assertEqual(r.status_code, 200)

    def test_traversal_is_404(self):
        with override_settings(MEDIA_ROOT=self.tmp):
            for bad in ('..%2Fdb.sqlite3', 'players/../../secret.txt',
                        'players/..\\secret.txt'):
                r = self.client.get(f'/media/{bad}')
                self.assertEqual(r.status_code, 404, bad)

    def test_missing_file_404_even_for_staff(self):
        self.client.force_login(self.staff)
        with override_settings(MEDIA_ROOT=self.tmp):
            self.assertEqual(
                self.client.get('/media/players/nope.png').status_code, 404)


class PortalAssetTests(TestCase):

    def test_anonymous_gets_404(self):
        r = self.client.get('/portal/assets/dash.js')
        self.assertEqual(r.status_code, 404)

    def test_parent_account_gets_404_for_dashjs_but_fallback_ok(self):
        """Per-asset ACL: dash.js is staff-only; img-fallback.js is any
        signed-in user (guardians' child cards reference it)."""
        u = User.objects.create_user('parent@example.com', password='x' * 20)
        Guardian.objects.create(user=u, full_name='P')
        self.client.force_login(u)
        self.assertEqual(
            self.client.get('/portal/assets/dash.js').status_code, 404)
        r = self.client.get('/portal/assets/img-fallback.js')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/javascript')

    def test_staff_gets_the_script(self):
        u = User.objects.create_user('staff2', password='x' * 20, is_staff=True)
        self.client.force_login(u)
        r = self.client.get('/portal/assets/dash.js')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/javascript')
        self.assertIn(b'subs-json', r.content)      # it is really the dashboard
        self.assertEqual(r['Cache-Control'], 'private, max-age=86400')

    def test_allow_list_only(self):
        u = User.objects.create_user('staff3', password='x' * 20, is_staff=True)
        self.client.force_login(u)
        for bad in ('styles.css', 'body-a.html', 'login.html', 'nope.js',
                    'img-fallback.js%2f..%2fdash.js'):
            r = self.client.get(f'/portal/assets/{bad}')
            self.assertEqual(r.status_code, 404, bad)


class Phase5SettingsTests(TestCase):
    """DB_ENGINE / SP_CACHE switches (config-level, via subprocess import)."""

    def _settings_with(self, extra_env):
        """Import the settings module alone (no django.setup — that would
        load the real DB backend and need psycopg; a config-level check
        only needs the switch logic in the module itself)."""
        env = dict(os.environ)
        env.pop('DJANGO_SETTINGS_MODULE', None)
        env.update(extra_env)
        code = ('import json; import sporting_pearls_backend.settings as s; '
                'print(json.dumps({"db": s.DATABASES["default"]["ENGINE"], '
                '"cache": s.CACHES["default"]["BACKEND"]}))')
        out = subprocess.run(
            [sys.executable, '-c', code],
            capture_output=True, text=True, env=env, cwd=BACKEND_DIR,
            timeout=120)
        return out

    def test_default_stays_sqlite_and_locmem(self):
        out = self._settings_with({})
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('sqlite3', out.stdout)
        self.assertIn('LocMemCache', out.stdout)

    def test_postgres_switch(self):
        out = self._settings_with({'DB_ENGINE': 'postgres',
                                   'DB_NAME': 'sp', 'DB_USER': 'sp',
                                   'DB_PASSWORD': 'pw'})
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('postgresql', out.stdout)

    def test_db_cache_switch(self):
        out = self._settings_with({'SP_CACHE': 'db'})
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn('DatabaseCache', out.stdout)


class PortalMarkupTests(TestCase):
    """Regression guards for the two bugs the Phase 5 browser QA found:

    1. parents_home crashed (500) for any player without a shirt number
       (`#{p.number:02d}` on None) — a real academy can absolutely have
       numberless players.
    2. player-card photos shipped an inline onerror= handler — illegal
       under the tightened CSP (script-src 'self').
    """

    def setUp(self):
        from django.contrib.auth.models import User
        squad, _ = Squad.objects.get_or_create(
            key='u17', defaults={'code': 'U17', 'label': 'U17'})
        # number deliberately left NULL
        self.numberless = Player.objects.create(
            squad=squad, ref='U17-99', first_name='No', last_name='Number')
        self.u = User.objects.create_user('numtest@example.com', password='x' * 20)
        from parents.models import Guardian, GuardianPlayer
        self.gp = Guardian.objects.create(user=self.u, full_name='Numberless G')
        GuardianPlayer.objects.create(guardian=self.gp, player=self.numberless)

    def test_parents_home_renders_without_shirt_number(self):
        self.client.force_login(self.u)
        r = self.client.get('/portal/parents/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'No Number', r.content)

    def test_no_inline_onerror_in_rendered_pages(self):
        """Staff dashboard + parent home + child page: zero inline event
        handlers (CSP script-src 'self' would block them silently)."""
        staff = User.objects.create_user('mkstaff', password='x' * 20,
                                         is_staff=True)
        pages = [
            ('/portal/', staff),
            ('/portal/parents/', self.u),
            (f'/portal/parents/child/{self.numberless.id}/', self.u),
        ]
        for url, user in pages:
            self.client.force_login(user)
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200, url)
            self.assertNotIn(b'onerror=', r.content, url)
            self.assertNotIn(b'onclick=', r.content, url)

    def test_pages_reference_the_fallback_script(self):
        self.client.force_login(self.u)
        for url in ('/portal/parents/',
                    f'/portal/parents/child/{self.numberless.id}/'):
            r = self.client.get(url)
            self.assertIn(b'/portal/assets/img-fallback.js', r.content, url)

    def test_parents_home_numbered_and_numberless(self):
        """Both card shapes render as well-formed markup (the first fix
        attempt left an unclosed <span> for numberless players — the
        browser mangled the cards; caught again by live browser QA)."""
        squad = Squad.objects.get(key='u17')
        numbered = Player.objects.create(
            squad=squad, ref='U17-77', first_name='Has', last_name='Number',
            number=9)
        from parents.models import GuardianPlayer
        GuardianPlayer.objects.create(guardian=self.gp, player=numbered)
        self.client.force_login(self.u)
        r = self.client.get('/portal/parents/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(b'<span class="kd-num">#09</span>', r.content)
        # exactly one number chip (the numberless player gets none)
        self.assertEqual(r.content.count(b'<span class="kd-num"'), 1)
        # balanced markup: every opened article/span is closed
        self.assertEqual(r.content.count(b'<article'), r.content.count(b'</article>'))
        self.assertGreaterEqual(r.content.count(b'<span'), r.content.count(b'</span>'))
