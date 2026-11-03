/* Sporting Pearls - index-2.js (verbatim v15) */
document.documentElement.classList.add('js');
var motionOK = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function revealAllFallback() {
var pl = document.getElementById('preloader');
if (pl) { pl.style.display = 'none'; }
document.body.classList.remove('locked');
document.body.style.overflow = '';
document.querySelectorAll('[data-reveal],.lines,.reveal-inner,.line-word,.heading-line,.v-node,.values-endcap,.tw-char').forEach(function (el) {
el.classList.add('in');
el.classList.add('on');
el.classList.add('typed');
});
var cur = document.getElementById('aboutCursor');
if (cur) cur.style.display = 'none';
}
if (typeof gsap === 'undefined') { revealAllFallback(); }
var prog = document.getElementById('progress');
var scrollTick = false;
window.addEventListener('scroll', function () {
if (!scrollTick) {
window.requestAnimationFrame(function () {
var h = document.documentElement;
prog.style.width = (window.scrollY / (h.scrollHeight - window.innerHeight) * 100) + '%';
scrollTick = false;
});
scrollTick = true;
}
}, { passive: true });

if (!motionOK) { revealAllFallback(); }
/* =========================================================
RIGHT-CLICK IMAGE PICKER & PERSISTENCE ENGINE
========================================================= */
let activeTargetImg = null;
const fileInput = document.getElementById('imageFileInput');
const toast = document.getElementById('imgToast');
const toastMsg = document.getElementById('imgToastMsg');
const copyPathBtn = document.getElementById('copyPathBtn');
const resetImgBtn = document.getElementById('resetImgBtn');
let lastSelectedPath = '';
// 1. Load saved replacements from localStorage on page boot
function loadSavedImages() {
document.querySelectorAll('img[data-swappable="true"]').forEach(img => {
const saved = localStorage.getItem('sp_img_' + img.id);
if (saved) {
img.src = saved;
}
});
}
loadSavedImages();
// 2. Right-click listener
document.addEventListener('contextmenu', function (e) {
const target = e.target.closest('img[data-swappable="true"]');
if (target) {
e.preventDefault();
activeTargetImg = target;
fileInput.value = ''; // reset
fileInput.click();
}
});
// 3. When a file is chosen
fileInput.addEventListener('change', function (e) {
const file = e.target.files[0];
if (file && activeTargetImg) {
const reader = new FileReader();
reader.onload = function (evt) {
const dataUrl = evt.target.result;
activeTargetImg.src = dataUrl;
// Persist in localStorage
if (activeTargetImg.id) {
localStorage.setItem('sp_img_' + activeTargetImg.id, dataUrl);
}
lastSelectedPath = 'images/' + file.name;
showToast(`Updated image to: <b style="color:var(--amber);">${lastSelectedPath}</b><br><span style="font-size:0.875rem;opacity:0.8;">(Loaded and stored in local cache)</span>`);
};
reader.readAsDataURL(file);
}
});
function showToast(htmlMsg) {
toastMsg.innerHTML = htmlMsg;
toast.classList.add('show');
clearTimeout(toast.timer);
toast.timer = setTimeout(hideToast, 5000);
}
function hideToast() {
toast.classList.remove('show');
}
/* Phase 5: the toast close button used an inline onclick= — now bound
   here so the CSP can drop script-src 'unsafe-inline'. */
