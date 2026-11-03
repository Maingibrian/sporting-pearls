"""Parent Portal views — /portal/parents/… — same brand, zero Django chrome.

Role separation: these views only open for authenticated users carrying a
`guardian_profile` that is still active. Staff are bounced to their own
portal; everyone else to the branded parent login.
"""
import functools
import pathlib
import re

from django.conf import settings
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from submissions.models import Fixture, POSITIONS
from submissions.portal import CODE_DISPLAY, photo_src
from submissions.portal_auth import burn_password_time
from submissions.email_branding import (complaint_alert_payload,
                                        complaint_received_payload)

from .models import (Announcement, AnnouncementRead, COMPLAINT_CATEGORIES,
                     COMPLAINT_STATUS, Complaint, ComplaintReply, Guardian,
                     ParentInvite, RELATION_CHOICES)

ASSETS = pathlib.Path(__file__).resolve().parent / 'parent_assets'

LOGIN_RATE_LIMIT = 8          # failed attempts per window
LOGIN_WINDOW_SECONDS = 900    # 15 minutes


# ── page rendering (same replace-token pattern as the staff portal) ─────

def _render(asset, tokens):
    body = (ASSETS / asset).read_text(encoding='utf-8')
    # portal-guide link on the sign-in page (hidden when SITE_URL unset)
    site = getattr(settings, 'SITE_URL', '')
    guide = (f'<a href="{site}/portal-guide.html" target="_blank" rel="noopener" '
             f'style="color:#5c6a7e;font-weight:700">New here? Read the parent guide →</a> · ') if site else ''
    tokens = {**tokens, '__GUIDE__': guide}
    for k, v in tokens.items():
        body = body.replace(k, v)
    leftovers = re.findall(r'__[A-Z][A-Z_]+__', body)
    if leftovers:
        raise RuntimeError(f'UNREPLACED PARENT TOKENS: {sorted(set(leftovers))}')
    return body


def _err(html):
    return f'<div class="lg-err">{html}</div>' if html else ''


def _esc(s):
    import html
    return html.escape(str(s), quote=True)


# ── guards ──────────────────────────────────────────────────────────────

