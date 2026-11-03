"""Management Portal — Cycle P3 staff desk pages (zero Django chrome).

Two branded pages reachable from the staff sidebar:

  /portal/desk/announcements/   composer + ledger (create, publish, broadcast)
  /portal/desk/complaints/      the welfare inbox (reply, note, status)

Role separation is inherited from portal._staff: parents are bounced to
their own portal on GET and rejected 403 on POST; anonymous users go to
the branded staff login. Emails leave through the same resend_send used
everywhere else (SP_MAIL_REDIRECT applies in QC mode).
"""
import re
from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import HttpResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie

from parents.models import (COMPLAINT_CATEGORIES, COMPLAINT_STATUS,
                            Announcement, Complaint, ComplaintReply, Guardian)
from parents.views import _esc, _mail, _st_chip, _portal_url
from submissions.email_branding import (announcement_payload,
                                        complaint_reply_payload)
from submissions.models import Squad
from submissions.portal import ASSETS, _staff

DESK_URLS = {
    'dash': '/portal/',
    'ann': '/portal/desk/announcements/',
    'comp': '/portal/desk/complaints/',
}

STAFF_CSS = '''
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
  background:radial-gradient(860px 360px at 88% -90px,rgba(31,122,111,.42),transparent 62%),
    radial-gradient(680px 320px at -80px 130%,rgba(245,157,30,.2),transparent 58%),
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
main{max-width:1060px;margin:26px auto 46px;padding:0 26px}
.card{background:#fff;border:1px solid #e7ebf2;border-radius:var(--r);box-shadow:var(--shadow-1)}
.sec-h{display:flex;align-items:center;gap:10px;margin:30px 0 14px}
.sec-h h3{font-family:Georgia,serif;font-size:20px;color:var(--navy);font-weight:600;position:relative;padding-left:15px}
.sec-h h3::before{content:'';position:absolute;left:0;top:3px;bottom:3px;width:5px;border-radius:4px;background:var(--gold)}
.foot{max-width:1060px;margin:0 auto;padding:22px 26px 40px;display:flex;gap:8px 18px;flex-wrap:wrap;align-items:center;
  color:var(--muted);font-size:13.5px;border-top:1px solid var(--hair)}
.foot b{color:var(--ink2);font-weight:600}
.foot .fbrand{margin-left:auto;font-size:12.5px;letter-spacing:.4px}
.note-ok{background:#eef7f0;border:1px solid #bfe0c8;color:#276749;border-radius:12px;padding:11px 15px;font-size:14.5px;
  margin-bottom:16px;box-shadow:inset 3px 0 0 #34a06b}
.note-err{background:#fdecea;border:1px solid #f3c2bb;color:#c0392b;border-radius:12px;padding:11px 15px;font-size:14.5px;
  margin-bottom:16px;box-shadow:inset 3px 0 0 #d9534f}
.stc{font-size:12.5px;font-weight:700;letter-spacing:1px;text-transform:uppercase;border-radius:999px;padding:4px 11px;
  display:inline-flex;align-items:center;gap:6px}
.stc::before{content:'';width:6px;height:6px;border-radius:50%;background:currentColor;flex:none}
.stc-open{background:#fdeee0;color:#a05a04}
.stc-rev{background:rgba(31,122,111,.1);color:#1f7a6f}
.stc-ok{background:#eef7f0;color:#276749}
.stc-off{background:#eef0f4;color:#5c6a7e}
.pill{font-size:12.5px;font-weight:700;letter-spacing:1.1px;text-transform:uppercase;border-radius:999px;padding:4px 11px;
  display:inline-flex;align-items:center;gap:6px}
.pill::before{content:'';width:6px;height:6px;border-radius:50%;background:currentColor;flex:none}
.pill-pub{background:#eef7f0;color:#276749}
.pill-draft{background:#fdeee0;color:#a05a04}
.chip{background:var(--gold);color:#122a52;font-size:12px;font-weight:800;letter-spacing:1.1px;text-transform:uppercase;
  border-radius:999px;padding:4px 11px;box-shadow:0 3px 10px rgba(245,157,30,.3)}
label{display:block;font-size:12px;font-weight:700;letter-spacing:1.2px;text-transform:uppercase;color:#7c88a1;margin:13px 0 6px}
input[type=text],select,textarea{width:100%;border:1.5px solid #d9dfe9;border-radius:11px;padding:10.5px 13px;font:inherit;
  font-size:15px;color:var(--ink);background:#fff;transition:border .15s,box-shadow .15s}
textarea{min-height:150px;resize:vertical;line-height:1.6}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--lagoon);box-shadow:0 0 0 3.5px rgba(31,122,111,.16)}
input::placeholder,textarea::placeholder{color:#9aa5b8}
button.act{margin-top:16px;background:var(--gold);color:#122a52;border:0;border-radius:11px;padding:12px 22px;font:inherit;
  font-size:14.5px;font-weight:700;cursor:pointer;transition:.16s;box-shadow:0 6px 16px rgba(245,157,30,.35)}
button.act:hover{transform:translateY(-1px);box-shadow:0 10px 22px rgba(245,157,30,.45)}
button.act:active{transform:none}
button.ghost{margin-top:0;background:transparent;border:1.5px solid #d9dfe9;color:var(--ink);border-radius:10px;
  padding:6.5px 13px;font:inherit;font-size:13.5px;font-weight:600;cursor:pointer;transition:.15s}
button.ghost:hover{border-color:var(--amber);color:#a05a04;background:rgba(245,157,30,.06)}
.row-check{display:inline-flex;align-items:center;gap:8px;font-size:14.5px;color:var(--ink);margin-top:14px;font-weight:500}
.row-check input{width:auto;accent-color:#a05a04}
.back{display:inline-flex;align-items:center;gap:7px;font-size:14px;font-weight:700;color:var(--lagoon);
  text-decoration:none;letter-spacing:.3px;margin-bottom:14px}
.back:hover{text-decoration:underline}
.grid2{display:grid;grid-template-columns:400px 1fr;gap:18px;align-items:start}
.grid2 .wide{grid-column:1/-1}
@media(max-width:880px){.grid2{grid-template-columns:1fr}}
@media(max-width:560px){.bar .who span{display:none}.top{padding:18px 18px 24px}main{padding:0 18px}.foot{padding:20px 18px 34px}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important;scroll-behavior:auto}}
'''