var toastClose = document.getElementById('imgToastClose');
if (toastClose) toastClose.addEventListener('click', hideToast);
copyPathBtn.addEventListener('click', function () {
if (lastSelectedPath) {
navigator.clipboard.writeText(lastSelectedPath);
copyPathBtn.textContent = 'Copied!';
setTimeout(() => { copyPathBtn.textContent = 'Copy Path'; }, 1500);
}
});
resetImgBtn.addEventListener('click', function () {
if (confirm('Reset all replaced images back to original online links?')) {
document.querySelectorAll('img[data-swappable="true"]').forEach(img => {
localStorage.removeItem('sp_img_' + img.id);
});
location.reload();
}
});
/* =========================================================
TYPEWRITER ENGINE: "About Sporting Pearls"
========================================================= */
function initTypewriter() {
const heading = document.getElementById('aboutTypewriter');
const cursor = document.getElementById('aboutCursor');
if (!heading) return;
const segments = heading.querySelectorAll('.tw-segment');
let charElements = [];
segments.forEach(seg => {
const text = seg.getAttribute('data-type') || seg.textContent;
seg.textContent = '';
for (let i = 0; i < text.length; i++) {
const span = document.createElement('span');
span.className = 'tw-char';
span.textContent = text[i];
seg.appendChild(span);
charElements.push(span);
}
});
if (!motionOK) {
charElements.forEach(ch => ch.classList.add('typed'));
if (cursor) cursor.style.display = 'none';
return;
}
let played = false;
ScrollTrigger.create({
trigger: heading,
start: "top 82%",
onEnter: () => {
if (played) return;
played = true;
if (cursor) {
cursor.classList.add('active');
cursor.style.opacity = '1';
}
let charIndex = 0;
const speed = 45; // ms per character
function typeNext() {
if (charIndex < charElements.length) {
charElements[charIndex].classList.add('typed');
charIndex++;
setTimeout(typeNext, speed + (Math.random() * 20));
} else {
setTimeout(() => {
if (cursor) cursor.classList.add('active');
}, 400);
}
}
setTimeout(typeNext, 200);
}
});
}
/* =========================================================
SERPENTINE DRAWING ENGINE (Values 01 to 06)
========================================================= */
function initValuesSerpentine() {
var VB_W = 900, VB_H = 1860;
var wrap = document.getElementById('valWrap');
var core = document.getElementById('valCore');
var layers = [...document.querySelectorAll('.v-path')];
var pen = document.getElementById('valPen');
var arrow = document.getElementById('valArrow');
var endcap = document.getElementById('valEndcap');
var nodes = [...document.querySelectorAll('.v-node')];
if (!wrap || !core) return;
var L = core.getTotalLength();
var aP = arrow.querySelector('path');
var AL = aP ? aP.getTotalLength() : 60;
if (aP) aP.style.setProperty('--al', AL);
layers.forEach(p => {
p.style.strokeDasharray = L;
p.style.strokeDashoffset = motionOK ? L : 0;
});
var thresholds = nodes.map(n => {
var y = parseFloat(n.dataset.y);
var lo = 0, hi = L;
while (hi - lo > 2) {
var mid = (lo + hi) / 2;
core.getPointAtLength(mid).y < y ? lo = mid : hi = mid;
}
return hi;
});
var finished = false;
function updateSerpentine() {
var p = 0;
if (!motionOK) {
p = 1;
} else {
var rect = wrap.getBoundingClientRect();
var start = window.innerHeight * 0.82;
p = (start - rect.top) / (rect.height * 0.94);
p = Math.max(0, Math.min(1, p));
}
var drawn = L * p;
layers.forEach(l => l.style.strokeDashoffset = L - drawn);
nodes.forEach((n, i) => {
n.classList.toggle('on', drawn >= thresholds[i] - 10);
});
// Travelling Pen
if (p > 0.002 && p < 0.995 && motionOK) {
var pt = core.getPointAtLength(drawn);
pen.style.left = (pt.x / VB_W * 100) + '%';
pen.style.top = (pt.y / VB_H * 100) + '%';
pen.style.opacity = '1';
} else {
pen.style.opacity = '0';
}
// Finish
if (p >= 0.995 && !finished) {
finished = true;
if (arrow) arrow.classList.add('draw');
if (endcap) endcap.classList.add('on');
}
}
window.addEventListener('scroll', updateSerpentine, { passive: true });
window.addEventListener('resize', updateSerpentine);
updateSerpentine();
}
function initParticles() {
var canvas = document.getElementById('impactCanvas');
if (!canvas || !canvas.getContext) return;
var section = canvas.parentElement;
var ctx = canvas.getContext('2d');
var W = 0, H = 0, dpr = 1, particles = [], ripples = [], running = false;
function resize() {
dpr = Math.min(window.devicePixelRatio || 1, 2);
W = section.offsetWidth; H = section.offsetHeight;
canvas.width = W * dpr; canvas.height = H * dpr;
canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
resize();
window.addEventListener('resize', resize);
var COUNT = 70;
for (var i = 0; i < COUNT; i++) {
particles.push({ x: Math.random() * W, y: Math.random() * H, r: Math.random() * 1.8 + 0.6, vx: (Math.random() - 0.5) * 0.15, vy: -(Math.random() * 0.25 + 0.08), a: Math.random() * 0.5 + 0.15 });
}
function addRipple(x, y) { ripples.push({ x: x, y: y, r: 0, a: 0.5 }); }
var items = section.querySelectorAll('.impact-item');
var rio = new IntersectionObserver(function (es) {
es.forEach(function (e) {
if (e.isIntersecting) {
var r = e.target.getBoundingClientRect();
var s = section.getBoundingClientRect();
addRipple(r.left - s.left + r.width / 2, r.top - s.top + r.height / 2);
rio.unobserve(e.target);
}
});
}, { threshold: 0.6 });
items.forEach(function (it) { rio.observe(it); });
function frame() {
requestAnimationFrame(frame);
if (!running) return;
ctx.clearRect(0, 0, W, H);
for (var i = 0; i < particles.length; i++) {
var p = particles[i];
p.x += p.vx; p.y += p.vy;
if (p.y < -5) { p.y = H + 5; p.x = Math.random() * W; }
if (p.x < -5) p.x = W + 5; if (p.x > W + 5) p.x = -5;
ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, 6.2832);
ctx.fillStyle = 'rgba(245,157,30,' + p.a + ')'; ctx.fill();
}
for (var r = ripples.length - 1; r >= 0; r--) {
var rp = ripples[r];
rp.r += 2.2; rp.a -= 0.008;
if (rp.a <= 0) { ripples.splice(r, 1); continue; }
ctx.beginPath(); ctx.arc(rp.x, rp.y, rp.r, 0, 6.2832);
ctx.strokeStyle = 'rgba(245,157,30,' + rp.a + ')'; ctx.lineWidth = 1.5; ctx.stroke();
}
}
var vio = new IntersectionObserver(function (es) {
es.forEach(function (e) { running = e.isIntersecting; });
}, { threshold: 0 });
vio.observe(section);
requestAnimationFrame(frame);
}
if (motionOK && typeof gsap !== 'undefined') {
gsap.registerPlugin(ScrollTrigger);
var lenis = null;
if (typeof Lenis !== 'undefined') {
lenis = new Lenis({ lerp: .08, autoRaf: false, syncTouch: true, smoothWheel: true });
lenis.on('scroll', ScrollTrigger.update);
gsap.ticker.add(function (time) { lenis.raf(time * 1000); });
gsap.ticker.lagSmoothing(0);
}
var preloader = document.getElementById('preloader');
function runPreloader(onComplete) {
if (!preloader) { if (onComplete) onComplete(); return; }
var $ = function (s) { return document.querySelector(s); };
var pre = $('#preloader'), wrapEl = $('#crestWrap'), wipe = $('#plWipe'),
brand = $('#plBrand'), progEl = $('#plProgress'), pct = $('#pct'),
glow = $('#glow');
var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
var S = 0.2;
var live = [], phases = [], pi = 0, t0 = null, rafId = null, running = false;
var OUT = 'cubic-bezier(.16,1,.3,1)', INOUT = 'cubic-bezier(.65,0,.35,1)',
BACK = 'cubic-bezier(.34,1.56,.64,1)', WIPE = 'cubic-bezier(.77,0,.18,1)';
function A(el, kf, opt) {
if (!el) return null;
var o = opt || {}; if (o.fill === undefined) o.fill = 'both';
if (o.duration) o.duration = Math.max(60, Math.round(o.duration * S));
if (o.delay) o.delay = Math.round(o.delay * S);
var an = el.animate(kf, o); live.push(an); return an;
}
/* ── choreography table (ms) ── */
function buildPhases() {
phases = [
[0, function () { A(glow, [{ opacity: 0 }, { opacity: 1 }], { duration: 700, easing: 'ease-out' }); }],
[100, function () { A($('.pl-logo-img'), [{ opacity: 0, transform: 'scale(.88)' }, { opacity: 1, transform: 'scale(1)' }], { duration: 750, easing: BACK }); }],
[3000, function () { A(brand, [{ opacity: 0, transform: 'translateY(12px)' }, { opacity: 1, transform: 'none' }], { duration: 550, easing: OUT }); }],
[3200, function () { A(progEl, [{ opacity: 0, transform: 'translateY(8px)' }, { opacity: 1, transform: 'none' }], { duration: 400, easing: OUT }); }],
[3600, function () { if (wrapEl) wrapEl.classList.add('idle'); }],
[4000, function () {
A(wrapEl, [{ opacity: 1, transform: 'scale(1)' }, { opacity: 0, transform: 'scale(.92)' }], { duration: 350, easing: 'ease-in' });
A(brand, [{ opacity: 1 }, { opacity: 0 }], { duration: 300, easing: 'ease-in' });
A(progEl, [{ opacity: 1 }, { opacity: 0 }], { duration: 300, easing: 'ease-in' });
A(glow, [{ opacity: 1 }, { opacity: 0 }], { duration: 300, easing: 'ease-in' });
}],
[4250, function () { A(wipe, [{ transform: 'translateY(101%)' }, { transform: 'translateY(0%)' }], { duration: 450, easing: WIPE }); }],
[4700, function () { if (pre) pre.style.background = 'transparent'; }],
[4820, function () { A(wipe, [{ transform: 'translateY(0%)' }, { transform: 'translateY(-101%)' }], { duration: 500, easing: WIPE }); }],
[5450, function () { finalize(); }]
];
}
function finalize() {
running = false;
if (pre) {
pre.classList.add('done');
pre.style.display = 'none';
}
document.body.classList.remove('locked');
if (typeof onComplete === 'function') onComplete();
}
var PCT_DUR = 3600;
function loop(now) {
if (t0 === null) t0 = now;
var t = now - t0;
while (pi < phases.length && phases[pi][0] * S <= t) { phases[pi][1](); pi++; }
if (t <= PCT_DUR * S) {
var p = Math.min(1, t / PCT_DUR), e = p * p * (3 - 2 * p);
if (pct) pct.textContent = Math.round(e * 100) + '%';
}
if (t < 5600 * S) { rafId = requestAnimationFrame(loop); }
}
function reset() {
if (rafId) cancelAnimationFrame(rafId);
live.forEach(function (a) { try { a.cancel(); } catch (e) { } });
live = []; pi = 0; t0 = null;
if (wrapEl) wrapEl.classList.remove('idle');
if (pre) {
pre.style.background = '';
pre.style.display = 'flex';
pre.classList.remove('done');
}
if (pct) pct.textContent = '0%';
document.body.classList.add('locked');
}
function start() {
if (running) return;
buildPhases();
reset();
running = true;
rafId = requestAnimationFrame(loop);
}
function reducedPath() {
document.documentElement.classList.add('rm');
if (pct) pct.textContent = '100%';
setTimeout(function () {
if (pre) {
pre.style.transition = 'opacity .6s ease';
pre.style.opacity = '0';
}
setTimeout(function () {
if (pre) pre.style.display = 'none';
document.body.classList.remove('locked');
if (typeof onComplete === 'function') onComplete();
}, 650);
}, 900);
}
if (reduced) {
reducedPath();
} else {
var gate = (document.fonts && document.fonts.ready)
? Promise.race([document.fonts.ready, new Promise(function (r) { setTimeout(r, 300); })])
: Promise.resolve();
gate.then(start);
}
}
function initPageAnimations() {
if (lenis) lenis.stop();
document.addEventListener('click', function (e) {
var a = e.target.closest('a[href^="#"]');
if (!a || a.hasAttribute('data-page')) return;
var href = a.getAttribute('href');
if (!href || href === '#' || href.length < 2) return;
e.preventDefault();
if (lenis) {
try { lenis.scrollTo(href, { offset: -70, duration: 1.2, easing: function (t) { return 1 - Math.pow(1 - t, 3); } }); }
catch (err) { var el = document.querySelector(href); if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 70, behavior: 'smooth' }); }
} else {
var el = document.querySelector(href);
if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 70, behavior: 'smooth' }); }

