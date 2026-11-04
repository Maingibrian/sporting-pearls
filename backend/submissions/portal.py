"""The live branded Management Portal — the academy's dashboard with zero
Django chrome, served straight from this backend at /portal/.

One login (staff account), then everything happens on the branded pages:
review submissions, publish fixtures, and manage the six squads' rosters
(hide / show / edit / photos / add / delete) — every change reaches the
website immediately through the same database the public API serves.

Assets live in submissions/portal_assets/ (styles + page body + login).
"""
import datetime as dt
import json
import re
from pathlib import Path

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .models import (Coach, FemininGalleryPhoto, Fixture, FormSubmission,
                     Player, Squad, POSITIONS)
from .safeguarding import is_dso, PORTAL_ADMIN_GROUP

# Phase 7 — the QR glyph used on player cards (kept next to the other
# card icons; the actual QR pages live in portal_qr.py).
from .portal_qr import QR_ICON
from .portal_auth import burn_password_time
from .views import _redact_sensitive

ASSETS = Path(__file__).resolve().parent / 'portal_assets'

# Phase 2 — staff login throttling (parity with the parent portal):
# 8 failed attempts per 15 minutes per IP, then a branded 429 page.
STAFF_LOGIN_LIMIT = 8
STAFF_LOGIN_WINDOW = 900


def _client_ip(request):
    fwd = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return fwd.split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')


def _staff_throttled(request):
    from django.core.cache import cache
    key = f'sp-stlg:{_client_ip(request)}'
    try:
        if cache.get(key) is None:
            cache.add(key, 0, STAFF_LOGIN_WINDOW)
        n = cache.get(key, 0)
    except ValueError:
        n = 0
    return n >= STAFF_LOGIN_LIMIT


def _staff_login_failed(request):
    from django.core.cache import cache
    try:
        cache.incr(f'sp-stlg:{_client_ip(request)}')
    except ValueError:
        pass

LABEL = {
    'contact-general-enquiry': 'General Enquiry',
    'form-01-player-registration': 'Player Registration',
    'form-02-trial-application': 'Trial Application',
    'form-03-parent-association': 'Parent Association',
    'form-04-volunteer-application': 'Volunteer Application',
    'form-05-coach-technical-staff': 'Coach & Technical Staff',
    'form-06-sponsorship-partnership': 'Sponsorship & Partnership',
    'form-10-safeguarding-report': 'Safeguarding Report',
    'partnership-application': 'Partnership Application',
    'newsletter-subscription': 'Newsletter Subscription',
}
SHORT = {
    'contact-general-enquiry': 'Enquiry',
    'form-01-player-registration': 'Registration',
    'form-02-trial-application': 'Trials',
    'form-03-parent-association': 'Parents',
    'form-04-volunteer-application': 'Volunteers',
    'form-05-coach-technical-staff': 'Coaches',
    'form-06-sponsorship-partnership': 'Sponsorship',
    'form-10-safeguarding-report': 'Safeguarding',
    'partnership-application': 'Partnership',
    'newsletter-subscription': 'Newsletter',
}
VERB = {
    'form-02-trial-application': 'applied for a trial',
    'form-01-player-registration': 'registered as a player',
    'form-10-safeguarding-report': 'filed a safeguarding report',
    'partnership-application': 'sent a partnership proposal',
    'form-06-sponsorship-partnership': 'sent a sponsorship enquiry',
    'newsletter-subscription': 'joined the newsletter',
    'contact-general-enquiry': 'sent a general enquiry',
    'form-03-parent-association': 'joined the Parent Association',
    'form-04-volunteer-application': 'signed up to volunteer',
    'form-05-coach-technical-staff': 'applied to coach',
}
STATUS_LABEL = {'new': 'New', 'reviewed': 'Reviewed', 'archived': 'Archived'}
EMAIL_LABEL = {'sent': 'Delivered', 'pending': 'Pending', 'failed': 'Failed'}
POSITION_LABEL = dict(POSITIONS)
CODE_DISPLAY = {'FEM': 'Féminin', 'U09': 'U9', 'U13': 'U13',
                'U15': 'U15', 'U17': 'U17', 'U19': 'U19'}
POS_CODES = [c for c, _ in POSITIONS]

EYE_HIDE = ('<svg class="i-hide" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8'
            'a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72'
            '-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>')
EYE_SHOW = ('<svg class="i-show" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10'
            '-7z"/><circle cx="12" cy="12" r="3"/></svg>')
PENCIL = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
          'stroke-linejoin="round"><path d="M12 20h9M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>')
CAMERA = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
          'stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>'
          '<circle cx="12" cy="13" r="4"/></svg>')
TRASH = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
         'stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 '
         '0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>')


def esc(s):
    import html
    return html.escape(str(s), quote=True)


def fmt_day(d):
    return f"{d.strftime('%a')} {d.day} {d.strftime('%b %Y')}"


def fmt_dt(d, full=False):
    d = timezone.localtime(d)
    if full:
        return f"{d.day} {d.strftime('%b %Y')} · {d.strftime('%H:%M')}"
    return f"{d.day} {d.strftime('%b')} · {d.strftime('%H:%M')}"


def ago(d, now):
    d = timezone.localtime(d).date()
    n = (now.date() - d).days
    if n <= 0:
        return 'today'
    if n == 1:
        return 'yesterday'
    return f'{n} days ago'


def initials(name):
    words = [w for w in re.split(r'\s+', str(name).strip()) if w]
    if not words:
        return 'SP'
    return ''.join(w[0] for w in words[:2]).upper()


def photo_src(p):
    if p.photo:
        try:
            return '/media/' + p.photo.name
        except ValueError:
            pass
    return p.photo_url or ''


