"""Phase 7 — player QR code cards.

Every child gets a QR code that opens their public profile page on the
academy website ({SITE_URL}/player.html?ref=XXXX). This module renders
print-friendly card pages:

  * /portal/qr/            staff  — every player, grouped by squad
  * /portal/qr/<ref>/      staff  — one player
  * /portal/parents/qr/<ref>/     guardian — own child only

Design notes
------------
* The QR is generated server-side with segno (pure Python, no network)
  and embedded as inline SVG — crisp at any print size.
* The encoded URL uses the PUBLIC website origin (SITE_URL in .env,
  written by install.sh). If it is unset (bare dev runserver) we fall
  back to the request origin and say so on screen.
* Profiles fail closed: an unpublished player's QR still prints (the
  office may want the card ready) but the card carries a clear warning
  that the profile page will answer "not available" until it is
  published. The public endpoint itself 404s unpublished players.
* CSP-safe: no inline event handlers — the Print button is bound by the
  allow-listed portal asset qr.js (access: any signed-in user).
"""
import io
from html import escape as _esc

import segno
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_GET

from .models import Player, Squad


def esc(s):
    return _esc(str(s), quote=True)

QR_ICON = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>'
    '<rect x="3" y="14" width="7" height="7" rx="1"/>'
    '<path d="M14 14h3v3h-3zM20 14v.01M14 20v.01M17.5 17.5h3M20 17v3"/></svg>'
)


def _site_base(request):
    """Public website origin for QR targets."""
    base = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    if base:
        return base, False
    return (f"{request.scheme}://{request.get_host()}").rstrip('/'), True


def _qr_svg(url):
    """segno → inline-able SVG string.

    BytesIO (segno's SVG writer emits bytes), xmldecl=False (no prolog
    when inlined in HTML), omitsize=True (no fixed width/height — the
    card CSS sizes the viewBox, so one SVG works on screen and print)."""
    buf = io.BytesIO()
    segno.make(url, error='m').save(buf, kind='svg', scale=8, border=2,
                                    dark='#000000', light=None,
                                    xmldecl=False, omitsize=True)
    return buf.getvalue().decode('utf-8')


def _card(p, base):
    url = f"{base}/player.html?ref={p.ref}"
    first = esc(p.first_name)
    full = f"{esc(p.first_name)} {esc(p.last_name)}"
    squad = esc(p.squad.label)
    ref = esc(p.ref)
    num = f"#{p.number:02d}" if p.number is not None else ""
    warn = '' if p.is_published else (
        '<div class="qrc-warn">Not published on the website yet — this code '
        'will show “profile not available” until the player is published '
        'from the dashboard.</div>')
    return (
        f'<article class="qrc{" qrc-draft" if not p.is_published else ""}">'
        f'<div class="qrc-qr" aria-hidden="true">{_qr_svg(url)}</div>'
        f'<h3>{full}</h3>'
        f'<div class="qrc-meta">{squad}{(" · " + num) if num else ""} · {ref}</div>'
        f'<div class="qrc-scan">Scan to view {first}&rsquo;s profile</div>'
        f'<div class="qrc-url">{esc(url)}</div>'
        f'{warn}</article>')


_PAGE_CSS = """
:root{--ink:#16233a;--muted:#5b6678;--line:#d8dde6;--amber:#f59d1e}
*{box-sizing:border-box;margin:0}
body{font:15px/1.5 'Segoe UI',system-ui,-apple-system,Arial,sans-serif;
color:var(--ink);background:#eef1f5;padding:22px}
.qr-toolbar{max-width:1060px;margin:0 auto 20px;display:flex;gap:14px;
align-items:center;flex-wrap:wrap;background:#fff;border:1px solid var(--line);
border-radius:12px;padding:14px 18px}
.qr-toolbar h1{font-size:17px;letter-spacing:.02em}
.qr-toolbar .note{color:var(--muted);font-size:13px;max-width:52ch}
.btn{display:inline-flex;align-items:center;gap:8px;border:0;border-radius:9px;
padding:10px 16px;font-weight:600;font-size:14px;cursor:pointer;
background:var(--amber);color:#231a06;text-decoration:none}
.btn.ghost{background:#fff;color:var(--ink);border:1.5px solid var(--line)}
.qr-wrap{max-width:1060px;margin:0 auto}
.qr-squad{margin:26px 0 10px;font-size:13px;font-weight:700;
letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.qr-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:16px}
.qrc{background:#fff;border:1.5px solid var(--line);border-radius:14px;
padding:18px 16px;text-align:center;page-break-inside:avoid;break-inside:avoid}
.qrc-draft{border-style:dashed;border-color:#c9a24a;background:#fffdf4}
.qrc-qr svg{width:158px;height:158px;display:block;margin:0 auto 10px}
.qrc h3{font-size:16.5px;margin-bottom:3px}
.qrc-meta{color:var(--muted);font-size:12.5px;letter-spacing:.04em}
.qrc-scan{margin-top:9px;font-size:13px;color:var(--ink)}
.qrc-url{margin-top:3px;font-size:10.5px;color:var(--muted);word-break:break-all}
.qrc-warn{margin-top:9px;font-size:11.5px;color:#7a5b12;background:#fdf3d7;
border:1px solid #ecd9a0;border-radius:8px;padding:6px 8px}
.qr-site-warn{max-width:1060px;margin:0 auto 18px;background:#fdecec;
border:1px solid #f0b9b9;color:#7c2a2a;border-radius:10px;padding:10px 14px;
font-size:13.5px}
@media print{
body{background:#fff;padding:0}
.qr-toolbar,.qr-site-warn{display:none}
.qr-grid{grid-template-columns:repeat(3,1fr);gap:10mm}
.qr-squad{margin:8mm 0 4mm}
.qrc{border:1.2pt solid #98a2b3;border-radius:8pt}
}
"""