def _page(request, asset, tokens, active, status=200):
    body = (ASSETS / asset).read_text(encoding='utf-8')
    merged = {
        '__CSRF__': get_token(request),
        '__STAFF_CSS__': STAFF_CSS,
        '__USER__': _esc(request.user.get_username()),
        '__NAV_DASH__': 'class="active"' if active == 'dash' else '',
        '__NAV_ANN__': 'class="active"' if active == 'ann' else '',
        '__NAV_COMP__': 'class="active"' if active == 'comp' else '',
        **tokens,
    }
    for k, v in merged.items():
        body = body.replace(k, v)
    leftovers = re.findall(r'__[A-Z][A-Z_]+__', body)
    if leftovers:
        raise RuntimeError(f'UNREPLACED DESK TOKENS: {sorted(set(leftovers))}')
    return HttpResponse(body, status=status)


def _audience_label(squads):
    names = [s.label for s in squads]
    return ' · '.join(names) if names else 'All squads'


# ══ Announcements — composer + ledger ════════════════════════════════════

def _broadcast(a, request):
    """Email a published announcement to the parents it is visible to.
    Returns (sent, failed, total)."""
    from django.db.models import Q
    base = Guardian.objects.filter(is_active=True, user__is_active=True) \
        .exclude(user__email='').exclude(user__is_staff=True).distinct()
    squad_ids = list(a.squads.values_list('id', flat=True))
    if squad_ids:
        base = base.filter(Q(links__player__squad_id__in=squad_ids)).distinct()
    sent = failed = 0
    url = _portal_url(request, '/portal/parents/announcements/')
    for g in base.select_related('user').distinct():
        payload = announcement_payload(g.full_name, a.title, a.body,
                                       _audience_label(a.squads.all()), url)
        payload['to'] = [g.user.email.lower()]
        ok, _ = _mail('announcement-broadcast', payload)
        sent, failed = (sent + 1, failed) if ok else (sent, failed + 1)
    return sent, failed, sent + failed