def player_card(p, squad_code):
    """One branded player card — now with live action buttons."""
    mono = (p.first_name[:1] + p.last_name[:1]).upper()
    img_src = photo_src(p)
    if img_src:
        photo_html = (f'<img src="{esc(img_src)}" alt="" loading="lazy" '
                      f'data-fb-hide="reveal-next">'
                      f'<div class="ava" style="display:none">{esc(mono)}</div>')
    else:
        photo_html = f'<div class="ava">{esc(mono)}</div>'
    star = ('<svg class="pl-star" viewBox="0 0 24 24" fill="currentColor" stroke="none">'
            '<path d="M12 2l2.9 6.2 6.6.8-4.9 4.6 1.3 6.6L12 17l-5.9 3.2 1.3-6.6L2.5 9l6.6-.8L12 2z"/></svg>'
            ) if p.is_captain else ''
    meta = ' · '.join(x for x in [
        p.position,
        f'{p.age} yrs' if p.age else '',
        f'{p.height_m} m' if p.height_m else '',
        ('Left' if p.foot == 'L' else 'Right') + '-footed' if p.foot else '',
    ] if x) or '—'
    motto = f'“{p.motto}”' if p.motto else 'Motto to follow from the data form.'
    no_txt = f'#{p.number:02d}' if p.number is not None else '#—'
    pill = ('<span class="pill p-sent">Live on site</span>' if p.is_published
            else '<span class="pill p-arc">Draft</span>')
    acts = (
        f'<span class="pl-acts">'
        f'<button class="iconbtn pl-act" data-act="toggle" title="'
        + ('Hide from the website' if p.is_published else 'Show on the website')
        + f'" aria-label="Toggle visibility">{EYE_HIDE}{EYE_SHOW}</button>'
        f'<button class="iconbtn pl-act" data-act="edit" title="Edit profile" aria-label="Edit profile">{PENCIL}</button>'
        f'<button class="iconbtn pl-act" data-act="photo" title="Upload photo" aria-label="Upload photo">{CAMERA}</button>'
        f'<button class="iconbtn pl-act danger" data-act="delete" title="Delete player" aria-label="Delete player">{TRASH}</button>'
        f'<a class="iconbtn pl-act" href="/portal/qr/{esc(p.ref)}/" title="QR code card" '
        f'aria-label="QR code card">{QR_ICON}</a>'
        f'</span>')
    draft = ' draft' if not p.is_published else ''
    return (
        f'<article class="card pl-card{draft}" data-squad="{esc(squad_code)}" data-pid="{p.id}" '
        f'data-ref="{esc(p.ref)}">'
        f'<div class="pl-photo">{photo_html}<span class="pl-num">{no_txt}</span>{star}</div>'
        f'<div class="pl-body"><h3>{esc(p.first_name)} {esc(p.last_name)}</h3>'
        f'<div class="pl-meta">{esc(meta)}</div>'
        f'<p class="pl-motto">{esc(motto)}</p></div>'
        f'<div class="pl-foot"><code>{esc(p.ref)}</code>{pill}{acts}</div>'
        f'</article>')


def coach_photo_src(c):
    if c.photo:
        return '/media/' + c.photo.name
    return ''


def coach_card(c):
    """One technical-team card — reuses the player-card scaffolding so
    the coaches view feels native to the rest of the portal (rev 28)."""
    mono = initials(c.name)
    if c.photo:
        photo_html = (f'<img src="{esc(coach_photo_src(c))}" alt="" loading="lazy" '
                      f'data-fb-hide="reveal-next">'
                      f'<div class="ava" style="display:none">{esc(mono)}</div>')
    else:
        photo_html = f'<div class="ava">{esc(mono)}</div>'
    pill = ('<span class="pill p-sent">Live on site</span>' if c.is_published
            else '<span class="pill p-arc">Draft</span>')
    meta = ' · '.join(x for x in [c.role,
                                  c.squad.label if c.squad else 'Academy-wide'] if x)
    acts = (
        f'<span class="pl-acts">'
        f'<button class="iconbtn co-act" data-act="toggle" title="'
        + ('Hide from the website' if c.is_published else 'Show on the website')
        + f'" aria-label="Toggle visibility">{EYE_HIDE}{EYE_SHOW}</button>'
        f'<button class="iconbtn co-act" data-act="edit" title="Edit profile" aria-label="Edit profile">{PENCIL}</button>'
        f'<button class="iconbtn co-act" data-act="photo" title="Upload photo" aria-label="Upload photo">{CAMERA}</button>'
        f'<button class="iconbtn co-act danger" data-act="delete" title="Remove coach" aria-label="Remove coach">{TRASH}</button>'
        f'</span>')
    draft = ' draft' if not c.is_published else ''
    return (
        f'<article class="card pl-card co-card{draft}" data-cid="{c.id}" '
        f'data-name="{esc(c.name)}">'
        f'<div class="pl-photo">{photo_html}</div>'
        f'<div class="pl-body"><h3>{esc(c.name)}</h3>'
        f'<div class="pl-meta">{esc(meta)}</div>'
        f'<p class="pl-motto">{esc(c.bio or "Short bio to follow once confirmed.")}</p></div>'
        f'<div class="pl-foot"><code>#{c.sort:02d}</code>{pill}{acts}</div>'
        f'</article>')


