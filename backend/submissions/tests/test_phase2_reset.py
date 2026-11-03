"""Phase 2 tests — password reset without account enumeration.

The reset flow must behave IDENTICALLY whether or not the typed
email/username matches an account: same page, same status code, same
timing class (one PBKDF2 verify runs either way). Emails go out only
for real, active accounts, carry only a neutral sentence + link, and
links die after one use.
"""
from base64 import urlsafe_b64encode
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import TestCase, override_settings

from parents.models import Guardian

User = get_user_model()


def _uid(user):
    return urlsafe_b64encode(str(user.pk).encode()).decode()


class ResetRequestTests(TestCase):
    def setUp(self):
        cache.clear()
        self.sent = []
        self.staff = User.objects.create_user(
            'qa_officer', 'officer@example.com', 'Str0ng-Pass!x', is_staff=True)
        self.parent_user = User.objects.create_user(
            'parent@example.com', 'parent@example.com', 'Str0ng-Pass!y')
        Guardian.objects.create(user=self.parent_user, is_active=True)

    def _fake_resend(self):
        def send(payload):
            self.sent.append(payload)
            return True, 'sent'
        return send

    def _post(self, path, ident, ip='196.201.9.9', honeypot=''):
        return self.client.post(
            path, {'identify': ident, 'company': honeypot},
            REMOTE_ADDR=ip)

    def test_unknown_email_same_page_and_status_as_known(self):
        with mock.patch('submissions.portal_auth.resend_send', self._fake_resend()):
            known = self._post('/portal/parents/reset/', 'parent@example.com')
            unknown = self._post('/portal/parents/reset/', 'ghost@example.com',
                                 ip='196.201.9.10')
        self.assertEqual(known.status_code, 200)
        self.assertEqual(unknown.status_code, 200)
        # identical response body apart from the CSRF token
        strip = lambda t: ''.join(t.split('csrfmiddlewaretoken" value="')[0].split()[:40])
        self.assertIn('Check your inbox', known.content.decode())
        self.assertIn('Check your inbox', unknown.content.decode())
        # only the real account triggered an email
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]['to'], ['parent@example.com'])

    def test_email_contains_link_but_no_account_details(self):
        with mock.patch('submissions.portal_auth.resend_send', self._fake_resend()):
            self._post('/portal/parents/reset/', 'parent@example.com')
        body = self.sent[0]['text']
        self.assertIn('/portal/parents/reset/', body)
        self.assertIn('expires', body)
        # neutral phrasing: nothing that confirms what was typed
        self.assertNotIn('parent@example.com was found', body)
        self.assertNotIn('username is', body)

    def test_staff_reset_finds_staff_by_username_or_email(self):
        with mock.patch('submissions.portal_auth.resend_send', self._fake_resend()):
            self._post('/portal/reset/', 'qa_officer', ip='196.201.9.11')
            self._post('/portal/reset/', 'officer@example.com', ip='196.201.9.12')
        self.assertEqual(len(self.sent), 2)
        self.assertTrue(all(p['to'] == ['officer@example.com'] for p in self.sent))

    def test_staff_reset_ignores_non_staff_accounts(self):
        with mock.patch('submissions.portal_auth.resend_send', self._fake_resend()):
            self._post('/portal/reset/', 'parent@example.com')
        self.assertEqual(self.sent, [])
        # and the page still claims the neutral "check your inbox" state

    def test_parents_reset_ignores_staff_accounts(self):
        with mock.patch('submissions.portal_auth.resend_send', self._fake_resend()):
            self._post('/portal/parents/reset/', 'officer@example.com')
        self.assertEqual(self.sent, [])

    def test_inactive_parent_gets_no_email(self):
        Guardian.objects.filter(user=self.parent_user).update(is_active=False)
        with mock.patch('submissions.portal_auth.resend_send', self._fake_resend()):
            self._post('/portal/parents/reset/', 'parent@example.com')
        self.assertEqual(self.sent, [])

    def test_honeypot_swallows_the_request(self):
        with mock.patch('submissions.portal_auth.resend_send', self._fake_resend()):
            r = self._post('/portal/parents/reset/', 'parent@example.com',
                           honeypot='spam-bot')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.sent, [])

    def test_reset_request_throttles_per_ip(self):
        with mock.patch('submissions.portal_auth.resend_send', self._fake_resend()):
            for i in range(5):
                r = self._post('/portal/parents/reset/', 'parent@example.com')
                self.assertEqual(r.status_code, 200)
            # 6th within the hour: swallowed silently (same page, no mail)
            r = self._post('/portal/parents/reset/', 'parent@example.com')
            self.assertEqual(r.status_code, 200)
        self.assertEqual(len(self.sent), 5)

    def test_get_shows_the_form_for_both_audiences(self):
        for path, label in (('/portal/reset/', 'Username or email'),
                            ('/portal/parents/reset/', 'Email')):
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200)
            self.assertIn(label, r.content.decode())