def _page(request, sections, title, back_href, back_label, site_warn=False):
    secs = ''.join(
        f'<h2 class="qr-squad">{esc(label)}</h2>'
        f'<div class="qr-grid">{"".join(cards)}</div>'
        for label, cards in sections)
    warn = ('<div class="qr-site-warn"><b>Heads-up:</b> SITE_URL is not set in '
            'backend/.env, so these QR codes point at this server&rsquo;s current '
            'address. Run the installer (or set SITE_URL) before printing cards '
            'for hand-out.</div>') if site_warn else ''
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — Sporting Pearls</title>
<style>{_PAGE_CSS}</style></head>
<body>
<div class="qr-toolbar">
  <h1>{esc(title)}</h1>
  <button class="btn" id="btn-print" type="button">Print these cards</button>
  <a class="btn ghost" href="{esc(back_href)}">{esc(back_label)}</a>
  <span class="note">Each QR code opens the player&rsquo;s public profile on the
  academy website. Profiles show only public information — name, squad, number,
  position, age, motto and photo.</span>
</div>
{warn}
<div class="qr-wrap">
{secs}
</div>
<script src="/portal/assets/qr.js"></script>
</body></html>"""
    return HttpResponse(html)


@require_GET
def qr_all(request):
    """Staff — every player's QR card, grouped by squad."""
    from .portal import _staff  # noqa: F401 — decorator, lazy (no cycle)

    @_staff
    def _inner(request):
        base, warn = _site_base(request)
        sections = []
        for squad in Squad.objects.all():
            cards = [_card(p, base) for p in
                     squad.players.select_related('squad')]
            if cards:
                sections.append((squad.label, cards))
        if not sections:
            sections = [('No players yet',
                         ['<article class="qrc"><h3>No players registered</h3>'
                          '<div class="qrc-meta">Add players from the dashboard '
                          'first — their QR cards appear here.</div></article>'])]
        return _page(request, sections, 'Player QR code cards',
                     '/portal/', 'Back to dashboard', site_warn=warn)
    return _inner(request)


@require_GET
def qr_one(request, ref):
    """Staff — one player's QR card."""
    from .portal import _staff

    @_staff
    def _inner(request):
        p = (Player.objects.select_related('squad')
             .filter(ref=ref).first())
        if p is None:
            return HttpResponse(
                '<h1 style="font-family:system-ui;padding:30px">Player not found.</h1>',
                status=404)
        base, warn = _site_base(request)
        return _page(request, [(p.squad.label, [_card(p, base)])],
                     f'QR card — {p.first_name} {p.last_name}',
                     '/portal/', 'Back to dashboard', site_warn=warn)
    return _inner(request)


@require_GET
def parents_qr(request, ref):
    """Guardian — a QR card for their OWN child only."""
    u = request.user
    gp = getattr(u, 'guardian_profile', None) if u.is_authenticated else None
    if gp is None or not gp.is_active:
        if u.is_authenticated and u.is_staff:
            from django.shortcuts import redirect
            return redirect('/portal/qr/' + ref + '/')
        from django.shortcuts import redirect
        return redirect('/portal/parents/login/')
    from parents.models import GuardianPlayer
    p = (Player.objects.select_related('squad')
         .filter(ref=ref,
                 guardian_links__guardian=gp).first())
    if p is None:
        return _parents_not_available()
    base, warn = _site_base(request)
    return _page(request, [(p.squad.label, [_card(p, base)])],
                 f'QR card — {p.first_name} {p.last_name}',
                 '/portal/parents/', 'Back to parent portal', site_warn=warn)


def _parents_not_available():
    return HttpResponse(
        """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Not available — Sporting Pearls</title>
<style>body{font:15px/1.6 system-ui,sans-serif;color:#16233a;background:#eef1f5;
display:grid;place-items:center;min-height:90vh;margin:0}
.c{background:#fff;border:1px solid #d8dde6;border-radius:14px;padding:34px 38px;
max-width:430px;text-align:center}h1{font-size:19px;margin-bottom:8px}
a{color:#b96a00;font-weight:600}</style></head><body><div class="c">
<h1>This QR card is not available</h1>
<p>The player profile is not linked to your guardian account.</p>
<p style="margin-top:14px"><a href="/portal/parents/">Back to the parent portal</a></p>
</div></body></html>""", status=404)
