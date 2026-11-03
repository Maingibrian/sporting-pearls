"""Branded HTML emails + the academy email signature — shared by all mail.

Every outbound email now ships as multipart (text + html): Resend accepts an
`html` key alongside `text`, and email clients render whichever part they
support. Everything here is deliberately email-client-safe:

  · table layout, inline styles only (no <style> block dependence)
  · web-safe font stacks — Georgia stands in for Fraunces (display),
    Arial for Work Sans (body)
  · brand tokens mirrored from portal_assets/styles.css
    (navy #0c1a33/#14284b · amber #f59d1e · pearl #fbfaf7 · sand #f3efe7)
  · "bulletproof" CTA buttons (real <table> + bgcolor, not background-image)

The signature is a *text* email signature (name block + contacts) — not an
illustration — exactly like a professional mailbox signature.
"""
import html as _html_mod

_esc = _html_mod.escape

# ── brand tokens (mirror portal_assets/styles.css) ───────────────────────
NAVY_2 = '#0c1a33'
NAVY = '#14284b'
INK = '#0b1a36'
BODY = '#2f3b4d'
MUTED = '#5c6a7e'
FAINT = '#98a1b0'
AMBER = '#f59d1e'
AMBER_2 = '#d97f06'
AMBER_INK = '#a05a04'
PEARL = '#fbfaf7'
SAND = '#f3efe7'
SAND_BORDER = '#e7e2d8'
SAND_INK = '#7a5410'
HAIR = '#e3e6ec'

BRAND_NAME = 'Sporting Pearls Football Academy'
BRAND_SHORT = 'Sporting Pearls'
LOCATION = 'Mtwapa · Kilifi County, Kenya'
CONTACT_EMAIL = 'info@sportingpearlsacademy.org'
WEB_URL = 'https://www.sportingpearlsacademy.org'
WEB_LABEL = 'sportingpearlsacademy.org'
TAGLINE = 'Developing talent. Building character. Transforming lives.'

SERIF = "Georgia,'Times New Roman',Times,serif"
SANS = "Arial,'Helvetica Neue',Helvetica,sans-serif"
MONO = "'Courier New',Courier,monospace"


# ── the email signature (a real text signature, not an image) ───────────
def signature_html():
    return f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="margin-top:30px;border-top:1px solid {HAIR};">
  <tr><td style="padding-top:20px;">
    <p style="margin:0 0 14px;font:{SANS};font-size:14.5px;color:{BODY};">Warm regards,</p>
    <p style="margin:0;font:{SERIF};font-size:16px;font-weight:bold;color:{NAVY};">The Academy Office</p>
    <p style="margin:3px 0 0;font:{SANS};font-size:14.5px;line-height:1.65;color:{MUTED};">
      Admissions &amp; Parent Liaison<br>
      <span style="color:{NAVY};font-weight:bold;">{BRAND_NAME}</span><br>
      {LOCATION}
    </p>
    <p style="margin:12px 0 0;font:{SANS};font-size:14.5px;line-height:1.7;">
      <a href="mailto:{CONTACT_EMAIL}"
         style="color:{AMBER_INK};font-weight:bold;text-decoration:none;">{CONTACT_EMAIL}</a><br>
      <a href="{WEB_URL}"
         style="color:{AMBER_INK};font-weight:bold;text-decoration:none;">{WEB_LABEL}</a>
    </p>
    <p style="margin:14px 0 0;font:{SANS};font-size:12.5px;letter-spacing:1.8px;color:{FAINT};">
      EST. 2020&nbsp;&nbsp;·&nbsp;&nbsp;{_esc(TAGLINE).upper()}
    </p>
  </td></tr>
</table>'''


def signature_text():
    return f"""—
Warm regards,

The Academy Office
Admissions & Parent Liaison
{BRAND_NAME}
{LOCATION}
{CONTACT_EMAIL}
{WEB_LABEL}

{TAGLINE}"""


# ── shared shell: navy header + white card + navy footer ────────────────
def _crest():
    return ('<table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>'
            '<td width="46" height="46" align="center" valign="middle" bgcolor="' + AMBER + '" '
            'style="border-radius:13px;font:' + SERIF + ';font-size:20px;font-weight:bold;'
            'color:' + NAVY_2 + ';box-shadow:inset 0 1px 0 rgba(255,255,255,.35);">SP</td>'
            '</tr></table>')


def _header():
    return f'''
