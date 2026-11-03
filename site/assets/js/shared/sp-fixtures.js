/* Sporting Pearls — sp-fixtures.js (Task 22: fixtures from Django admin)
   ------------------------------------------------------------------
   The Fixtures section ships showing "Coming Soon". Once the backend is
   deployed and API_BASE is set, published Fixtures added from the Django
   admin appear here automatically (Coming Soon is replaced). No backend
   or empty list → the Coming Soon panel stays.                        */
(function () {
  "use strict";
  var cfg = window.SP_CONFIG || {};
  var API = (cfg.API_BASE || "").replace(/\/+$/, "");
  var soon = document.getElementById("fixSoon");
  var list = soon && soon.closest(".match-list");
  if (!API || !soon || !list) return;

  var MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  var AWAY_BADGES = ["tb-a1", "tb-a2", "tb-a3"];

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function article(m, i) {
    var d = m.date ? new Date(m.date + "T00:00:00") : null;
    var dd = d ? ("0" + d.getDate()).slice(-2) : "--";
    var mm = d ? MONTHS[d.getMonth()] : "";
    var weAreHome = m.home_away !== "away";
    var our = m.team || "Sporting Pearls";
    var opp = m.opponent || "TBD";
    var ko = m.kickoff ? ("Kick-off " + m.kickoff) : "Kick-off TBC";
    var badgeCls = weAreHome ? "tb-home" : AWAY_BADGES[i % AWAY_BADGES.length];
    var oppBadgeCls = weAreHome ? AWAY_BADGES[i % AWAY_BADGES.length] : "tb-home";
    var stubNo = "MD·" + ("00" + (m.id != null ? m.id : i + 1)).slice(-3);
    return '<article class="match" data-reveal>' +
      '<div class="match-main">' +
      '<div class="team ' + (weAreHome ? "home" : "away") + '">' +
      '<span class="tbadge ' + badgeCls + '">SP</span>' +
      '<div class="tname"><b>' + esc(our) + '</b><span>' + (weAreHome ? "Home" : "Away") + '</span></div></div>' +
      '<div class="match-centre"><span class="comp">' + esc(m.competition || "") + '</span><span class="vs">VS</span><span class="ko">' + esc(ko) + '</span></div>' +
      '<div class="team ' + (weAreHome ? "away" : "home") + '">' +
      '<span class="tbadge ' + oppBadgeCls + '">' + esc((opp.slice(0, 2) || "?").toUpperCase()) + '</span>' +
      '<div class="tname"><b>' + esc(opp) + '</b><span>' + (weAreHome ? "Away" : "Home") + '</span></div></div>' +
      '</div>' +
      '<aside class="match-stub">' +
      '<span class="stub-date"><b>' + dd + '</b><i>' + mm + '</i></span>' +
      '<span class="stub-venue">' + esc(m.venue || "TBC") + '</span>' +
      '<span class="barcode"></span>' +
      '<span class="stub-no">' + esc(stubNo) + '</span>' +
      '</aside>' +
      '</article>';
  }

  fetch(API + "/api/fixtures/")
    .then(function (r) { return r.json(); })
    .then(function (j) {
      var fx = (j && j.fixtures) || [];
      if (!fx.length) return; /* keep Coming Soon */
      var html = fx.map(article).join("");
      list.innerHTML = html;
      if (window.gsap && window.ScrollTrigger) {
        window.gsap.utils.toArray(".match").forEach(function (el) {
          window.gsap.set(el, { y: 26, opacity: 0 });
          window.gsap.to(el, {
            y: 0, opacity: 1, duration: .9, ease: "power3.out",
            scrollTrigger: { trigger: el, start: "top 86%" }
          });
        });
        window.ScrollTrigger.refresh();
      }
    })
    .catch(function () { /* offline → Coming Soon stays */ });
})();
