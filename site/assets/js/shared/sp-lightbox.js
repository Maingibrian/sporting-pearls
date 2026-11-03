/* Sporting Pearls — sp-lightbox.js (rev 1)
 * Gallery lightbox for the static site.
 * Binds to any container marked data-lightbox (feminin gallery, about-us collage,
 * index moment wall). Click a photo → it flies open at the centre of the screen
 * while the page behind is dimmed and BLURRED. Close with ×, the backdrop,
 * Esc, or the arrow keys / side buttons to browse the group.
 *
 * CSP-safe: no injected <style> tags, no eval; styling via el.style.* (CSSOM)
 * and motion via the Web Animations API. Honours prefers-reduced-motion.
 */
(function () {
  'use strict';

  var RM = false;
  try { RM = matchMedia('(prefers-reduced-motion: reduce)').matches; } catch (e) {}

  var SEL = '[data-lightbox]';
  var state = {
    open: false,
    group: [],      /* [{img, cap}] in DOM order */
    index: 0,
    lastFocus: null,
    scrollY: 0
  };

  /* ---------- helpers ---------- */
  function css(el, props) {
    for (var k in props) el.style[k] = props[k];
  }
  function figOf(node) {
    return node && node.closest ? node.closest('figure') : null;
  }
  function captionOf(img) {
    var fig = figOf(img);
    if (!fig) return null;
    var cap = fig.querySelector('figcaption');
    if (!cap) return null;
    var head = cap.querySelector('span');
    var kicker = head ? head.textContent.replace(/\s+/g, ' ').trim() : '';
    var clone = cap.cloneNode(true);
    var sp = clone.querySelector('span');
    if (sp) sp.parentNode.removeChild(sp);
    var text = clone.textContent.replace(/\s+/g, ' ').trim();
    if (!kicker && !text) return null;
    return { kicker: kicker, text: text };
  }
  function srcOf(img) {
    return (img.currentSrc || img.getAttribute('src') || '');
  }

  /* ---------- overlay skeleton (built once, reused) ---------- */
  var ui = null;
  function build() {
    if (ui) return ui;

    var root = document.createElement('div');
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-label', 'Photo viewer');
    css(root, {
      position: 'fixed', inset: '0', zIndex: '4700',
      display: 'none',
      background: 'rgba(7,15,31,.52)',
      webkitBackdropFilter: 'blur(0px) saturate(1.05)',
      backdropFilter: 'blur(0px) saturate(1.05)',
      fontFamily: 'var(--fm, "Work Sans", Arial, sans-serif)',
      opacity: '0'
    });

    var stage = document.createElement('div');
    css(stage, { position: 'absolute', inset: '0', overflow: 'hidden' });
    root.appendChild(stage);

    var frame = document.createElement('div');       /* moving photo box */
    css(frame, {
      position: 'absolute', left: '50%', top: '50%',
      transform: 'translate(-50%,-50%)',
      willChange: 'transform, width, height'
    });
    stage.appendChild(frame);

    var img = document.createElement('img');
    img.alt = '';
    css(img, {
      display: 'block', width: '100%', height: '100%',
      objectFit: 'contain', borderRadius: 'inherit',
      boxShadow: '0 40px 90px -30px rgba(2,8,20,.75)'
    });
    frame.appendChild(img);

    var cap = document.createElement('div');
    css(cap, {
      position: 'absolute', left: '50%', bottom: '3.4vh', transform: 'translateX(-50%)',
      maxWidth: 'min(86vw, 640px)', textAlign: 'center',
      color: 'rgba(251,250,247,.92)', fontSize: '.82rem', lineHeight: '1.55',
      letterSpacing: '.01em', textShadow: '0 2px 14px rgba(2,8,20,.8)',
      opacity: '0'
    });
    var capKick = document.createElement('span');
    css(capKick, {
      display: 'block', fontWeight: '700', letterSpacing: '.2em', textTransform: 'uppercase',
      fontSize: '.6rem', color: 'var(--amber-3, #f5b03a)', marginBottom: '.3rem'
    });
    var capTxt = document.createElement('span');
    cap.appendChild(capKick);
    cap.appendChild(capTxt);
    root.appendChild(cap);

    var counter = document.createElement('div');
    css(counter, {
      position: 'absolute', top: '1.4rem', left: '50%', transform: 'translateX(-50%)',
      color: 'rgba(251,250,247,.72)', fontSize: '.66rem', fontWeight: '700',
      letterSpacing: '.22em', textTransform: 'uppercase',
      opacity: '0'
    });
    root.appendChild(counter);

    function pill(label, ary) {
      var b = document.createElement('button');
      b.type = 'button';
      b.setAttribute('aria-label', label);
      b.innerHTML = ary;
      css(b, {
        position: 'absolute', display: 'flex', alignItems: 'center', justifyContent: 'center',
        width: '46px', height: '46px', borderRadius: '50%',
        border: '1px solid rgba(251,250,247,.32)',
        background: 'rgba(12,26,51,.45)',
        webkitBackdropFilter: 'blur(6px)', backdropFilter: 'blur(6px)',
        color: '#fbfaf7', cursor: 'pointer', padding: '0',
        transition: 'background .3s, border-color .3s, transform .3s'
      });
      b.addEventListener('mouseenter', function () {
        css(b, { background: 'var(--amber,#f59d1e)', borderColor: 'var(--amber,#f59d1e)', color: '#0c1a33', transform: 'scale(1.08)' });
      });
      b.addEventListener('mouseleave', function () {
        css(b, { background: 'rgba(12,26,51,.45)', borderColor: 'rgba(251,250,247,.32)', color: '#fbfaf7', transform: 'scale(1)' });
      });
      return b;
    }

    var prev = pill('Previous photo', '&#8249;');
    css(prev, { left: 'max(1.2rem, env(safe-area-inset-left))', top: '50%', marginTop: '-23px' });
    root.appendChild(prev);

    var next = pill('Next photo', '&#8250;');
    css(next, { right: 'max(1.2rem, env(safe-area-inset-right))', top: '50%', marginTop: '-23px' });
    root.appendChild(next);

    var close = pill('Close photo viewer', '&#10005;');
    css(close, { right: 'max(1.2rem, env(safe-area-inset-right))', top: '1.2rem' });
    root.appendChild(close);

    prev.addEventListener('click', function (e) { e.stopPropagation(); step(-1); });
    next.addEventListener('click', function (e) { e.stopPropagation(); step(1); });
    close.addEventListener('click', function (e) { e.stopPropagation(); closeLightbox(); });
    stage.addEventListener('click', function () { closeLightbox(); });

    document.body.appendChild(root);

    ui = { root: root, stage: stage, frame: frame, img: img, cap: cap, capKick: capKick, capTxt: capTxt,
           counter: counter, prev: prev, next: next, close: close };
    return ui;
  }

  /* ---------- geometry ---------- */
  function targetBox(natW, natH) {
    var vw = innerWidth, vh = innerHeight;
    var maxW = Math.min(vw * .88, 1320);
    var maxH = vh * .8;
    var r = (natW && natH) ? natW / natH : 16 / 10;
    var w = maxW, h = w / r;
    if (h > maxH) { h = maxH; w = h * r; }
    return { w: Math.round(w), h: Math.round(h) };
  }

  function show(i, viaNav) {
    var item = state.group[i];
    if (!item) return;
    state.index = i;

    var u = ui;
    u.img.src = srcOf(item.img);
    u.img.alt = item.img.alt || '';
    u.capKick.textContent = item.cap ? item.cap.kicker : '';
    u.capTxt.textContent = item.cap ? item.cap.text : '';
    u.cap.style.display = (item.cap && (item.cap.kicker || item.cap.text)) ? 'block' : 'none';
    u.counter.textContent = (state.group.length > 1) ? (i + 1) + ' / ' + state.group.length : '';
    u.counter.style.display = state.group.length > 1 ? 'block' : 'none';
    var solo = state.group.length < 2;
    u.prev.style.display = solo ? 'none' : 'flex';
    u.next.style.display = solo ? 'none' : 'flex';

    var nw = item.img.naturalWidth || 1200;
    var nh = item.img.naturalHeight || 800;
    var box = targetBox(nw, nh);
    u.frame.style.width = box.w + 'px';
    u.frame.style.height = box.h + 'px';

    if (viaNav) {
      /* slide-swap: current frame glides out left/right, new one glides in */
      var dir = viaNav; /* +1 or -1 */
      var vw = innerWidth;
      u.frame.animate([
        { transform: 'translate(calc(-50% + ' + (dir * -46) + 'px), -50%) scale(.94)', opacity: 0 },
        { transform: 'translate(-50%, -50%) scale(1)', opacity: 1 }
      ], { duration: RM ? 0 : 380, easing: 'cubic-bezier(.2,.8,.25,1)' });
    }
  }

  function step(dir) {
    if (!state.open) return;
    var n = state.index + dir;
    if (n < 0) n = state.group.length - 1;
    if (n >= state.group.length) n = 0;
    if (n === state.index) return;
    show(n, dir);
  }

  /* ---------- open / close ---------- */
  function openLightbox(firstImg) {
    var container = firstImg.closest(SEL);
    if (!container) return;

    var imgs = [];
    var nodes = container.querySelectorAll('img');
    for (var k = 0; k < nodes.length; k++) {
      var im = nodes[k];
      if (im.closest(SEL) !== container) continue;   /* ignore nested groups */
      if (!im.getAttribute('src')) continue;
      imgs.push({ img: im, cap: captionOf(im) });
    }
    var idx = 0;
    for (var j = 0; j < imgs.length; j++) {
      if (imgs[j].img === firstImg) { idx = j; break; }
    }
    if (!imgs.length) return;

    state.group = imgs;
    state.index = idx;
    state.lastFocus = document.activeElement;

    var u = build();
    show(idx, 0);

    u.root.style.display = 'block';
    state.scrollY = window.scrollY;
    css(document.documentElement, { overflow: 'hidden' });
    css(document.body, { overflow: 'hidden' });
    state.open = true;

    var thumb = firstImg.getBoundingClientRect();

    if (!RM) {
      /* backdrop: dim + BLUR the page behind */
      u.root.animate([
        { opacity: 0, webkitBackdropFilter: 'blur(0px) saturate(1.05)', backdropFilter: 'blur(0px) saturate(1.05)' },
        { opacity: 1, webkitBackdropFilter: 'blur(18px) saturate(1.05)', backdropFilter: 'blur(18px) saturate(1.05)' }
      ], { duration: 420, easing: 'cubic-bezier(.3,.6,.2,1)', fill: 'forwards' });

      /* FLIP: the photo flies from its tile to the centre of the screen */
      var bw = u.frame.offsetWidth, bh = u.frame.offsetHeight;
      var cx = innerWidth / 2, cy = innerHeight / 2;
      var sx = thumb.width / bw, sy = thumb.height / bh;
      var tx = (thumb.left + thumb.width / 2) - cx;
      var ty = (thumb.top + thumb.height / 2) - cy;
      u.frame.style.transformOrigin = 'center';
      u.frame.animate([
        {
          transform: 'translate(calc(-50% + ' + tx + 'px), calc(-50% + ' + ty + 'px)) scale(' + sx + ', ' + sy + ')',
          borderRadius: '14px'
        },
        {
          transform: 'translate(-50%, -50%) scale(1, 1)',
          borderRadius: '10px'
        }
      ], { duration: 520, easing: 'cubic-bezier(.22,.9,.24,1)', fill: 'forwards' });

      u.cap.animate([{ opacity: 0, transform: 'translateX(-50%) translateY(10px)' },
                     { opacity: 1, transform: 'translateX(-50%) translateY(0)' }],
                    { duration: 380, delay: 240, easing: 'ease-out', fill: 'forwards' });
      u.counter.animate([{ opacity: 0 }, { opacity: 1 }],
                        { duration: 300, delay: 300, fill: 'forwards' });
      u.close.animate([{ opacity: 0, transform: 'scale(.7)' }, { opacity: 1, transform: 'scale(1)' }],
                      { duration: 260, delay: 200, easing: 'cubic-bezier(.3,1.4,.4,1)', fill: 'forwards' });
    } else {
      u.root.style.opacity = '1';
      css(u.root, { webkitBackdropFilter: 'blur(18px)', backdropFilter: 'blur(18px)' });
      u.cap.style.opacity = '1';
      u.counter.style.opacity = '1';
    }

    u.close.focus({ preventScroll: true });
  }

  function closeLightbox() {
    if (!state.open) return;
    var u = ui;
    var item = state.group[state.index];
    state.open = false;

    function finish() {
      u.root.style.display = 'none';
      u.root.getAnimations().forEach(function (a) { a.cancel(); });
      css(document.documentElement, { overflow: '' });
      css(document.body, { overflow: '' });
      window.scrollTo(0, state.scrollY);
      if (state.lastFocus && state.lastFocus.focus) {
        try { state.lastFocus.focus({ preventScroll: true }); } catch (e) {}
      }
    }

    if (!RM && item) {
      /* fly the photo back into its tile */
      var thumb = item.img.getBoundingClientRect();
      var bw = u.frame.offsetWidth, bh = u.frame.offsetHeight;
      var cx = innerWidth / 2, cy = innerHeight / 2;
      var sx = thumb.width / bw, sy = thumb.height / bh;
      var tx = (thumb.left + thumb.width / 2) - cx;
      var ty = (thumb.top + thumb.height / 2) - cy;
      u.frame.animate([
        { transform: 'translate(-50%, -50%) scale(1, 1)', borderRadius: '10px' },
        {
          transform: 'translate(calc(-50% + ' + tx + 'px), calc(-50% + ' + ty + 'px)) scale(' + sx + ', ' + sy + ')',
          borderRadius: '14px'
        }
      ], { duration: 400, easing: 'cubic-bezier(.5,0,.75,.4)', fill: 'forwards' });
      u.root.animate([
        { opacity: 1, webkitBackdropFilter: 'blur(18px) saturate(1.05)', backdropFilter: 'blur(18px) saturate(1.05)' },
        { opacity: 0, webkitBackdropFilter: 'blur(0px)', backdropFilter: 'blur(0px)' }
      ], { duration: 340, easing: 'ease-in', fill: 'forwards' });
      u.cap.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 160, fill: 'forwards' });
      u.counter.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 160, fill: 'forwards' });
      setTimeout(finish, 410);
    } else {
      finish();
    }
  }

  /* ---------- events ---------- */
  document.addEventListener('click', function (e) {
    if (state.open) return;                       /* clicks inside viewer handled by its own nodes */
    var t = e.target;
    if (!t || !t.closest) return;
    var box = t.closest(SEL);
    if (!box) return;
    var fig = t.closest('figure') || box;
    var img = t.tagName === 'IMG' ? t : fig.querySelector('img');
    if (!img || !box.contains(img)) return;
    /* ignore icons / decorative svgs */
    if (img.closest('svg')) return;
    e.preventDefault();
    openLightbox(img);
  }, false);

  document.addEventListener('keydown', function (e) {
    if (!state.open) return;
    if (e.key === 'Escape') { e.preventDefault(); closeLightbox(); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); step(-1); }
    else if (e.key === 'ArrowRight') { e.preventDefault(); step(1); }
  });

  window.addEventListener('pageshow', function (e) {
    if (e.persisted && state.open) closeLightbox();
  });
})();
