"""Phase 3 tests — truthful, resilient public forms.

Covers:
  * payload shape guards (empty / junk / oversize payloads get honest
    4xx errors, never reference numbers, never stored rows)
  * form-10 content guard (an empty "report" is rejected)
  * notification-email minimisation (medical + ID values withheld from
    the email body; the ledger keeps the full payload)
  * R26 staff-ledger redaction (plain staff see masked values,
    portal administrators + superuser see everything)

Run:  .venv/bin/python manage.py test submissions.tests.test_phase3 -v 1
"""
from django.test import Client, TestCase, override_settings

from ..models import FormSubmission, SafeguardingReport
from ..safeguarding import PORTAL_ADMIN_GROUP
from ..views import _is_sensitive_key, _redact_sensitive

FORM_URL = '/api/forms/{}/'
FORM10 = 'form-10-safeguarding-report'
FORM01 = 'form-01-player-registration'
NEWS = 'newsletter-subscription'
ENQ = 'form-08-contact-form'


def post(slug, data, meta=None):
    return Client().post(FORM_URL.format(slug),
                         {'slug': slug, 'data': data,
                          'meta': meta or {'ua': 'test'}},
                         content_type='application/json')


class SentMail:
    """Recorder for resend_send — collects payloads instead of POSTing."""

    def __init__(self):
        self.sent = []

    def __call__(self, payload):
        self.sent.append(payload)
        return True, 'sent'


# ── shape guards ──────────────────────────────────────────────────────────

class ShapeGuardTests(TestCase):

    def test_empty_payload_rejected(self):
        r = post(ENQ, {})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.json()['ok'])
        self.assertEqual(FormSubmission.objects.count(), 0)

    def test_all_sentinel_payload_rejected(self):
        r = post(ENQ, {'name': '(empty)', 'email': '(empty)', 'msg': ''})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(FormSubmission.objects.count(), 0)

    def test_single_junk_field_rejected(self):
        r = post(ENQ, {'x': 'y'})
        self.assertEqual(r.status_code, 400)

    def test_two_real_fields_accepted(self):
        r = post(ENQ, {'name': 'Amina', 'message': 'hello there'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['ok'])
        self.assertTrue(r.json()['ref'].startswith('SP-ENQ-'))

    def test_newsletter_needs_email(self):
        r = post(NEWS, {'enter your email address': 'not-an-email'})
        self.assertEqual(r.status_code, 400)
        r = post(NEWS, {'enter your email address': 'fan@example.com'})
        self.assertEqual(r.status_code, 200)

    def test_oversize_value_rejected(self):
        r = post(ENQ, {'name': 'Amina', 'message': 'x' * 4001})
        self.assertEqual(r.status_code, 400)
        self.assertIn('too long', r.json()['error'])

    def test_too_many_fields_rejected(self):
        data = {f'field {i}': 'value' for i in range(201)}
        r = post(ENQ, data)
        self.assertEqual(r.status_code, 400)
        self.assertIn('too many fields', r.json()['error'])

    def test_oversize_body_rejected(self):
        import json as _json
        body = _json.dumps({'slug': ENQ, 'meta': {},
                            'data': {'name': 'Amina', 'message': 'y' * 70000}})
        r = Client().post(FORM_URL.format(ENQ), body, content_type='application/json')
        self.assertEqual(r.status_code, 413)

    def test_honeypot_still_fake_succeeds_without_storing(self):
        r = post(ENQ, {'name': 'Bot', 'message': 'spam', 'company': 'http://x'})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()['stored'])
        self.assertEqual(FormSubmission.objects.count(), 0)