def parent_required(view):
    @functools.wraps(view)
    def inner(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/portal/parents/login/')
        gp = getattr(request.user, 'guardian_profile', None)
        if gp is None:
            return redirect('/portal/' if request.user.is_staff
                            else '/portal/parents/login/')
        if not gp.is_active:
            return _paused_page(request, gp)
        return view(request, *args, **kwargs)
    return inner


def _throttled(request):
    """8 failed parent logins per 15 min per IP → 429 branded page."""
    ip = (request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
          or request.META.get('REMOTE_ADDR', ''))
    key = f'sp-plg:{ip}'
    try:
        if cache.get(key) is None:
            cache.add(key, 0, LOGIN_WINDOW_SECONDS)
        n = cache.get(key, 0)
    except ValueError:
        n = 0
    return n >= LOGIN_RATE_LIMIT


def _record_failure(request):
    ip = (request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
          or request.META.get('REMOTE_ADDR', ''))
    key = f'sp-plg:{ip}'
    try:
        cache.incr(key)
    except ValueError:
        pass


# ── login ───────────────────────────────────────────────────────────────

@ensure_csrf_cookie
def parents_login(request):
    if request.user.is_authenticated:
        gp = getattr(request.user, 'guardian_profile', None)
        if gp and gp.is_active:
            return redirect('/portal/parents/')
        if request.user.is_staff:
            return redirect('/portal/')
    error = ''
    if request.method == 'POST':
        if _throttled(request):
            return HttpResponse(_render('login.html', {
                '__CSRF__': get_token(request), '__ERROR__': _err(_esc(
                    'Too many attempts — please wait 15 minutes and try again.')),
                '__EMAIL__': '', '__DISABLED__': 'disabled',
            }), status=429)
        user = authenticate(request, username=(request.POST.get('username') or '').strip().lower(),
                            password=request.POST.get('password', ''))
        gp = getattr(user, 'guardian_profile', None) if user else None
        if user is None:
            burn_password_time()      # equalise timing for unknown emails
            error = 'Wrong email or password — please try again.'
            _record_failure(request)
        elif gp is None:
            # valid credentials but not a guardian account — same message,
            # so the parent login can never be used to test staff logins
            error = 'Wrong email or password — please try again.'
            _record_failure(request)
        elif not gp.is_active:
            error = ('This account is currently paused. Please contact the '
                     'academy office at info@sportingpearlsacademy.org.')
            _record_failure(request)
        else:
            auth_login(request, user)
            return redirect('/portal/parents/')
    return HttpResponse(_render('login.html', {
        '__CSRF__': get_token(request), '__ERROR__': _err(_esc(error)),
        '__EMAIL__': _esc(request.POST.get('username', '')),
        '__DISABLED__': '',
    }))


def _next_fixture(squad, today):
    """The next published fixture that names this squad, or None."""
    pub = Fixture.objects.filter(is_published=True, date__gte=today)
    for f in pub:
        hay = f'{f.team}'.lower()
        if squad.code.lower() in hay or CODE_DISPLAY.get(squad.code, squad.code).lower() in hay \
                or squad.label.lower() in hay:
            return f
    return None


def _fx_html(fx):
    if fx is None:
        return ('<b>Next fixture to be announced</b>'
                '<span>The coach will publish it soon.</span>')
    return (f'<b>{_esc(fx.team)} v {_esc(fx.opponent)}</b>'
            f'<span>{fx.date:%a %d %b}'
            + (f' · {_esc(fx.kickoff)}' if fx.kickoff else '')
            + (f' · {_esc(fx.venue)}' if fx.venue else '') + '</span>')


def _squad_text(squad):
    disp = CODE_DISPLAY.get(squad.code, squad.code)
    lbl = squad.label
    return lbl if disp.lower() in lbl.lower() else f'{disp} · {lbl}'


def _ava(p):
    mono = ((p.first_name[:1] + p.last_name[:1]).upper() if p.first_name
            and p.last_name else 'SP')
    src = photo_src(p)
    if src:
        return (f'<img src="{_esc(src)}" alt="" '
                f'data-fb-hide="reveal-next">'
                f'<div class="ava" style="display:none">{_esc(mono)}</div>')
    return f'<div class="ava">{_esc(mono)}</div>'


# ── P2: announcements visibility (empty squads = everyone) ─────────────

def _visible_qs(gp):
    squad_ids = list(gp.links.values_list('player__squad_id', flat=True))
    return (Announcement.objects.filter(is_published=True)
            .filter(Q(squads__isnull=True) | Q(squads__id__in=squad_ids))
            .distinct())


def _unread(gp):
    return _visible_qs(gp).exclude(reads__guardian=gp).count()


@ensure_csrf_cookie
def parents_home(request):
    """P2 dashboard: stat tiles, announcement preview, child cards."""
    gp = getattr(request.user, 'guardian_profile', None) \
        if request.user.is_authenticated else None
    if gp is None or not gp.is_active:
        if request.user.is_authenticated and request.user.is_staff:
            return redirect('/portal/')
        return redirect('/portal/parents/login/')

    now = timezone.localtime(timezone.now())
    links = list(gp.links.select_related('player', 'player__squad')
                 .order_by('player__squad__sort', 'player__ref'))

    cards = []
    nearest = None
    for ln in links:
        p = ln.player
        fx = _next_fixture(p.squad, now.date())
        if fx and (nearest is None or fx.date < nearest.date):
            nearest = fx
        # shirt number is optional on the model — never format None
        num_html = (f'<span class="kd-num">#{p.number:02d}</span>'
                    if p.number is not None else '')
        cards.append(
            f'<a class="kd-link" href="/portal/parents/child/{p.id}/">'
            f'<article class="kd-card">'
            f'<div class="kd-photo">{_ava(p)}{num_html}</div>'
            f'<div class="kd-body"><h3>{_esc(p.first_name)} {_esc(p.last_name)}</h3>'
            f'<div class="kd-squad"><span class="dot" style="background:{_esc(p.squad.accent)}"></span>'
            f'{_esc(_squad_text(p.squad))}</div>'
            f'<div class="kd-fx">{_fx_html(fx)}</div>'
            f'<span class="kd-more">Open profile →</span></div></article></a>')
    if not cards:
        cards.append('<article class="kd-card"><div class="kd-body">'
                     '<h3>No child linked yet</h3><div class="kd-squad">The office '
                     'is matching your application — check back shortly.</div></div></article>')

    unread = _unread(gp)
    prev = []
    for a in _visible_qs(gp)[:2]:
        seen = a.reads.filter(guardian=gp).exists()
        excerpt = a.body[:132].strip() + ('…' if len(a.body) > 132 else '')
        prev.append(
            f'<a class="pv-row{" pv-un" if not seen else ""}" '
            f'href="/portal/parents/announcements/{a.id}/">'
            f'<span class="pv-dot" aria-hidden="true"></span>'
            f'<span class="pv-body"><b>{_esc(a.title)}</b>'
            f'<span>{_esc(excerpt)}</span></span>'
            f'<span class="pv-date">{(a.published_at or a.created_at):%d %b}</span></a>')
    if not prev:
        prev.append('<div class="pv-row pv-none"><span class="pv-body">'
                    '<b>No announcements yet</b><span>Notices from the academy '
                    'will appear here.</span></span></div>')

    kickoff = (f'{nearest.date:%a %d %b}'
               + (f' · {_esc(nearest.kickoff)}' if nearest.kickoff else '')) \
        if nearest else 'To be announced'

    # P3: welfare desk tile — cases still needing attention
    open_cases = gp.complaints.exclude(status__in=('closed', 'resolved')).count()
    cases_sub = ('open at the welfare desk' if open_cases
                 else 'all quiet — nothing open')

    tokens = {
        '__CSRF__': get_token(request),
        '__GUARDIAN__': _esc(gp.full_name),
        '__RELATION__': _esc(gp.get_relation_display()),
        '__CHILD_CARDS__': '\n'.join(cards),
        '__N_CHILDREN__': str(len(links)),
        '__PLURAL__': 'ren' if len(links) != 1 else '',
        '__TODAY__': now.strftime('%A %d %B %Y'),
        '__UNREAD_N__': str(unread),
        '__NEXT_KICKOFF__': kickoff,
        '__PREVIEW__': '\n'.join(prev),
        '__CASES_N__': str(open_cases),
        '__CASES_SUB__': _esc(cases_sub),
    }
    tokens.update(_chrome(request, gp, 'home'))
    return HttpResponse(_render('home.html', tokens))


@require_POST
def parents_logout(request):
    auth_logout(request)
    return redirect('/portal/parents/login/')


# ── activation (one-time emailed link) ──────────────────────────────────

def _invite_state(invite):
    if invite.is_accepted:
        return 'accepted'
    if invite.is_expired:
        return 'expired'
    return 'ok'


ICON_OK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
           'stroke-linecap="round" stroke-linejoin="round" style="width:26px;height:26px">'
           '<path d="M20 6L9 17l-5-5"/></svg>')
ICON_CLOCK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round" stroke-linejoin="round" style="width:26px;height:26px">'
              '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>')
ICON_HELP = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
             'stroke-linecap="round" stroke-linejoin="round" style="width:26px;height:26px">'
             '<circle cx="12" cy="12" r="9"/><path d="M9.1 9a3 3 0 015.8 1c0 2-3 2.2-3 4"/><circle cx="12" cy="17.2" r=".6" fill="currentColor"/></svg>')
ICON_PAUSE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round" stroke-linejoin="round" style="width:26px;height:26px">'
              '<circle cx="12" cy="12" r="9"/><path d="M10 9v6M14 9v6"/></svg>')


def _state_block(icon, title, text, show_login=True, extra=''):
    link = ('<a href="/portal/parents/login/">Go to parent sign in</a>' if show_login else '')
    return (f'<div class="state"><div class="ico">{icon}</div>'
            f'<h2>{_esc(title)}</h2><p>{text}</p>{extra}{link}</div>')