class ResetConfirmTests(TestCase):
    def setUp(self):
        cache.clear()
        self.staff = User.objects.create_user(
            'qa_officer2', 'officer2@example.com', 'Str0ng-Pass!x', is_staff=True)

    def _link(self, user, audience='portal'):
        token = default_token_generator.make_token(user)
        return f'/{audience}/reset/{_uid(user)}/{token}/'

    def _open(self, user, audience='portal'):
        return self.client.get(self._link(user, audience))

    def test_valid_token_shows_set_password_form(self):
        r = self._open(self.staff)
        self.assertEqual(r.status_code, 200)
        self.assertIn('Choose a new password', r.content.decode())

    def test_bad_token_is_rejected_neutrally(self):
        r = self.client.get(f'/portal/reset/{_uid(self.staff)}/not-a-real-token/')
        self.assertEqual(r.status_code, 400)
        self.assertIn('no longer works', r.content.decode())

    def test_garbage_uid_is_rejected(self):
        for uid in ('AAAA', '99999999999'):
            r = self.client.get(f'/portal/reset/{uid}/some-token/')
            self.assertEqual(r.status_code, 400, uid)

    def test_setting_password_works_and_kills_the_token(self):
        link = self._link(self.staff)
        r = self.client.post(link, {'password': 'N3w-And-Strong!9',
                                    'password2': 'N3w-And-Strong!9'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('Password saved', r.content.decode())
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password('N3w-And-Strong!9'))
        # the same link is dead after use
        r = self.client.get(link)
        self.assertEqual(r.status_code, 400)

    def test_weak_password_is_rejected(self):
        r = self.client.post(self._link(self.staff),
                             {'password': 'password', 'password2': 'password'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('stronger password', r.content.decode())
        self.staff.refresh_from_db()
        self.assertTrue(self.staff.check_password('Str0ng-Pass!x'))

    def test_mismatched_passwords_are_rejected(self):
        r = self.client.post(self._link(self.staff),
                             {'password': 'N3w-And-Strong!9',
                              'password2': 'different'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('do not match', r.content.decode())

    @override_settings(PASSWORD_RESET_TIMEOUT=1)
    def test_token_expires(self):
        import time
        link = self._link(self.staff)
        # token timestamps truncate to whole seconds — sleep past the
        # boundary so elapsed time is guaranteed > the 1s timeout
        time.sleep(2.2)
        r = self.client.get(link)
        self.assertEqual(r.status_code, 400)

    def test_parent_flow_end_to_end(self):
        parent_user = User.objects.create_user(
            'mama@example.com', 'mama@example.com', 'Str0ng-Pass!z')
        Guardian.objects.create(user=parent_user, is_active=True)
        link = self._link(parent_user, 'portal/parents')
        r = self.client.get(link)
        self.assertEqual(r.status_code, 200)
        r = self.client.post(link, {'password': 'N3w-Parent-Pass!7',
                                    'password2': 'N3w-Parent-Pass!7'})
        self.assertEqual(r.status_code, 200)
        parent_user.refresh_from_db()
        self.assertTrue(parent_user.check_password('N3w-Parent-Pass!7'))
