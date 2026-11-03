"""Management Portal — the restricted DSO desk (Phase 1, zero Django chrome).

/portal/dso/            report queue (ref, status, categories, child, age)
/portal/dso/r/<ref>/    full report + status workflow + case notes + audit
/portal/dso/audit/      the append-only access & action log

Access is the strictest in the system: an active, signed-in staff user
who has EXPLICITLY been granted the DSO role (submissions.safeguarding.
DSO_GROUP — granted with `manage.py sp_dso grant <username>`). Everyone
else — including superusers without the role — receives a neutral 403
page that confirms nothing about what is behind the door.

Every meaningful action writes a SafeguardingAuditEntry: views, status
changes, assignments, case notes. Nothing is ever deleted; the audit
model refuses updates at the application layer.
"""
import html as _html_mod
import re
from pathlib import Path
from urllib.parse import quote

from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from parents.views import _esc
from submissions.models import SafeguardingAuditEntry, SafeguardingReport
from submissions.portal import ASSETS, _staff
from submissions.portal_desk import STAFF_CSS
from submissions.safeguarding import DSO_GROUP, SAFEGUARDING_STATUS, is_dso

DSO_URLS = {
    'dash': '/portal/',
    'reports': '/portal/dso/',
    'audit': '/portal/dso/audit/',
}

STATUS_LABEL = dict(SAFEGUARDING_STATUS)
STATUS_CHIP = {
    'received': ('stc-open', 'Received'),
    'under_review': ('stc-rev', 'Under review'),
    'escalated_external': ('stc-esc', 'Escalated'),
    'actioned': ('stc-ok', 'Actioned'),
    'closed': ('stc-off', 'Closed'),
}

DSO_CSS = STAFF_CSS + '''
.stc-esc{background:#fdecea;color:#c0392b}
.dso-alert{display:flex;gap:14px;align-items:flex-start;border:1.5px dashed rgba(192,57,43,.45);
  background:rgba(192,57,43,.05);border-radius:14px;padding:14px 17px;margin-bottom:18px}
.dso-alert b{color:var(--navy)}
.dso-alert p{font-size:14px;color:#5c6a7e;line-height:1.55;margin-top:2px}
.rep{display:flex;align-items:flex-start;gap:12px;padding:15px 18px;text-decoration:none;
  color:inherit;transition:.15s;margin-bottom:12px}
.rep:hover{border-color:rgba(245,157,30,.6);transform:translateY(-1px)}
.rep-main{min-width:0;flex:1}
.rep-top{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.rep-top h3{font-family:Georgia,serif;font-size:15.5px;color:var(--navy);font-weight:600}
.rep-ref{font-family:'Sarasa Mono SC',monospace;font-size:12.5px;color:#7c88a1;background:#f3f5f9;border-radius:6px;padding:1.5px 7px}
.rep-meta{font-size:13.5px;color:#5c6a7e;margin-top:4px}
.rep-side{flex:none;text-align:right}
.rep-date{font-size:12.5px;color:var(--muted)}
.meta{display:grid;gap:9px}
.meta .row{display:grid;grid-template-columns:150px 1fr;gap:10px;font-size:14.5px;
  align-items:start;border-bottom:1px dashed var(--hair);padding-bottom:8px}
.meta .row span{color:#7c88a1;font-size:12px;font-weight:700;letter-spacing:1px;text-transform:uppercase;padding-top:3px}
.meta .row b{color:var(--ink);font-weight:500;line-height:1.55;word-break:break-word}
.narr{background:#fdfbf7;border:1.5px solid #efe7d6;border-radius:12px;padding:16px 18px;
  font-size:14.5px;line-height:1.7;color:var(--ink);white-space:pre-wrap;word-break:break-word}
.audit-row{display:grid;grid-template-columns:150px 170px 1fr;gap:12px;padding:11px 4px;
  border-bottom:1px dashed var(--hair);font-size:13.5px}
.audit-row:last-child{border-bottom:0}
.audit-when{color:var(--muted)}
.audit-act{font-weight:700;color:var(--navy)}
.audit-det{color:#5c6a7e;line-height:1.55;word-break:break-word}
.audit-det code{font-family:'Sarasa Mono SC',monospace;background:#f3f5f9;border-radius:5px;padding:1px 6px;font-size:12.5px}
.strow{display:flex;gap:8px;flex-wrap:wrap}
.strow .ghost.curst{border-color:var(--lagoon);color:var(--lagoon);background:rgba(31,122,111,.07)}
.pane h3{font-family:Georgia,serif;font-size:17px;color:var(--navy);font-weight:600;margin-bottom:10px}
.pane .sub{font-size:13px;color:var(--muted);margin:2px 0 14px}
@media(max-width:720px){.audit-row{grid-template-columns:1fr;gap:3px}.meta .row{grid-template-columns:120px 1fr}}
'''


