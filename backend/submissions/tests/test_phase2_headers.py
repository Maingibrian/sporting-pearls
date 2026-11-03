"""Phase 2 tests — response security headers on every Django-served path.

Covers SecurityHeadersMiddleware (CSP / Permissions-Policy / COOP) and
the settings-driven headers (nosniff, referrer policy, X-Frame-Options),
plus the branded 404/500 handlers (no stack traces, no internal paths).
"""
from django.test import TestCase, override_settings


class HeaderTests(TestCase):
    """Security headers must appear on portal, API, admin and 404 pages."""

    def _expect_headers(self, response):
        csp = response.get('Content-Security-Policy', '')
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        self.assertIn("base-uri 'self'", csp)
        self.assertIn("form-action 'self'", csp)
        self.assertEqual(response.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(response.get('Referrer-Policy'),
                         'strict-origin-when-cross-origin')
        self.assertEqual(response.get('Permissions-Policy'),
                         'camera=(), microphone=(), geolocation=(), payment=()')
        self.assertEqual(response.get('Cross-Origin-Opener-Policy'), 'same-origin')

    def test_headers_on_portal_login(self):
        r = self.client.get('/portal/login/')
        self.assertEqual(r.status_code, 200)
        self._expect_headers(r)
        self.assertEqual(r.get('X-Frame-Options'), 'DENY')

    def test_headers_on_api_health(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self._expect_headers(r)

    def test_headers_on_admin_login(self):
        r = self.client.get('/admin/login/')
        self.assertEqual(r.status_code, 200)
        self._expect_headers(r)

    def test_headers_on_404(self):
        r = self.client.get('/portal/definitely-not-a-page/')
        self.assertEqual(r.status_code, 404)
        self._expect_headers(r)

    def test_headers_on_parent_login(self):
        r = self.client.get('/portal/parents/login/')
        self.assertEqual(r.status_code, 200)
        self._expect_headers(r)

    def test_headers_on_media_missing_file(self):
        r = self.client.get('/media/players/nope.jpg')
        self.assertEqual(r.status_code, 404)
        self._expect_headers(r)


class ErrorPageTests(TestCase):
    def test_404_is_branded_and_leaks_nothing(self):
        r = self.client.get('/portal/definitely-not-a-page/')
        self.assertEqual(r.status_code, 404)
        text = r.content.decode()
        self.assertIn('That page does not exist', text)
        self.assertIn('Sporting Pearls', text)
        # no internals: no settings, no module paths, no tracebacks
        for leak in ('DEBUG', 'Traceback', 'settings.py',
                     'django.', 'Exception', 'ALLOWED_HOSTS'):
            self.assertNotIn(leak, text)

    def test_500_handler_renders_branded_neutral_page(self):
        from submissions.portal_auth import branded_500
        from django.test import RequestFactory
        req = RequestFactory().get('/portal/')
        r = branded_500(req)
        self.assertEqual(r.status_code, 500)
        text = r.content.decode()
        self.assertIn('Something went wrong on our side', text)
        self.assertIn('Your data is safe', text)
        for leak in ('DEBUG', 'Traceback', 'settings.py', 'Exception'):
            self.assertNotIn(leak, text)


class SessionCookieTests(TestCase):
    def test_session_cookie_hardening(self):
        from django.conf import settings as s
        self.assertTrue(s.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(s.SESSION_COOKIE_SAMESITE, 'Lax')
        self.assertEqual(s.CSRF_COOKIE_SAMESITE, 'Lax')
        self.assertLessEqual(s.SESSION_COOKIE_AGE, 12 * 3600)
        self.assertLessEqual(s.PASSWORD_RESET_TIMEOUT, 3600)
        self.assertTrue(s.SECURE_CONTENT_TYPE_NOSNIFF)
        self.assertEqual(s.X_FRAME_OPTIONS, 'DENY')

    def test_proxy_header_default_off(self):
        """Untrusted by default: clients cannot spoof X-Forwarded-Proto."""
        from sporting_pearls_backend import settings as s
        self.assertIsNone(s.SECURE_PROXY_SSL_HEADER)

    def test_proxy_header_env_toggle(self):
        from sporting_pearls_backend.settings import _proxy_ssl_header
        self.assertIsNone(_proxy_ssl_header('0'))
        self.assertIsNone(_proxy_ssl_header(''))
        self.assertEqual(_proxy_ssl_header('1'),
                         ('HTTP_X_FORWARDED_PROTO', 'https'))

    def test_csp_policy_shape(self):
        from submissions.middleware import CSP_POLICY
        # Phase 5 (R27): scripts are same-origin ONLY — no unsafe-inline
        # (inline handlers became data-fb attributes; the portal and the
        # three formerly-inline pages load external files).
        self.assertIn("script-src 'self'", CSP_POLICY)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", CSP_POLICY)
        # styles keep the inline allowance (style="" attributes + the
        # portal's inlined CSS) — no script vector under script-src 'self'
        self.assertIn("style-src 'self' 'unsafe-inline'", CSP_POLICY)
        # …and the vectors that must stay blocked outright
        self.assertIn("object-src 'none'", CSP_POLICY)
        self.assertIn("base-uri 'self'", CSP_POLICY)
        self.assertIn("form-action 'self'", CSP_POLICY)
        self.assertIn("frame-ancestors 'none'", CSP_POLICY)