// Close mobile menu if open
document.body.classList.remove('sp-nav-lock');
const navPro = document.getElementById('spNavPro');
if (navPro) navPro.classList.remove('sp-nav-open');
});
if (typeof SplitType !== 'undefined') {
try { var split = new SplitType('.hero h1', { types: 'words' }); gsap.from(split.words, { yPercent: 120, rotate: 4, opacity: 0, stagger: .06, duration: 1, ease: 'power4.out', delay: .15 }); } catch (e) { }
}
gsap.from('.hero-tagline,.hero-sub,.hero-actions', { y: 24, opacity: 0, stagger: .12, duration: .9, ease: 'power3.out', delay: .3 });
gsap.to('.hero-media', { yPercent: 14, ease: 'none', scrollTrigger: { trigger: '.hero', start: 'top top', end: 'bottom top', scrub: true } });
gsap.utils.toArray('[data-count]').forEach(function (el) {
var end = +el.getAttribute('data-count'); el.textContent = '0';
gsap.to(el, { textContent: end, duration: 1.6, ease: 'power2.out', snap: { textContent: 1 }, scrollTrigger: { trigger: el, start: 'top 88%', once: true } });
});
gsap.utils.toArray('[data-reveal]').forEach(function (el) {
gsap.set(el, { y: 26, opacity: 0 });
gsap.to(el, { y: 0, opacity: 1, duration: .9, ease: 'power3.out', scrollTrigger: { trigger: el, start: 'top 86%' } });
});
// Headings
gsap.utils.toArray('.mask-reveal-heading').forEach(heading => {
const wrappers = heading.querySelectorAll('.reveal-wrapper');
wrappers.forEach(wrapper => {
const inner = wrapper.querySelector('.reveal-inner');
const mask = wrapper.querySelector('.reveal-mask');
gsap.timeline({
scrollTrigger: { trigger: heading, start: "top 88%" }
})
.set(mask, { x: '0%' })
.set(inner, { y: '110%' })
.to(mask, { x: '101%', duration: 0.8, ease: "power4.inOut" }, 0)
.to(inner, { y: '0%', duration: 0.8, ease: "power3.out" }, 0.15);
});
});
gsap.utils.toArray('.line-anim-heading').forEach(heading => {
const words = heading.querySelectorAll('.line-word');
const line = heading.querySelector('.heading-line');
gsap.set(words, { y: 30, opacity: 0 });
gsap.set(line, { scaleX: 0 });
gsap.timeline({
scrollTrigger: { trigger: heading, start: "top 85%" }
})
.to(words, { y: 0, opacity: 1, duration: 0.8, ease: "power3.out", stagger: 0.1 }, 0)
.to(line, { scaleX: 1, duration: 1.2, ease: "power4.inOut" }, "-=0.4");
});
var refreshDebounce = null;
function scheduleRefresh() { if (refreshDebounce) clearTimeout(refreshDebounce); refreshDebounce = setTimeout(function () { ScrollTrigger.refresh(); refreshDebounce = null; }, 150); }
document.querySelectorAll('img').forEach(function (img) { if (!img.complete) img.addEventListener('load', scheduleRefresh, { once: true }); });
window.addEventListener('load', function () { if (refreshDebounce) { clearTimeout(refreshDebounce); refreshDebounce = null; } ScrollTrigger.refresh(); });
if (lenis) lenis.start();
initParticles();
initTypewriter();
initValuesSerpentine();
}
var skipSplash = false; try { skipSplash = !!sessionStorage.getItem('spSplashSeen'); } catch (e) { }
if (preloader && !skipSplash) {
try { sessionStorage.setItem('spSplashSeen', '1'); } catch (e) { }
document.body.style.overflow = 'hidden';
runPreloader(function () { document.body.style.overflow = ''; initPageAnimations(); });
} else {
var plDone = document.getElementById('preloader'); if (plDone) plDone.style.display = 'none';
initPageAnimations();
}
}