@ensure_csrf_cookie
@_staff
def staff_announcements(request):
    error = ''
    if request.method == 'POST':
        title = (request.POST.get('title') or '').strip()[:150]
        body_txt = (request.POST.get('body') or '').strip()
        action = request.POST.get('action') or 'draft'
        squad_ids = [int(v) for v in request.POST.getlist('squads')
                     if str(v).isdigit()]
        squads = list(Squad.objects.filter(id__in=squad_ids))
        if len(title) < 4:
            error = 'Give the announcement a clear title (at least 4 characters).'
        elif len(body_txt) < 15:
            error = 'The announcement body needs a couple of sentences (at least 15 characters).'
        else:
            a = Announcement.objects.create(
                title=title, body=body_txt, created_by=request.user,
                is_published=False,
                pinned=bool(request.POST.get('pinned')))
            a.squads.set(squads)
            mailed = 0
            if action == 'publish':
                a.is_published = True
                a.published_at = timezone.now()
                a.save(update_fields=['is_published', 'published_at'])
                if request.POST.get('email_now'):
                    mailed, failed, _total = _broadcast(a, request)
                    if failed:
                        error = (f'Published and emailed to {mailed} parent(s), but '
                                 f'{failed} send(s) failed — check the server log.')
            qs = ('posted=1&mailed=' + str(mailed)) if action == 'publish' else 'drafted=1'
            errq = ('&err=' + quote(error)) if error else ''
            return redirect(f'/portal/desk/announcements/?{qs}{errq}')

    rows = []
    for a in Announcement.objects.select_related('created_by').prefetch_related('squads'):
        pub = a.is_published
        st_pill = ('<span class="pill pill-pub">Published</span>' if pub
                   else '<span class="pill pill-draft">Draft</span>')
        pin_pill = '<span class="chip">Pinned</span>' if a.pinned else ''
        action = 'Unpublish' if pub else 'Publish'
        toggle = (f'<form method="post" action="/portal/desk/announcements/{a.id}/toggle/" '
                  f'class="inlineform">{_csrf_input(request)}'
                  f'<button class="ghost" type="submit">{action}</button></form>')
        when = (f'{timezone.localtime(a.published_at):%d %b %Y · %H:%M}'
                if a.published_at else
                f'draft · created {timezone.localtime(a.created_at):%d %b %Y}')
        by = (f' · by {_esc(a.created_by.get_username())}' if a.created_by else '')
        rows.append(
            f'<div class="an-row card"><div class="an-main">'
            f'<div class="an-top">{st_pill}{pin_pill}'
            f'<span class="an-date">{_esc(when)}</span></div>'
            f'<h3>{_esc(a.title)}</h3>'
            f'<p>{_esc(a.body[:170].strip() + ("…" if len(a.body) > 170 else ""))}</p>'
            f'<span class="an-for">For: {_esc(_audience_label(a.squads.all()))}{by}</span>'
            f'</div><div class="an-acts">{toggle}</div></div>')
    if not rows:
        rows.append('<div class="an-row card"><div class="an-main"><h3>No announcements yet</h3>'
                    '<p>Compose the first notice on the left — parents see it the moment '
                    'it is published.</p></div></div>')

    squad_boxes = '\n'.join(
        f'<label class="sq-check"><input type="checkbox" name="squads" value="{s.id}">'
        f'<span class="sqdot" style="background:{_esc(s.accent)}"></span>{_esc(s.label)}</label>'
        for s in Squad.objects.order_by('sort'))
    note = ''
    if request.GET.get('err'):
        note = f'<div class="note-err">{_esc(request.GET.get("err"))}</div>'
    elif request.GET.get('posted'):
        m = request.GET.get('mailed', '0')
        note = ('<div class="note-ok">Announcement published — it is live on the parents&#8217; '
                f'board{f" and emailed to {m} parent(s)" if m != "0" else ""}.</div>')
    elif request.GET.get('drafted'):
        note = '<div class="note-ok">Draft saved — publish it from the list when it is ready.</div>'
    elif error:
        note = f'<div class="note-err">{_esc(error)}</div>'

    return _page(request, 'desk-announcements.html', {
        '__NOTE__': note,
        '__SQUAD_BOXES__': squad_boxes,
        '__ANN_ROWS__': '\n'.join(rows),
        '__N_PUB__': str(Announcement.objects.filter(is_published=True).count()),
        '__N_DRAFT__': str(Announcement.objects.filter(is_published=False).count()),
    }, 'ann')


