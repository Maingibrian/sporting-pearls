/* Sporting Pearls - leadership-governance.js (v25)
   Hero background scroll parallax (same pattern as shared/scroll-parallax.js),
   reduced-motion safe. All other behaviour (reveals, data-plx cards, nav,
   count-up, marquee) is handled by site-core.js. */
(function () {
  var heroBg = document.getElementById('heroBg');
  var RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (!heroBg || RM) return;
  var tick = false;
  window.addEventListener('scroll', function () {
    if (!tick) {
      tick = true;
      window.requestAnimationFrame(function () {
        heroBg.style.transform = 'translateY(' + (window.scrollY * 0.25).toFixed(1) + 'px)';
        tick = false;
      });
    }
  }, { passive: true });
})();
