"""Phase 7 tests — Results page content + player QR codes.

Covers:
* /api/results/ — published-only, ordering, derived W/D/L outcome,
  shape of every field the results page renders.
* /api/players/<ref>/ — the QR-code target: public fields only,
  unpublished and unknown refs fail closed with 404 (a printed QR can
  never leak an un-published profile), photo URL resolution.
* QR card pages — staff-only bulk and single views (anonymous is
  redirected to login, guardians bounced to their portal / get 404 on
  others' children), guardian access to their OWN child's card, the
  encoded URL pointing at SITE_URL/player.html?ref=..., and the
  segno SVG actually embedded in the page.
* The qr.js portal asset is allow-listed and reachable by any signed-in
  user (guardians print cards too).
"""
import datetime
import re

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings

from parents.models import Guardian, GuardianPlayer
from submissions.models import Player, Result, Squad

User = get_user_model()


def _sq(**kw):
    d = dict(key='feminin', code='FEM', label='Sporting Pearls Féminin',
             formation='4-3-3', accent='#f59d1e', sort=1)
    d.update(kw)
    return Squad.objects.create(**d)


def _pl(squad, **kw):
    d = dict(ref='FEM-01', first_name='Rehema', last_name='Juma',
             position='MF', age=15, motto='Play flat, pass sharp.',
             is_published=True)
    d.update(kw)
    return Player.objects.create(squad=squad, **d)


class ResultsApiTests(TestCase):
    def test_shape_order_and_outcome(self):
        r1 = Result.objects.create(team='SP Féminin', opponent='Kilifi Stars',
                                   competition='County League', date=datetime.date(2026, 10, 4),
                                   venue='Mtwapa Grounds', home_away='home',
                                   our_score=3, their_score=1, is_published=True)
        Result.objects.create(team='SP U15', opponent='Mombasa XI',
                              date=datetime.date(2026, 10, 11),
                              our_score=0, their_score=0, is_published=True)
        Result.objects.create(team='SP U17', opponent='Malindi FC',
                              date=datetime.date(2026, 10, 18),
                              our_score=1, their_score=2, is_published=False)
        res = self.client.get('/api/results/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 2)          # unpublished never leaves
        self.assertEqual(data['results'][0]['opponent'], 'Mombasa XI')   # newest first
        self.assertEqual(data['results'][1]['opponent'], 'Kilifi Stars')
        first = data['results'][1]
        self.assertEqual(first['outcome'], 'W')
        self.assertEqual(first['our_score'], 3)
        self.assertEqual(first['their_score'], 1)
        self.assertEqual(first['date'], '2026-10-04')
        for key in ('team', 'opponent', 'competition', 'date', 'venue',
                    'home_away', 'our_score', 'their_score', 'outcome', 'report'):
            self.assertIn(key, first)
        self.assertEqual(data['results'][0]['outcome'], 'D')
        self.assertEqual(r1.outcome, 'W')

    def test_empty_is_honest_not_an_error(self):
        res = self.client.get('/api/results/')
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['results'], [])


class PlayerPublicApiTests(TestCase):
    def setUp(self):
        self.sq = _sq()

    def test_published_player_public_fields(self):
        _pl(self.sq)
        res = self.client.get('/api/players/FEM-01/')
        self.assertEqual(res.status_code, 200)
        p = res.json()['player']
        self.assertEqual(p['first'], 'Rehema')
        self.assertEqual(p['squad']['key'], 'feminin')
        self.assertEqual(p['squad']['label'], 'Sporting Pearls Féminin')
        # public surface only — the private fields never appear
        for absent in ('height_m', 'foot', 'photo_url', 'is_published',
                       'pitch_order', 'squad_id', 'id'):
            self.assertNotIn(absent, p)
        self.assertNotIn('guardian', str(res.content))

    def test_unpublished_fails_closed(self):
        _pl(self.sq, ref='FEM-02', is_published=False)
        res = self.client.get('/api/players/FEM-02/')
        self.assertEqual(res.status_code, 404)

    def test_unknown_ref_404(self):
        res = self.client.get('/api/players/FEM-99/')
        self.assertEqual(res.status_code, 404)