def _forbidden(request):
    """Neutral 403: confirms nothing about what lives behind this door."""
    body = (ASSETS / 'dso-forbidden.html').read_text(encoding='utf-8')
    return HttpResponse(body, status=403)


def _dso(view):
    """_staff (login + is_staff) AND the explicit DSO role."""
    @_staff
    def staff_first(request, *args, **kwargs):
        if not is_dso(request.user):
            return _forbidden(request)
        return view(request, *args, **kwargs)
    return staff_first


def _page(request, asset, tokens, active, status=200):
    body = (ASSETS / asset).read_text(encoding='utf-8')
    merged = {
        '__CSRF__': get_token(request),
        '__DSO_CSS__': DSO_CSS,
        '__USER__': _esc(request.user.get_username()),
        '__NAV_DASH__': 'class="active"' if active == 'dash' else '',
        '__NAV_REPORTS__': 'class="active"' if active == 'reports' else '',
        '__NAV_AUDIT__': 'class="active"' if active == 'audit' else '',
        **tokens,
    }
    for k, v in merged.items():
        body = body.replace(k, v)
    leftovers = re.findall(r'__[A-Z][A-Z_]+__', body)
    if leftovers:
        raise RuntimeError(f'UNREPLACED DSO TOKENS: {sorted(set(leftovers))}')
    return HttpResponse(body, status=status)


def _chip(status):
    cls, label = STATUS_CHIP.get(status, ('stc-off', status))
    return f'<span class="stc {cls}">{_esc(label)}</span>'


def _fmt(d):
    return f'{timezone.localtime(d):%d %b %Y · %H:%M}'


def _notify_label(r):
    """Human wording for the DSO-notification outcome (no raw config text)."""
    s = (r.email_status or '').strip()
    if s == 'sent':
        return 'Yes — notification email sent'
    if s == 'pending':
        return 'Pending'
    if 'skipped' in s:
        return 'No email configured — report is desk-only'
    if s:
        return 'Notification failed — see the audit log'
    return 'Pending'


def _ago(d, now):
    n = (now.date() - timezone.localtime(d).date()).days
    return 'today' if n <= 0 else ('yesterday' if n == 1 else f'{n} days ago')


def _audit_user(request):
    return request.user, request.user.get_username()


def _audit(report, request, action, detail=''):
    actor, actor_name = _audit_user(request)
    return SafeguardingAuditEntry.objects.create(
        report=report, report_ref=report.ref, actor=actor,
        actor_username=actor_name, action=action, detail=detail)


def _csrf_input(request):
    return f'<input type="hidden" name="csrfmiddlewaretoken" value="{get_token(request)}">'


# ══ Queue ═════════════════════════════════════════════════════════════════

@ensure_csrf_cookie
@_dso
def dso_reports(request):
    cur = request.GET.get('s', 'all')
    valid = ('all',) + tuple(dict(SAFEGUARDING_STATUS))
    if cur not in valid:
        cur = 'all'
    qs = SafeguardingReport.objects.select_related('assigned_to')
    if cur != 'all':
        qs = qs.filter(status=cur)
    counts = {'all': SafeguardingReport.objects.count()}
    for code, _lbl in SAFEGUARDING_STATUS:
        counts[code] = SafeguardingReport.objects.filter(status=code).count()

    chips = []
    for code, lbl in [('all', 'All')] + list(SAFEGUARDING_STATUS):
        active = ' on' if code == cur else ''
        chips.append(f'<a class="fchip{active}" href="/portal/dso/?s={code}">'
                     f'{_esc(lbl)} <span class="cn">{counts.get(code, 0)}</span></a>')

    now = timezone.now()
    rows = []
    for r in qs:
        child = _esc(r.child_name or '(child not identified)')
        cats = _esc(r.categories or '—')
        pref = 'Anonymous' if r.reporter_preference == 'anonymous' else 'Confidential'
        assigned = (f' · {_esc(r.assigned_to.get_username())}' if r.assigned_to else '')
        rows.append(
            f'<a class="rep card" href="/portal/dso/r/{_esc(r.ref)}/">'
            f'<span class="rep-main"><span class="rep-top">{_chip(r.status)}'
            f'<h3>{child}</h3><code class="rep-ref">{_esc(r.ref)}</code></span>'
            f'<span class="rep-meta">{cats} · {pref}{assigned}</span></span>'
            f'<span class="rep-side"><span class="rep-date">{_esc(_fmt(r.created_at))}'
            f'<br>{_esc(_ago(r.created_at, now))}</span></span></a>')
    if not rows:
        rows.append('<div class="rep card"><span class="rep-main"><h3>Nothing here</h3>'
                    '<span class="rep-meta">No reports with this status.</span></span></div>')

    open_n = counts.get('received', 0) + counts.get('under_review', 0)
    return _page(request, 'dso-reports.html', {
        '__CHIPS__': '\n'.join(chips),
        '__REP_ROWS__': '\n'.join(rows),
        '__OPEN_N__': str(open_n),
        '__TOTAL_N__': str(counts.get('all', 0)),
    }, 'reports')