<tr><td bgcolor="{NAVY_2}" style="border-radius:18px 18px 0 0;padding:24px 40px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
    <td width="62" valign="middle">{_crest()}</td>
    <td valign="middle">
      <div style="font:{SERIF};font-size:18px;font-weight:600;color:{PEARL};letter-spacing:.3px;">
        {BRAND_SHORT}</div>
      <div style="font:{SANS};font-size:13px;letter-spacing:2.6px;color:rgba(251,250,247,.55);
                  text-transform:uppercase;margin-top:3px;">Football Academy · Parent &amp; Family Office</div>
    </td>
  </tr></table>
</td></tr>'''


def _footer():
    return f'''
<tr><td bgcolor="{NAVY_2}" style="border-radius:0 0 18px 18px;padding:22px 40px;text-align:center;">
  <div style="font:{SERIF};font-size:15px;color:{PEARL};">{BRAND_NAME}</div>
  <div style="font:{SANS};font-size:12.5px;color:rgba(251,250,247,.55);margin-top:5px;letter-spacing:.4px;">
    {LOCATION} · Est. 2020</div>
  <div style="font:{SANS};font-size:12px;color:{AMBER};margin-top:8px;letter-spacing:.6px;">{_esc(TAGLINE)}</div>
</td></tr>'''


def _shell(preheader, inner):
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{BRAND_NAME}</title></head>
<body style="margin:0;padding:0;background:{SAND};">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}&#847;&zwnj;&nbsp;&#847;&zwnj;&nbsp;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" bgcolor="{SAND}">
<tr><td align="center" style="padding:30px 12px;">
  <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0"
         style="width:100%;max-width:600px;">
    {_header()}
    <tr><td bgcolor="#ffffff" style="padding:38px 40px 34px;">{inner}</td></tr>
    {_footer()}
  </table>
  <div style="font:{SANS};font-size:12px;color:{FAINT};margin-top:16px;max-width:520px;
              line-height:1.6;text-align:center;">
    You are receiving this message because you (or your child) are in contact with {BRAND_SHORT}.
  </div>
</td></tr></table>
</body></html>'''


def _eyebrow(text):
    return (f'<div style="font:{SANS};font-size:12px;font-weight:bold;letter-spacing:2.4px;'
            f'color:{AMBER_INK};text-transform:uppercase;margin-bottom:12px;">{text}</div>')


def _headline(text):
    return (f'<h1 style="margin:0 0 18px;font:{SERIF};font-size:26px;line-height:1.25;'
            f'color:{INK};font-weight:600;">{text}</h1>')


def _p(text, extra=''):
    return (f'<p style="margin:0 0 14px;font:{SANS};font-size:15px;line-height:1.7;'
            f'color:{BODY};{extra}">{text}</p>')


def _bullet_table(rows):
    trs = ''.join(
        f'<tr><td width="26" valign="top" style="padding:7px 0 0;font:{SANS};font-size:15px;'
        f'color:{AMBER};font-weight:bold;">&#8226;</td>'
        f'<td style="padding:6px 0;font:{SANS};font-size:14.5px;line-height:1.6;color:{BODY};">{row}</td></tr>'
        for row in rows)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" '
            f'border="0" style="margin:2px 0 18px;">{trs}</table>')


def _note_box(title, text):
    return f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:6px 0 4px;">
  <tr><td bgcolor="{SAND}" style="border:1px solid {SAND_BORDER};border-radius:10px;padding:14px 18px;">
    <div style="font:{SANS};font-size:13.5px;font-weight:bold;letter-spacing:1px;color:{SAND_INK};
                text-transform:uppercase;margin-bottom:5px;">{title}</div>
    <div style="font:{SANS};font-size:14.5px;line-height:1.65;color:{SAND_INK};">{text}</div>
  </td></tr>
</table>'''


def _cta(url, label):
    return f'''
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0 0;">
  <tr><td bgcolor="{AMBER}" style="border-radius:11px;">
    <a href="{url}" style="display:inline-block;padding:15px 34px;font:{SANS};font-size:15px;
       font-weight:bold;color:{NAVY_2};text-decoration:none;border-radius:11px;">{label}</a>
  </td></tr>