@override_settings(SITE_URL='https://sportingpearlsacademy.org',
                   MEDIA_ROOT='/tmp/sp-p7-media')
class QrCardPageTests(TestCase):
    def setUp(self):
        self.sq = _sq()
        self.pub = _pl(self.sq)                                   # FEM-01
        self.draft = _pl(self.sq, ref='FEM-02', first_name='Aisha',
                          last_name='Njeri', is_published=False)   # FEM-02
        self.staff = User.objects.create_user('qrstaff', 's@x.io', 'pw1',
                                              is_staff=True)
        # guardian with a link to FEM-01 only
        self.gu = User.objects.create_user('grace', 'g@x.io', 'pw2')
        self.guardian = Guardian.objects.create(user=self.gu,
                                                full_name='Grace Juma',
                                                relation='mother')
        GuardianPlayer.objects.create(guardian=self.guardian, player=self.pub)

    def test_bulk_requires_staff(self):
        res = Client().get('/portal/qr/')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/portal/login/', res['Location'])
        c = Client()
        c.force_login(self.gu)                    # guardian -> own portal
        res = c.get('/portal/qr/')
        self.assertEqual(res.status_code, 302)
        self.assertIn('/portal/parents/', res['Location'])
        c2 = Client()
        c2.force_login(self.staff)
        res = c2.get('/portal/qr/')
        self.assertEqual(res.status_code, 200)
        body = res.content.decode()
        self.assertIn('Player QR code cards', body)
        # both players on the sheet, unpublished one flagged
        self.assertIn('Rehema Juma', body)
        self.assertIn('Aisha Njeri', body)
        self.assertIn('qrc-draft', body)
        # QR encodes the public profile URL against SITE_URL
        self.assertIn('https://sportingpearlsacademy.org/player.html?ref=FEM-01', body)
        # segno SVG actually embedded
        self.assertIn('<svg', body)
        self.assertIn('viewBox', body)
        # CSP: no inline event handlers anywhere
        self.assertNotRegex(body, r'on(click|load|error)=')

    def test_single_card_staff(self):
        c = Client()
        c.force_login(self.staff)
        res = c.get('/portal/qr/FEM-01/')
        self.assertEqual(res.status_code, 200)
        body = res.content.decode()
        self.assertIn('Rehema Juma', body)
        self.assertIn('player.html?ref=FEM-01', body)
        self.assertNotIn('Aisha Njeri', body)      # single, not the roster

    def test_single_unknown_ref_404(self):
        c = Client()
        c.force_login(self.staff)
        self.assertEqual(c.get('/portal/qr/FEM-99/').status_code, 404)

    def test_guardian_own_child_only(self):
        c = Client()
        c.force_login(self.gu)
        res = c.get('/portal/parents/qr/FEM-01/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Rehema Juma', res.content.decode())
        # someone else's child (the draft player is not linked to grace)
        self.assertEqual(c.get('/portal/parents/qr/FEM-02/').status_code, 404)

    def test_qr_asset_allowlisted_for_signed_in(self):
        self.assertEqual(Client().get('/portal/assets/qr.js').status_code, 404)
        c = Client()
        c.force_login(self.gu)
        res = c.get('/portal/assets/qr.js')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/javascript')

    def test_dashboard_shows_qr_buttons(self):
        c = Client()
        c.force_login(self.staff)
        res = c.get('/portal/')
        body = res.content.decode()
        self.assertIn('/portal/qr/FEM-01/"', body)
        self.assertIn('Print QR cards', body)

    def test_parent_child_page_links_qr(self):
        c = Client()
        c.force_login(self.gu)
        res = c.get(f'/portal/parents/child/{self.pub.id}/')
        body = res.content.decode()
        self.assertIn('/portal/parents/qr/FEM-01/', body)
        self.assertIn('Print QR profile card', body)