# ══ Report detail ═════════════════════════════════════════════════════════

@ensure_csrf_cookie
@_dso
def dso_report_detail(request, ref):
    r = SafeguardingReport.objects.select_related('assigned_to').filter(ref=ref).first()
    if r is None:
        return redirect('/portal/dso/')
    note = ''

    if request.method == 'POST':
        action = request.POST.get('action') or ''
        if action == 'status':
            new = request.POST.get('status', '')
            if new in dict(SAFEGUARDING_STATUS) and new != r.status:
                old_label = STATUS_LABEL.get(r.status, r.status)
                r.status = new
                if r.assigned_to is None:
                    r.assigned_to = request.user
                r.save(update_fields=['status', 'assigned_to', 'updated_at'])
                _audit(r, request, 'status_changed',
                       f'{old_label} → {STATUS_LABEL.get(new, new)}')
                return redirect(f'/portal/dso/r/{r.ref}/?ok=status')
        elif action == 'assign':
            if r.assigned_to_id != request.user.id:
                r.assigned_to = request.user
                r.save(update_fields=['assigned_to', 'updated_at'])
                _audit(r, request, 'assigned',
                       f'assigned to {request.user.get_username()}')
            return redirect(f'/portal/dso/r/{r.ref}/?ok=assign')
        elif action == 'note':
            body_txt = (request.POST.get('note') or '').strip()
            if len(body_txt) < 3:
                note = 'Write the case note first.'
            else:
                _audit(r, request, 'note_added', body_txt[:5000])
                return redirect(f'/portal/dso/r/{r.ref}/?ok=note')
        else:
            return redirect(f'/portal/dso/r/{r.ref}/')

    # every full view of the report is audited
    _audit(r, request, 'viewed', '')

    def row(label, value):
        v = str(value or '').strip()
        return (f'<div class="row"><span>{_esc(label)}</span>'
                f'<b>{_esc(v) if v else "—"}</b></div>')

    identity = (
        row('Reporting preference',
            'Completely anonymous' if r.reporter_preference == 'anonymous'
            else 'Confidential (identity known to DSO only)'))
    if r.reporter_preference != 'anonymous':
        identity += (row('Reporter name', r.reporter_name)
                     + row('Reporter role', r.reporter_role)
                     + row('Reporter phone', r.reporter_contact)
                     + row('Reporter email', r.reporter_email))

    detail_rows = (
        row('Child / player', r.child_name)
        + row('Estimated age / DOB', r.child_age)
        + row('Squad tier', r.squad)
        + row('Incident categories', r.categories.replace('; ', ' · ') if r.categories else '')
        + row('Persons in question', r.persons_in_question)
        + row('Date of incident', r.incident_date)
        + row('Approximate time', r.incident_time)
        + row('Location', r.location)
        + row('Witnesses', r.witnesses)
        + row('Disclosed to others', r.disclosure_history)
        + row('External authority', r.external_authority)
        + row('OB / police reference', r.police_ob))

    assigned_label = (r.assigned_to.get_username() if r.assigned_to else 'Unassigned')
    status_btns = '\n'.join(
        f'<form method="post" class="inlineform" action="/portal/dso/r/{_esc(r.ref)}/">'
        f'{_csrf_input(request)}<input type="hidden" name="action" value="status">'
        f'<input type="hidden" name="status" value="{code}">'
        f'<button class="ghost{" curst" if r.status == code else ""}" type="submit">'
        f'{_esc(lbl)}</button></form>'
        for code, lbl in SAFEGUARDING_STATUS)

    audit_rows = []
    for e in r.audit_entries.all():
        audit_rows.append(
            f'<div class="audit-row"><span class="audit-when">{_esc(_fmt(e.created_at))}</span>'
            f'<span class="audit-act">{_esc(e.get_action_display())} · '
            f'<small style="color:#7c88a1;font-weight:500">{_esc(e.actor_username)}</small></span>'
            f'<span class="audit-det">{_esc(e.detail) if e.detail else "&#8212;"}</span></div>')
    audit_html = '\n'.join(audit_rows) or '<p class="sub">No entries yet.</p>'

    ok = request.GET.get('ok')
    oknote = ''
    if ok == 'status':
        oknote = '<div class="note-ok">Status updated — the change is in the audit trail.</div>'
    elif ok == 'note':
        oknote = '<div class="note-ok">Case note saved to the audit trail.</div>'
    elif ok == 'assign':
        oknote = '<div class="note-ok">The report is now assigned to you.</div>'
    elif note:
        oknote = f'<div class="note-err">{_esc(note)}</div>'

    return _page(request, 'dso-report.html', {
        '__NOTE__': oknote,
        '__REF__': _esc(r.ref),
        '__STATUS__': _chip(r.status),
        '__RECEIVED__': _esc(_fmt(r.created_at)),
        '__ASSIGNED__': _esc(assigned_label),
        '__NOTIFY__': _esc(_notify_label(r)),
        '__IDENTITY__': identity,
        '__DETAIL__': detail_rows,
        '__NARRATIVE__': _esc(r.narrative or '(no narrative given)'),
        '__STATUS_BTNS__': status_btns,
        '__AUDIT__': audit_html,
        '__ASSIGN_STATE__': ('hidden' if r.assigned_to_id == request.user.id else ''),
    }, 'reports')


