"""Phase 1 — safeguarding data protection: shared constants + parsing.

Safeguarding reports (site form 10) are the most restricted data this
system holds. They are deliberately moved OUT of the generic
FormSubmission ledger into a dedicated, permission-gated model, and this
module owns:

  * the role/group names used across admin, portal and tests,
  * the report status workflow,
  * the label-keyed parser that turns the browser serialisation of
    form-10 into structured fields (pure function — imported by the
    data migration, the public API and the DSO portal), and
  * the idempotent legacy-row mover used by migration 0004.

Nothing here imports Django models, so it is safe to load inside a
migration's historical context.
"""

# ── Roles (Django groups) ────────────────────────────────────────────────
# Parent/Guardian is not a Django group: it is the Guardian profile in the
# parents app (see parents.models.Guardian). The three groups below are
# created by data migration submissions.0004.

DSO_GROUP = 'DSO (Designated Safeguarding Officer)'
STAFF_GROUP = 'Academy Staff'
PORTAL_ADMIN_GROUP = 'Portal Administrators'

LEGACY_SAFEGUARDING_SLUG = 'form-10-safeguarding-report'


def is_dso(user):
    """True only for active users explicitly granted the DSO role.

    Superusers are deliberately NOT exempt: safeguarding access must be
    an explicit, reviewable grant (break-glass = temporarily add the DSO
    group to the admin account; every grant is visible in the group list
    and audited on use).
    """
    if user is None or not getattr(user, 'is_active', False):
        return False
    return user.groups.filter(name=DSO_GROUP).exists()


# ── Report workflow ──────────────────────────────────────────────────────
SAFEGUARDING_STATUS = [
    ('received', 'Received'),
    ('under_review', 'Under review'),
    ('actioned', 'Actioned'),
    ('escalated_external', 'Escalated — external authority'),
    ('closed', 'Closed'),
]

# The six incident categories printed on form 10 (checkbox cards). The
# browser serialiser keys them under one shared label, so values arrive
# either as a list of checked option values (fixed serialiser) or — for
# legacy payloads — as "Yes"/"No" noise. The parser maps both shapes.
SAFEGUARDING_CATEGORIES = [
    # (canonical short label, markers matched against option values/keys)
    ('Physical harm / excessive force', ('physical',)),
    ('Emotional abuse / bullying', ('emotional',)),
    ('Sexual misconduct / grooming', ('sexual',)),
    ('Neglect / medical risk', ('neglect', 'unsafe environment')),
    ('Discrimination / harassment', ('discrimination',)),
    ('Financial exploitation / extortion', ('financial',)),
]

# label key (lower-cased, whitespace-collapsed) → model field
_FIELD_MAP = {
    'reporting preference': '_preference_raw',
    'reporter full name': 'reporter_name',
    'your role in the academy': 'reporter_role',
    'direct phone number': 'reporter_contact',
    'email address': 'reporter_email',
    'child / player name (if known)': 'child_name',
    'estimated age / dob': 'child_age',
    'squad tier involved': 'squad',
    'person(s) whose conduct is in question (if applicable)': 'persons_in_question',
    'date of incident / occurrence': 'incident_date',
    'approximate time': 'incident_time',
    'specific location / field': 'location',
    'detailed factual description of the concern / incident': 'narrative',
    'names of any witnesses / observers': 'witnesses',
    'has the child disclosed this to anyone else?': 'disclosure_history',
    'has external authority been notified?': 'external_authority',
    'ob number / police reference (if applicable)': 'police_ob',
}

# Keys that never carry report content — dropped from the preserved
# "extra" catch-all.
_NOISE_PREFIXES = ('_', 'company', 'i confirm', 'reporting status')


def _norm_key(k):
    return ' '.join(str(k or '').split()).strip().lower()


def _first(v):
    if isinstance(v, list):
        v = v[0] if v else ''
    return str(v or '').strip()


def _clip(v, n):
    v = _first(v)
    return v[:n]