class SiteWiringTests(TestCase):
    """The shipped static pages carry the Phase 7 wiring."""

    SITE = None  # set in setUpClass from the kit tree

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from pathlib import Path
        # Portable: resolve the shipped site/ folder relative to this test
        # file (kit root is three levels up from backend/submissions/tests/),
        # so the suite works on any install path, not just the build machine.
        cls.SITE = Path(__file__).resolve().parents[3] / 'site'

    def _page(self, name):
        return (self.SITE / name).read_text(encoding='utf-8')

    def test_results_page_exists_and_is_honest(self):
        html = self._page('results.html')
        self.assertIn('id="resSoon"', html)                 # coming soon panel
        self.assertIn('id="resGroups"', html)               # JS render target
        self.assertIn('sp-results.js', html)
        self.assertIn('results.css', html)
        self.assertNotIn('Coming Soon', self._page('index.html')
                         .replace('Fixtures Coming Soon', ''))  # sanity: no bleed

    def test_player_page_exists_fail_closed(self):
        html = self._page('player.html')
        self.assertIn('id="plbMissing"', html)              # honest not-available
        self.assertIn('sp-player.js', html)
        self.assertIn('name="robots"', html)                # noindex
        self.assertIn('noindex', html)

    def test_squad_player_cards_carry_unique_qr(self):
        """Every squad player card (dossier modal) shows the player's
        unique QR → public profile link (owner request, rev 21)."""
        html = self._page('the-squad.html')
        self.assertIn('assets/js/vendor/qr.min.js', html)   # self-hosted (CSP)
        self.assertIn('id="mQr"', html)                     # QR render target
        self.assertIn('id="mQrLink"', html)                 # profile link
        js = (self.SITE / 'assets' / 'js' / 'pages'
              / 'the-squad.js').read_text(encoding='utf-8')
        self.assertIn("player.html?ref=' + encodeURIComponent(pref)", js)
        self.assertIn("p.ref || ''", js)                    # live refs from API
        self.assertIn('SQUAD_CODE', js)                     # demo-mode refs
        lib = (self.SITE / 'assets' / 'js' / 'vendor'
               / 'qr.min.js').read_text(encoding='utf-8')
        self.assertIn('qrcode-generator', lib)              # MIT attribution
        self.assertNotIn('eval(', lib)                      # CSP-safe
        # demo-mode profile fallback (same dataset as the squad page —
        # real register 2026-27: U12-01 Suleimann Alii et al.)
        pj = (self.SITE / 'assets' / 'js' / 'shared'
              / 'sp-player.js').read_text(encoding='utf-8')
        self.assertIn('DEMO_PROFILES', pj)
        self.assertIn("'U12-01'", pj)                       # real register ref
        self.assertIn("'U19-05'", pj)                       # Alii Thoya (CM)

    def test_nav_and_footer_wiring_everywhere(self):
        pages = [p.name for p in self.SITE.glob('*.html')]
        self.assertIn('results.html', pages)
        self.assertIn('player.html', pages)
        with_nav = [p for p in pages if 'data-title="Results"'
                    in self._page(p)]
        self.assertGreater(len(with_nav), 35)
        for name in with_nav:
            html = self._page(name)
            m = re.search(r'<a class="sp-nav-item" href="([^"]*)"'
                          r'[^>]*data-title="Results"', html)
            self.assertIsNotNone(m, name)
            self.assertEqual(m.group(1), 'results.html', name)

    def test_no_inline_onerror_left_in_js_templates(self):
        for rel in ('shared/site-core.js', 'shared/nav-pro.js',
                    'shared/scroll-parallax.js', 'pages/index.js',
                    'pages/academy.js', 'pages/coaching-philosophy.js',
                    'pages/join-us.js', 'pages/institutional-blueprint.js',
                    'pages/partners.js'):
            src = (self.SITE / 'assets/js' / rel).read_text(encoding='utf-8')
            self.assertNotIn('onerror=', src, rel)
            self.assertIn('data-fb="${fallbackImg}"', src, rel)