class SafeguardingContentGuardTests(TestCase):

    def test_empty_report_rejected(self):
        r = post(FORM10, {'reporting preference': 'Completely Anonymous',
                          'approximate time': '(empty)'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('empty', r.json()['error'])
        self.assertEqual(SafeguardingReport.objects.count(), 0)

    def test_all_sentinel_report_rejected(self):
        r = post(FORM10, {'reporting preference': 'Completely Anonymous',
                          'detailed factual description of the concern / incident': '(empty)'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(SafeguardingReport.objects.count(), 0)

    def test_minimal_real_report_accepted(self):
        r = post(FORM10, {
            'reporting preference': 'Completely Anonymous',
            'child / player name (if known)': 'Test Child',
            'nature of the safeguarding incident': ['Physical harm / excessive force'],
        })
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['ref'].startswith('SP-SAFE-'))
        self.assertEqual(SafeguardingReport.objects.count(), 1)

    def test_narrative_only_report_accepted(self):
        r = post(FORM10, {
            'reporting preference': 'Completely Anonymous',
            'detailed factual description of the concern / incident':
                'A coach raised his voice at a child during training.',
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(SafeguardingReport.objects.count(), 1)

    def test_existing_full_report_still_accepted(self):
        """Phase 1 shape (categories list) must keep passing the guard."""
        r = post(FORM10, {
            'reporting preference': 'Confidential (Name Known to Safeguarding Officer Only)',
            'reporter full name': 'Witness One',
            'email address': 'witness@example.com',
            'child / player name (if known)': 'Test Child',
            'estimated age / dob': '12',
            'squad tier involved': 'U13',
            'nature of the safeguarding incident': ['Emotional abuse / bullying'],
            'detailed factual description of the concern / incident':
                'Bullying observed at the pitch side over three sessions.',
            'names of any witnesses / observers': 'Another parent',
        })
        self.assertEqual(r.status_code, 200)
        rep = SafeguardingReport.objects.get()
        self.assertEqual(rep.child_name, 'Test Child')


# ── email minimisation ────────────────────────────────────────────────────

class EmailRedactionTests(TestCase):

    MEDICAL = {
        'first name': 'Brian',
        'last name': 'Otieno',
        'blood group (if known)': 'O+',
        'known allergies (food, medication, insect bites, etc.)': 'Peanuts',
        'nhif / medical insurance provider': 'NHIF',
        'insurance / member number': '123456789',
        'birth certificate / upi no.': '2888777',
        'national id / passport number': '3344555',
        'guardian phone': '+254700000000',
    }

    def test_redact_sensitive_masks_medical_and_id(self):
        out, masked = _redact_sensitive(self.MEDICAL)
        self.assertEqual(masked, 6)
        self.assertEqual(out['first name'], 'Brian')          # untouched
        self.assertNotIn('O+', out['blood group (if known)'])  # masked
        self.assertNotIn('Peanuts', out['known allergies (food, medication, insect bites, etc.)'])
        self.assertNotIn('2888777', out['birth certificate / upi no.'])
        self.assertIn('withheld', out['blood group (if known)'])

    def test_is_sensitive_key_patterns(self):
        for k in ('Blood Group (If known)', 'Known Allergies (Food…)',
                  'NHIF / Medical Insurance Provider', 'Family Physician / Preferred Clinic',
                  'Birth Certificate / UPI No.', 'National ID / Passport Number',
                  'Medical Declaration / Pre-existing Conditions'):
            self.assertTrue(_is_sensitive_key(k), k)
        for k in ('First Name', 'Guardian Phone', 'Residential Area', 'Email Address'):
            self.assertFalse(_is_sensitive_key(k), k)

    def test_notification_email_withholds_medical_from_body(self):
        from unittest import mock
        from .. import views as v
        rec = SentMail()
        with mock.patch.object(v, 'resend_send', rec):
            r = post(FORM01, self.MEDICAL)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(rec.sent), 1)          # notification only (no auto-reply in tests)
        text = rec.sent[0]['text']
        self.assertIn('Brian', text)                 # ordinary data passes
        self.assertNotIn('O+', text)                 # blood group withheld
        self.assertNotIn('Peanuts', text)            # allergy withheld
        self.assertNotIn('123456789', text)          # member number withheld
        self.assertNotIn('2888777', text)            # birth cert withheld
        self.assertNotIn('3344555', text)            # national ID withheld
        self.assertIn('withheld', text)
        self.assertIn('staff portal', text)

    def test_ledger_still_stores_full_payload(self):
        from unittest import mock
        from .. import views as v
        with mock.patch.object(v, 'resend_send', SentMail()):
            post(FORM01, self.MEDICAL)
        row = FormSubmission.objects.get()
        self.assertEqual(row.payload['blood group (if known)'], 'O+')
        self.assertEqual(row.payload['national id / passport number'], '3344555')

    def test_plain_enquiry_email_not_flagged(self):
        from unittest import mock
        from .. import views as v
        rec = SentMail()
        with mock.patch.object(v, 'resend_send', rec):
            post(ENQ, {'name': 'Amina', 'message': 'hello'})
        self.assertNotIn('withheld', rec.sent[0]['text'])


# ── R26: staff ledger redaction ───────────────────────────────────────────

class LedgerRedactionTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth.models import Group, User
        cls.payload = {
            'first name': 'Brian',
            'blood group (if known)': 'O+',
            'birth certificate / upi no.': '2888777',
            'guardian phone': '+254700000000',
        }
        FormSubmission.objects.create(
            ref='SP-REG-20260101-TEST', form_slug=FORM01,
            name='Brian Otieno', email='g@example.com', payload=cls.payload)
        cls.staff = User.objects.create_user('plainstaff', password='pw-12345678',
                                             is_staff=True)
        cls.admin_user = User.objects.create_user('padmin', password='pw-12345678',
                                                  is_staff=True)
        cls.admin_user.groups.add(Group.objects.get(name=PORTAL_ADMIN_GROUP))
        cls.super = User.objects.create_superuser('boss', password='pw-12345678')

    def _dashboard_json(self, username):
        c = Client()
        c.login(username=username, password='pw-12345678')
        html = c.get('/portal/').content.decode()
        # the dashboard embeds the answer sheet as JSON in a script tag
        import json as _json, re as _re
        m = _re.search(
            r'<script type="application/json" id="subs-json">(.*?)</script>',
            html, _re.S)
        if not m:
            self.fail('subs-json script tag not found in dashboard')
        return _json.loads(m.group(1))

    def test_plain_staff_sees_masked_values(self):
        subs = self._dashboard_json('plainstaff')
        self.assertEqual(len(subs), 1)
        self.assertTrue(subs[0]['restricted'])
        self.assertEqual(subs[0]['answers']['first name'], 'Brian')
        self.assertNotIn('O+', subs[0]['answers']['blood group (if known)'])
        self.assertNotIn('2888777', subs[0]['answers']['birth certificate / upi no.'])
        self.assertIn('withheld', subs[0]['answers']['blood group (if known)'])

    def test_portal_admin_sees_full_values(self):
        subs = self._dashboard_json('padmin')
        self.assertFalse(subs[0]['restricted'])
        self.assertEqual(subs[0]['answers']['blood group (if known)'], 'O+')
        self.assertEqual(subs[0]['answers']['birth certificate / upi no.'], '2888777')

    def test_superuser_sees_full_values(self):
        subs = self._dashboard_json('boss')
        self.assertFalse(subs[0]['restricted'])
        self.assertEqual(subs[0]['answers']['blood group (if known)'], 'O+')
