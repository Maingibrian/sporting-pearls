"""Phase 2 — password reset (both portals) + branded error pages.

Design rules (PRODUCTION-READINESS.md §4, Phase 2):

  * NO account enumeration: the request form ALWAYS shows the same
    "if that account exists, a link is on its way" page, whether or
    not the email/username matched anything. The email is only sent
    when a matching ACTIVE account exists.
  * Constant-ish time: every POST burns one dummy PBKDF2 verify so
    "account exists" vs "does not" cannot be told apart by timing.
  * Tokens: Django's default_token_generator (signed against the
    user's pk + password hash + timestamp). Setting a new password
    changes the hash, which kills the link automatically. Links
    expire after settings.PASSWORD_RESET_TIMEOUT (default 1 hour).
  * Abuse control: 5 reset requests per IP per audience per hour,
    plus the same 'company' honeypot the public forms use.
  * Emails carry only a neutral sentence + the link. No username
    echo, no account details.
  * Security log (sporting.auth): audience, user pk and IP — never
    the address typed into the form, never tokens or passwords.

Branded 404/500 handlers for every Django-served path live here too
(handler404 / handler500 in urls.py).
"""
import logging
from base64 import urlsafe_b64decode, urlsafe_b64encode
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.utils.encoding import force_str
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .middleware import client_ip
from .views import resend_send

logger = logging.getLogger('sporting.auth')

ASSETS = Path(__file__).resolve().parent / 'portal_assets'

RESET_RATE_LIMIT = 5        # requests per IP per audience…
RESET_WINDOW = 3600         # …per hour

# audience -> (login url, login label, link path, finder)
AUDIENCES = {
    'staff': {
        'login_url': '/portal/login/',
        'login_label': 'Management Portal sign-in',
        'link_path': '/portal/reset/',
        'name': 'Management Portal',
    },
    'parents': {
        'login_url': '/portal/parents/login/',
        'login_label': 'Parent Portal sign-in',
        'link_path': '/portal/parents/reset/',
        'name': 'Parent Portal',
    },
}


# ── helpers ────────────────────────────────────────────────────────────

def _esc(s):
    import html
    return html.escape(str(s), quote=True)


def _render(asset, tokens):
    body = (ASSETS / asset).read_text(encoding='utf-8')
    for k, v in tokens.items():
        body = body.replace(k, v)
    return body


_DUMMY_HASH = None


def burn_password_time():
    """Run one full password verify so POST timing does not reveal
    whether the account lookup matched anything."""
    global _DUMMY_HASH
    from django.contrib.auth.hashers import check_password, make_password
    if _DUMMY_HASH is None:
        _DUMMY_HASH = make_password('sp-constant-time-placeholder')
    check_password('not-the-password', _DUMMY_HASH)


def _find_user(audience, ident):
    """Resolve the account for a reset request, or None.

    staff: username OR email, must be staff + active.
    parents: the username IS the guardian's email (lowercased),
    must carry an active guardian profile.
    """
    User = get_user_model()
    ident = (ident or '').strip()
    if not ident:
        return None
    if audience == 'staff':
        from django.db.models import Q
        return (User.objects.filter(Q(username=ident) | Q(email__iexact=ident),
                                    is_staff=True, is_active=True)
                .order_by('pk').first())
    user = (User.objects.filter(username=ident.lower(), is_active=True)
            .select_related('guardian_profile').order_by('pk').first())
    gp = getattr(user, 'guardian_profile', None)
    if gp is None or not gp.is_active:
        return None          # not a guardian, or paused — no email
    return user


def _throttle_ok(request, audience):
    key = f'sp-pwr:{audience}:{client_ip(request)}'
    try:
        if cache.get(key) is None:
            cache.add(key, 0, RESET_WINDOW)
        count = cache.get(key, 0)
    except ValueError:
        count = 0
    if count >= RESET_RATE_LIMIT:
        logger.warning('reset throttle tripped audience=%s ip=%s',
                       audience, client_ip(request))
        return False
    try:
        cache.incr(key)
    except ValueError:
        pass
    return True


def _uid(user):
    return urlsafe_b64encode(str(user.pk).encode()).decode()


def _user_from_uid(uidb64):
    try:
        pk = force_str(urlsafe_b64decode(uidb64))
        if not pk.isdigit():
            return None
        return get_user_model().objects.filter(pk=int(pk), is_active=True).first()
    except (TypeError, ValueError, UnicodeDecodeError):
        return None


# ── request a reset link ───────────────────────────────────────────────

