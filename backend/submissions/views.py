"""JSON API for the static site.

POST /api/forms/<slug>/   — store a submission, email the academy (Resend),
                            send a branded auto-reply, return {ok, ref}.
GET  /api/fixtures/       — published fixtures for the homepage panel.
GET  /api/players/        — published rosters for the six squad pages.
GET  /api/health/         — uptime probe.

Covers all 13 site forms (01–10 + partnership + newsletter + general
enquiry). The browser sync layer (sp-forms.js) keys answers by each
field's visible label, so name/email extraction below matches keys
case-insensitively and falls back to pattern scans.

Spam protection: per-IP rate limit + honeypot field ("company") that must
stay empty. reCAPTCHA deliberately skipped (user decision).
"""
import json
import re
import secrets
from datetime import datetime as dt

import requests
from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import Coach, Fixture, FormSubmission, Player, Result, Squad, \
    SafeguardingAuditEntry, SafeguardingReport
from .safeguarding import LEGACY_SAFEGUARDING_SLUG, report_fields_for_create

FORMS = {
    'contact-general-enquiry': ('General Enquiry', 'GENQ'),
    'form-01-player-registration': ('Player Registration', 'REG'),
    'form-02-trial-application': ('Trial Application', 'TRIAL'),
    'form-03-parent-association': ('Parent Association', 'PARENT'),
    'form-04-volunteer-application': ('Volunteer Application', 'VOL'),
    'form-05-coach-technical-staff': ('Coach / Technical Staff', 'COACH'),
    'form-06-sponsorship-partnership': ('Sponsorship & Partnership', 'SPON'),
    'form-07-donation-support': ('Donation & Support', 'SUP'),
    'form-08-contact-form': ('Contact Form Enquiry', 'ENQ'),
    'form-09-media-photo-consent': ('Media & Photo Consent', 'MC'),
    'form-10-safeguarding-report': ('Safeguarding Report', 'SAFE'),
    'partnership-application': ('Partnership Application', 'PART'),
    'newsletter-subscription': ('Newsletter Subscription', 'NEWS'),
}

EMAIL_RE = re.compile(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}')
NAME_KEYS = ('name', 'fullname', 'full_name', 'first_name', 'firstname',
             'player_name', 'child_name', 'organisation', 'organization',
             'company_name', 'your_name', 'full name', 'your full name',
             'contact name', 'guardian name', 'parent name',
             'parent/guardian name', 'contact person')
EMAIL_KEYS = ('email', 'e_mail', 'email_address', 'contact_email',
              'your email', 'email address', 'your email address',
              'enter your email address')

# Phase 3 — payload shape guards + email minimisation -----------------------
MAX_BODY_BYTES = 65536      # a JSON form payload has no business being 64 KB
MAX_FIELDS = 200            # the longest real form (form-01) has ~60 answers
MAX_VALUE_CHARS = 4000      # generous even for a long narrative
MAX_LIST_ITEMS = 20         # checkbox groups have at most 6
EMPTY_VALUES = ('', '(empty)', '(not selected)', '(none selected)')

# Special-category keys (label substrings, lower-cased) whose values are
# withheld from NOTIFICATION EMAILS. The staff portal shows them (restricted
# to portal administrators — see portal.py); email bodies must not carry
# medical details or identity-document numbers through third-party relays.
SENSITIVE_PATTERNS = ('blood', 'allerg', 'chronic', 'injur', 'surger',
                      'nhif', 'insurance', 'member number', 'physician',
                      'doctor', 'medical', 'pre-existing',
                      'birth certificate', 'upi', 'national id',
                      'passport number')


def _is_sensitive_key(key):
    k = str(key).strip().lower()
    return any(p in k for p in SENSITIVE_PATTERNS)


def _redact_sensitive(fields):
    """fields -> (copy with sensitive values masked, number masked).

    Only used for the academy notification email body. The database stores
    the full payload; display-side restriction is handled separately.
    """
    out, masked = {}, 0
    for k, v in fields.items():
        if _is_sensitive_key(k):
            out[k] = '[withheld from email — view in the staff portal]'
            masked += 1
        else:
            out[k] = v
    return out, masked


def _nonempty_count(fields):
    """How many fields carry a real answer (not sentinels / blanks)."""
    n = 0
    for v in fields.values():
        vals = v if isinstance(v, list) else [v]
        if any(str(x).strip() not in EMPTY_VALUES for x in vals):
            n += 1
    return n