@ensure_csrf_cookie
def parents_activate(request, token):
    invite = (ParentInvite.objects.filter(token=token)
              .select_related('player', 'player__squad').first())
    if invite is None:
        return HttpResponse(_render('activate.html', {
            '__MODE__': _state_block(
                ICON_HELP, 'We could not find this link',
                'The invitation link is not valid. Check the email you received, '
                'or ask the academy office to send a fresh invitation.'),}), status=410)
    state = _invite_state(invite)
    if state == 'accepted':
        return HttpResponse(_render('activate.html', {
            '__MODE__': _state_block(
                ICON_OK, 'Account already activated',
                f'This invitation was already used to open the account for '
                f'<b>{_esc(invite.guardian_name)}</b> ({_esc(invite.email)}). '
                f'Sign in with the password you chose.'),}), status=409)
    if state == 'expired':
        return HttpResponse(_render('activate.html', {
            '__MODE__': _state_block(
                ICON_CLOCK, 'This link has expired',
                f'Invitations stay live for 72 hours for safety. Ask the academy '
                f'office to resend it to <b>{_esc(invite.email)}</b> — it takes a moment.'),}),
            status=410)

    error = ''
    if request.method == 'POST':
        pw1 = request.POST.get('password', '')
        pw2 = request.POST.get('password2', '')
        phone = (request.POST.get('phone') or '').strip()[:40]
        relation = request.POST.get('relation') or invite.relation
        if relation not in dict(RELATION_CHOICES):
            relation = 'Guardian'
        if pw1 != pw2:
            error = 'The two passwords do not match.'
        else:
            try:
                validate_password(pw1)
            except ValidationError as e:
                error = ' '.join(e.messages)
        if not error:
            created = _accept_invite(request, invite, pw1, phone, relation)
            if created:
                return redirect('/portal/parents/')
            error = ('This email is already used by another account and the '
                     'link can no longer be activated. Contact the academy office.')
    child_line = _child_html(invite)
    mode_html = (
        '<h2>Set up your account</h2>'
        '<p class="lg-sub">One last step and your Parent Portal is ready.</p>'
        f'<div class="sum"><b>{_esc(invite.guardian_name)}</b>'
        f'<span>{_esc(invite.email)}</span></div>'
        f'{child_line}'
        f'<form method="post" action="/portal/parents/activate/{_esc(token)}/">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="' + get_token(request) + '">'
        '<div class="two">'
        '<div><label for="id-rel">I am the child&#8217;s</label>'
        f'<select id="id-rel" name="relation">{_relation_opts(invite.relation, request.POST.get("relation"))}</select></div>'
        '<div><label for="id-phone">Phone (optional)</label>'
        f'<input id="id-phone" name="phone" value="{_esc(request.POST.get("phone", ""))}" placeholder="+254 …"></div>'
        '</div>'
        '<label for="id-pw1">Choose a password</label>'
        '<input id="id-pw1" type="password" name="password" autocomplete="new-password" required minlength="8">'
        '<label for="id-pw2">Repeat the password</label>'
        '<input id="id-pw2" type="password" name="password2" autocomplete="new-password" required>'
        f'{_err(_esc(error))}'
        '<button type="submit">Open my Parent Portal</button>'
        '</form>'
        '<div class="lg-foot">By activating, you agree to receive academy '
        'communication for your child&#8217;s squad.</div>')
    return HttpResponse(_render('activate.html', {'__MODE__': mode_html}))


def _relation_opts(selected, posted=None):
    sel = posted or selected or 'Guardian'
    return '\n'.join(
        f'<option value="{_esc(v)}"{" selected" if v == sel else ""}>{_esc(v)}</option>'
        for v, _ in RELATION_CHOICES)


def _child_html(invite):
    p = invite.player
    if p is None:
        return ('<div class="kd-squad"><span class="dot"></span>Child profile to be '
                'matched by the academy office after activation.</div>')
    label = CODE_DISPLAY.get(p.squad.code, p.squad.label)
    return (f'<div class="kd-squad"><span class="dot" style="background:{_esc(p.squad.accent)}"></span>'
            f'{_esc(p.first_name)} {_esc(p.last_name)} · {_esc(label)}</div>')


def _accept_invite(request, invite, password, phone, relation):
    """Create User + Guardian + child link; log the parent in. Returns bool."""
    from django.contrib.auth import get_user_model
    from django.db import transaction
    User = get_user_model()
    email = invite.email.lower()
    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=email, email=email, password=password,
                first_name=invite.guardian_name.split()[0][:30]
                if invite.guardian_name.split() else '',
                last_name=' '.join(invite.guardian_name.split()[1:])[:150],
            )
            guardian = Guardian.objects.create(
                user=user, full_name=invite.guardian_name,
                phone=phone, relation=relation)
            if invite.player is not None:
                guardian.links.create(player=invite.player, is_primary=True)
            invite.accepted_at = timezone.now()
            invite.save(update_fields=['accepted_at'])
    except Exception:
        return False
    auth_login(request, user)
    return True


def _paused_page(request, gp):
    return HttpResponse(_render('activate.html', {
        '__MODE__': _state_block(
            ICON_PAUSE, 'Account paused',
            f'Hello {_esc(gp.full_name)} — the academy has paused this account '
            f'({_esc(request.user.get_username())}). Contact '
            '<b>info@sportingpearlsacademy.org</b> to sort it out in minutes.',
            show_login=False),
    }), status=403)


def csrf_failure(request, reason=''):
    """Branded 403 for expired/missing CSRF (e.g. stale tabs) — same shell
    as the paused-account state page, with two ways back to the portal."""
    gp = getattr(request.user, 'guardian_profile', None) \
        if getattr(request, 'user', None) and request.user.is_authenticated else None
    if gp is not None and gp.is_active:
        return redirect('/portal/parents/')
    return HttpResponse(_render('activate.html', {
        '__MODE__': _state_block(
            ICON_PAUSE, 'This page expired for safety',
            'For your protection the form timed out or its security token went '
            'stale. Nothing was lost — simply sign in again and continue.',
            extra='<div class="state-links">'
                  '<a href="/portal/parents/login/">Parent sign in</a>'
                  '<a href="/portal/">Staff sign in</a></div>',
            show_login=False),
    }), status=403)


# ════════════════════════════════════════════════════════════════════════
# Cycle P2 — shared chrome, announcements board, my child, account
# ════════════════════════════════════════════════════════════════════════

