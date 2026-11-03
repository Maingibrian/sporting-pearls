"""Parser unit tests — the label-keyed rules that turn the browser
serialisation of form 10 into structured SafeguardingReport fields.

The same pure function serves the live API, the legacy migration and
these tests, so the parsing rules can never drift between paths.
"""
from django.test import SimpleTestCase

from submissions.safeguarding import extract_safeguarding, report_fields_for_create


def form10_payload(**over):
    """A realistic form-10 payload as sp-forms.js v23 serialises it."""
    p = {
        'Reporting Preference': 'Confidential (Name Known to Safeguarding Officer Only)',
        'Reporter Full Name': 'Jane Mwangi',
        'Your Role in the Academy': 'Parent / Legal Guardian',
        'Direct Phone Number': '0711 000 000',
        'Email Address': 'jane@example.com',
        'Child / Player Name (If known)': 'Test Child',
        'Estimated Age / DOB': '12 years old',
        'Squad Tier Involved': 'U13',
        'Nature of the Safeguarding Incident (Select all that apply)': [
            'Physical Abuse / Inappropriate Physical Contact',
            'Neglect / Unsafe Environment / Medical',
        ],
        'Person(s) Whose Conduct is in Question (If applicable)': 'A. Coach',
        'Date of Incident / Occurrence': '2026-10-20',
        'Approximate Time': '16:30',
        'Specific Location / Field': 'Main pitch, Mtwapa',
        'Detailed Factual Description of the Concern / Incident': 'Factual narrative here.',
        'Names of Any Witnesses / Observers': 'Two parents',
        'Has the Child Disclosed this to Anyone Else?': 'Disclosed to mother',
        'Has External Authority Been Notified?': 'No - Academy Internal Escalation First',
        'OB Number / Police Reference (If applicable)': '',
        'I confirm that the information provided is true': 'Yes',
    }
    p.update(over)
    return p


class ExtractTests(SimpleTestCase):

    def test_full_confidential_payload(self):
        out = extract_safeguarding(form10_payload())
        self.assertEqual(out['reporter_preference'], 'confidential')
        self.assertEqual(out['reporter_name'], 'Jane Mwangi')
        self.assertEqual(out['reporter_email'], 'jane@example.com')
        self.assertEqual(out['reporter_contact'], '0711 000 000')
        self.assertEqual(out['child_name'], 'Test Child')
        self.assertEqual(out['squad'], 'U13')
        self.assertEqual(out['categories'],
                         ['Physical harm / excessive force', 'Neglect / medical risk'])
        self.assertEqual(out['narrative'], 'Factual narrative here.')
        self.assertEqual(out['location'], 'Main pitch, Mtwapa')
        self.assertEqual(out['police_ob'], '')
        # the truth-affirmation checkbox is noise, not content
        self.assertNotIn('i confirm that the information provided is true', out['extra'])

    def test_anonymous_strips_identity(self):
        out = extract_safeguarding(form10_payload(
            **{'Reporting Preference': 'Completely Anonymous',
               'Reporter Full Name': 'Should Vanish',
               'Email Address': 'should@vanish.example'}))
        self.assertEqual(out['reporter_preference'], 'anonymous')
        for f in ('reporter_name', 'reporter_role', 'reporter_contact', 'reporter_email'):
            self.assertNotIn(f, out)

    def test_legacy_yes_no_shape_cannot_recover_categories(self):
        """Pre-fix payloads stored a single Yes/No under the shared label —
        WHICH categories were ticked was already lost at serialisation time.
        The parser must not invent them; the 'Yes' is preserved in extra."""
        out = extract_safeguarding(form10_payload(**{
            'Nature of the Safeguarding Incident (Select all that apply)': 'Yes'}))
        self.assertNotIn('categories', out)
        self.assertEqual(out['extra'].get(
            'nature of the safeguarding incident (select all that apply)'), 'Yes')

    def test_category_prefix_matching_survives_label_noise(self):
        """The 80-char label slice + b/p concatenation must not break matching."""
        out = extract_safeguarding(
            {'nature of the safeguarding incident (select all that appl':
             ['Sexual Misconduct / Inappropriate Grooming']})
        self.assertEqual(out['categories'], ['Sexual misconduct / grooming'])

    def test_unmatched_keys_preserved_in_extra(self):
        out = extract_safeguarding({'A New Future Question': 'answer'})
        self.assertEqual(out['extra'], {'a new future question': 'answer'})

    def test_create_kwargs_categories_joined(self):
        data = report_fields_for_create(form10_payload())
        self.assertEqual(data['categories'],
                         'Physical harm / excessive force; Neglect / medical risk')
        self.assertEqual(data['reporter_preference'], 'confidential')
