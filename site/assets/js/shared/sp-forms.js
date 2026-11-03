/* Sporting Pearls — sp-forms.js (Django backend sync layer, v3 — Phase 3)
   ------------------------------------------------------------------
   Syncs the site's 13 forms to the Django backend:
     POST {API_BASE}/api/forms/<slug>/   { slug, data, meta }

   Phase 3 — truthful form states. The old version showed the page's
   success screen BEFORE the server answered (and invented a reference
   number with Math.random()). This version inverts the flow:

   - Pages call SP_FORMS.finish(form, opts) when their own validation
     passes. The success screen / reference number appears ONLY after
     the server has acknowledged the submission (real reference).
   - If the server cannot be reached, an honest "Not sent yet" panel
     replaces the success story: the form stays on the page (nothing
     is lost), a copy is queued on this device and retried on the
     next visit, and the visitor is told exactly that.
   - A server-side rejection (invalid / too many requests) is NEVER
     queued — the visitor sees the reason and keeps their answers.
   - Drafts: every form (except the newsletter box) autosaves on this
     device while you type and offers to restore it on your next
     visit. Drafts and undelivered copies expire after 48 hours.
   - When an undelivered copy finally goes through on a later visit,
     a discreet note shows the real reference number.
   - Demo mode (API_BASE empty): pages keep their on-page behaviour;
     the reference slot shows a clearly marked DEMO code, because
     nothing is sent or stored anywhere.

   Serialization stays label-based (see fieldLabel) so notification
   emails remain human-readable. A hidden honeypot ("company") is
   injected into every form; bots that fill it are silently dropped
   by the backend.                                                          */
