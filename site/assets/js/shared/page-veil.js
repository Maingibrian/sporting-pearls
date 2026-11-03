/* Sporting Pearls — page-veil.js (rev 24)
 * "The Rolling Pearl" page transition for the static site.
 * Loaded synchronously in <head> on every page (after img-fallback.js).
 *
 * The story: the ball you clicked carries you through the site.
 *   EXIT  — a navy circle blooms from the exact click point; the round
 *           crest rolls from under your cursor toward screen centre,
 *           arriving with a slight downward stretch (still in motion).
 *   ENTER — the new page opens under full navy; the crest completes the
 *           arrival — it drops the last few pixels, lands with an impact
 *           squash, rebounds and settles — then rolls back home to the
 *           point you clicked, shrinking as the navy contracts around it,
 *           and pops a ripple over the revealed page.
 *
 * rev 24 — full-teardown diagnosis of every remaining "weird" frame:
 *   1. HANDOFF POP (exit→enter): the exit crest used to freeze in a
 *      landing squash scale(1.13,.89) at centre while the enter crest
 *      started round scale(1,1) → the ball visibly popped at navigation.
 *      Now the exit ends mid-air — translate(0,-30px) scale(.98,1.04) —
 *      and the enter WAITS in exactly that state (inline style), so the
 *      frozen old-page frame and the first new-page frame are identical.
 *   2. LEAP-FROM-REST: the old enter bounce started at rest and jumped
 *      42px UP before squashing — a ball at rest doesn't leap. Now the
 *      first thing that happens on enter is a short gravity FALL into
 *      the impact squash (energy continues from the exit roll).
 *   3. CLIPPED BALL REVEAL (exit start): the circle used a slow-start
 *      ease, so the crest sat clipped/partially visible while it was
 *      already rolling away. The circle now blooms fast first
 *      (cubic-bezier(.22,.68,.24,1)) and the roll waits 60ms — the ball
 *      is fully on screen before it moves.
 *   4. INVISIBLE RIPPLE: the ring lived INSIDE the veil, so the veil's
 *      own clip-path cropped it — on enter the contracting circle made
 *      the ripple almost entirely invisible, on exit it was hidden while
 *      small. The ring is now a separate top-level element (z 4601),
 *      never clipped, and fires exactly as the ball lands.
 *   5. Sequencing: still ONE animation per element, strictly ordered on
 *      a single shared clock — fall/impact/rebound 0-380, contraction
 *      340-820, roll 420-820 (ends with the contraction), ripple
 *      770-1090, cleanup 1180 (after the ripple finishes).
 *
 * CSP-safe: no injected <style> tags, no eval; all styling via el.style.*
 * (CSSOM) and all motion via the Web Animations API.
 * Honours prefers-reduced-motion (transition disabled completely).
 */
