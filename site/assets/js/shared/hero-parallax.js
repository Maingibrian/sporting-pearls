/* Sporting Pearls - hero-parallax.js (v1)
   Hero background scroll parallax for photo heroes — same pattern as
   leadership-governance.js / shared/scroll-parallax.js, reduced-motion safe.
   Usage: give the hero background element id="heroBg". */
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