CHROME_CSS = '''
*{box-sizing:border-box;margin:0;padding:0}
:root{--navy:#0c1a33;--navy2:#14284b;--amber:#f59d1e;--lagoon:#1f7a6f;--pearl:#fbfaf7;--muted:#8a94a6;--hair:#e4e8ef;
  --ink:#1a2436;--ink2:#5c6a7e;--r:18px;
  --gold:linear-gradient(135deg,#ffb748,#f59d1e 58%,#ec8d08);
  --teal:linear-gradient(135deg,#28998c,#1f7a6f 62%,#186458);
  --pitch:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='520' height='260' viewBox='0 0 520 260'%3E%3Cg fill='none' stroke='%23ffffff' stroke-opacity='.06' stroke-width='1.4'%3E%3Ccircle cx='260' cy='130' r='62'/%3E%3Ccircle cx='260' cy='130' r='4'/%3E%3Cpath d='M260 0v260M0 40h92v180H0M520 40h-92v180h92'/%3E%3C/g%3E%3C/svg%3E");
  --shadow-1:0 1px 2px rgba(12,26,51,.05),0 12px 30px -12px rgba(12,26,51,.14);
  --shadow-2:0 2px 4px rgba(12,26,51,.05),0 22px 48px -16px rgba(12,26,51,.22)}
html{scroll-behavior:smooth}
html,body{min-height:100%}
body{font-family:'Work Sans','Segoe UI',system-ui,-apple-system,Arial,sans-serif;background:var(--pearl);color:var(--ink);
  background-image:radial-gradient(1100px 420px at 50% -160px,rgba(20,40,75,.055),transparent 70%)}
::selection{background:rgba(245,157,30,.32)}
:focus-visible{outline:3px solid rgba(31,122,111,.5);outline-offset:2px;border-radius:6px}
.top{position:relative;overflow:hidden;color:var(--pearl);padding:22px 26px 30px;
  background:radial-gradient(860px 360px at 88% -90px,rgba(31,122,111,.5),transparent 62%),
    radial-gradient(680px 320px at -80px 130%,rgba(245,157,30,.16),transparent 58%),
    linear-gradient(126deg,#0c1a33 0%,#13294e 46%,#0c1a33 100%)}
.top::after{content:'';position:absolute;inset:0;background:var(--pitch) right -50px top -20px no-repeat;
  background-size:520px 260px;pointer-events:none;
  -webkit-mask-image:linear-gradient(100deg,transparent 46%,#000 82%);mask-image:linear-gradient(100deg,transparent 46%,#000 82%)}
.top::before{content:'';position:absolute;width:300px;height:300px;border-radius:50%;
  border:1.5px solid rgba(245,157,30,.3);right:-60px;top:-110px;z-index:0}
.top>*{position:relative;z-index:1}
.bar{max-width:1060px;margin:0 auto;display:flex;align-items:center;gap:14px}
.mark{width:44px;height:44px;border-radius:13px;background:var(--gold);color:#122a52;display:grid;place-items:center;
  font-family:Georgia,serif;font-weight:700;font-size:18px;
  box-shadow:0 8px 20px rgba(245,157,30,.42),inset 0 0 0 1.5px rgba(255,255,255,.3)}
.bar h1{font-family:Georgia,serif;font-size:19px;font-weight:600;letter-spacing:.2px}
.bar small{display:block;font-size:11.5px;letter-spacing:2.6px;text-transform:uppercase;color:#7fd0c5;margin-top:3px;
  font-family:'Work Sans',sans-serif;font-weight:600}
.bar .who{margin-left:auto;display:flex;align-items:center;gap:12px}
.bar .who span{font-size:14px;color:#c8d2e4}
form.signout{display:inline}
.bar button{background:rgba(251,250,247,.08);color:#dbe3f0;border:1px solid rgba(255,255,255,.24);border-radius:999px;
  padding:7.5px 15px;font:inherit;font-size:13.5px;font-weight:600;cursor:pointer;transition:.15s;white-space:nowrap}
.bar button:hover{border-color:var(--amber);color:var(--amber);background:rgba(245,157,30,.1)}
.hero{max-width:1060px;margin:26px auto 0}
.hero h2{font-family:Georgia,serif;font-size:clamp(23px,3.4vw,31px);font-weight:600;color:#fff;position:relative;padding-bottom:13px}
.hero h2::after{content:'';position:absolute;left:1px;bottom:0;width:48px;height:3.5px;border-radius:3px;
  background:linear-gradient(90deg,#ffb748,#f59d1e)}
.hero p{font-size:14.5px;color:#a9b6ce;margin-top:9px}
.pnav{max-width:1060px;margin:18px auto 0;display:flex;gap:9px;flex-wrap:wrap}
.pnav a{display:inline-flex;align-items:center;gap:8px;background:rgba(251,250,247,.07);border:1px solid rgba(251,250,247,.2);
  color:#dbe3f0;text-decoration:none;font-size:14px;font-weight:600;letter-spacing:.3px;padding:9px 16px;border-radius:999px;
  transition:.16s;box-shadow:inset 0 1px 0 rgba(255,255,255,.05)}
.pnav a svg{width:15px;height:15px;flex:none;opacity:.9}
.pnav a:hover{background:rgba(251,250,247,.13);border-color:rgba(245,157,30,.6);color:#ffd48a;transform:translateY(-1px)}
.pnav a.active{background:var(--gold);border-color:transparent;color:#122a52;box-shadow:0 7px 20px rgba(245,157,30,.4)}
.pnav a.active svg{opacity:1}
.pnav .nb{background:#e04f3f;color:#fff;font-size:12.5px;font-weight:700;min-width:18px;height:18px;border-radius:999px;
  display:inline-grid;place-items:center;padding:0 5px;font-family:'Work Sans',sans-serif;box-shadow:0 2px 6px rgba(224,79,63,.45)}
main{max-width:1060px;margin:26px auto 46px;padding:0 26px}
.card{background:#fff;border:1px solid #e7ebf2;border-radius:var(--r);box-shadow:var(--shadow-1)}
.sec-h{display:flex;align-items:center;gap:10px;margin:30px 0 14px}
.sec-h h3{font-family:Georgia,serif;font-size:20px;color:var(--navy);font-weight:600;position:relative;padding-left:15px}
.sec-h h3::before{content:'';position:absolute;left:0;top:3px;bottom:3px;width:5px;border-radius:4px;background:var(--gold)}
.sec-h a{margin-left:auto;font-size:13.5px;font-weight:700;color:var(--lagoon);text-decoration:none;white-space:nowrap}
.sec-h a:hover{text-decoration:underline}
.foot{max-width:1060px;margin:0 auto;padding:22px 26px 40px;display:flex;gap:8px 18px;flex-wrap:wrap;align-items:center;
  color:var(--muted);font-size:13.5px;border-top:1px solid var(--hair)}
.foot b{color:var(--ink2);font-weight:600}
.foot .fbrand{margin-left:auto;font-size:12.5px;letter-spacing:.4px}
.note-ok{background:#eef7f0;border:1px solid #bfe0c8;color:#276749;border-radius:12px;padding:11px 15px;font-size:14.5px;
  margin-bottom:16px;box-shadow:inset 3px 0 0 #34a06b}
.chip{background:var(--teal);color:#fff;font-size:12.5px;font-weight:700;letter-spacing:1.1px;text-transform:uppercase;
  border-radius:999px;padding:4px 11px;box-shadow:0 3px 8px rgba(31,122,111,.3)}
@media(max-width:560px){.bar .who span{display:none}.top{padding:18px 18px 24px}main{padding:0 18px}.foot{padding:20px 18px 34px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;scroll-behavior:auto}}
'''


