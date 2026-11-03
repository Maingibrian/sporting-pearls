/* Sporting Pearls — sp-results.js (Phase 7)
   ------------------------------------------------------------------
   The Results page ships showing "Coming Soon". Once the backend is
   deployed and API_BASE is set, published Results entered from the
   Django admin appear here automatically (Coming Soon is replaced).
   No backend or empty list → the Coming Soon panel stays. Every field
   is escaped; scores/outcomes come from the server, never client-side
   logic.                                                          */
(function () {
  "use strict";
  var cfg = window.SP_CONFIG || {};
  var API = (cfg.API_BASE || "").replace(/\/+$/, "");
  var soon = document.getElementById("resSoon");
  var groups = document.getElementById("resGroups");
  if (!API || !soon || !groups) return;

  var MONTHS = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"];
  var MON3 = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function matchCard(m) {
    var d = m.date ? new Date(m.date + "T00:00:00") : null;
    var dd = d ? ("0" + d.getDate()).slice(-2) : "--";
    var mm = d ? MON3[d.getMonth()] : "";
    var weAreHome = m.home_away !== "away";
    var our = m.team || "Sporting Pearls";
    var opp = m.opponent || "TBD";
    var home = weAreHome ? our : opp;
    var away = weAreHome ? opp : our;
    var homeFirst = weAreHome;
    var out = m.outcome || "D";
    var meta = [];
    if (m.competition) meta.push('<span class="res-badge">' + esc(m.competition) + "</span>");
    if (m.venue) meta.push(esc(m.venue));
    meta.push(weAreHome ? "Home" : "Away");
    var report = m.report
      ? '<p class="res-report">' + esc(m.report) + "</p>" : "";
    return (
      '<article class="res-match">' +
      '<div class="res-date"><b>' + dd + "</b><span>" + esc(mm) + "</span></div>" +
      '<div class="res-teams">' +
      '<p class="rt"><span>' + esc(homeFirst ? home : away) + '</span>' +
      '<span class="vs">vs</span>' +
      "<span>" + esc(homeFirst ? away : home) + "</span></p>" +
      '<div class="res-meta">' + meta.join("") + "</div>" +
      report +
      "</div>" +
      '<div class="res-score"><b>' +
      (homeFirst
        ? esc(m.our_score) + " – " + esc(m.their_score)
        : esc(m.their_score) + " – " + esc(m.our_score)) +
      '</b><span class="res-out res-out-' + esc(out.toLowerCase()) + '">' +
      esc(out) + "</span></div>" +
      "</article>");
  }

  function monthKey(d) { return d.getFullYear() + "-" + ("0" + (d.getMonth() + 1)).slice(-2); }

  function render(list) {
    var byMonth = {};          // key -> {label, items[]}
    var order = [];
    for (var i = 0; i < list.length; i++) {
      var m = list[i];
      var d = m.date ? new Date(m.date + "T00:00:00") : null;
      if (!d || isNaN(d.getTime())) continue;
      var k = monthKey(d);
      if (!byMonth[k]) {
        byMonth[k] = { label: MONTHS[d.getMonth()] + " " + d.getFullYear(), items: [] };
        order.push(k);
      }
      byMonth[k].items.push(m);
    }
    var html = "";
    for (var j = 0; j < order.length; j++) {
      var g = byMonth[order[j]];
      html += '<section class="res-group"><h3 class="res-month">' + esc(g.label) + "</h3>";
      for (var n = 0; n < g.items.length; n++) html += matchCard(g.items[n]);
      html += "</section>";
    }
    groups.innerHTML = html;
    groups.hidden = false;
    soon.hidden = true;
  }

  fetch(API + "/api/results/", { credentials: "omit" })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (data) {
      if (data && data.ok && data.count > 0 && Array.isArray(data.results)) {
        render(data.results);
      }
      // empty list or API trouble → the honest Coming Soon panel stays
    })
    .catch(function () { /* offline / no backend: keep Coming Soon */ });
})();