# ══ Audit log ═════════════════════════════════════════════════════════════

@ensure_csrf_cookie
@_dso
def dso_audit(request):
    cur = request.GET.get('a', 'all')
    valid = ('all',) + tuple(dict(SafeguardingAuditEntry.ACTION_CHOICES))
    if cur not in valid:
        cur = 'all'
    qs = SafeguardingAuditEntry.objects.select_related('report', 'actor')
    if cur != 'all':
        qs = qs.filter(action=cur)
    counts = {'all': SafeguardingAuditEntry.objects.count()}
    for code, _lbl in SafeguardingAuditEntry.ACTION_CHOICES:
        counts[code] = SafeguardingAuditEntry.objects.filter(action=code).count()

    chips = [f'<a class="fchip{" on" if cur == "all" else ""}" href="/portal/dso/audit/">'
             f'All <span class="cn">{counts.get("all", 0)}</span></a>']
    for code, lbl in SafeguardingAuditEntry.ACTION_CHOICES:
        chips.append(f'<a class="fchip{" on" if cur == code else ""}" '
                     f'href="/portal/dso/audit/?a={code}">{_esc(lbl)} '
                     f'<span class="cn">{counts.get(code, 0)}</span></a>')

    rows = []
    for e in qs[:400]:
        link = (f'/portal/dso/r/{_esc(e.report_ref)}/' if e.report_id else '')
        ref_html = (f'<a href="{link}" style="color:var(--lagoon);font-weight:600">'
                    f'{_esc(e.report_ref)}</a>' if link else f'<code>{_esc(e.report_ref)}</code>')
        rows.append(
            f'<div class="audit-row"><span class="audit-when">{_esc(_fmt(e.created_at))}</span>'
            f'<span class="audit-act">{_esc(e.get_action_display())} · {ref_html} · '
            f'<small style="color:#7c88a1;font-weight:500">{_esc(e.actor_username)}</small></span>'
            f'<span class="audit-det">{_esc(e.detail) if e.detail else "&#8212;"}</span></div>')
    if not rows:
        rows.append('<p class="sub">The log is empty.</p>')

    return _page(request, 'dso-audit.html', {
        '__CHIPS__': '\n'.join(chips),
        '__AUDIT__': '\n'.join(rows),
        '__TOTAL_N__': str(counts.get('all', 0)),
    }, 'audit')