def _chrome(request, gp, active):
    """Tokens shared by every P2/P3 page: nav pills, unread badge, header."""
    unread = _unread(gp)
    badge = f'<b class="nb">{unread}</b>' if unread else ''
    return {
        '__CHROME_CSS__': CHROME_CSS,
        '__NAV_OVERVIEW__': 'class="active"' if active == 'home' else '',
        '__NAV_BOARD__': 'class="active"' if active == 'board' else '',
        '__NAV_WELFARE__': 'class="active"' if active == 'welfare' else '',
        '__NAV_ACCOUNT__': 'class="active"' if active == 'account' else '',
        '__UNREAD_BADGE__': badge,
    }


# ── P3: complaints desk helpers ────────────────────────────────────────

ST_CHIP = {
    'open': ('stc-open', 'Open'),
    'in_review': ('stc-rev', 'In review'),
    'resolved': ('stc-ok', 'Resolved'),
    'closed': ('stc-off', 'Closed'),
}


def _st_chip(status):
    cls, label = ST_CHIP.get(status, ('stc-off', status))
    return f'<span class="stc {cls}">{_esc(label)}</span>'


def _portal_url(request, path='/portal/parents/complaints/'):
    """Absolute portal URL for email CTAs (falls back to the brand domain)."""
    try:
        return request.build_absolute_uri(path)
    except Exception:
        return 'https://www.sportingpearlsacademy.org' + path


def _mail(kind, payload):
    """Fire one branded email; failures never break the request — they are
    printed to the server log so QC/deploy can spot them."""
    import sys
    from submissions.views import resend_send
    try:
        payload.update({'from': settings.EMAIL_FROM})
        ok, detail = resend_send(payload)
        if not ok:
            print(f'[portal-mail] {kind}: {detail}', file=sys.stderr)
        return ok, detail
    except Exception as exc:  # pragma: no cover
        print(f'[portal-mail] {kind}: {exc}', file=sys.stderr)
        return False, str(exc)


def _audience(a):
    names = [s.label for s in a.squads.all()]
    return ' · '.join(names) if names else 'All squads'


def _para_html(body):
    paras = [p.strip().replace('\n', '<br>') for p in body.split('\n\n') if p.strip()]
    return '</p><p>'.join(_esc(p) for p in paras) or '—'


def _not_found(request, title, text):
    return HttpResponse(_render('activate.html', {
        '__MODE__': _state_block(ICON_HELP, title, text),
    }), status=404)


@ensure_csrf_cookie
@parent_required
def parents_announcements(request):
    """The announcements board — pinned first, newest first, unread flagged."""
    gp = request.user.guardian_profile
    rows = []
    for a in _visible_qs(gp):
        seen = a.reads.filter(guardian=gp).exists()
        excerpt = a.body[:150].strip() + ('…' if len(a.body) > 150 else '')
        chips = (f'<span class="chip">Pinned</span>' if a.pinned else '') \
            + ('<span class="an-new">New</span>' if not seen else '')
        rows.append(
            f'<a class="an-card card{" an-unread" if not seen else ""}" '
            f'href="/portal/parents/announcements/{a.id}/">'
            f'<div class="an-top">{chips}'
            f'<span class="an-date">{(a.published_at or a.created_at):%A %d %B %Y}</span></div>'
            f'<h3>{_esc(a.title)}</h3>'
            f'<p>{_esc(excerpt)}</p>'
            f'<span class="an-for">For: {_esc(_audience(a))}</span></a>')
    if not rows:
        rows.append('<div class="an-empty card"><b>No announcements yet</b>'
                    '<span>When the academy posts a notice for your child&#8217;s '
                    'squad it will appear here.</span></div>')
    return HttpResponse(_render('announcements.html', {
        '__CSRF__': get_token(request),
        '__GUARDIAN__': _esc(gp.full_name),
        '__RELATION__': _esc(gp.get_relation_display()),
        '__AN_ROWS__': '\n'.join(rows),
        '__UNREAD_N__': str(_unread(gp)),
        '__PLURAL__': 's' if _unread(gp) != 1 else '',
    } | _chrome(request, gp, 'board')))


@ensure_csrf_cookie
@parent_required
def parents_announcement_detail(request, aid):
    """One announcement; opening it records the read receipt."""
    gp = request.user.guardian_profile
    a = _visible_qs(gp).filter(id=aid).select_related('created_by').first()
    if a is None:
        return _not_found(request, 'Announcement not available',
                          'This notice does not exist, was never published to '
                          'your child&#8217;s squad, or has been withdrawn.')
    AnnouncementRead.objects.get_or_create(announcement=a, guardian=gp)
    return HttpResponse(_render('announcement.html', {
        '__CSRF__': get_token(request),
        '__GUARDIAN__': _esc(gp.full_name),
        '__RELATION__': _esc(gp.get_relation_display()),
        '__AN_TITLE__': _esc(a.title),
        '__AN_DATE__': f'{(a.published_at or a.created_at):%A %d %B %Y}',
        '__AN_AUDIENCE__': _esc(_audience(a)),
        '__AN_PINNED__': '<span class="chip">Pinned</span>' if a.pinned else '',
        '__AN_BODY__': f'<p>{_para_html(a.body)}</p>',
    } | _chrome(request, gp, 'board')))