def _csrf_input(request):
    return f'<input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">'


@_staff
def staff_announcement_toggle(request, aid):
    """POST only: flip publish state; first publish stamps published_at."""
    if request.method != 'POST':
        return redirect('/portal/desk/announcements/')
    a = Announcement.objects.filter(id=aid).first()
    if a is None:
        return redirect('/portal/desk/announcements/?err=Announcement+not+found')
    a.is_published = not a.is_published
    if a.is_published and a.published_at is None:
        a.published_at = timezone.now()
    a.save(update_fields=['is_published', 'published_at'])
    return redirect('/portal/desk/announcements/?posted=1&mailed=0'
                    if a.is_published else '/portal/desk/announcements/?drafted=1')


# ══ Complaints — the welfare inbox ═══════════════════════════════════════

@ensure_csrf_cookie
@_staff
def staff_complaints(request):
    cur = request.GET.get('s', 'all')
    if cur not in ('all',) + tuple(dict(COMPLAINT_STATUS)):
        cur = 'all'
    qs = Complaint.objects.select_related('guardian', 'player', 'player__squad')
    if cur != 'all':
        qs = qs.filter(status=cur)
    counts = {'all': Complaint.objects.count()}
    for code, _lbl in COMPLAINT_STATUS:
        counts[code] = Complaint.objects.filter(status=code).count()
    chips = []
    for code, lbl in [('all', 'All')] + list(COMPLAINT_STATUS):
        active = ' on' if code == cur else ''
        chips.append(
            f'<a class="fchip{active}" href="/portal/desk/complaints/?s={code}">'
            f'{_esc(lbl)} <span class="cn">{counts.get(code, 0)}</span></a>')
    rows = []
    for c in qs:
        n = c.replies.count()
        child = (f'{c.player.first_name} {c.player.last_name}' if c.player else 'Whole family')
        rows.append(
            f'<a class="case card" href="/portal/desk/complaints/{c.id}/">'
            f'<span class="case-main"><span class="case-top">{_st_chip(c.status)}'
            f'<h3>{_esc(c.subject)}</h3><code class="case-ref">#{c.id}</code></span>'
            f'<span class="case-meta">{_esc(c.guardian.full_name)} · '
            f'{_esc(c.get_category_display())} · {_esc(child)} · {n} message'
            f'{"s" if n != 1 else ""}</span></span>'
            f'<span class="case-side"><span class="case-date">activity '
            f'{timezone.localtime(c.updated_at):%d %b}</span></span></a>')
    if not rows:
        rows.append('<div class="case card"><span class="case-main"><h3>Nothing here</h3>'
                    '<span class="case-meta">No cases with this status.</span></span></div>')
    open_n = Complaint.objects.filter(status__in=('open', 'in_review')).count()
    return _page(request, 'desk-complaints.html', {
        '__CHIPS__': '\n'.join(chips),
        '__CASE_ROWS__': '\n'.join(rows),
        '__OPEN_N__': str(open_n),
    }, 'comp')