def _has_content(v):
    """True when a parsed report field carries real content (not sentinels)."""
    if not v:
        return False
    if isinstance(v, list):
        return any(_has_content(x) for x in v)
    if isinstance(v, dict):
        return bool(v)
    return str(v).strip() not in EMPTY_VALUES


def _norm(fields):
    """{label: value_or_list} -> {lowercased label: first value as str}."""
    out = {}
    for k, v in fields.items():
        if isinstance(v, list):
            v = v[0] if v else ''
        out[str(k).strip().lower()] = str(v or '').strip()
    return out


def client_ip(request):
    fwd = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return fwd.split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')


def resend_send(payload):
    """POST to the Resend API. Returns (ok, detail).

    SP_MAIL_REDIRECT (settings/env): when set, EVERY outbound email is
    redirected to that address instead of its real recipient, and the
    original recipient is preserved in the subject as [QC→original].
    Demo/QC mode — production .env files simply leave it unset."""
    if not settings.RESEND_API_KEY:
        return False, 'skipped (no RESEND_API_KEY configured)'
    payload = dict(payload)
    redirect_to = (getattr(settings, 'SP_MAIL_REDIRECT', '') or '').strip()
    if redirect_to:
        orig = ', '.join(payload.get('to') or [])
        if orig != redirect_to:
            payload['to'] = [redirect_to]
            payload['subject'] = f'[QC→{orig}] {payload.get("subject", "")}'
    try:
        r = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {settings.RESEND_API_KEY}',
                     'Content-Type': 'application/json'},
            json=payload, timeout=10)
        if r.status_code < 300:
            return True, 'sent'
        return False, f'HTTP {r.status_code}: {r.text[:200]}'
    except requests.RequestException as exc:
        return False, f'network error: {exc}'


def _flatten(fields):
    """{key: value_or_list} -> one-line summary of the answers."""
    lines = []
    for k, v in fields.items():
        if k.startswith('_'):
            continue
        if isinstance(v, list):
            v = ', '.join(str(x) for x in v)
        label = k.replace('_', ' ').strip().capitalize()
        lines.append(f'{label}: {v}')
    return '\n'.join(lines) or '(no fields)'


def _submit_safeguarding(request, fields, ip, ua):
    """Store a form-10 report in the RESTRICTED safeguarding store.

    Never touches the FormSubmission ledger (so the staff dashboard,
    admin ledger and CSV export cannot reveal that a report exists),
    emails the DSO a minimal notification only, and writes an audit
    entry for every step. Returns the JSON response body (with an
    optional 'status' key the caller must pop before serialising).
    """
    from .email_branding import safeguarding_ack_payload, \
        safeguarding_notification_payload

    data = report_fields_for_create(fields)
    # Phase 3 content guard: a report with no narrative, no child and no
    # incident information is not a report — reject it honestly rather
    # than storing an empty row with a reference number. (Sentinel values
    # like "(empty)" do not count as content.)
    if not (_has_content(data.get('narrative')) or
            _has_content(data.get('child_name')) or
            _has_content(data.get('categories')) or
            data.get('extra')):
        return {'ok': False, 'status': 400,
                'error': 'the report appears to be empty — please describe the concern'}

    ref = f'SP-SAFE-{dt.now():%Y%m%d}-{secrets.token_hex(2).upper()}'
    report = SafeguardingReport.objects.create(
        ref=ref, ip=ip or None,
        user_agent=(ua or '')[:300],
        **{k: v for k, v in data.items() if k != 'extra'},
        extra=data.get('extra', {}),
    )
    SafeguardingAuditEntry.objects.create(
        report=report, report_ref=ref, actor=None,
        actor_username='public form', action='received',
        detail='Report received through the website form.')

    # 1) minimal notification to the DSO only — never the general inbox
    dso_email = (getattr(settings, 'DSO_EMAIL', '') or '').strip()
    if dso_email:
        dso_url = request.build_absolute_uri('/portal/dso/')
        payload = safeguarding_notification_payload(ref, dso_url)
        ok, detail = resend_send({**payload,
                                  'from': settings.EMAIL_FROM,
                                  'to': [dso_email]})
    else:
        ok, detail = False, 'skipped (no DSO_EMAIL configured)'
    # classify: a skip (no DSO address / no API key) is not a failure
    if ok:
        short = 'sent'
        audit_detail = 'DSO notification: sent.'
    elif 'skipped' in detail:
        short = 'skipped'
        audit_detail = 'DSO notification: not sent (email not configured).'
    else:
        short = 'failed'
        audit_detail = f'DSO notification failed: {detail[:160]}'
    report.email_status = short
    report.email_error = '' if ok else detail
    report.save(update_fields=['email_status', 'email_error'])
    SafeguardingAuditEntry.objects.create(
        report=report, report_ref=ref, actor=None,
        actor_username='public form', action='notified',
        detail=audit_detail)

    # 2) neutral acknowledgment to a CONFIDENTIAL reporter who left an
    # email (anonymous reports cannot be acknowledged)
    if settings.AUTO_REPLY and report.reporter_preference == 'confidential' \
            and report.reporter_email:
        ack = safeguarding_ack_payload(report.reporter_name, ref,
                                       settings.EMAIL_TO)
        ack.update({'from': settings.EMAIL_FROM, 'to': [report.reporter_email]})
        resend_send(ack)

    return {'ok': True, 'ref': ref, 'stored': True}