@ensure_csrf_cookie
@parent_required
def parents_child(request, pid):
    """My Child — one child's profile, guarded through GuardianPlayer."""
    gp = request.user.guardian_profile
    ln = (gp.links.filter(player_id=pid)
          .select_related('player', 'player__squad').first())
    if ln is None:
        return _not_found(request, 'Profile not linked to your account',
                          'This player profile is not linked to your guardian '
                          'account. If something looks wrong, contact the '
                          'academy office at info@sportingpearlsacademy.org.')
    p = ln.player
    now = timezone.localtime(timezone.now())
    fx = _next_fixture(p.squad, now.date())
    pos = dict(POSITIONS).get(p.position, '—') if p.position else '—'
    facts = [
        ('Squad', _squad_text(p.squad)),
        ('Shirt number', f'#{p.number:02d}' if p.number is not None else '—'),
        ('Position', pos),
        ('Age', f'{p.age} years' if p.age else '—'),
        ('Height', f'{p.height_m} m' if p.height_m else '—'),
        ('Preferred foot', dict(p._meta.get_field('foot').choices).get(p.foot, '—')
         if p.foot else '—'),
        ('Player reference', p.ref),
        ('Team role', 'Captain' if p.is_captain else 'Squad player'),
    ]
    fact_html = '\n'.join(
        f'<div class="cf"><span>{_esc(k)}</span><b>{_esc(v)}</b></div>' for k, v in facts)
    motto = (f'<blockquote class="motto"><span class="mq">&ldquo;</span>'
             f'{_esc(p.motto)}</blockquote>') if p.motto.strip() else ''
    return HttpResponse(_render('child.html', {
        '__CSRF__': get_token(request),
        '__GUARDIAN__': _esc(gp.full_name),
        '__RELATION__': _esc(gp.get_relation_display()),
        '__CHILD_PHOTO__': _ava(p),
        '__CHILD_NAME__': _esc(f'{p.first_name} {p.last_name}'),
        '__CHILD_REF__': _esc(p.ref),
        '__SQUAD_DOT__': _esc(p.squad.accent),
        '__SQUAD_TEXT__': _esc(_squad_text(p.squad)),
        '__CAPTAIN__': '<span class="cap">Captain</span>' if p.is_captain else '',
        '__FACTS__': fact_html,
        '__MOTTO__': motto,
        '__NEXT_FX__': _fx_html(fx),
    } | _chrome(request, gp, 'home')))


@ensure_csrf_cookie
@parent_required
def parents_account(request):
    """Account settings — profile details + password change."""
    gp = request.user.guardian_profile
    note = ''
    if request.method == 'POST':
        which = request.POST.get('which')
        if which == 'profile':
            phone = (request.POST.get('phone') or '').strip()[:40]
            relation = request.POST.get('relation') or gp.relation
            if relation not in dict(RELATION_CHOICES):
                relation = 'Guardian'
            gp.phone, gp.relation = phone, relation
            gp.save(update_fields=['phone', 'relation'])
            note = '<div class="note-ok">Your contact details were saved.</div>'
        elif which == 'password':
            cur = request.POST.get('current', '')
            p1 = request.POST.get('password', '')
            p2 = request.POST.get('password2', '')
            user = authenticate(request, username=request.user.get_username(),
                                password=cur)
            if user is None:
                note = '<div class="note-err">The current password is not correct.</div>'
            elif p1 != p2:
                note = '<div class="note-err">The two new passwords do not match.</div>'
            else:
                try:
                    validate_password(p1, user=user)
                except ValidationError as e:
                    note = '<div class="note-err">' + _esc(' '.join(e.messages)) + '</div>'
                else:
                    user.set_password(p1)
                    user.save(update_fields=['password'])
                    from django.contrib.auth import update_session_auth_hash
                    update_session_auth_hash(request, user)
                    note = '<div class="note-ok">Your new password is active — it works from your next sign-in on other devices too.</div>'
    kids = '\n'.join(
        f'<div class="acct-kid"><span class="dot" style="background:{_esc(l.player.squad.accent)}"></span>'
        f'{_esc(l.player.first_name)} {_esc(l.player.last_name)}'
        f'<em>{_esc(_squad_text(l.player.squad))}</em></div>'
        for l in gp.links.select_related('player', 'player__squad'))
    if not kids:
        kids = '<div class="acct-kid"><span class="dot"></span>No child linked yet<em>The office is matching your application.</em></div>'
    rel_opts = '\n'.join(
        f'<option value="{_esc(v)}"{" selected" if v == gp.relation else ""}>{_esc(v)}</option>'
        for v, _ in RELATION_CHOICES)
    return HttpResponse(_render('account.html', {
        '__CSRF__': get_token(request),
        '__GUARDIAN__': _esc(gp.full_name),
        '__RELATION__': _esc(gp.get_relation_display()),
        '__NOTE__': note,
        '__PHONE__': _esc(gp.phone),
        '__REL_OPTS__': rel_opts,
        '__EMAIL__': _esc(request.user.get_username()),
        '__SINCE__': f'{gp.created_at:%B %Y}' if gp.created_at else '—',
        '__KIDS__': kids,
    } | _chrome(request, gp, 'account')))


# ════════════════════════════════════════════════════════════════════════
# Cycle P3 — the complaints & welfare desk (parent side)
# ════════════════════════════════════════════════════════════════════════