@ensure_csrf_cookie
@_staff
def staff_complaint_detail(request, cid):
    c = (Complaint.objects.select_related('guardian', 'player', 'player__squad')
         .filter(id=cid).first())
    if c is None:
        return redirect('/portal/desk/complaints/?s=all')
    error = ''
    if request.method == 'POST':
        action = request.POST.get('action') or 'reply'
        if action == 'status':
            new = request.POST.get('status')
            if new in dict(COMPLAINT_STATUS):
                c.status = new
                if c.assigned_to is None:
                    c.assigned_to = request.user
                c.save()
            return redirect(f'/portal/desk/complaints/{c.id}/?ok=status')
        body_txt = (request.POST.get('message') or '').strip()
        internal = bool(request.POST.get('internal'))
        if len(body_txt) < 3:
            error = 'Write the reply first.'
        else:
            ComplaintReply.objects.create(
                complaint=c, by_staff=request.user, body=body_txt,
                is_internal=internal)
            if not internal:
                if c.status == 'open':
                    c.status = 'in_review'
                if c.assigned_to is None:
                    c.assigned_to = request.user
                c.save()
                excerpt = body_txt[:180] + ('…' if len(body_txt) > 180 else '')
                payload = complaint_reply_payload(
                    c.guardian.full_name, f'#{c.id}', c.subject, excerpt,
                    _portal_url(request, f'/portal/parents/complaints/{c.id}/'))
                payload['to'] = [c.guardian.user.email.lower() if c.guardian.user.email
                                 else c.guardian.user.get_username()]
                _mail('complaint-reply', payload)
            else:
                c.save()
            return redirect(f'/portal/desk/complaints/{c.id}/?ok='
                            + ('note' if internal else 'reply'))

    thread = []
    entries = [('guardian', c.guardian.full_name, c.created_at, c.message, False)]
    for r in c.replies.select_related('by_staff'):
        if r.by_staff is not None:
            who = f'Staff · {r.by_staff.get_username()}'
            kind = 'staff'
        else:
            who = c.guardian.full_name
            kind = 'guardian'
        entries.append((kind, who, r.created_at, r.body, r.is_internal))
    for kind, who, when, body_txt, internal in entries:
        badge = ('<span class="int">Internal note — never shown to the parent</span>'
                 if internal else '')
        thread.append(
            f'<div class="msg {kind}{" internal" if internal else ""}">'
            f'<div class="msg-h"><b>{_esc(who)}</b>{badge}'
            f'<span>{_esc(f"{timezone.localtime(when):%A %d %B %Y · %H:%M}")}</span></div>'
            f'<div class="msg-b"><p>{_paras(body_txt)}</p></div></div>')

    status_btns = '\n'.join(
        f'<form method="post" class="inlineform" action="/portal/desk/complaints/{c.id}/">'
        f'{_csrf_input(request)}<input type="hidden" name="action" value="status">'
        f'<input type="hidden" name="status" value="{code}">'
        f'<button class="ghost{" curst" if c.status == code else ""}" type="submit">'
        f'{_esc(lbl)}</button></form>'
        for code, lbl in COMPLAINT_STATUS)
    ok = request.GET.get('ok')
    note = ''
    if ok == 'reply':
        note = ('<div class="note-ok">Reply sent — the parent has been notified by '
                'email and it is visible in their portal.</div>')
    elif ok == 'note':
        note = ('<div class="note-ok">Internal note saved — it stays invisible to '
                'the parent and other cases cannot see it.</div>')
    elif ok == 'status':
        note = '<div class="note-ok">Case status updated.</div>'
    elif error:
        note = f'<div class="note-err">{_esc(error)}</div>'

    child = (f'{c.player.first_name} {c.player.last_name} · '
             f'{c.player.squad.label}' if c.player else 'Whole family')
    phone = c.guardian.phone or '—'
    return _page(request, 'desk-complaint.html', {
        '__NOTE__': note,
        '__CASE_REF_NUM__': str(c.id),
        '__CASE_REF__': f'#{c.id}',
        '__CASE_SUBJECT__': _esc(c.subject),
        '__CASE_STATUS__': _st_chip(c.status),
        '__CASE_GUARDIAN__': _esc(c.guardian.full_name),
        '__CASE_RELATION__': _esc(c.guardian.get_relation_display()),
        '__CASE_PHONE__': _esc(phone),
        '__CASE_CAT__': _esc(c.get_category_display()),
        '__CASE_CHILD__': _esc(child),
        '__CASE_OPENED__': _esc(f'{timezone.localtime(c.created_at):%A %d %B %Y}'),
        '__CASE_UPDATED__': _esc(f'{timezone.localtime(c.updated_at):%d %b %Y · %H:%M}'),
        '__THREAD__': '\n'.join(thread),
        '__STATUS_BTNS__': status_btns,
    }, 'comp')


def _paras(body):
    paras = [p.strip().replace('\n', '<br>') for p in body.split('\n\n') if p.strip()]
    return '</p><p>'.join(_esc(p) for p in paras) or '—'