@require_POST
@csrf_exempt
def submit_form(request, slug):
    if slug not in FORMS:
        return JsonResponse({'ok': False, 'error': f'unknown form "{slug}"'}, status=404)
    label, prefix = FORMS[slug]

    try:
        body = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'invalid JSON body'}, status=400)
    if not isinstance(body, dict):
        return JsonResponse({'ok': False, 'error': 'invalid JSON body'}, status=400)
    if len(request.body) > MAX_BODY_BYTES:
        return JsonResponse({'ok': False, 'error': 'submission too large'}, status=413)

    fields = body.get('data')
    if not isinstance(fields, dict):
        fields = {}

    # per-IP throttle — per form…
    ip = client_ip(request)
    key = f'spf:{ip}:{slug}'
    try:
        if cache.get(key) is None:
            cache.add(key, 0, 60)
        count = cache.incr(key)
    except ValueError:
        count = 1
    if count > settings.RATE_LIMIT_PER_MINUTE:
        return JsonResponse({'ok': False, 'error': 'too many requests, please try again shortly'},
                            status=429)
    # …and across ALL forms (Phase 2: one IP spraying every form was
    # 13 × the per-form budget; a whole office shares one NAT address,
    # so the ceiling is generous)
    gkey = f'spf-all:{ip}'
    try:
        if cache.get(gkey) is None:
            cache.add(gkey, 0, 60)
        gcount = cache.incr(gkey)
    except ValueError:
        gcount = 1
    if gcount > max(settings.RATE_LIMIT_PER_MINUTE * 4, 30):
        return JsonResponse({'ok': False, 'error': 'too many requests, please try again shortly'},
                            status=429)

    # honeypot: pretend success, store nothing, send nothing
    if str(fields.get('company', '') or '').strip():
        return JsonResponse({'ok': True, 'ref': '', 'stored': False})

    # Phase 3 payload shape guards — validation parity with the pages.
    # The browser forms enforce their own required fields; these checks
    # stop junk payloads from earning reference numbers, and give the
    # honest client a real error it can show (never queued for retry).
    if len(fields) > MAX_FIELDS:
        return JsonResponse({'ok': False, 'error': 'too many fields'}, status=400)
    for v in fields.values():
        vals = v if isinstance(v, list) else [v]
        if len(vals) > MAX_LIST_ITEMS:
            return JsonResponse({'ok': False, 'error': 'too many answers in one field'}, status=400)
        if any(len(str(x)) > MAX_VALUE_CHARS for x in vals):
            return JsonResponse({'ok': False, 'error': 'one answer is too long (4000 characters max)'}, status=400)
    if slug != LEGACY_SAFEGUARDING_SLUG:
        need = 1 if slug == 'newsletter-subscription' else 2
        if _nonempty_count(fields) < need:
            return JsonResponse({'ok': False, 'error': 'submission appears to be empty'}, status=400)
        if slug == 'newsletter-subscription':
            if not any(EMAIL_RE.search(str(x)) for v in fields.values()
                       for x in (v if isinstance(v, list) else [v])):
                return JsonResponse({'ok': False, 'error': 'a valid email address is required'}, status=400)

    # safeguarding reports take a separate, restricted path: they never
    # enter the shared ledger and are never emailed in full
    if slug == LEGACY_SAFEGUARDING_SLUG:
        resp = _submit_safeguarding(
            request, fields, ip, str(body.get('meta', {}).get('ua', ''))[:300])
        status = resp.pop('status', 200)
        return JsonResponse(resp, status=status)

    norm = _norm(fields)

    email = ''
    for k in EMAIL_KEYS:
        m = EMAIL_RE.search(norm.get(k, ''))
        if m:
            email = m.group(0)
            break
    if not email:  # fall back: first email-looking VALUE (never keys — a
        for v in norm.values():  # placeholder like "you@example.com" may be
            m = EMAIL_RE.search(v)  # used as a field key)
            if m:
                email = m.group(0)
                break

    name = ''
    for k in NAME_KEYS:
        if norm.get(k):
            name = norm[k][:200]
            break
    if not name:  # fall back: first field whose label mentions a name
        for k, v in norm.items():
            if 'name' in k and v and k not in ('username', 'surname', 'last name'):
                name = v[:200]
                break

    ref = f'SP-{prefix}-{dt.now():%Y%m%d}-{secrets.token_hex(2).upper()}'
    obj = FormSubmission.objects.create(
        ref=ref, form_slug=slug, name=name, email=email, payload=fields,
        ip=ip or None,
        user_agent=str(body.get('meta', {}).get('ua', ''))[:300],
    )

    # 1) notification to the academy inbox. Phase 3: medical details and
    # identity-document numbers are withheld from the email body — the
    # answer sheet in the restricted staff ledger is the display surface.
    safe_fields, masked = _redact_sensitive(fields)
    text = (f'New {label} submission — ref {ref}\n\n'
            f'From: {name or "(no name given)"}'
            f'{f" <{email}>" if email else ""}\n\n'
            f'{_flatten(safe_fields)}\n\n'
            f'Review it in the admin dashboard → /admin/')
    if masked:
        text += (f'\n\nNOTE: {masked} answer(s) containing medical details or ID '
                 'numbers were withheld from this email — open the answer '
                 'sheet in the staff portal.')
    ok, detail = resend_send({
        'from': settings.EMAIL_FROM,
        'to': [settings.EMAIL_TO],
        'reply_to': email or None,
        'subject': f'[Sporting Pearls] {label} — {name or ref}',
        'text': text,
    })
    obj.email_status = ('sent' if ok else detail)[:32]
    obj.email_error = '' if ok else detail

    # 2) branded auto-reply to the visitor (multipart html + text, with signature)
    if ok and settings.AUTO_REPLY and email:
        from .email_branding import auto_reply_payload
        reply = auto_reply_payload(name, label, ref)
        reply.update({'from': settings.EMAIL_FROM, 'to': [email]})
        resend_send(reply)

    obj.save(update_fields=['email_status', 'email_error'])
    return JsonResponse({'ok': True, 'ref': ref, 'stored': True})