DESK_CSS = '''
  .stc{font-size:12.5px;font-weight:700;letter-spacing:1px;text-transform:uppercase;border-radius:999px;padding:4px 11px;
    display:inline-flex;align-items:center;gap:6px}
  .stc::before{content:'';width:6px;height:6px;border-radius:50%;background:currentColor;flex:none}
  .stc-open{background:#fdeee0;color:#a05a04}
  .stc-rev{background:rgba(31,122,111,.1);color:#1f7a6f}
  .stc-ok{background:#eef7f0;color:#276749}
  .stc-off{background:#eef0f4;color:#5c6a7e}
  label{display:block;font-size:12px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#7c88a1;margin:13px 0 6px}
  input,select,textarea{width:100%;border:1.5px solid #d9dfe9;border-radius:11px;padding:10.5px 13px;font:inherit;font-size:15px;
    color:var(--ink);background:#fff;transition:border .15s,box-shadow .15s}
  textarea{min-height:130px;resize:vertical;line-height:1.6}
  input:focus,select:focus,textarea:focus{outline:none;border-color:var(--lagoon);box-shadow:0 0 0 3.5px rgba(31,122,111,.16)}
  input::placeholder,textarea::placeholder{color:#9aa5b8}
  button{margin-top:16px;background:var(--teal);color:#fff;border:0;border-radius:11px;padding:12px 22px;font:inherit;
    font-size:14.5px;font-weight:700;cursor:pointer;transition:.16s;box-shadow:0 6px 16px rgba(31,122,111,.32)}
  button:hover{transform:translateY(-1px);box-shadow:0 10px 22px rgba(31,122,111,.4)}
  button:active{transform:none}
  .note-err{background:#fdecea;border:1px solid #f3c2bb;color:#c0392b;border-radius:12px;padding:11px 15px;font-size:14.5px;
    margin-bottom:14px;box-shadow:inset 3px 0 0 #d9534f}
  .two{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  .case{position:relative;display:flex;align-items:flex-start;gap:13px;padding:16px 18px 16px 21px;text-decoration:none;
    color:inherit;transition:.16s;overflow:hidden}
  .case::before{content:'';position:absolute;left:0;top:0;bottom:0;width:4px;background:linear-gradient(180deg,#b9c3d4,#dfe4ec)}
  .case:hover{transform:translateY(-2px);box-shadow:var(--shadow-2);border-color:rgba(31,122,111,.45)}
  .case .ic{width:40px;height:40px;border-radius:12px;flex:none;display:grid;place-items:center;
    background:rgba(31,122,111,.1);color:var(--lagoon)}
  .case .ic svg{width:19px;height:19px}
  .case-main{min-width:0;flex:1}
  .case-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
  .case-top h3{font-family:Georgia,serif;font-size:15.5px;color:var(--navy);font-weight:600}
  .case-ref{font-family:'Sarasa Mono SC',monospace;font-size:12.5px;color:#7c88a1;background:#f3f5f9;border-radius:6px;padding:1.5px 7px}
  .case-meta{font-size:13.5px;color:#5c6a7e;margin-top:5px;line-height:1.55}
  .case-side{flex:none;text-align:right;display:flex;flex-direction:column;gap:5px;align-items:flex-end}
  .case-date{font-size:12.5px;color:var(--muted)}
  .newcase{padding:22px 24px;margin-bottom:22px;position:relative;overflow:hidden}
  .newcase::before{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:linear-gradient(90deg,#ffb748,#f59d1e,#28998c)}
  .newcase h3{font-family:Georgia,serif;font-size:18px;color:var(--navy);font-weight:600;margin-bottom:5px}
  .newcase .sub{font-size:14px;color:#5c6a7e;margin-bottom:4px;line-height:1.55}
  .safe{border:1px dashed rgba(31,122,111,.45);background:rgba(31,122,111,.06);color:#1f5c54;border-radius:12px;
    padding:10px 14px;font-size:13.5px;line-height:1.6;margin:14px 0 2px}
  .safe b{color:#1f7a6f}
  .empty{padding:30px 22px;text-align:center;display:flex;flex-direction:column;gap:6px}
  .empty b{font-family:Georgia,serif;color:var(--navy);font-size:16.5px}
  .empty span{font-size:14.5px;color:#5c6a7e}
  @media(max-width:560px){.two{grid-template-columns:1fr}.case-side{display:none}}
'''


@ensure_csrf_cookie
@parent_required
def parents_complaints(request):
    """The complaints & welfare desk — open a private case or follow one."""
    gp = request.user.guardian_profile
    error = ''
    if request.method == 'POST':
        category = request.POST.get('category') or 'other'
        if category not in dict(COMPLAINT_CATEGORIES):
            category = 'other'
        subject = (request.POST.get('subject') or '').strip()[:150]
        message = (request.POST.get('message') or '').strip()
        child = None
        if request.POST.get('child'):
            ln = gp.links.filter(player_id=request.POST.get('child')).first()
            if ln:
                child = ln.player
        if len(subject) < 4:
            error = 'Please give the case a short subject (at least 4 characters).'
        elif len(message) < 15:
            error = 'Please describe the matter in a few sentences (at least 15 characters).'
        else:
            c = Complaint.objects.create(
                guardian=gp, player=child, category=category,
                subject=subject, message=message, status='open')
            cat_label = dict(COMPLAINT_CATEGORIES)[category]
            url = _portal_url(request)
            confirm = complaint_received_payload(gp.full_name, f'#{c.id}', subject,
                                                 cat_label, url)
            confirm['to'] = [request.user.get_username()]
            _mail('complaint-received', confirm)
            alert = complaint_alert_payload(
                f'#{c.id}', gp.full_name, cat_label, subject,
                (f'{child.first_name} {child.last_name}' if child else ''), url)
            alert['to'] = [settings.EMAIL_TO]
            _mail('complaint-alert', alert)
            return redirect(f'/portal/parents/complaints/{c.id}/?new=1')

    rows = []
    for c in gp.complaints.select_related('player', 'player__squad'):
        n_replies = c.replies.count()
        last = c.updated_at
        rows.append(
            f'<a class="case card" href="/portal/parents/complaints/{c.id}/">'
            f'<span class="ic"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
            f'<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></span>'
            f'<span class="case-main"><span class="case-top">{_st_chip(c.status)}'
            f'<h3>{_esc(c.subject)}</h3>'
            f'<code class="case-ref">#{c.id}</code></span>'
            f'<span class="case-meta">{_esc(c.get_category_display())}'
            + (f' · about {_esc(c.player.first_name)}' if c.player else '')
            + f' · {n_replies} repl{"y" if n_replies == 1 else "ies"} · last activity '
            f'{_esc(f"{(c.updated_at or c.created_at):%d %b %Y}")}</span></span>'
            f'<span class="case-side"><span class="case-date">opened '
            f'{(c.created_at):%d %b %Y}</span></span></a>')
    if not rows:
        rows.append('<div class="empty card"><b>No cases yet</b><span>When you raise '
                    'a concern it appears here as a private case that only you and the '
                    'academy staff can read.</span></div>')

    cat_opts = '\n'.join(
        f'<option value="{_esc(v)}">{_esc(lbl)}</option>' for v, lbl in COMPLAINT_CATEGORIES)
    kid_opts = '\n'.join(
        f'<option value="{l.player.id}">{_esc(l.player.first_name)} {_esc(l.player.last_name)}'
        f' · {_esc(_squad_text(l.player.squad))}</option>'
        for l in gp.links.select_related('player', 'player__squad'))

    body = (ASSETS / 'complaints.html').read_text(encoding='utf-8')
    tokens = {
        '__CSRF__': get_token(request),
        '__GUARDIAN__': _esc(gp.full_name),
        '__RELATION__': _esc(gp.get_relation_display()),
        '__DESK_CSS__': DESK_CSS,
        '__ERROR__': _err(_esc(error)),
        '__CAT_OPTS__': cat_opts,
        '__KID_OPTS__': kid_opts,
        '__CASE_ROWS__': '\n'.join(rows),
        '__OPEN_N__': str(gp.complaints.exclude(status='closed').count()),
    } | _chrome(request, gp, 'welfare')
    for k, v in tokens.items():
        body = body.replace(k, v)
    leftovers = re.findall(r'__[A-Z][A-Z_]+__', body)
    if leftovers:
        raise RuntimeError(f'UNREPLACED PARENT TOKENS: {sorted(set(leftovers))}')
    return HttpResponse(body)