</table>'''


def _url_fallback(url):
    return (f'<p style="margin:16px 0 0;font:{MONO};font-size:13px;line-height:1.6;color:{MUTED};'
            f'background:{SAND};border:1px solid {SAND_BORDER};border-radius:8px;'
            f'padding:10px 14px;word-break:break-all;">{url}</p>')


# ══ EMAIL 1 — Parent Portal invitation ═══════════════════════════════════

def invite_email_html(guardian_name, child_phrase, url):
    g = _esc(guardian_name or 'Parent')
    child = _esc(child_phrase or '')
    return _shell(
        preheader='Great news — the application has been approved. Activate your '
                  'Parent Portal account inside.',
        inner=(
            _eyebrow('Parent Portal · Invitation')
            + _headline('Karibu! The application has been approved.')
            + _p(f'Dear {g},')
            + _p(f'Great news — <b style="color:{INK};">{child}application at '
                 f'{BRAND_NAME} has been approved</b>. The academy office has opened '
                 f'a Parent Portal account for you, so you can walk with us through '
                 f'every season of your child\u2019s journey.')
            + _p('Your personal activation link is below. It works <b>once</b> and '
                 f'expires after <b>72 hours</b> — it exists only so that you can choose '
                 f'your own private password.')
            + _cta(url, 'Set up your parent account')
            + _url_fallback(url)
            + f'<div style="margin:28px 0 10px;font:{SANS};font-size:13.5px;font-weight:bold;'
              f'letter-spacing:1.6px;color:{MUTED};text-transform:uppercase;">Inside the portal</div>'
            + _bullet_table([
                '<b style="color:' + INK + ';">Your child\u2019s squad card</b> — their team, '
                'photo and the next published fixture',
                '<b style="color:' + INK + ';">Academy announcements</b> — news from the '
                'office, squad by squad',
                '<b style="color:' + INK + ';">A private welfare desk</b> — raise a concern '
                'and get answers from staff, in writing',
            ])
            + _note_box('One-time link · 72 hours',
                        'Please do not forward this email — anyone who holds the link can '
                        'claim the account. If it expires, simply ask the academy office to '
                        'send a fresh one.')
            + signature_html()
        ))


def invite_email_text(guardian_name, child_phrase, url):
    return f"""Dear {guardian_name},

Great news — {child_phrase}application at {BRAND_NAME} has been approved.

The academy office has opened a Parent Portal account for you. Set it up
with this personal link (it works once and expires after 72 hours):

  {url}

Once you are in, the portal keeps you close to the academy:

  · Your child's squad card and their next fixture
  · Announcements from the academy, squad by squad
  · A private complaints & welfare desk answered by staff

Please do not forward this link — anyone who holds it can claim the
account. If it expires, simply ask the academy office to send a fresh one.

Karibu, and thank you for trusting us with your child.

{signature_text()}"""


def invite_email_payload(url, guardian_name, child_phrase):
    """The exact payload handed to resend_send for an invitation."""
    return {
        'subject': f'Your {BRAND_SHORT} parent account — activate it now',
        'html': invite_email_html(guardian_name, child_phrase, url),
        'text': invite_email_text(guardian_name, child_phrase, url),
    }


# ══ EMAIL 2 — Form auto-reply ("thank you, we received your message") ════

def auto_reply_email_html(name, label, ref):
    n = _esc(name or 'friend')
    return _shell(
        preheader=f'We have received your {label.lower()} (reference {ref}) and will '
                  'get back to you shortly.',
        inner=(
            _eyebrow('Academy Office · Message received')
            + _headline('Asante — we have received your message.')
            + _p(f'Dear {n},')
            + _p(f'Thank you for reaching out to <b style="color:{INK};">{BRAND_NAME}</b>. '
                 f'We have received your <b>{_esc(label.lower())}</b> and our team will '
                 f'get back to you shortly.')
            + _p(f'Keep your reference number handy in case you write to us again: '
                 f'<b style="color:{AMBER_INK};">{_esc(ref)}</b>.')
            + _note_box('What happens next',
                        'A member of the academy office reads every message and replies '
                        'within a few working days. Urgent matters are best raised by '
                        f'email at {_esc(CONTACT_EMAIL)}.')
            + f'<p style="margin:22px 0 0;font:{SERIF};font-size:15px;font-style:italic;'
              f'color:{AMBER_INK};">{TAGLINE}</p>'
            + signature_html()
        ))


def auto_reply_email_text(name, label, ref):
    return f"""Dear {name or 'friend'},

Thank you for reaching out to {BRAND_NAME}. We have received your
{label.lower()} (reference {ref}) and our team will get back to you shortly.

Keep your reference number ({ref}) handy in case you write to us again.
Urgent matters are best raised by email at {CONTACT_EMAIL}.

{TAGLINE}

{signature_text()}"""


def auto_reply_payload(name, label, ref):
    return {
        'subject': f'Thank you for contacting {BRAND_NAME}',
        'html': auto_reply_email_html(name, label, ref),
        'text': auto_reply_email_text(name, label, ref),
    }


def _body_paras(body):
    """Announcement plain-text body -> escaped HTML paragraphs (safe)."""
    paras = [p.strip() for p in (body or '').split('\n\n') if p.strip()]
    out = []
    for p in paras:
        esc = _esc(p).replace('\n', '<br>')
        out.append(_p(esc))
    return ''.join(out) or _p('—')


def _ref_box(ref):
    return (f'<p style="margin:0 0 14px;font:{SANS};font-size:14px;color:{BODY};">'
            f'Your case reference: <b style="color:{AMBER_INK};">{_esc(ref)}</b> — '
            f'quote it any time you write to the office.</p>')


# ══ EMAIL 3 — Complaint received (parent confirmation) ═══════════════════

def complaint_received_email_html(parent_name, ref, subject, category_label, portal_url):
    g = _esc(parent_name or 'Parent')
    return _shell(
        preheader=f'Your concern "{subject}" is now case {ref} at the welfare desk.',
        inner=(
            _eyebrow('Parent Portal · Welfare desk')
            + _headline('Asante — your concern has reached the academy office.')
            + _p(f'Dear {g},')
            + _p(f'We have opened a <b style="color:{INK};">private case</b> for the matter '
                 f'you raised under <b>&ldquo;{_esc(subject)}&rdquo;</b> '
                 f'({_esc(category_label.lower())}). Only you and authorised academy staff '
                 f'can read this thread.')
            + _ref_box(ref)
            + _note_box('What happens next',
                        'A member of staff reviews every case and replies inside the portal, '
                        'so the whole conversation stays in one place. Each time the academy '
                        'replies, you receive an email like this one. Urgent welfare matters '
                        f'are best raised by phone or at {_esc(CONTACT_EMAIL)}.')
            + _cta(portal_url, 'Open the welfare desk')
            + _url_fallback(portal_url)
            + signature_html()
        ))


def complaint_received_email_text(parent_name, ref, subject, category_label, portal_url):
    return f"""Dear {parent_name or 'Parent'},

Thank you for reaching out. We have opened a private case for the matter
you raised under "{subject}" ({category_label.lower()}).

Your case reference: {ref}

What happens next: a member of staff reviews every case and replies
inside the Parent Portal, so the whole conversation stays in one place.
Each time the academy replies, you receive an email. Urgent welfare
matters are best raised by phone or at {CONTACT_EMAIL}.

Open the welfare desk: {portal_url}

{signature_text()}"""


def complaint_received_payload(parent_name, ref, subject, category_label, portal_url):
    return {
        'subject': f'Case {ref} received — {BRAND_SHORT} welfare desk',
        'html': complaint_received_email_html(parent_name, ref, subject, category_label, portal_url),
        'text': complaint_received_email_text(parent_name, ref, subject, category_label, portal_url),
    }


# ══ EMAIL 4 — Complaint alert (staff notification) ═══════════════════════

def complaint_alert_email_html(ref, guardian_name, category_label, subject,
                               child_phrase, portal_url, followup=False):
    head = ('Follow-up on a parent case' if followup
            else 'New parent concern — a case is waiting.')
    intro = (
        f'{_esc(guardian_name)} has added a new message to case '
        f'<b style="color:{INK};">{_esc(ref)}</b>.' if followup else
        f'{_esc(guardian_name)} ({_esc(category_label.lower())}) has opened a private '
        f'case about <b style="color:{INK};">&ldquo;{_esc(subject)}&rdquo;</b>'
        + (f' regarding <b>{_esc(child_phrase)}</b>.' if child_phrase else '.'))
    return _shell(
        preheader=f'Case {ref} — {"follow-up by" if followup else "opened by"} {guardian_name}.',
        inner=(
            _eyebrow('Management Portal · Welfare desk')
            + _headline(head)
            + _p(intro)
            + _note_box('Handle it in the portal',
                        'Reply from the welfare desk so the whole conversation stays in one '
                        'auditable thread. Internal notes stay private to staff; every public '
                        'reply emails the parent automatically.')
            + _cta(portal_url, 'Open the welfare inbox')
            + _url_fallback(portal_url)
            + signature_html()
        ))


def complaint_alert_email_text(ref, guardian_name, category_label, subject,
                               child_phrase, portal_url, followup=False):
    head = ('Follow-up on a parent case' if followup
            else 'New parent concern — a case is waiting.')
    if followup:
        intro = f'{guardian_name} has added a new message to case {ref}.'
    else:
        child = f' regarding {child_phrase}' if child_phrase else ''
        intro = (f'{guardian_name} ({category_label.lower()}) has opened a private case '
                 f'about "{subject}"{child}.')
    return f"""{head}

{intro}

Handle it in the Management Portal welfare desk so the whole conversation
stays in one auditable thread. Internal notes stay private to staff; every
public reply emails the parent automatically.

Open the welfare inbox: {portal_url}

{signature_text()}"""


def complaint_alert_payload(ref, guardian_name, category_label, subject,
                            child_phrase, portal_url, followup=False):
    return {
        'subject': (f'[Welfare desk] Follow-up on case {ref}' if followup
                    else f'[Welfare desk] New parent concern — case {ref}'),
        'html': complaint_alert_email_html(ref, guardian_name, category_label, subject,
                                           child_phrase, portal_url, followup),
        'text': complaint_alert_email_text(ref, guardian_name, category_label, subject,
                                           child_phrase, portal_url, followup),
    }


# ══ EMAIL 5 — Staff replied (parent notification) ════════════════════════

def complaint_reply_email_html(parent_name, ref, subject, excerpt, portal_url):
    g = _esc(parent_name or 'Parent')
    return _shell(
        preheader=f'The academy has replied to your case {ref} — "{subject}".',
        inner=(
            _eyebrow('Parent Portal · Welfare desk')
            + _headline('The academy has replied to your case.')
            + _p(f'Dear {g},')
            + _p(f'A member of staff has responded to your case '
                 f'<b>&ldquo;{_esc(subject)}&rdquo;</b> (reference '
                 f'<b style="color:{AMBER_INK};">{_esc(ref)}</b>).')
            + _note_box('From their reply', _esc(excerpt))
            + _p('Sign in to the Parent Portal to read the full conversation, '
                 'reply, and follow the case to resolution.')
            + _cta(portal_url, 'Read the reply')
            + _url_fallback(portal_url)
            + signature_html()
        ))


def complaint_reply_email_text(parent_name, ref, subject, excerpt, portal_url):
    return f"""Dear {parent_name or 'Parent'},

A member of staff has responded to your case "{subject}"
(reference {ref}):

  "{excerpt}"

Sign in to the Parent Portal to read the full conversation, reply, and
follow the case to resolution:

  {portal_url}

{signature_text()}"""


def complaint_reply_payload(parent_name, ref, subject, excerpt, portal_url):
    return {
        'subject': f'The academy replied — case {ref}',
        'html': complaint_reply_email_html(parent_name, ref, subject, excerpt, portal_url),
        'text': complaint_reply_email_text(parent_name, ref, subject, excerpt, portal_url),
    }


# ══ EMAIL 6 — Announcement broadcast (to parents) ════════════════════════

def announcement_email_html(guardian_name, title, body, audience_label, portal_url):
    g = _esc(guardian_name or 'Parent')
    return _shell(
        preheader=f'{title} — a notice from {BRAND_SHORT}.',
        inner=(
            _eyebrow('Academy announcement')
            + _headline(_esc(title))
            + _p(f'Dear {g},')
            + _body_paras(body)
            + _note_box('Who this notice is for', f'{_esc(audience_label)}. Sign in to '
                        'the Parent Portal to see every notice for your children&#8217;s squads.')
            + _cta(portal_url, 'Open the parent portal')
            + _url_fallback(portal_url)
            + signature_html()
        ))


def announcement_email_text(guardian_name, title, body, audience_label, portal_url):
    return f"""Dear {guardian_name or 'Parent'},

{title}

{body}

Who this notice is for: {audience_label}. Sign in to the Parent Portal to
see every notice for your children's squads:

  {portal_url}

{signature_text()}"""


def announcement_payload(guardian_name, title, body, audience_label, portal_url):
    return {
        'subject': f'{BRAND_SHORT}: {title}',
        'html': announcement_email_html(guardian_name, title, body, audience_label, portal_url),
        'text': announcement_email_text(guardian_name, title, body, audience_label, portal_url),
    }


# ══ EMAIL 7 — Safeguarding: DSO notification (minimal by design) ═════════
#
# This is the ONLY email the safeguarding flow sends to the academy, and
# it deliberately carries NO report content: no child name, no narrative,
# no reporter identity. Its single job is to tell the Designated
# Safeguarding Officer that a report is waiting inside the access-controlled
# portal. (Kenya Data Protection Act 2019 — special-category data stays
# in the restricted store; inboxes are not that store.)

def safeguarding_notification_email_html(ref, dso_url):
    return _shell(
        preheader=f'A new safeguarding report ({ref}) is waiting in the DSO desk.',
        inner=(
            _eyebrow('Safeguarding · DSO desk')
            + _headline('A new safeguarding report has been received.')
            + _p(f'A confidential report was submitted through the academy website '
                 f'and is now available in the restricted DSO desk. For the privacy '
                 f'of everyone involved, no details are included in this message.')
            + _p('Reference: <b style="color:' + AMBER_INK + ';">' + _esc(ref) + '</b>')
            + _note_box('Act promptly',
                        'Please review the report in the portal as soon as possible. '
                        'If a child may be in immediate danger, contact the Police '
                        '(999 / 112) or Childline Kenya (116) first, then record the '
                        'escalation in the desk.')
            + _cta(dso_url, 'Open the DSO desk')
            + _url_fallback(dso_url)
            + signature_html()
        ))


def safeguarding_notification_email_text(ref, dso_url):
    return f"""A new safeguarding report has been received through the academy
website and is now available in the restricted DSO desk. For the privacy
of everyone involved, no details are included in this message.

Reference: {ref}

Please review the report as soon as possible. If a child may be in
immediate danger, contact the Police (999 / 112) or Childline Kenya (116)
first, then record the escalation in the desk.

Open the DSO desk: {dso_url}

{signature_text()}"""


def safeguarding_notification_payload(ref, dso_url):
    return {
        'subject': f'[Safeguarding] New report received — {ref}',
        'html': safeguarding_notification_email_html(ref, dso_url),
        'text': safeguarding_notification_email_text(ref, dso_url),
    }


# ══ EMAIL 8 — Safeguarding: reporter acknowledgment ══════════════════════
#
# Sent only when the reporter chose the confidential option and left an
# email address. Neutral subject (shared inboxes exist), no content
# repetition, plus the statutory emergency numbers.

def safeguarding_ack_email_html(name, ref, contact_email):
    n = _esc(name or 'friend')
    return _shell(
        preheader='Your confidential report has been received and logged.',
        inner=(
            _eyebrow('Academy Office · Message received')
            + _headline('Asante — your confidential report has been received.')
            + _p(f'Dear {n},')
            + _p(f'Thank you for trusting <b style="color:{INK};">{BRAND_NAME}</b>. '
                 'Your confidential report has been received and passed to the '
                 'Designated Safeguarding Officer, who reviews every report '
                 'personally.')
            + _p('Your reference: <b style="color:' + AMBER_INK + ';">' + _esc(ref) + '</b>')
            + _note_box('If a child is in immediate danger',
                        'Do not wait for a reply — contact the Police (999 / 112) or '
                        'Childline Kenya (116) straight away.')
            + _p('Because of the sensitive nature of these reports, please keep '
                 'this reference and quote it if you need to add information: '
                 f'{_esc(contact_email)}.')
            + signature_html()
        ))


def safeguarding_ack_email_text(name, ref, contact_email):
    return f"""Dear {name or 'friend'},

Thank you for trusting {BRAND_NAME}. Your confidential report has been
received and passed to the Designated Safeguarding Officer, who reviews
every report personally.

Your reference: {ref}

If a child is in immediate danger, do not wait for a reply — contact the
Police (999 / 112) or Childline Kenya (116) straight away.

Because of the sensitive nature of these reports, please keep this
reference and quote it if you need to add information: {contact_email}.

{signature_text()}"""


def safeguarding_ack_payload(name, ref, contact_email):
    return {
        'subject': f'Thank you for contacting {BRAND_NAME}',
        'html': safeguarding_ack_email_html(name, ref, contact_email),
        'text': safeguarding_ack_email_text(name, ref, contact_email),
    }
