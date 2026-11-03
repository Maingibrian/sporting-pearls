/* Sporting Pearls — sp-feminin-gallery.js (rev 25)
   ------------------------------------------------------------------
   The Féminin "On the Pitch" gallery ships HIDDEN. It appears only
   when the backend serves real, published photos of the girls'
   programme:

     GET {API_BASE}/api/gallery/feminin/   { photos: [{image, alt, caption}] }

   Photos are uploaded and published from the Django admin
   (Féminin gallery photos). No API_BASE, no photos, or any error →
   the section stays hidden: no stock stand-ins for the girls' team. */
(function () {
  "use strict";
  var cfg = window.SP_CONFIG || {};
  var API = (cfg.API_BASE || "").replace(/\/+$/, "");
  var sec = document.getElementById("on-the-pitch");
  var grid = sec && sec.querySelector(".fg-grid");
  if (!API || !sec || !grid || !sec.hidden) return;

  /* The rev-24 collage rhythm: five tile shapes, cycled. */
  var LAYOUTS = ["t-hero", "t-up", "t-down", "t-wide2", "t-portrait"];

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function tile(p, i) {
    var cls = "fg-tile " + LAYOUTS[i % LAYOUTS.length];
    var cap = p.caption
      ? "<figcaption><span>" + esc(p.caption) + "</span></figcaption>"
      : "";
    return '<figure class="' + cls + '" data-reveal>' +
      '<img src="' + esc(p.image) + '" alt="' + esc(p.alt || "Féminin training") +
      '" loading="lazy" data-fb-hide="parent">' + cap + "</figure>";
  }

  fetch(API + "/api/gallery/feminin/")
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var photos = (j && j.photos) || [];
      if (!photos.length) return; /* nothing published → stays hidden */

      grid.innerHTML = photos.map(tile).join("");
      sec.hidden = false;

      /* Reveal the fresh tiles exactly like site-core reveals the rest
         of the page (its observer ran before these nodes existed). */
      var fresh = sec.querySelectorAll("[data-reveal]");
      if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        fresh.forEach(function (el) { el.classList.add("in"); });
        return;
      }
      var io = new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      }, { threshold: 0, rootMargin: "0px 0px -8% 0%" });
      fresh.forEach(function (el) { io.observe(el); });
    })
    .catch(function () { /* offline / misconfigured → stays hidden */ });
})();