def build_page(request):
    now = timezone.localtime(timezone.now())
    gen_date = now.strftime('%d %b %Y · %H:%M').lstrip('0')

    # Phase 3 (R26): medical details and ID numbers in the ledger are
    # restricted. Portal administrators and superusers see the full answer
    # sheet; every other staff account sees those values masked.
    full_intake = request.user.is_superuser or \
        request.user.groups.filter(name=PORTAL_ADMIN_GROUP).exists()

    subs = list(FormSubmission.objects.order_by('-created_at', 'ref'))
    fixes = list(Fixture.objects.order_by('date'))
    squads = list(Squad.objects.order_by('sort'))
    players = list(Player.objects.select_related('squad').order_by('squad__sort', 'pitch_order', 'ref'))

    total = len(subs)
    c_new = sum(1 for s in subs if s.status == 'new')
    c_rev = sum(1 for s in subs if s.status == 'reviewed')
    c_arc = sum(1 for s in subs if s.status == 'archived')
    c_pend = sum(1 for s in subs if s.email_status != 'sent')
    c_sent = total - c_pend
    fx_pub = sum(1 for f in fixes if f.is_published)
    forms = len({s.form_slug for s in subs})

    # ---- donut ----
    p1 = round(c_new / total * 100, 1) if total else 0
    p2 = round((c_new + c_rev) / total * 100, 1) if total else 0
    donut = (f"conic-gradient(#f59d1e 0 {p1}%, #2f8f83 {p1}% {p2}%, #8a94a6 {p2}% 100%)")

    # ---- bars ----
    counts = {}
    for s in subs:
        counts[s.form_slug] = counts.get(s.form_slug, 0) + 1
    mx = max(counts.values()) if counts else 1
    bars = []
    for slug, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        w = max(round(n / mx * 100), 7)
        bars.append(
            '                <div class="bar-row">'
            f'<span class="b-name">{esc(SHORT.get(slug, slug))}</span>'
            f'<span class="bar-track"><span class="bar-fill" style="width:{w}%"></span></span>'
            f'<span class="b-n">{n}</span></div>')
    bars_html = '\n'.join(bars)

    # ---- activity (latest 5) ----
    acts = []
    for s in subs[:5]:
        color = {'new': '#f59d1e', 'reviewed': '#2f8f83'}.get(s.status, '#8a94a6')
        acts.append(
            '                <div class="act-item"><span class="act-dot" style="background:' + color + '"></span>'
            f'<div><p><b>{esc(s.name or "Someone")}</b> {esc(VERB.get(s.form_slug, "submitted " + LABEL.get(s.form_slug, s.form_slug)))}</p>'
            f'<time>{esc(fmt_dt(s.created_at))} — {esc(ago(s.created_at, now))}</time></div></div>')
    activity_html = '\n'.join(acts)

    # ---- submission rows + JSON ----
    from parents.models import Complaint, ParentInvite
    invited_sub_ids = set(ParentInvite.objects.filter(submission__isnull=False)
                          .values_list('submission_id', flat=True))
    active_sub_ids = set(ParentInvite.objects.filter(submission__isnull=False,
                                                     accepted_at__isnull=False)
                         .values_list('submission_id', flat=True))
    c_desk = Complaint.objects.filter(status__in=('open', 'in_review')).count()
    rows, jsubs = [], []
    for i, s in enumerate(subs):
        label = LABEL.get(s.form_slug, s.form_slug)
        ftypes = [s.status] + (['pend'] if s.email_status != 'sent' else [])
        search = ' '.join([s.name or '', s.email or '', s.ref, label]).lower()
        st_pill = f'p-{s.status}'
        em_pill = 'p-sent' if s.email_status == 'sent' else 'p-pend'
        rows.append(
            f'<tr data-f="{" ".join(ftypes)}" data-search="{esc(search)}">'
            f'<td class="c-check"><input type="checkbox" class="row-check" aria-label="Select entry"></td>'
            f'<td class="c-who"><span class="who"><span class="ava">{esc(initials(s.name))}</span>'
            f'<span><strong>{esc(s.name or "Unnamed entry")}</strong>'
            f'<small>{esc(s.email or "no email given")}</small></span></span></td>'
            f'<td><code class="ref">{esc(s.ref)}</code></td>'
            f'<td class="c-form">{esc(label)}</td>'
            f'<td><span class="pill {st_pill}">{esc(STATUS_LABEL.get(s.status, s.status))}</span></td>'
            f'<td><span class="pill {em_pill}">{esc(EMAIL_LABEL.get(s.email_status, s.email_status))}</span></td>'
            f'<td class="c-when">{esc(fmt_dt(s.created_at))}<small>{esc(ago(s.created_at, now))}</small></td>'
            f'<td><button class="iconbtn view-row" data-idx="{i}" title="Open answer sheet" aria-label="Open entry">'
            f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>'
            f'</button></td></tr>')
        answers = s.payload or {}
        restricted = False
        if not full_intake:
            answers, masked = _redact_sensitive(answers)
            restricted = masked > 0
        jsubs.append({
            'name': s.name or 'Unnamed entry',
            'email': s.email or '',
            'ref': s.ref,
            'form_label': label,
            'status': s.status,
            'status_label': STATUS_LABEL.get(s.status, s.status),
            'email_status': s.email_status,
            'email_label': EMAIL_LABEL.get(s.email_status, s.email_status),
            'when_full': fmt_dt(s.created_at, full=True),
            'guardian_invited': s.id in invited_sub_ids,
            'guardian_active': s.id in active_sub_ids,
            'answers': answers,
            'restricted': restricted,
        })
    subs_json = json.dumps(jsubs, ensure_ascii=False).replace('</', '<\\/')
    rows_html = '\n'.join(rows)

    # ---- fixtures ----
    fcards = []
    for f in fixes:
        comp = f.competition or 'Friendly'
        side = 'Home fixture' if f.home_away == 'home' else 'Away fixture'
        pub = f.is_published
        cls = '' if pub else ' fx-draft'
        tog = (f'<button class="fx-toggle on" data-fid="{f.id}" title="Click to unpublish">'
               f'{EYE_HIDE}{EYE_SHOW}<span class="fx-t-label">Published</span></button>' if pub else
               f'<button class="fx-toggle off" data-fid="{f.id}" title="Click to publish">'
               f'{EYE_HIDE}{EYE_SHOW}<span class="fx-t-label">Draft</span></button>')
        fcards.append(
            f'<article class="card fx-card{cls}" data-fid="{f.id}">'
            f'<div class="fx-top"><span class="fx-comp">{esc(comp)}</span>{tog}</div>'
            f'<h3>{esc(f.team)} <em>vs</em> {esc(f.opponent)}</h3>'
            f'<div class="fx-meta">'
            f'<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2.5"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>{fmt_day(f.date)} · {esc(f.kickoff or "Kick-off TBC")}</span>'
            f'<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 0 1 16 0z"/><circle cx="12" cy="10" r="2.6"/></svg>{esc(f.venue or "Venue TBC")}</span>'
            f'<span><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17L17 7M9 7h8v8"/></svg>{side}</span>'
            f'</div></article>')
    fx_cards_html = '\n'.join(fcards)

    minis = []
    for f in fixes:
        if not f.is_published:
            continue
        short = str(f.team).replace('Sporting Pearls', 'SP')
        dtxt = f"{f.date.day} {f.date.strftime('%b').upper()} · {f.kickoff or 'TBC'}"
        minis.append(
            '                <div class="mb-fx"><b>' + esc(short) + ' v ' + esc(f.opponent) + '</b>'
            f'<span class="mb-venue">{esc(f.venue or "Venue TBC")}</span>'
            f'<span class="mb-date">{esc(dtxt)}</span></div>')
    if len(fixes) > len(minis):
        minis.append('                <div style="font-size:12.5px;color:#8a94a6;margin-top:9px">'
                     '+ 1 more fixture waiting in draft — publish it when ready.</div>')
    fx_mini_html = '\n'.join(minis)

    # ---- players ----
    squad_label = {s.code: CODE_DISPLAY.get(s.code, s.code) for s in squads}
    pub_players = sum(1 for p in players if p.is_published)

    chips = []
    for s in squads:
        n = sum(1 for p in players if p.squad_id == s.id)
        chips.append(
            f'<button class="chip pchip" data-pf="{esc(s.code)}">'
            f'{esc(squad_label[s.code])} <span class="cn">{n}</span></button>')
    chips_html = '\n'.join('          ' + c for c in chips)

    cards = []
    for p in players:
        cards.append(player_card(p, p.squad.code))
    cards_html = '\n'.join(cards)

    # ---- technical team (rev 28: coach management from the portal) ----
    coaches = list(Coach.objects.select_related('squad').order_by('sort', 'name'))
    coach_cards_html = '\n'.join(coach_card(c) for c in coaches)
    coach_grid_style = '' if coaches else 'display:none'
    coach_empty_style = 'display:none' if coaches else ''
    squad_opts = ('<option value="">Academy-wide (no squad)</option>'
                  + ''.join(f'<option value="{esc(s.code)}">{esc(s.label)}</option>'
                            for s in squads))

    # ---- assemble ----
    css = (ASSETS / 'styles.css').read_text(encoding='utf-8')
    body = ((ASSETS / 'body-a.html').read_text(encoding='utf-8')
            + (ASSETS / 'body-b.html').read_text(encoding='utf-8'))

    tokens = {
        '__CSS__': css,
        '__TODAY_LONG__': now.strftime('%a %-d %b').replace(' 0', ' '),
        '__GEN_DATE__': gen_date,
        '__CSRF__': get_token(request),
        '__USER_NAME__': esc(request.user.get_username()),
        '__DSO_NAV__': (
            '<a class="nav-item" href="/portal/dso/" style="color:#c86a5a">'
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7'
            'c0 6 8 10 8 10z"/></svg>Safeguarding desk</a>'
            if is_dso(request.user) else ''),
        '__CN_ALL__': str(total),
        '__CN_NEW__': str(c_new),
        '__CN_REV__': str(c_rev),
        '__CN_ARC__': str(c_arc),
        '__CN_PEND__': str(c_pend),
        '__CN_FX__': str(len(fixes)),
        '__CN_PLAYERS__': str(len(players)),
        '__CN_DESK__': str(c_desk),
        '__PLAY_TOT__': str(len(players)),
        '__PLAY_PUB__': str(pub_players),
        '__TOTAL__': str(total),
        '__NEW__': str(c_new),
        '__SENT__': str(c_sent),
        '__FORMS__': str(forms),
        '__FX_PUB__': str(fx_pub),
        '__DONUT__': donut,
        '__LEG_NEW__': str(c_new),
        '__LEG_REV__': str(c_rev),
        '__LEG_ARC__': str(c_arc),
        '__BARS__': bars_html,
        '__ACTIVITY__': activity_html,
        '__SUBS_ROWS__': rows_html,
        '__SUBS_JSON__': subs_json,
        '__PLAYERS_JSON__': json.dumps(
            [_player_payload(p) for p in players], ensure_ascii=False).replace('</', '<\\/'),
        '__FX_CARDS__': fx_cards_html,
        '__FX_MINI__': fx_mini_html,
        '__PLAYER_CHIPS__': chips_html,
        '__PLAYER_CARDS__': cards_html,
        '__CN_COACHES__': str(len(coaches)),
        '__COACH_CARDS__': coach_cards_html,
        '__COACH_GRID_STYLE__': coach_grid_style,
        '__COACH_EMPTY_STYLE__': coach_empty_style,
        '__COACH_SQUAD_OPTS__': squad_opts,
        '__COACHES_JSON__': json.dumps(
            [_coach_payload(c) for c in coaches], ensure_ascii=False).replace('</', '<\\/'),
    }
    for k, v in tokens.items():
        body = body.replace(k, v)

    leftovers = re.findall(r'__[A-Z][A-Z_]+__', body)
    if leftovers:
        raise RuntimeError(f'UNREPLACED PORTAL TOKENS: {sorted(set(leftovers))}')
    return body