(function () {
  "use strict";
  var cfg = window.SP_CONFIG || {};
  var API = (cfg.API_BASE || "").replace(/\/+$/, "");

  var SLUGS = {
    generalEnquiry: "contact-general-enquiry",
    playerRegForm: "form-01-player-registration",
    trialForm: "form-02-trial-application",
    parentForm: "form-03-parent-association",
    volunteerForm: "form-04-volunteer-application",
    coachForm: "form-05-coach-technical-staff",
    sponsorForm: "form-06-sponsorship-partnership",
    donationForm: "form-07-donation-support",
    contactForm: "form-08-contact-form",
    consentForm: "form-09-media-photo-consent",
    safeForm: "form-10-safeguarding-report",
    partnerForm: "partnership-application",
    newsletterForm: "newsletter-subscription"
  };
  var SAFEGUARDING_SLUG = SLUGS.safeForm;
  var KEEP_MS = 48 * 60 * 60 * 1000;   /* drafts + offline queue: 48 h  */
  var QUEUE_MAX = 5;                    /* undelivered copies per form  */

  /* one-time stylesheet: sync note, offline panel, restore bar, toast */
  var st = document.createElement("style");
  st.textContent =
    ".sp-sync-line{margin:.65rem 0 0;font:600 .78rem/1.5 'Work Sans',sans-serif;letter-spacing:.02em}" +
    ".sp-sync-line.ok{color:#1f9d61}.sp-sync-line.warn{color:#c0536e}" +
    ".sp-sync-line a{color:inherit;text-decoration:underline}" +
    ".sp-hp{position:absolute!important;left:-9999px!important;top:-9999px!important;width:1px;height:1px;opacity:0;pointer-events:none}" +
    ".sp-problem{max-width:640px;margin:0 auto 1.6rem;padding:1.3rem 1.5rem;border:1px solid rgba(192,83,110,.45);" +
    "border-left:5px solid #c0536e;background:rgba(192,83,110,.06);border-radius:10px;text-align:left}" +
    ".sp-problem h3{margin:0 0 .6rem;font:700 1.05rem/1.3 'Oswald',sans-serif;letter-spacing:.02em;color:#c0536e;outline:none}" +
    ".sp-problem p{margin:.45rem 0;font:400 .9rem/1.65 'Work Sans',sans-serif;color:inherit}" +
    ".sp-problem p.sp-emergency{font-weight:600}" +
    ".sp-problem .sp-actions{display:flex;flex-wrap:wrap;gap:.7rem;margin-top:1rem;align-items:center}" +
    ".sp-problem button{cursor:pointer;font:600 .82rem/1 'Work Sans',sans-serif;letter-spacing:.03em;text-transform:uppercase;" +
    "padding:.75rem 1.15rem;border-radius:6px;border:1px solid #c0536e;background:#c0536e;color:#fff}" +
    ".sp-problem button.sp-ghost{background:transparent;color:#c0536e}" +
    ".sp-problem a{color:inherit;text-decoration:underline;font:600 .82rem/1 'Work Sans',sans-serif}" +
    ".sp-restore{display:flex;flex-wrap:wrap;gap:.8rem;align-items:center;justify-content:space-between;" +
    "max-width:640px;margin:0 auto 1.4rem;padding:.85rem 1.1rem;border:1px dashed rgba(47,143,131,.6);" +
    "background:rgba(47,143,131,.07);border-radius:8px;font:500 .85rem/1.5 'Work Sans',sans-serif}" +
    ".sp-restore p{margin:0}" +
    ".sp-restore .sp-actions{display:flex;gap:.6rem}" +
    ".sp-restore button{cursor:pointer;font:600 .78rem/1 'Work Sans',sans-serif;padding:.55rem .9rem;border-radius:6px;border:1px solid #2f8f83}" +
    ".sp-restore button.sp-keep{background:#2f8f83;color:#fff}" +
    ".sp-restore button.sp-fresh{background:transparent;color:#2f8f83}" +
    ".sp-toast{position:fixed;left:16px;bottom:16px;z-index:99999;max-width:340px;padding:.9rem 2.4rem .9rem 1.1rem;" +
    "background:#13203b;color:#fff;border-radius:10px;box-shadow:0 8px 28px rgba(0,0,0,.35);" +
    "font:500 .84rem/1.55 'Work Sans',sans-serif}" +
    ".sp-toast b{color:#f5b942}" +
    ".sp-toast .sp-x{position:absolute;top:6px;right:8px;background:none;border:none;color:#fff;cursor:pointer;" +
    "font:700 1rem/1 sans-serif;opacity:.7}";
  document.head.appendChild(st);

  /* ── serialization (label-keyed — unchanged contract) ── */

  function fieldLabel(el) {
    var host = el.closest(".field") || el.closest(".committee-card") || el.closest("label");
    var lb = host ? host.querySelector("label") : null;
    if (!lb && el.labels && el.labels.length) { lb = el.labels[0]; }
    if (lb) {
      var t = lb.textContent.replace(/[*\u2192]/g, "").replace(/\s+/g, " ").trim().slice(0, 80);
      if (t) return t;
    }
    return el.placeholder || el.id || "Field";
  }

  function isHoneypot(el) {
    return el.name === "company" || el.id === "company_website" ||
           (typeof el.className === "string" && el.className.indexOf("sp-hp") !== -1);
  }

  function serialize(form) {
    var out = {};
    Array.prototype.forEach.call(form.querySelectorAll("input, select, textarea"), function (el) {
      if (isHoneypot(el)) return;
      if (el.type === "file" || el.type === "submit" || el.type === "button" ||
          el.type === "reset" || el.type === "hidden") return;
      if (el.type === "radio" && !el.checked) return;
      if (!el.id && !el.name && !el.placeholder) return;
      var label = fieldLabel(el), val;
      if (el.type === "checkbox") {
        if (el.name && el.name.indexOf('"') === -1) {
          var group = form.querySelectorAll('input[type="checkbox"][name="' + el.name + '"]');
          if (group.length > 1) {
            if (out[label] !== undefined) return;
            var vals = [];
            Array.prototype.forEach.call(group, function (g) {
              if (g.checked) vals.push(g.value || "Yes");
            });
            out[label] = vals.length ? vals : "(none selected)";
            return;
          }
        }
        val = el.checked ? "Yes" : "No";
      } else if (el.tagName === "SELECT") {
        val = el.value || "(not selected)";
      } else {
        val = el.value || "(empty)";
      }
      if (out[label] !== undefined) return; /* keep first occurrence */
      out[label] = val;
    });
    return out;
  }

  /* restore a draft: same label matching as serialize() */
  var SKIP_VALUES = { "(empty)": 1, "(not selected)": 1, "(none selected)": 1 };

  function restore(form, data) {
    var els = form.querySelectorAll("input, select, textarea");
    Array.prototype.forEach.call(els, function (el) {
      if (isHoneypot(el) || el.type === "file" || el.type === "submit" ||
          el.type === "button" || el.type === "reset" || el.type === "hidden") return;
      var label = fieldLabel(el);
      if (!(label in data)) return;
      var val = data[label];
      if (el.type === "checkbox") {
        if (el.name && el.name.indexOf('"') === -1) {
          var group = form.querySelectorAll('input[type="checkbox"][name="' + el.name + '"]');
          if (group.length > 1) {
            var list = Array.isArray(val) ? val : [val];
            Array.prototype.forEach.call(group, function (g) {
              g.checked = list.indexOf(g.value || "Yes") !== -1;
            });
            return;
          }
        }
        el.checked = val === "Yes";
      } else if (el.type === "radio") {
        el.checked = (el.value === val);
      } else if (el.tagName === "SELECT") {
        if (val && !SKIP_VALUES[val]) {
          Array.prototype.forEach.call(el.options, function (o) {
            if (o.value === val || o.textContent.trim() === val) { el.value = o.value; }
          });
        }
      } else {
        el.value = (val && !SKIP_VALUES[val]) ? val : "";
      }
    });
  }

  /* ── transport ──
     resolves {ok, ref}  |  rejects Error with .kind:
       'offline'  network / 5xx  → queue + honest offline panel
       'invalid'  4xx validation → show reason, never queue
       'busy'     429            → show reason, never queue                */

  function send(slug, payload) {
    return fetch(API + "/api/forms/" + slug + "/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (r.ok && j.ok) { return j; }
        var err = new Error((j && j.error) || ("HTTP " + r.status));
        if (r.status === 429) { err.kind = "busy"; }
        else if (r.status >= 400 && r.status < 500) { err.kind = "invalid"; }
        else { err.kind = "offline"; }
        throw err;
      });
    }, function () {
      var e = new Error("network unreachable");
      e.kind = "offline";
      throw e;
    });
  }

  /* ── offline queue (48 h retention, max 5, migrated legacy shape) ── */

  function readQueue(slug) {
    var key = "sp_pending_" + slug, q;
    try { q = JSON.parse(localStorage.getItem(key) || "[]"); } catch (e) { q = []; }
    if (!Array.isArray(q)) q = [];
    var now = Date.now(), keep = [];
    for (var i = 0; i < q.length; i++) {
      var it = q[i];
      if (it && it.payload) {
        if (now - (it.at || now) < KEEP_MS) { keep.push(it); }
      } else if (it) {                    /* legacy v2 entry (bare payload) */
        keep.push({ at: now, payload: it });
      }
    }
    return keep;
  }

  function writeQueue(slug, q) {
    try { localStorage.setItem("sp_pending_" + slug, JSON.stringify(q.slice(-QUEUE_MAX))); }
    catch (e) { /* private mode etc. */ }
  }

  function queue(slug, payload) {
    var q = readQueue(slug);
    q.push({ at: Date.now(), payload: payload });
    writeQueue(slug, q);
  }

  /* ── drafts (48 h, all forms except the newsletter box) ── */

  function draftKey(form) { return "sp_draft_" + form.id; }

  function saveDraft(form) {
    try {
      localStorage.setItem(draftKey(form),
        JSON.stringify({ at: Date.now(), data: serialize(form) }));
    } catch (e) { /* private mode etc. */ }
  }

  function clearDraft(form) {
    /* cancel any pending debounced save first, or it would resurrect
       the draft right after a successful submission cleared it */
    try {
      if (form._spDraftTimer) {
        clearTimeout(form._spDraftTimer);
        form._spDraftTimer = null;
      }
    } catch (e) {}
    try { localStorage.removeItem(draftKey(form)); } catch (e) {}
  }

  function offerDraft(form) {
    var raw;
    try { raw = JSON.parse(localStorage.getItem(draftKey(form)) || "null"); } catch (e) { raw = null; }
    if (!raw || !raw.data) return;
    if (Date.now() - (raw.at || 0) >= KEEP_MS) { clearDraft(form); return; }
    var when = new Date(raw.at);
    var bar = document.createElement("div");
    bar.className = "sp-restore";
    var p = document.createElement("p");
    var sensitive = SLUGS[form.id] === SAFEGUARDING_SLUG;
    p.textContent = "We found an unfinished version of this form on this device, saved " +
      when.toLocaleDateString() + " " + when.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) +
      ". It is kept on this device only" + (sensitive ? ", for up to 48 hours" : "") + ".";
    var acts = document.createElement("div");
    acts.className = "sp-actions";
    var keep = document.createElement("button");
    keep.type = "button"; keep.className = "sp-keep"; keep.textContent = "Continue where I left off";
    var fresh = document.createElement("button");
    fresh.type = "button"; fresh.className = "sp-fresh"; fresh.textContent = "Start fresh";
    acts.appendChild(keep); acts.appendChild(fresh);
    bar.appendChild(p); bar.appendChild(acts);
    form.parentNode.insertBefore(bar, form);
    keep.addEventListener("click", function () {
      restore(form, raw.data);
      bar.parentNode.removeChild(bar);
      var first = form.querySelector("input:not(.sp-hp), select, textarea");
      if (first && first.focus) { first.focus(); }
    });
    fresh.addEventListener("click", function () {
      clearDraft(form);
      bar.parentNode.removeChild(bar);
    });
  }

  /* ── honest problem panel (offline / rejected) ── */

  function killProblem(form) {
    var old = form.parentNode && form.parentNode.querySelector(".sp-problem");
    if (old && old.parentNode) { old.parentNode.removeChild(old); }
  }

  function showProblem(form, result, retry) {
    killProblem(form);
    var slug = SLUGS[form.id] || "";
    var panel = document.createElement("div");
    panel.className = "sp-problem";
    panel.setAttribute("role", "alert");
    var h = document.createElement("h3");
    h.tabIndex = -1;
    var why = document.createElement("p");
    if (result.state === "offline") {
      h.textContent = "Not sent yet";
      why.textContent = "We couldn't reach the academy server just now. Nothing is lost — " +
        "your answers are still on this page, and a copy is kept on this device. " +
        "We'll try again automatically next time you visit this site " +
        "(kept for up to 48 hours, then deleted from this device).";
    } else {
      h.textContent = "Not sent";
      why.textContent = "The form couldn't be accepted: " + (result.message || "please check your answers") +
        ". Your answers are still on this page — nothing was lost.";
    }
    panel.appendChild(h); panel.appendChild(why);
    if (slug === SAFEGUARDING_SLUG) {
      var em = document.createElement("p");
      em.className = "sp-emergency";
      em.textContent = "If a child is in immediate danger, please call Childline Kenya 116 " +
        "(toll-free, 24 hours) now — do not wait for this form.";
      panel.appendChild(em);
    }
    var acts = document.createElement("div");
    acts.className = "sp-actions";
    var again = document.createElement("button");
    again.type = "button"; again.textContent = "Try again now";
    again.addEventListener("click", function () {
      killProblem(form);
      if (retry) { retry(); }
      else if (typeof form.requestSubmit === "function") { form.requestSubmit(); }
      else { form.dispatchEvent(new Event("submit", { cancelable: true })); }
    });
    acts.appendChild(again);
    panel.appendChild(acts);
    form.parentNode.insertBefore(panel, form);
    if (h.focus) { h.focus(); }
    panel.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  /* ── discreet note when an earlier copy finally goes through ── */

  function notifyDelivered(slug, ref) {
    if (!ref) return;
    var t = document.createElement("div");
    t.className = "sp-toast";
    t.setAttribute("role", "status");
    var safe = slug === SAFEGUARDING_SLUG;
    t.innerHTML = (safe
      ? "Your earlier confidential report has now been delivered to the academy."
      : "A form you submitted earlier from this device has now been delivered.") +
      " Reference: <b></b>";
    t.querySelector("b").textContent = ref;
    var x = document.createElement("button");
    x.type = "button"; x.className = "sp-x"; x.setAttribute("aria-label", "Dismiss");
    x.textContent = "\u00d7";
    x.addEventListener("click", function () {
      if (t.parentNode) { t.parentNode.removeChild(t); }
    });
    t.appendChild(x);
    document.body.appendChild(t);
    setTimeout(function () {
      if (t.parentNode) { t.parentNode.removeChild(t); }
    }, 25000);
  }

  /* ── the public contract ──
     deliver(form, cb): cb({state:'demo'|'sent'|'offline'|'error', ref?, message?})
     finish(form, opts): full page flow. opts:
        refEl   id of the element that shows the reference
        hide    [ids] to hide when the success state shows
        modal   id of the success block ('active' class)
        reveal  id of the success block to unhide (contact page style)
        onCls   class to add instead of 'active' (partners uses 'on')
        onSettled  fn() called after any settled attempt (unbusy etc.)     */

  function buildPayload(form) {
    var slug = SLUGS[form.id];
    var data = serialize(form);
    var hp = form.querySelector('input[name="company"]');
    if (hp && String(hp.value || "").trim()) data.company = hp.value; /* bot hit — backend drops it */
    return {
      slug: slug,
      data: data,
      meta: { page: location.pathname, ref: document.referrer || "", ua: navigator.userAgent }
    };
  }

  function deliver(form, cb) {
    if (!API) { cb({ state: "demo" }); return; }
    var slug = SLUGS[form.id];
    if (!slug) { cb({ state: "demo" }); return; }
    var payload = buildPayload(form);
    send(slug, payload)
      .then(function (j) { cb({ state: "sent", ref: j.ref }); })
      .catch(function (err) {
        if (err && (err.kind === "offline")) {
          queue(slug, payload);
          cb({ state: "offline" });
        } else {
          cb({ state: "error", message: err && err.message ? err.message : "please try again" });
        }
      });
  }

  function demoCode() { return "DEMO-" + Math.floor(1000 + Math.random() * 9000); }

  function finish(form, opts) {
    opts = opts || {};
    deliver(form, function (r) {
      if (r.state === "sent" || r.state === "demo") {
        if (opts.refEl) {
          var re = document.getElementById(opts.refEl);
          if (re) { re.textContent = r.state === "sent" ? (r.ref || "—") : demoCode(); }
        }
        if (r.state === "sent") { clearDraft(form); }
        (opts.hide || []).forEach(function (id) {
          var el = document.getElementById(id);
          if (el) { el.style.display = "none"; }
        });
        if (opts.modal) {
          var m = document.getElementById(opts.modal);
          if (m) {
            m.classList.add(opts.onCls || "active");
            var f = m.querySelector("h2, b, p");
            if (f) { f.setAttribute("tabindex", "-1"); if (f.focus) { f.focus(); } }
            if (m.scrollIntoView) { m.scrollIntoView({ behavior: "smooth", block: "center" }); }
          }
        }
        if (opts.reveal) {
          var rv = document.getElementById(opts.reveal);
          if (rv) {
            rv.hidden = false;
            if (rv.scrollIntoView) { rv.scrollIntoView({ behavior: "smooth", block: "center" }); }
          }
        }
        killProblem(form);
      } else {
        showProblem(form, r, function () { finish(form, opts); });
      }
      if (opts.onSettled) { opts.onSettled(r); }
    });
  }

  /* ── wiring ── */

  function injectHoneypot(form) {
    if (form.querySelector(".sp-hp")) return;
    var hp = document.createElement("input");
    hp.type = "text"; hp.name = "company"; hp.className = "sp-hp";
    hp.tabIndex = -1; hp.autocomplete = "off"; hp.setAttribute("aria-hidden", "true");
    form.appendChild(hp);
  }

  function note(form, ok, ref, msg) {
    var host = form.parentNode;
    var line = document.createElement("p");
    line.className = "sp-sync-line " + (ok ? "ok" : "warn");
    line.setAttribute("role", "status");
    if (msg) { line.textContent = msg; }
    else if (ok) { line.textContent = ref ? ("Received by the academy — reference " + ref + ".") : "Received by the academy."; }
    else { line.textContent = "Not sent right now — a copy is kept on this device and will retry next time you visit this site."; }
    host.appendChild(line);
  }

  function wire(form) {
    if (!form || form.dataset.spSyncWired) return;
    form.dataset.spSyncWired = "1";
    injectHoneypot(form);

    if (form.id === "newsletterForm") {
      /* no page handler, no modal: intercept, confirm inline */
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!API) { note(form, true, null, "Thanks for subscribing!"); return; }
        deliver(form, function (r) {
          if (r.state === "sent") { note(form, true, r.ref, null); }
          else if (r.state === "demo") { note(form, true, null, "Thanks for subscribing!"); }
          else if (r.state === "offline") { note(form, false, null, null); }
          else { note(form, false, null, "The subscription couldn't be accepted: " + r.message); }
        });
      });
      return;
    }

    /* drafts: autosave while typing, offer restore on visit */
    form.addEventListener("input", function () {
      clearTimeout(form._spDraftTimer);
      form._spDraftTimer = setTimeout(function () { saveDraft(form); }, 700);
    });
    form.addEventListener("change", function () {
      clearTimeout(form._spDraftTimer);
      form._spDraftTimer = null;
      saveDraft(form);
    });
    offerDraft(form);
  }

  /* retry anything queued from a previous offline visit.
     Sequential per form: each undeliverable item is held back and put
     back in one write at the end (never overwrite a re-queued item). */
  function retryPending() {
    Object.keys(SLUGS).forEach(function (id) {
      var slug = SLUGS[id], key = "sp_pending_" + slug, q = readQueue(slug);
      if (!q.length) { try { localStorage.removeItem(key); } catch (e) {} return; }
      var rest = q.slice();
      var heldBack = [];
      (function next() {
        var item = rest.shift();
        if (!item) {
          if (heldBack.length) { writeQueue(slug, heldBack); }
          else { try { localStorage.removeItem(key); } catch (e) {} }
          return;
        }
        send(slug, item.payload).then(function (j) {
          notifyDelivered(slug, j && j.ref);
          next();
        }).catch(function (err) {
          if (err && err.kind === "offline") {
            heldBack.push(item); /* still unreachable — keep it  */
          } /* invalid/busy: dropped for good — it can never pass */
          next();
        });
      })();
    });
  }

  function boot() {
    Object.keys(SLUGS).forEach(function (id) { wire(document.getElementById(id)); });
    if (API) { retryPending(); }
  }

  window.SP_FORMS = {
    deliver: deliver,
    finish: finish,
    serialize: serialize
  };

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", boot); }
  else { boot(); }
})();