(function () {
  'use strict';

  var RM = false;
  try { RM = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}

  var KEY = 'spVeilPoint';

  /* enter timing (ms) — one shared clock so every layer stays in step */
  var T = {
    settleDur: 380,     /* 0    → 380   fall + impact squash + rebound  */
    veilDelay: 340,     /* 340  → 820   circle contracts toward the pt  */
    veilDur: 480,
    rollDelay: 420,     /* 420  → 820   the crest rolls home (lands as
                          the navy finishes contracting)               */
    rollDur: 400,
    ringDelay: 770,     /* 770  → 1090  ripple pops as the ball lands   */
    ringDur: 320,
    cleanupAt: 1180
  };
  /* exit timing (ms) */
  var X = {
    bloomDur: 460,      /* 0   → 460   circle blooms from the click pt  */
    rollDelay: 60,      /* 60  → 480   crest rolls to centre            */
    rollDur: 420,
    ringDur: 480,       /* 0   → 480   ripple under the cursor          */
    navigateAt: 500
  };
  /* the shared handoff pose: where the exit ball stops and the enter
   * ball waits — 30px above centre, stretched along its downward motion */
  var HOVER_Y = -30;

  function readPoint() {
    try {
      var raw = sessionStorage.getItem(KEY);
      sessionStorage.removeItem(KEY);
      if (!raw) return null;
      var p = JSON.parse(raw);
      if (p && isFinite(p.x) && isFinite(p.y)) return p;
    } catch (e) {}
    return null;
  }
  function storePoint(x, y) {
    try { sessionStorage.setItem(KEY, JSON.stringify({ x: x, y: y })); } catch (e) {}
  }

  /* ---------- veil factory (inline CSSOM styles only) ---------- */
  function makeVeil(x, y) {
    var veil = document.createElement('div');
    veil.setAttribute('aria-hidden', 'true');
    veil.style.position = 'fixed';
    veil.style.inset = '0';
    veil.style.zIndex = '4600';
    veil.style.pointerEvents = 'none';
    veil.style.background = 'radial-gradient(120% 90% at 50% 8%, #14284b 0%, #0c1a33 62%)';

    var pearl = document.createElement('div');
    pearl.style.position = 'absolute';
    pearl.style.left = x + 'px';
    pearl.style.top = y + 'px';
    pearl.style.width = '76px';
    pearl.style.height = '76px';
    pearl.style.margin = '-38px 0 0 -38px';
    pearl.style.borderRadius = '50%';
    pearl.style.overflow = 'hidden';
    pearl.style.background = '#f59d1e';
    pearl.style.boxShadow = '0 14px 34px rgba(2,8,20,.55)';
    var img = document.createElement('img');
    img.alt = '';
    img.src = 'logo.png';
    img.style.width = '100%';
    img.style.height = '100%';
    img.style.objectFit = 'cover';
    img.style.display = 'block';
    pearl.appendChild(img);
    veil.appendChild(pearl);

    document.documentElement.appendChild(veil);
    return { veil: veil, pearl: pearl, x: x, y: y };
  }

  /* the ripple lives OUTSIDE the veil so the veil's own clip-path can
   * never crop it (rev 23 cropped it away to almost nothing on enter) */
  function makeRing(x, y) {
    var ring = document.createElement('div');
    ring.setAttribute('aria-hidden', 'true');
    ring.style.position = 'fixed';
    ring.style.left = x + 'px';
    ring.style.top = y + 'px';
    ring.style.width = '150px';
    ring.style.height = '150px';
    ring.style.margin = '-75px 0 0 -75px';
    ring.style.borderRadius = '50%';
    ring.style.border = '2px solid rgba(245,157,30,.85)';
    ring.style.opacity = '0';
    ring.style.pointerEvents = 'none';
    ring.style.zIndex = '4601';
    document.documentElement.appendChild(ring);
    return ring;
  }

  /* ================= ENTER SIDE ================= */
  var pending = !RM && readPoint();
  var enterDone = false;
  var enterVeil = null;
  var enterRing = null;

  function cleanup() {
    if (enterDone) return;
    enterDone = true;
    if (enterVeil && enterVeil.parentNode) enterVeil.parentNode.removeChild(enterVeil);
    if (enterRing && enterRing.parentNode) enterRing.parentNode.removeChild(enterRing);
    /* always hand the page back its scroll */
    document.documentElement.style.overflow = '';
    document.body.style.overflow = '';
  }

  if (pending) {
    var ev = makeVeil(pending.x, pending.y);
    ev.veil.id = 'spVeil';
    enterVeil = ev.veil;
    ev.pearl.style.left = '50%';   /* the ball waits at centre */
    ev.pearl.style.top = '50%';
    ev.pearl.style.margin = '-38px 0 0 -38px';
    /* WAIT POSE — identical to the exit's final frame, so the navigation
     * handoff is frame-perfect: 30px above centre, stretched downwards */
    ev.pearl.style.transform = 'translate(0,' + HOVER_Y + 'px) scale(.98,1.04)';

    /* keep the page still while the veil is up (restored in cleanup) */
    document.documentElement.style.overflow = 'hidden';

    function playEnter() {
      if (enterDone) return;
      var cx = innerWidth / 2, cy = innerHeight / 2;
      var px = pending.x, py = pending.y;
      var dx = px - cx, dy = py - cy;
      var dir = dx >= 0 ? 1 : -1;

      enterRing = makeRing(px, py);

      /* 1) the crest completes its arrival: a short gravity fall into an
       *    impact squash at centre, one rebound, a micro-squash, settle.
       *    Frame 0 equals the wait pose — no pop — and the whole thing
       *    ends at the identity transform so the roll picks up cleanly. */
      ev.pearl.animate([
        { transform: 'translate(0,' + HOVER_Y + 'px) scale(.98,1.04)', easing: 'cubic-bezier(.55,0,.8,.55)' },
        { transform: 'translate(0,0) scale(1.18,.82)', offset: .22, easing: 'cubic-bezier(.25,.6,.45,1)' },
        { transform: 'translate(0,-15px) scale(.99,1.01)', offset: .55, easing: 'cubic-bezier(.5,0,.7,.5)' },
        { transform: 'translate(0,0) scale(1.05,.95)', offset: .82, easing: 'cubic-bezier(.3,.6,.4,1)' },
        { transform: 'translate(0,0) scale(1,1)' }
      ], { duration: T.settleDur, fill: 'forwards' });

      /* 2) the veil contracts back toward the point that was clicked */
      ev.veil.animate([
        { clipPath: 'circle(150% at ' + px + 'px ' + py + 'px)' },
        { clipPath: 'circle(0% at ' + px + 'px ' + py + 'px)' }
      ], { duration: T.veilDur, delay: T.veilDelay, easing: 'cubic-bezier(.77,0,.18,1)', fill: 'forwards' });

      /* 3) after the settle, the ball rolls home to the click point,
       *    shrinking as it travels — it arrives exactly as the navy
       *    finishes contracting around it. */
      ev.pearl.animate([
        { transform: 'translate(0,0) rotate(0deg) scale(1)', opacity: 1, easing: 'cubic-bezier(.5,.05,.6,.95)' },
        { transform: 'translate(' + (dx * .55) + 'px,' + (dy * .55 - 12) + 'px) rotate(' + (dir * 140) + 'deg) scale(.68)', offset: .55, easing: 'cubic-bezier(.45,.2,.7,.6)' },
        { transform: 'translate(' + dx + 'px,' + dy + 'px) rotate(' + (dir * 230) + 'deg) scale(.1)', opacity: 0 }
      ], { duration: T.rollDur, delay: T.rollDelay, fill: 'forwards' });

      /* 4) the ripple pops over the revealed page exactly as the ball
       *    lands — a separate element, so nothing clips it. */
      enterRing.animate([
        { transform: 'scale(.2)', opacity: .9 },
        { transform: 'scale(1.7)', opacity: 0 }
      ], { duration: T.ringDur, delay: T.ringDelay, easing: 'cubic-bezier(.2,.7,.3,1)', fill: 'forwards' });

      setTimeout(cleanup, T.cleanupAt);
    }

    function start() {
      /* two rAFs: by the second frame the page beneath has painted at least
       * once, so contracting the veil can never reveal a blank page */
      requestAnimationFrame(function () { requestAnimationFrame(playEnter); });
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', start);
    } else {
      start();
    }
    setTimeout(cleanup, 5200); /* failsafe — never trap the page */
    window.addEventListener('pageshow', function (e) { if (e.persisted) cleanup(); });
  }

  /* ================= EXIT SIDE ================= */
  function eligible(a, e) {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return null;
    if (a.target && a.target !== '_self') return null;
    if (a.hasAttribute('download') || a.hasAttribute('data-no-veil')) return null;
    var href = a.getAttribute('href');
    if (!href || href.charAt(0) === '#') return null;
    if (/^(mailto:|tel:|sms:|javascript:|data:|blob:)/i.test(href)) return null;
    if (/\.(zip|rar|7z|pdf|png|jpe?g|webp|gif|svg|ico|mp4|webm|xml|json|txt|csv|ics)([?#]|$)/i.test(href)) return null;
    var url;
    try { url = new URL(a.href, location.href); } catch (err) { return null; }
    if (url.origin !== location.origin) return null;
    if (url.pathname === location.pathname && url.search === location.search) return null;
    return url.href;
  }

  if (!RM) {
    var busy = false;
    document.addEventListener('click', function (e) {
      if (busy) return;
      var t = e.target;
      var a = t && t.closest ? t.closest('a') : null;
      if (!a) return;
      var href = eligible(a, e);
      if (!href) return;
      e.preventDefault();
      busy = true;

      /* keyboard activation reports 0/0 — fall back to screen centre */
      var x = (e.clientX || innerWidth / 2);
      var y = (e.clientY || innerHeight / 2);
      if (!x) x = innerWidth / 2;
      if (!y) y = innerHeight / 2;
      storePoint(x, y);

      var v = makeVeil(x, y);
      v.veil.style.pointerEvents = 'auto'; /* swallow further clicks while leaving */
      var ring = makeRing(x, y);
      var cx = innerWidth / 2, cy = innerHeight / 2;
      var dx = cx - x, dy = cy - y;
      var dir = dx >= 0 ? 1 : -1;
      var R = Math.ceil(Math.hypot(innerWidth, innerHeight));

      /* circle blooms from the exact click point — fast first so the
       * crest is revealed immediately, then eases to full cover */
      v.veil.animate([
        { clipPath: 'circle(0px at ' + x + 'px ' + y + 'px)' },
        { clipPath: 'circle(' + R + 'px at ' + x + 'px ' + y + 'px)' }
      ], { duration: X.bloomDur, easing: 'cubic-bezier(.22,.68,.24,1)', fill: 'forwards' });

      /* the crest waits a beat (60ms — by then the bloom has uncovered
       * it fully), then rolls to centre with a small hop, arriving 30px
       * ABOVE centre with a downward stretch — the exact pose the next
       * page's enter picks up. The roll ends at a full 360° revolution
       * so the crest lands UPRIGHT — the enter veil's ball waits
       * unrotated, and the handoff between the two frames is pixel-
       * perfect (a partial rotation would pop the crest's orientation
       * at the navigation boundary). */
      v.pearl.animate([
        { transform: 'translate(0,0) rotate(0deg) scale(1)', easing: 'cubic-bezier(.4,.1,.55,.9)' },
        { transform: 'translate(' + (dx * .5) + 'px,' + (dy * .5 - 22) + 'px) rotate(' + (dir * 165) + 'deg) scale(1.03)', offset: .55, easing: 'cubic-bezier(.35,.55,.3,1)' },
        { transform: 'translate(' + dx + 'px,' + (dy + HOVER_Y) + 'px) rotate(' + (dir * 360) + 'deg) scale(.98,1.04)' }
      ], { duration: X.rollDur, delay: X.rollDelay, fill: 'forwards' });

      /* amber ripple right under the cursor — never clipped */
      ring.animate([
        { transform: 'scale(.25)', opacity: .85 },
        { transform: 'scale(1.5)', opacity: 0 }
      ], { duration: X.ringDur, easing: 'cubic-bezier(.2,.7,.3,1)', fill: 'forwards' });

      /* navigate once the screen is covered */
      setTimeout(function () { window.location.href = href; }, X.navigateAt);

      /* if navigation never fires (rare), never trap the user */
      setTimeout(function () {
        if (v.veil.parentNode) {
          v.veil.parentNode.removeChild(v.veil);
          if (ring.parentNode) ring.parentNode.removeChild(ring);
          busy = false;
        }
      }, 1700);
    }, false);
  }
})();
