"""Phase 2 tests — login throttling and message hygiene.

Before Phase 2 the STAFF portal login had no rate limit at all, the
Django admin login had none either, and a valid-credentials-but-not-
staff attempt got a distinct message ("does not have portal access"),
which turns the login form into an account-validity oracle once the
password is known. These tests pin the fixed behaviour.
"""
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase

User = get_user_model()


class StaffLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff = User.objects.create_user(
            'qa_staff', 'staff@example.com', 'Str0ng-Pass!x', is_staff=True)

    def _post(self, u='qa_staff', p='wrong-password'):
        return self.client.post('/portal/login/',
                                {'username': u, 'password': p,
                                 'next': '/portal/'}, REMOTE_ADDR='196.201.9.9')

    def test_wrong_password_gets_generic_message(self):
        r = self._post()
        self.assertEqual(r.status_code, 200)
        self.assertIn('Wrong username or password', r.content.decode())

    def test_unknown_user_gets_same_message_and_same_status(self):
        r = self._post(u='no_such_user_xyz')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Wrong username or password', r.content.decode())

    def test_valid_credentials_non_staff_gets_same_message(self):
        """A parent/plain account must not be distinguishable from a
        wrong password on the staff login."""
        User.objects.create_user('qa_plain', 'p@example.com', 'Str0ng-Pass!y')
        r = self._post(u='qa_plain', p='Str0ng-Pass!y')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Wrong username or password', r.content.decode())
        self.assertNotIn('does not have portal access', r.content.decode())

    def test_correct_login_still_works(self):
        r = self._post(p='Str0ng-Pass!x')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(r['Location'].startswith('/portal/'))

    def test_throttle_after_eight_failures(self):
        for i in range(8):
            r = self._post()
            self.assertEqual(r.status_code, 200)
        r = self._post()                       # 9th attempt
        self.assertEqual(r.status_code, 429)
        self.assertIn('Too many attempts', r.content.decode())
        # and the form is disabled, not silently broken
        self.assertIn('disabled', r.content.decode())

    def test_throttle_is_per_ip(self):
        for i in range(8):
            self._post()
        other = self.client.post(
            '/portal/login/', {'username': 'qa_staff', 'password': 'wrong',
                               'next': '/portal/'}, REMOTE_ADDR='197.5.5.5')
        self.assertEqual(other.status_code, 200)   # different IP, fine

    def test_success_unaffected_by_earlier_failures(self):
        for i in range(7):
            self._post()
        r = self._post(p='Str0ng-Pass!x')      # 8th attempt is the good one
        self.assertEqual(r.status_code, 302)

    def test_timing_equalizer_is_cheap_and_safe(self):
        from submissions.portal_auth import burn_password_time
        burn_password_time()
        burn_password_time()                   # idempotent, no exception


class AdminLoginThrottleTests(TestCase):
    def setUp(self):
        cache.clear()

    def _post(self, u='admin', p='wrong-password'):
        return self.client.post('/admin/login/',
                                {'username': u, 'password': p,
                                 'next': '/admin/'},
                                REMOTE_ADDR='196.201.9.9')

    def test_admin_login_throttles_after_eight_failures(self):
        for i in range(8):
            r = self._post()
            self.assertIn(r.status_code, (200, 302))
        r = self._post()
        self.assertEqual(r.status_code, 429)
        self.assertIn('Too many sign-in attempts', r.content.decode())

    def test_admin_throttle_only_touches_admin_login(self):
        for i in range(8):
            self._post()
        # the same IP can still use the rest of the site
        r = self.client.get('/portal/login/', REMOTE_ADDR='196.201.9.9')
        self.assertEqual(r.status_code, 200)
        r = self.client.get('/', REMOTE_ADDR='196.201.9.9')
        self.assertEqual(r.status_code, 200)