@ensure_csrf_cookie
@parent_required
def parents_complaint_detail(request, cid):
    """One private case: the thread plus follow-up. Internal staff notes are
    never rendered here. Replying to a closed case reopens it."""
    gp = request.user.guardian_profile
    c = gp.complaints.select_related('player', 'player__squad').filter(id=cid).first()
    if c is None:
        return _not_found(request, 'Case not linked to your account',
                          'This case does not exist or belongs to another guardian '
                          'account. Every case is private to the family that opened '
                          'it — if something looks wrong, contact the academy office '
                          'at info@sportingpearlsacademy.org.')
    error = ''
    if request.method == 'POST':
        body_txt = (request.POST.get('message') or '').strip()
        if len(body_txt) < 3:
            error = 'Please write a message first.'
        else:
            ComplaintReply.objects.create(complaint=c, by_guardian=gp, body=body_txt)
            reopened = c.status == 'closed'
            if reopened:
                c.status = 'open'
            c.save()
            cat_label = c.get_category_display()
            alert = complaint_alert_payload(
                f'#{c.id}', gp.full_name, cat_label, c.subject,
                (f'{c.player.first_name} {c.player.last_name}' if c.player else ''),
                _portal_url(request), followup=True)
            alert['to'] = [settings.EMAIL_TO]
            _mail('complaint-alert', alert)
            return redirect(f'/portal/parents/complaints/{c.id}/?added=1')

    entries = [
        ('guardian', 'You', c.created_at, c.message, False),
    ]
    for r in c.replies.exclude(is_internal=True).select_related('by_staff'):
        if r.by_staff is not None:
            entries.append(('staff', f'The academy · {r.by_staff.get_username()}',
                            r.created_at, r.body, False))
        else:  # the guardian's own follow-up
            entries.append(('guardian', 'You', r.created_at, r.body, False))
    thread = []
    for kind, who, when, body_txt, internal in entries:
        thread.append(
            f'<div class="msg {kind}"><div class="msg-h"><b>{_esc(who)}</b>'
            f'<span>{_esc(f"{timezone.localtime(when):%A %d %B %Y · %H:%M}")}</span></div>'
            f'<div class="msg-b"><p>{_para_html(body_txt)}</p></div></div>')
    note = ''
    if request.GET.get('new'):
        note = ('<div class="note-ok">Your case is open — the academy office has been '
                'notified and a confirmation email is on its way. Keep the case number '
                'for reference.</div>')
    elif request.GET.get('added'):
        note = '<div class="note-ok">Your message was added to the case.</div>'
    elif error:
        note = f'<div class="note-err">{_esc(error)}</div>'

    body = (ASSETS / 'complaint.html').read_text(encoding='utf-8')
    closed_note = ('<div class="closed">This case is closed — replying below reopens '
                   'it for the office.</div>' if c.status == 'closed' else '')
    tokens = {
        '__CSRF__': get_token(request),
        '__GUARDIAN__': _esc(gp.full_name),
        '__RELATION__': _esc(gp.get_relation_display()),
        '__DESK_CSS__': DESK_CSS,
        '__NOTE__': note,
        '__CASE_ID__': str(c.id),
        '__CASE_REF__': f'#{c.id}',
        '__CASE_SUBJECT__': _esc(c.subject),
        '__CASE_STATUS__': _st_chip(c.status),
        '__CASE_CAT__': _esc(c.get_category_display()),
        '__CASE_CHILD__': _esc(f'{c.player.first_name} {c.player.last_name}'
                               f' · {_squad_text(c.player.squad)}' if c.player else 'Whole family'),
        '__CASE_OPENED__': _esc(f'{timezone.localtime(c.created_at):%A %d %B %Y}'),
        '__CASE_UPDATED__': _esc(f'{timezone.localtime(c.updated_at):%d %b %Y · %H:%M}'),
        '__THREAD__': '\n'.join(thread),
        '__CLOSED_NOTE__': closed_note,
    } | _chrome(request, gp, 'welfare')
    for k, v in tokens.items():
        body = body.replace(k, v)
    leftovers = re.findall(r'__[A-Z][A-Z_]+__', body)
    if leftovers:
        raise RuntimeError(f'UNREPLACED PARENT TOKENS: {sorted(set(leftovers))}')
    return HttpResponse(body)