# ── views ───────────────────────────────────────────────────────────────

def _staff(view):
    """Wrap a view: anonymous users go to the branded login; non-staff too.
    Signed-in parents are bounced to their own portal (403 on actions) —
    parent accounts can never touch staff endpoints."""
    def inner(request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_staff \
                and hasattr(request.user, 'guardian_profile'):
            if request.method == 'POST':
                return JsonResponse({'ok': False, 'error': 'Staff access required.'},
                                    status=403)
            from django.shortcuts import redirect
            return redirect('/portal/parents/')
        if not request.user.is_authenticated or not request.user.is_staff:
            from django.shortcuts import redirect
            nxt = request.get_full_path() if request.method == 'GET' else '/portal/'
            return redirect(f'/portal/login/?next={nxt}')
        return view(request, *args, **kwargs)
    return inner


@ensure_csrf_cookie
def portal_login(request):
    if request.user.is_authenticated and request.user.is_staff:
        return _safe_redirect(request, '/portal/')
    error = ''
    disabled = ''
    nxt = request.GET.get('next') or request.POST.get('next') or '/portal/'
    if request.method == 'POST':
        if _staff_throttled(request):
            error = 'Too many attempts — please wait 15 minutes and try again.'
            disabled = 'disabled'
            import logging
            logging.getLogger('sporting.auth').warning(
                'staff login throttle tripped ip=%s', _client_ip(request))
            return HttpResponse(login_page(request, error, nxt, disabled),
                                status=429)
        user = authenticate(request, username=request.POST.get('username', ''),
                            password=request.POST.get('password', ''))
        if user is not None:
            if not user.is_staff:
                error = 'Wrong username or password — please try again.'
                _staff_login_failed(request)
            else:
                auth_login(request, user)
                return _safe_redirect(request, nxt)
        else:
            burn_password_time()      # equalise timing for unknown usernames
            error = 'Wrong username or password — please try again.'
            _staff_login_failed(request)
    page = login_page(request, error, nxt, disabled)
    return HttpResponse(page)


def _safe_redirect(request, fallback):
    from django.shortcuts import redirect
    nxt = request.POST.get('next') or request.GET.get('next') or fallback
    if not nxt.startswith('/') or nxt.startswith('//'):
        nxt = fallback
    return redirect(nxt)


def login_page(request, error='', nxt='/portal/', disabled=''):
    token = get_token(request)
    err_html = f'<div class="lg-err">{esc(error)}</div>' if error else ''
    site = getattr(settings, 'SITE_URL', '')
    guide = (f'<a href="{site}/portal-guide.html" target="_blank" rel="noopener" '
             f'style="color:#5c6a7e;font-weight:700">New here? Read the user guide →</a><br>') if site else ''
    return ((ASSETS / 'login.html').read_text(encoding='utf-8')
            .replace('__CSRF__', token)
            .replace('__ERROR__', err_html)
            .replace('__NEXT__', esc(nxt))
            .replace('__GUIDE__', guide)
            .replace('__DISABLED__', disabled))


@require_POST
def portal_logout(request):
    auth_logout(request)
    from django.shortcuts import redirect
    return redirect('/portal/login/')


@ensure_csrf_cookie
@_staff
def portal_home(request):
    return HttpResponse(build_page(request))


# ── player actions (all POST, staff-only, CSRF protected) ───────────────

def _bad(msg):
    return JsonResponse({'ok': False, 'error': msg}, status=400)


def _get_player(pid):
    try:
        return Player.objects.select_related('squad').get(id=pid)
    except (Player.DoesNotExist, ValueError, TypeError):
        return None


def _player_payload(p):
    return {
        'id': p.id, 'ref': p.ref, 'squad': p.squad.code,
        'number': p.number, 'first_name': p.first_name, 'last_name': p.last_name,
        'position': p.position, 'position_label': POSITION_LABEL.get(p.position, ''),
        'age': p.age, 'height_m': p.height_m, 'foot': p.foot, 'motto': p.motto,
        'is_captain': p.is_captain, 'is_published': p.is_published,
        'pitch_order': p.pitch_order,
        'photo': photo_src(p),
    }


def _clean_fields(data, p=None):
    """Validate shared edit/add fields. Returns (updates dict, error str)."""
    upd = {}
    if 'first_name' in data:
        v = str(data['first_name']).strip()
        if not v or len(v) > 60:
            return None, 'First name is required (max 60 characters).'
        upd['first_name'] = v
    if 'last_name' in data:
        v = str(data['last_name']).strip()
        if not v or len(v) > 60:
            return None, 'Last name is required (max 60 characters).'
        upd['last_name'] = v
    if 'number' in data:
        v = data['number']
        if v in (None, ''):
            upd['number'] = None
        else:
            try:
                v = int(v)
            except (TypeError, ValueError):
                return None, 'Shirt number must be a whole number.'
            if not 0 <= v <= 99:
                return None, 'Shirt number must be between 0 and 99.'
            upd['number'] = v
    if 'position' in data:
        v = str(data['position'] or '').strip().upper()
        if v and v not in POS_CODES:
            return None, 'Unknown position code.'
        upd['position'] = v
    if 'age' in data:
        v = data['age']
        if v in (None, ''):
            upd['age'] = None
        else:
            try:
                v = int(v)
            except (TypeError, ValueError):
                return None, 'Age must be a whole number.'
            if not 4 <= v <= 60:
                return None, 'Age must be between 4 and 60.'
            upd['age'] = v
    if 'height_m' in data:
        v = str(data['height_m'] or '').strip()
        if v and not re.fullmatch(r'[0-2]\.[0-9]{1,2}', v):
            return None, 'Height should look like 1.68 (metres).'
        upd['height_m'] = v
    if 'foot' in data:
        v = str(data['foot'] or '').strip().upper()
        if v and v not in ('R', 'L'):
            return None, 'Foot must be R or L.'
        upd['foot'] = v
    if 'motto' in data:
        upd['motto'] = str(data['motto'] or '').strip()[:300]
    if 'is_captain' in data:
        upd['is_captain'] = bool(data['is_captain']) and str(data['is_captain']) not in ('0', 'false')
    if 'is_published' in data:
        upd['is_published'] = bool(data['is_published']) and str(data['is_published']) not in ('0', 'false')
    return upd, None


@require_POST
@_staff
def player_toggle(request, pid):
    p = _get_player(pid)
    if not p:
        return _bad('Player not found.')
    p.is_published = not p.is_published
    p.save(update_fields=['is_published', 'updated_at'])
    return JsonResponse({'ok': True, 'published': p.is_published,
                         'live': Player.objects.filter(is_published=True).count()})


@require_POST
@_staff
def player_delete(request, pid):
    p = _get_player(pid)
    if not p:
        return _bad('Player not found.')
    ref = p.ref
    squad = p.squad.code
    p.delete()
    return JsonResponse({'ok': True, 'ref': ref, 'squad': squad,
                         'total': Player.objects.count()})


@require_POST
@_staff
def player_edit(request, pid):
    import json as _json
    p = _get_player(pid)
    if not p:
        return _bad('Player not found.')
    try:
        data = _json.loads(request.body or '{}')
    except ValueError:
        return _bad('Bad request body.')
    if data.get('is_captain'):
        Player.objects.filter(squad=p.squad_id, is_captain=True).exclude(id=p.id) \
            .update(is_captain=False)
    upd, err = _clean_fields(data)
    if err:
        return _bad(err)
    for k, v in upd.items():
        setattr(p, k, v)
    p.save()
    return JsonResponse({'ok': True, 'player': _player_payload(p)})


@require_POST
@_staff
def player_photo(request, pid):
    """Upload a squad photo — Phase 2 hardened.

    Beyond the legacy name/size checks the file is now fully decoded
    with Pillow (catches renamed non-images and truncated files), the
    stored extension always matches the REAL format, and the image is
    re-encoded on save so EXIF metadata — including GPS coordinates,
    which have no business leaking from a children's academy — is
    stripped. Decompression bombs are rejected by the pixel cap.
    """
    p = _get_player(pid)
    if not p:
        return _bad('Player not found.')
    f = request.FILES.get('file')
    if not f:
        return _bad('Choose a photo file first.')
    if f.size > 8 * 1024 * 1024:
        return _bad('Photo is larger than 8 MB — please resize it first.')
    ext = Path(f.name).suffix.lower()
    if ext not in ('.jpg', '.jpeg', '.png', '.webp'):
        return _bad('Photos must be JPG, PNG or WebP.')

    import io
    from django.core.files.base import ContentFile
    from PIL import Image

    raw = f.read()
    try:
        img = Image.open(io.BytesIO(raw))
        img.verify()                     # pass 1: structural integrity
        img = Image.open(io.BytesIO(raw))
        # header-only checks before the expensive full decode
        if (img.width or 0) * (img.height or 0) > 40_000_000:
            return _bad('That image is too large to process — please resize it first.')
        img.load()                       # pass 2: full decode (truncation)
    except Exception:
        return _bad('That file is not a readable image — it may be damaged '
                    'or not really a photo.')
    fmt = (img.format or '').upper()
    if fmt not in ('JPEG', 'PNG', 'WEBP'):
        return _bad('Photos must be JPG, PNG or WebP.')

    # Re-encode clean copies: metadata (EXIF/GPS/ICC) never lands in
    # /media/ and the extension always matches the real format.
    buf = io.BytesIO()
    if fmt == 'JPEG':
        img.convert('RGB').save(buf, 'JPEG', quality=85)
        ext = '.jpg'
    elif fmt == 'PNG':
        img.save(buf, 'PNG')
        ext = '.png'
    else:
        img.save(buf, 'WEBP', quality=85)
        ext = '.webp'

    name = f'{p.squad.code}-{p.ref}-{get_valid_filename(Path(f.name).stem)}{ext}'
    try:
        p.photo.save(name, ContentFile(buf.getvalue()), save=True)
    except Exception:
        return _bad('That file could not be stored as an image.')
    return JsonResponse({'ok': True, 'photo': photo_src(p), 'player': _player_payload(p)})


@require_POST
@_staff
def player_add(request):
    import json as _json
    try:
        data = _json.loads(request.body or '{}')
    except ValueError:
        return _bad('Bad request body.')
    code = str(data.get('squad') or '').strip().upper()
    squad = Squad.objects.filter(code=code).first()
    if not squad:
        return _bad('Choose a squad.')
    if not str(data.get('first_name') or '').strip() or not str(data.get('last_name') or '').strip():
        return _bad('First and last name are required.')
    upd, err = _clean_fields(data)
    if err:
        return _bad(err)
    # next free REF code in the squad: CODE-NN
    existing = {q.ref for q in Player.objects.filter(squad=squad)}
    n = 1
    while f'{squad.code}-{n:02d}' in existing:
        n += 1
    ref = f'{squad.code}-{n:02d}'
    p = Player(squad=squad, ref=ref, pitch_order=data.get('pitch_order') or 12,
               is_published=False)
    for k, v in upd.items():
        setattr(p, k, v)
    p.save()
    return JsonResponse({'ok': True, 'player': _player_payload(p),
                         'total': Player.objects.count()})


def _coach_payload(c):
    return {
        'id': c.id,
        'name': c.name,
        'role': c.role,
        'squad': c.squad.code if c.squad else '',
        'squad_label': c.squad.label if c.squad else '',
        'bio': c.bio,
        'photo': coach_photo_src(c),
        'published': c.is_published,
        'sort': c.sort,
    }


def _clean_coach_fields(data):
    """Validate the coach fields the portal may set (rev 28)."""
    name = str(data.get('name') or '').strip()
    role = str(data.get('role') or '').strip()
    if not (1 <= len(name) <= 120):
        return None, 'Name is required (max 120 characters).'
    if not (1 <= len(role) <= 120):
        return None, 'Role is required (max 120 characters).'
    bio = str(data.get('bio') or '').strip()
    if len(bio) > 600:
        return None, 'Bio is limited to 600 characters.'
    try:
        sort = int(data.get('sort') or 0)
    except (TypeError, ValueError):
        sort = 0
    if not (0 <= sort <= 99):
        return None, 'Display order must be between 0 and 99.'
    code = str(data.get('squad') or '').strip().upper()
    squad = Squad.objects.filter(code=code).first() if code else None
    if code and not squad:
        return None, 'Unknown squad.'
    return {'name': name, 'role': role, 'bio': bio, 'sort': sort,
            'squad': squad}, None


@require_POST
@_staff
def coach_toggle(request, cid):
    c = Coach.objects.filter(pk=cid).first()
    if not c:
        return _bad('Coach not found.')
    c.is_published = not c.is_published
    c.save(update_fields=['is_published', 'updated_at'])
    return JsonResponse({'ok': True, 'published': c.is_published,
                         'live': Coach.objects.filter(is_published=True).count()})


@require_POST
@_staff
def coach_delete(request, cid):
    c = Coach.objects.filter(pk=cid).first()
    if not c:
        return _bad('Coach not found.')
    name = c.name
    if c.photo:
        c.photo.delete(save=False)
    c.delete()
    return JsonResponse({'ok': True, 'name': name,
                         'total': Coach.objects.count()})


@require_POST
@_staff
def coach_edit(request, cid):
    c = Coach.objects.filter(pk=cid).first()
    if not c:
        return _bad('Coach not found.')
    try:
        data = json.loads(request.body or '{}')
    except ValueError:
        return _bad('Bad request body.')
    upd, err = _clean_coach_fields(data)
    if err:
        return _bad(err)
    for k, v in upd.items():
        setattr(c, k, v)
    if 'is_published' in data:
        c.is_published = bool(data.get('is_published'))
    c.save()
    return JsonResponse({'ok': True, 'coach': _coach_payload(c)})


@require_POST
@_staff
def coach_add(request):
    try:
        data = json.loads(request.body or '{}')
    except ValueError:
        return _bad('Bad request body.')
    upd, err = _clean_coach_fields(data)
    if err:
        return _bad(err)
    c = Coach(is_published=bool(data.get('is_published')), **upd)
    c.save()
    return JsonResponse({'ok': True, 'coach': _coach_payload(c),
                         'total': Coach.objects.count()})


@require_POST
@_staff
def coach_photo(request, cid):
    """Upload a coach photo (rev 28).

    CoachPhotoStorage re-encodes every save path — EXIF/GPS stripped,
    extension matched to the real format, decompression bombs capped —
    so this view only pre-checks size/extension and turns storage
    failures into a friendly toast instead of a 500.
    """
    c = Coach.objects.filter(pk=cid).first()
    if not c:
        return _bad('Coach not found.')
    f = request.FILES.get('file')
    if not f:
        return _bad('Choose a photo file first.')
    if f.size > 8 * 1024 * 1024:
        return _bad('Photo is larger than 8 MB — please resize it first.')
    if Path(f.name).suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
        return _bad('Photos must be JPG, PNG or WebP.')
    name = f'coach-{get_valid_filename(Path(f.name).stem)}'
    try:
        if c.photo:
            c.photo.delete(save=False)
        c.photo.save(name, f, save=True)
    except ValueError:
        return _bad('That file is not a readable image — it may be damaged '
                    'or not really a photo.')
    except Exception:
        return _bad('That file could not be stored as an image.')
    return JsonResponse({'ok': True, 'photo': coach_photo_src(c),
                         'coach': _coach_payload(c)})


@require_POST
@_staff
def submission_status(request, ref):
    from django.db.models import Count
    from django.shortcuts import get_object_or_404
    status = request.POST.get('status', '')
    if status not in ('new', 'reviewed', 'archived'):
        return _bad('Unknown status.')
    s = get_object_or_404(FormSubmission, ref=ref)
    s.status = status
    s.save(update_fields=['status'])
    tally = dict(FormSubmission.objects.values_list('status')
                 .annotate(n=Count('id')).order_by())
    return JsonResponse({'ok': True, 'ref': s.ref, 'status': s.status, 'tally': tally})


@require_POST
@_staff
def submission_invite(request, ref):
    """Approve & invite guardian — creates the invite and emails the
    one-time activation link (72 h). JSON body:
    {guardian_name, email, phone, relation, player_id: int|'new'|'',
     child_name, new_squad, new_age}"""
    import json as _json
    from parents.services import (EMAIL_RE, create_and_send_invite,
                                  create_player_from_application, find_child,
                                  prefill_from_submission)
    from submissions.models import Squad
    s = FormSubmission.objects.filter(ref=ref).first()
    if not s:
        return _bad('Submission not found.')
    try:
        data = _json.loads(request.body or '{}')
    except ValueError:
        return _bad('Bad request body.')
    pf = prefill_from_submission(s)

    guardian_name = str(data.get('guardian_name') or pf['guardian_name'] or '').strip()
    email = str(data.get('email') or '').strip()
    relation = str(data.get('relation') or 'Guardian').strip()
    child_name = str(data.get('child_name') or pf['child_name'] or '').strip()
    if not guardian_name:
        return _bad('Guardian name is required.')
    if not EMAIL_RE.fullmatch(email):
        return _bad('That email address does not look right.')

    player = None
    if data.get('player_id') == 'new':
        code = str(data.get('new_squad') or pf['squad_hint'] or '').strip().upper()
        squad = Squad.objects.filter(code=code).first()
        if not squad:
            return _bad('Choose a squad for the new player profile.')
        age = data.get('new_age') or pf['age'] or None
        player = create_player_from_application(child_name or guardian_name, squad,
                                                age=age)
    elif data.get('player_id') not in (None, '', 'none', 'null'):
        player = _get_player(data.get('player_id'))
        if player is None:
            return _bad('That player profile could not be found.')
    else:
        player = find_child(child_name, pf['squad_hint'])

    invite, ok, detail = create_and_send_invite(
        guardian_name=guardian_name, email=email, relation=relation,
        player=player, invited_by=request.user, submission=s, request=request)
    if invite is None:
        return _bad(detail)
    if not ok and not getattr(invite, 'invite_url', None):
        # refused — an active invite already exists for this email
        return JsonResponse({'ok': False, 'error': detail,
                             'link': getattr(invite, 'invite_url', '')}, status=409)
    return JsonResponse({
        'ok': True,
        'sent': ok,
        'detail': detail,
        'child': f'{player.first_name} {player.last_name}' if player else '',
        'player_id': player.id if player else None,
        'expires': timezone.localtime(invite.expires_at).strftime('%d %b %Y %H:%M'),
        'link': getattr(invite, 'invite_url', ''),
        'email_status': invite.email_status,
    })


@require_POST
@_staff
def fixture_toggle(request, fid):
    from django.shortcuts import get_object_or_404
    f = get_object_or_404(Fixture, id=fid)
    f.is_published = not f.is_published
    f.save(update_fields=['is_published'])
    return JsonResponse({'ok': True, 'published': f.is_published,
                         'live': Fixture.objects.filter(is_published=True).count()})


# ── Phase 5: CSP-tight dashboard asset + authenticated /media/ gate ────

# The only portal assets ever served by URL (dash.js was an inline
# <script> block in body-b.html until the Phase 5 CSP refactor;
# img-fallback.js replaces the inline onerror= photo fallbacks).
# Access: 'staff' = any staff account; 'auth' = any signed-in user
# (guardians load img-fallback.js on their child cards too).
PORTAL_ASSET_FILES = {
    'dash.js': ('application/javascript', 'staff'),
    'img-fallback.js': ('application/javascript', 'auth'),
    'qr.js': ('application/javascript', 'auth'),
}


def portal_asset(request, name):
    """Serve an externalised portal script.

    Locked to a fixed allow-list (no traversal: a bare name, no slashes,
    must exist in PORTAL_ASSET_FILES) with a per-asset access rule —
    dash.js is staff-only, img-fallback.js is available to any
    signed-in user (guardians' child-card pages reference it).
    """
    from django.http import Http404
    entry = PORTAL_ASSET_FILES.get(name)
    if entry is None:
        raise Http404('no such asset')
    ctype, access = entry
    if not request.user.is_authenticated:
        raise Http404('no such asset')
    if access == 'staff' and not request.user.is_staff:
        raise Http404('no such asset')
    resp = HttpResponse((ASSETS / name).read_text(encoding='utf-8'),
                        content_type=ctype)
    resp['Cache-Control'] = 'private, max-age=86400'
    return resp


def media_serve(request, path):
    """Authenticated gate in front of /media/ (Phase 5, R17).

    Before Phase 5 every /media/ URL was fetchable unauthenticated — an
    unpublished player's photo was one guessable path away. Policy now:

      * photos of PUBLISHED players stay public — the public squad pages
        embed them by design (media-consented, is_published=True);
      * photos of PUBLISHED coaches stay public — the technical-team
        section embeds them by design (adult staff, is_published=True);
      * PUBLISHED Féminin gallery photos stay public — the 'On the
        Pitch' section renders them by design (rev 25, is_published=True);
      * every other file requires a signed-in user: staff manage all
        players; guardians may fetch only their own children's files;
      * missing, forbidden and traversal paths all return the same plain
        404 — no existence oracle, nothing revealed.
    """
    import mimetypes
    import posixpath
    from django.http import FileResponse, Http404

    clean = posixpath.normpath(path)
    if (clean in ('', '.') or clean.startswith('..') or clean.startswith('/')
            or '\\' in path):
        raise Http404
    root = Path(settings.MEDIA_ROOT).resolve()
    fpath = (root / clean)
    try:
        fpath.resolve().relative_to(root)
    except ValueError:
        raise Http404
    if not fpath.is_file():
        raise Http404

    published = False
    if clean.startswith('players/'):
        published = Player.objects.filter(
            photo=clean, is_published=True).exists()
    elif clean.startswith('coaches/'):
        published = Coach.objects.filter(
            photo=clean, is_published=True).exists()
    elif clean.startswith('gallery/feminin/'):
        # Féminin 'On the Pitch' photos (rev 25): public only while the
        # photo row is published — the section appears on the site solely
        # through real, admin-uploaded images.
        published = FemininGalleryPhoto.objects.filter(
            photo=clean, is_published=True).exists()

    if not published:
        u = request.user
        allowed = False
        if u.is_authenticated:
            if u.is_staff or u.is_superuser:
                allowed = True
            elif hasattr(u, 'guardian_profile'):
                from parents.models import GuardianPlayer
                allowed = GuardianPlayer.objects.filter(
                    guardian__user=u, player__photo=clean).exists()
        if not allowed:
            raise Http404

    ctype = mimetypes.guess_type(clean)[0] or 'application/octet-stream'
    resp = FileResponse(fpath.open('rb'), content_type=ctype)
    if published:
        resp['Cache-Control'] = 'public, max-age=3600'
    else:
        resp['Cache-Control'] = 'private, max-age=3600'
    return resp