@require_GET
def fixtures_list(request):
    fixtures = (Fixture.objects.filter(is_published=True)
                .values('id', 'team', 'opponent', 'competition', 'date',
                        'kickoff', 'venue', 'home_away'))
    data = [{**f, 'date': f['date'].isoformat()} for f in fixtures]
    return JsonResponse({'ok': True, 'count': len(data), 'fixtures': data})


@require_GET
def results_list(request):
    """Published match results for the public Results page (Phase 7).

    Newest first; outcome (W/D/L) is derived server-side so the page
    never has to trust client-side score logic. Unpublished rows never
    leave the building."""
    results = (Result.objects.filter(is_published=True)
               .order_by('-date', '-id'))
    data = [{
        'team': r.team,
        'opponent': r.opponent,
        'competition': r.competition,
        'date': r.date.isoformat(),
        'venue': r.venue,
        'home_away': r.home_away,
        'our_score': r.our_score,
        'their_score': r.their_score,
        'outcome': r.outcome,
        'report': r.report,
    } for r in results]
    return JsonResponse({'ok': True, 'count': len(data), 'results': data})


@require_GET
def player_public(request, ref):
    """One published player's public profile (Phase 7 — QR code target).

    The QR code on a child's card points at the website profile page,
    which reads this endpoint. Public fields only — exactly what the
    squad page already publishes (name, squad, number, position, age,
    motto, photo). Unpublished or unknown refs fail closed with 404 so
    a printed QR can never leak an un-published profile. Includes the
    squad key so the page can link back to the right squad tab."""
    try:
        p = Player.objects.select_related('squad').get(ref=ref)
    except Player.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'not found'}, status=404)
    if not p.is_published:
        return JsonResponse({'ok': False, 'error': 'not found'}, status=404)
    photo = ''
    if p.photo:
        try:
            photo = request.build_absolute_uri(p.photo.url)
        except ValueError:
            photo = ''
    elif p.photo_url:
        photo = p.photo_url
    return JsonResponse({
        'ok': True,
        'player': {
            'ref': p.ref,
            'first': p.first_name,
            'last': p.last_name,
            'no': p.number,
            'pos': p.position,
            'age': p.age,
            'motto': p.motto,
            'photo': photo,
            'captain': p.is_captain,
            'squad': {
                'key': p.squad.key,
                'code': p.squad.code,
                'label': p.squad.label,
                'accent': p.squad.accent,
            },
        },
    })