def extract_safeguarding(fields):
    """{label: value_or_list} → dict of SafeguardingReport field values.

    Pure function: the same parser serves the live API, the legacy data
    migration and the tests, so parsing rules can never drift between
    paths. Unknown labels are preserved in ``extra`` (minus noise) so no
    part of a report is ever silently dropped.
    """
    out = {}
    extra = {}
    for k, v in (fields or {}).items():
        nk = _norm_key(k)
        if not nk:
            continue
        if nk.startswith('nature of the safeguarding incident'):
            cats = _parse_categories(k, v)
            if cats:
                out['categories'] = cats
                continue
            # nothing recoverable (pre-fix Yes/No shape) — keep the raw
            # value in extra rather than dropping it silently
            ev = _first(v)
            if ev and ev not in ('(empty)', '(not selected)'):
                extra[nk] = ev
            continue
        field = _FIELD_MAP.get(nk)
        if field:
            out[field] = _clip(v, 2000 if field == 'narrative' else 300)
        elif not any(nk.startswith(p) for p in _NOISE_PREFIXES):
            ev = v if isinstance(v, list) else _clip(v, 500)
            if ev not in ('', [], '(empty)', '(not selected)'):
                extra[nk] = ev

    pref = _first(out.pop('_preference_raw', '')).lower()
    out['reporter_preference'] = 'anonymous' if 'anonymous' in pref else 'confidential'
    if out['reporter_preference'] == 'anonymous':
        # Defence in depth: the form hides these fields, but an anonymous
        # report must never store identity even if a client misbehaves.
        for f in ('reporter_name', 'reporter_role', 'reporter_contact', 'reporter_email'):
            out.pop(f, None)
    out['extra'] = extra
    return out


def _parse_categories(label_key, value):
    """Both serialiser shapes → list of canonical category labels."""
    cats = []
    if isinstance(value, list):
        for item in value:
            s = _first(item).lower()
            for canon, markers in SAFEGUARDING_CATEGORIES:
                if any(m in s for m in markers) and canon not in cats:
                    cats.append(canon)
    else:
        # legacy single "Yes"/"No" — match on the label itself
        if _first(value).lower() == 'yes':
            kl = _norm_key(label_key)
            for canon, markers in SAFEGUARDING_CATEGORIES:
                if any(m in kl for m in markers) and canon not in cats:
                    cats.append(canon)
    return cats


def report_fields_for_create(fields):
    """extract_safeguarding output → safe **kwargs for
    SafeguardingReport.objects.create (no database types, just strings)."""
    data = extract_safeguarding(fields)
    cats = data.get('categories', [])
    data['categories'] = '; '.join(cats)
    return data


# ── Legacy migration (used by migration 0004; idempotent) ────────────────

def migrate_legacy_rows(apps=None):
    """Move every legacy form-10 ledger row into the restricted model.

    Called by data migration 0004 with the historical app registry, and
    callable on the live registry (tests, re-runs). Each moved report
    gets an audit entry recording the migration; the source ledger row is
    then deleted so no staff-facing surface ever sees it again.
    """
    if apps is None:
        from django.apps import apps as real_apps
        apps = real_apps
    FormSubmission = apps.get_model('submissions', 'FormSubmission')
    SafeguardingReport = apps.get_model('submissions', 'SafeguardingReport')
    SafeguardingAuditEntry = apps.get_model('submissions', 'SafeguardingAuditEntry')

    moved = 0
    for fs in FormSubmission.objects.filter(form_slug=LEGACY_SAFEGUARDING_SLUG):
        data = report_fields_for_create(fs.payload or {})
        report, _created = SafeguardingReport.objects.get_or_create(
            ref=fs.ref,
            defaults={
                'reporter_preference': data.get('reporter_preference', 'confidential'),
                'reporter_name': data.get('reporter_name', fs.name or ''),
                'reporter_email': data.get('reporter_email', fs.email or ''),
                'reporter_contact': data.get('reporter_contact', ''),
                'reporter_role': data.get('reporter_role', ''),
                'child_name': data.get('child_name', ''),
                'child_age': data.get('child_age', ''),
                'squad': data.get('squad', ''),
                'categories': data.get('categories', ''),
                'persons_in_question': data.get('persons_in_question', ''),
                'incident_date': data.get('incident_date', ''),
                'incident_time': data.get('incident_time', ''),
                'location': data.get('location', ''),
                'narrative': data.get('narrative', ''),
                'witnesses': data.get('witnesses', ''),
                'disclosure_history': data.get('disclosure_history', ''),
                'external_authority': data.get('external_authority', ''),
                'police_ob': data.get('police_ob', ''),
                'extra': data.get('extra', {}),
                'ip': fs.ip,
                'user_agent': fs.user_agent,
                'status': 'received',
            })
        SafeguardingAuditEntry.objects.create(
            report=report, report_ref=report.ref,
            actor=None, actor_username='system (migration)',
            action='migrated',
            detail='Legacy ledger row moved into the restricted safeguarding '
                   'store during the Phase 1 upgrade.')
        fs.delete()
        moved += 1
    return moved