@ensure_csrf_cookie
def reset_request(request, audience):
    cfg = AUDIENCES[audience]
    if request.method == 'POST':
        # identical page whether throttled, honeypotted, matched or not
        sent_page = _render('reset-sent.html', {
            '__AUD__': cfg['name'],
            '__LOGIN_URL__': cfg['login_url'],
            '__LOGIN_LABEL__': cfg['login_label'],
        })
        ident = request.POST.get('identify', '')
        if str(request.POST.get('company', '') or '').strip():
            return HttpResponse(sent_page)             # honeypot: swallow
        if not _throttle_ok(request, audience):
            return HttpResponse(sent_page)             # throttled: swallow
        burn_password_time()                           # timing parity
        user = _find_user(audience, ident)
        if user is not None:
            token = default_token_generator.make_token(user)
            link = request.build_absolute_uri(
                f"{cfg['link_path']}{_uid(user)}/{token}/")
            ok, _ = resend_send({
                'from': settings.EMAIL_FROM,
                'to': [user.email] if user.email else [],
                'subject': 'Set a new Sporting Pearls portal password',
                'text': ('Someone asked to reset the password for a '
                         f'{cfg["name"]} account.\n\n'
                         'If that was you, open this link to choose a new '
                         f'password (it expires in '
                         f'{settings.PASSWORD_RESET_TIMEOUT // 60} minutes):\n'
                         f'{link}\n\n'
                         'If you did not ask for this, ignore this email — '
                         'the link stops working on its own and nothing '
                         'else changes.'),
            })
            logger.info('reset requested audience=%s user_pk=%s ip=%s sent=%s',
                        audience, user.pk, client_ip(request), ok)
        else:
            logger.info('reset requested audience=%s user_pk=- ip=%s',
                        audience, client_ip(request))
        return HttpResponse(sent_page)

    return HttpResponse(_render('reset-request.html', {
        '__CSRF__': get_token(request),
        '__ACTION__': cfg['link_path'],
        '__AUD__': cfg['name'],
        '__FIELD_LABEL__': 'Username or email' if audience == 'staff' else 'Email',
        '__FIELD_TYPE__': 'text' if audience == 'staff' else 'email',
        '__LOGIN_URL__': cfg['login_url'],
    }))


# ── set a new password from the emailed link ───────────────────────────

@ensure_csrf_cookie
def reset_confirm(request, audience, uidb64, token):
    cfg = AUDIENCES[audience]
    ctx = {
        '__AUD__': cfg['name'],
        '__LOGIN_URL__': cfg['login_url'],
        '__LOGIN_LABEL__': cfg['login_label'],
        '__REQ_URL__': cfg['link_path'],
    }
    user = _user_from_uid(uidb64)
    if user is None or not default_token_generator.check_token(user, token):
        return HttpResponse(_render('reset-invalid.html', ctx), status=400)

    if request.method == 'POST':
        pw1 = request.POST.get('password', '')
        pw2 = request.POST.get('password2', '')
        err = ''
        if pw1 != pw2:
            err = 'The two passwords do not match.'
        else:
            try:
                validate_password(pw1, user=user)
            except Exception:                       # noqa: BLE001 — Django
                err = ('Please choose a stronger password — at least 8 '
                       'characters, not a common word.')
        if not err:
            user.set_password(pw1)
            user.save(update_fields=['password'])   # kills the token too
            logger.info('reset completed audience=%s user_pk=%s ip=%s',
                        audience, user.pk, client_ip(request))
            return HttpResponse(_render('reset-done.html', ctx))
        return HttpResponse(_render('reset-set.html', {
            '__CSRF__': get_token(request),
            '__ACTION__': f'{cfg["link_path"]}{uidb64}/{token}/',
            '__AUD__': cfg['name'],
            '__ERR__': f'<div class="lg-err">{_esc(err)}</div>',
        }))

    return HttpResponse(_render('reset-set.html', {
        '__CSRF__': get_token(request),
        '__ACTION__': f'{cfg["link_path"]}{uidb64}/{token}/',
        '__AUD__': cfg['name'],
        '__ERR__': '',
    }))


def staff_reset_request(request):
    return reset_request(request, 'staff')


def parents_reset_request(request):
    return reset_request(request, 'parents')


def staff_reset_confirm(request, uidb64, token):
    return reset_confirm(request, 'staff', uidb64, token)


def parents_reset_confirm(request, uidb64, token):
    return reset_confirm(request, 'parents', uidb64, token)


# ── branded error pages (handler404 / handler500) ──────────────────────

def _error_page(asset, status, request):
    site = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    return HttpResponse(_render(asset, {
        '__SITE_URL__': site or '/portal/login/',
        '__SITE_LABEL__': 'the website' if site else 'the Management Portal',
    }), status=status)


def branded_404(request, exception=None):
    return _error_page('error-404.html', 404, request)


def branded_500(request):
    logger = logging.getLogger('django.request')
    logger.error('500 rendered for path=%s ip=%s',
                 getattr(request, 'path', '?'), client_ip(request))
    return _error_page('error-500.html', 500, request)