@require_GET
def players_roster(request):
    """Published rosters for the six squad pages, in pitch order.
    Shape mirrors the site's internal TEAMS structure so the page can
    render dashboard-managed players without any code change:
    {ok, count, squads: [{key, code, label, form, accent, captain, players:[…]}]}
    `captain` is the index of the captain inside `players` (-1 if none)."""
    squads_out = []
    total = 0
    for squad in Squad.objects.all():
        players = []
        cap_idx = -1
        qs = squad.players.filter(is_published=True)
        for i, p in enumerate(qs):
            photo = ''
            if p.photo:
                try:
                    photo = request.build_absolute_uri(p.photo.url)
                except ValueError:
                    photo = ''
            elif p.photo_url:
                photo = p.photo_url
            if p.is_captain and cap_idx < 0:
                cap_idx = i
            players.append({
                'ref': p.ref,
                'no': p.number,
                'first': p.first_name,
                'last': p.last_name,
                'pos': p.position,
                'age': p.age,
                'ht': p.height_m,
                'foot': p.foot,
                'motto': p.motto,
                'photo': photo,
            })
        squads_out.append({
            'key': squad.key,
            'code': squad.code,
            'label': squad.label,
            'form': squad.formation,
            'accent': squad.accent,
            'captain': cap_idx,
            'players': players,
        })
        total += len(players)
    return JsonResponse({'ok': True, 'count': total, 'squads': squads_out})


@require_GET
def coaches_list(request):
    """Published coaching staff for the website's technical-team section
    (Phase 4 — admin-settable content, like fixtures and rosters).
    Public read-only; the shape mirrors players_roster so the site can
    render it with the same fetch-and-cache pattern:
    {ok, count, coaches: [{name, role, squad, bio, photo}]}
    """
    out = []
    for c in Coach.objects.filter(is_published=True).select_related('squad'):
        photo = ''
        if c.photo:
            try:
                photo = request.build_absolute_uri(c.photo.url)
            except ValueError:
                photo = ''
        out.append({
            'name': c.name,
            'role': c.role,
            'squad': c.squad.label if c.squad else '',
            'bio': c.bio,
            'photo': photo,
        })
    return JsonResponse({'ok': True, 'count': len(out), 'coaches': out})


@require_GET
def health(request):
    return JsonResponse({'ok': True, 'service': 'sporting-pearls-backend',
                         'time': dt.now().isoformat(timespec='seconds')})


@require_GET
def healthz(request):
    """Liveness + database readiness probe (Phase 5, R20).

    Registered at '' and /healthz/ (uptime monitors / load balancers
    point here). No auth, no internals leaked: the response carries a
    boolean ok and the service name only — the failure reason goes to
    the logs, never to the client.
    """
    import logging
    from django.db import connection
    try:
        with connection.cursor() as cur:
            cur.execute('SELECT 1')
            cur.fetchone()
    except Exception:
        logging.getLogger('django.request').exception(
            'healthz: database readiness check failed')
        return JsonResponse({'ok': False}, status=503)
    return JsonResponse({'ok': True, 'service': 'sporting-pearls-backend',
                         'time': dt.now().isoformat(timespec='seconds')})
