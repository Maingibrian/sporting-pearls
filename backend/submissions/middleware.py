"""Phase 2/5 security middleware — response headers + admin-login throttling.

SecurityHeadersMiddleware adds the headers Django's SecurityMiddleware
does not ship: Content-Security-Policy, Permissions-Policy and
Cross-Origin-Opener-Policy, on EVERY Django-served response (portal,
parent portal, DSO desk, admin, API, /media/).

CSP rationale (PRODUCTION-READINESS.md §4):
  * script-src is 'self' with NO 'unsafe-inline' as of Phase 5 (R27
    closed): every inline onerror=/onclick= handler on the public site
    moved to data-fb attributes handled by assets/js/shared/
    img-fallback.js; the three pages with inline <script> blocks
    (core-values, our-story, vision-mission) load external files; the
    portal dashboard script moved to /portal/assets/dash.js; Django's
    own admin templates were verified to contain no inline scripts or
    event handlers (Django 6.1.2). Google Fonts and the CDN script
    libraries (gsap/lenis/splittype) are self-hosted, so nothing needs
    a third-party script origin.
  * style-src keeps 'unsafe-inline': the pages use inline style=""
    attributes and the portal inlines its CSS. No script can be
    injected through a style attribute under script-src 'self'.
  * The static website gets the identical policy from the nginx
    templates (add_header in location /) so headers exist with or
    without the Django backend in the request path.

AdminLoginThrottle: POST /admin/login/ is rate-limited per IP
(8 attempts / 15 min) — the branded portals had throttling since
Phase 1 parents work, but the Django admin login had none.
"""
import logging

from django.core.cache import cache
from django.http import HttpResponse

logger = logging.getLogger('sporting.auth')

CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "object-src 'none'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'"
)

PERMISSIONS_POLICY = 'camera=(), microphone=(), geolocation=(), payment=()'

ADMIN_LOGIN_LIMIT = 8            # POST attempts per window…
ADMIN_LOGIN_WINDOW = 900         # …of 15 minutes, per IP


def client_ip(request):
    fwd = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return fwd.split(',')[0].strip() or request.META.get('REMOTE_ADDR', '')


class SecurityHeadersMiddleware:
    """CSP + Permissions-Policy + COOP on every response this app serves."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault('Content-Security-Policy', CSP_POLICY)
        response.headers.setdefault('Permissions-Policy', PERMISSIONS_POLICY)
        response.headers.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        return response


class AdminLoginThrottle:
    """Per-IP throttle on the Django admin login form.

    Counts only FAILED attempts (form re-rendered, status 200); a
    successful sign-in (302) clears the counter. Hitting the limit
    returns a plain 429 page without touching the auth stack.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        is_target = (request.method == 'POST'
                     and request.path == '/admin/login/')
        if is_target:
            key = f'sp-admlg:{client_ip(request)}'
            try:
                if cache.get(key) is None:
                    cache.add(key, 0, ADMIN_LOGIN_WINDOW)
                count = cache.get(key, 0)
            except ValueError:
                count = 0
            if count >= ADMIN_LOGIN_LIMIT:
                logger.warning('admin login throttle tripped for ip=%s',
                               client_ip(request))
                return HttpResponse(
                    '<!doctype html><meta charset="utf-8"><title>Too many attempts</title>'
                    '<body style="font-family:system-ui;padding:40px;color:#1a2436;background:#fbfaf7">'
                    '<h1>Too many sign-in attempts</h1>'
                    '<p>For security, admin sign-in from this connection is paused '
                    'for 15 minutes. Please try again shortly.</p></body>',
                    status=429)
            request._sp_admin_login_key = key
        response = self.get_response(request)

        key = getattr(request, '_sp_admin_login_key', None)
        if key:
            try:
                if response.status_code in (301, 302):
                    cache.delete(key)          # success — reset the counter
                elif response.status_code == 200:
                    cache.incr(key)            # failure — form re-rendered
            except ValueError:
                pass
        return response
