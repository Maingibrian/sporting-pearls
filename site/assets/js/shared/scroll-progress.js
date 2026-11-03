/* Sporting Pearls - scroll-progress.js (verbatim v15) */
/* ═══════ 2. SCROLL PROGRESS BAR ═══════ */
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
