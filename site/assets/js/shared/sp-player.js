/* Sporting Pearls — sp-player.js (Phase 7, updated rev 22 — real register 2026-27)
   ------------------------------------------------------------------
   Public player profile — the target of the QR codes shown on every
   squad player card. Reads ?ref=XXXX and renders the PUBLIC fields
   only (name, squad, number, position, age, motto, photo).

   LIVE SITES (API_BASE set): fetches /api/players/<ref>/ — unknown or
   unpublished refs fail closed to the honest "not available" panel,
   never a fabricated profile.

   DEMO MODE (no API_BASE): renders from the bundled showcase roster
   below — the exact dataset the-squad.js carries in demo mode
   (exported from backend/player_seed.json; regenerate both together).
   Every card QR scans to a working profile in demo mode too.        */
(function () {
  "use strict";

  /* Bundled register (demo mode only) — real academy squads,
     season 2026-27. Regenerated together with the-squad.js and
     backend/player_seed.json. */
  var DEMO_SQUADS = {
  "u12": {
    "label": "U12 Foundation Squad",
    "accent": "#2e6f9e",
    "code": "U12"
  },
  "u14": {
    "label": "U14 Development Squad",
    "accent": "#2f8f83",
    "code": "U14"
  },
  "u16": {
    "label": "U16 Performance Squad",
    "accent": "#1f567e",
    "code": "U16"
  },
  "u19": {
    "label": "U19 Senior Squad",
    "accent": "#f59d1e",
    "code": "U19"
  },
  "feminin": {
    "label": "Sporting Pearls Féminin",
    "accent": "#f59d1e",
    "code": "FEM"
  }
};

var DEMO_PROFILES = {
    'U12-01':{"no": 12, "first": "Suleimann", "last": "Alii", "pos": "GK", "age": 11, "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U12-02':{"no": 23, "first": "Brian", "last": "Karisa Samuel", "pos": "GK", "age": 10, "sq": "u12", "cap": false, "motto": "", "photo": "assets/img/squad/u16-09.jpg"},
    'U12-03':{"no": 3, "first": "Albert", "last": "Oruka", "pos": "FB", "age": 12, "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U12-04':{"no": 13, "first": "Baruku", "last": "Kadiri", "pos": "FB", "age": "", "sq": "u12", "cap": false, "motto": "", "photo": "assets/img/squad/u16-06.jpg"},
    'U12-05':{"no": 14, "first": "Dzuya", "last": "Kadiri", "pos": "WB", "age": "", "sq": "u12", "cap": false, "motto": "", "photo": "assets/img/squad/u16-05.jpg"},
    'U12-06':{"no": 15, "first": "Blessing", "last": "Ngala Anderson", "pos": "WB", "age": 13, "sq": "u12", "cap": false, "motto": "", "photo": "assets/img/squad/u16-12.jpg"},
    'U12-07':{"no": 22, "first": "Edwin", "last": "Namriba Dominic", "pos": "WB", "age": 12, "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U12-08':{"no": 24, "first": "Moses", "last": "Levis Njeru", "pos": "FB", "age": 12, "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U12-09':{"no": 27, "first": "Edison", "last": "Kenga Karima", "pos": "FB", "age": "", "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U12-10':{"no": 35, "first": "Baraka", "last": "Dunga Martin", "pos": "WB", "age": 13, "sq": "u12", "cap": false, "motto": "", "photo": "assets/img/squad/u16-11.jpg"},
    'U12-11':{"no": 39, "first": "Lewis", "last": "Kiti Chigiri", "pos": "WB", "age": 13, "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U12-12':{"no": 16, "first": "Ibrahim", "last": "Hamisi Chai", "pos": "CM", "age": 11, "sq": "u12", "cap": false, "motto": "", "photo": "assets/img/squad/u16-10.jpg"},
    'U12-13':{"no": 11, "first": "Mohammed", "last": "Rama", "pos": "W", "age": "", "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U12-14':{"no": 17, "first": "Bryhton", "last": "Mwambaru Samuel", "pos": "ST", "age": 10, "sq": "u12", "cap": false, "motto": "", "photo": "assets/img/squad/u16-04.jpg"},
    'U12-15':{"no": 25, "first": "Reagan", "last": "Mwangala Peter", "pos": "W", "age": 13, "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U12-16':{"no": 26, "first": "Anderson", "last": "Ndaa Garama", "pos": "ST", "age": 11, "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U12-17':{"no": 28, "first": "Leonard", "last": "Wanje Alii", "pos": "ST", "age": 13, "sq": "u12", "cap": false, "motto": "", "photo": "assets/img/squad/u16-23.jpg"},
    'U12-18':{"no": 0, "first": "Michael", "last": "Kalu Johnson", "pos": "", "age": "", "sq": "u12", "cap": false, "motto": "", "photo": ""},
    'U14-01':{"no": 1, "first": "Elijah", "last": "Mwakwekwe Chai", "pos": "GK", "age": 13, "sq": "u14", "cap": false, "motto": "", "photo": "assets/img/squad/u16-16.jpg"},
    'U14-02':{"no": 3, "first": "Amos", "last": "Justus Kuto", "pos": "FB", "age": 15, "sq": "u14", "cap": false, "motto": "", "photo": "assets/img/squad/u16-18.jpg"},
    'U14-03':{"no": 5, "first": "Alfred", "last": "Dzombo Onesmus", "pos": "FB", "age": 14, "sq": "u14", "cap": false, "motto": "", "photo": "assets/img/squad/u16-13.jpg"},
    'U14-04':{"no": 12, "first": "Arnesta", "last": "Ziggy Kambi", "pos": "FB", "age": 14, "sq": "u14", "cap": false, "motto": "", "photo": "assets/img/squad/u16-21.jpg"},
    'U14-05':{"no": 13, "first": "Lenious", "last": "Chikodza", "pos": "FB", "age": 13, "sq": "u14", "cap": false, "motto": "", "photo": ""},
    'U14-06':{"no": 15, "first": "Kelvin", "last": "Baraka Safari", "pos": "CB", "age": 14, "sq": "u14", "cap": false, "motto": "", "photo": ""},
    'U14-07':{"no": 19, "first": "Isaac", "last": "Murayi Rapando", "pos": "RB", "age": 13, "sq": "u14", "cap": false, "motto": "", "photo": ""},
    'U14-08':{"no": 21, "first": "Ben", "last": "Chivatsi Munga", "pos": "WB", "age": 14, "sq": "u14", "cap": false, "motto": "", "photo": ""},
    'U14-09':{"no": 23, "first": "Rama", "last": "Lewa Jonathan", "pos": "WB", "age": 14, "sq": "u14", "cap": false, "motto": "", "photo": ""},
    'U14-10':{"no": 49, "first": "Feswal", "last": "Rama", "pos": "WB", "age": 14, "sq": "u14", "cap": false, "motto": "", "photo": "assets/img/squad/u16-22.jpg"},
    'U14-11':{"no": 4, "first": "Abdul", "last": "Charo Karrisa", "pos": "CM", "age": 12, "sq": "u14", "cap": false, "motto": "", "photo": ""},
    'U14-12':{"no": 25, "first": "Nevyline", "last": "Mkare Kahindi", "pos": "CM", "age": 14, "sq": "u14", "cap": false, "motto": "", "photo": "assets/img/squad/u19-01.jpg"},
    'U14-13':{"no": 8, "first": "Phillip", "last": "Karema Kahindi", "pos": "ST", "age": 12, "sq": "u14", "cap": false, "motto": "", "photo": "assets/img/squad/u16-15.jpg"},
    'U14-14':{"no": 14, "first": "Joshua", "last": "Karisa Samuel", "pos": "ST", "age": 15, "sq": "u14", "cap": false, "motto": "", "photo": "assets/img/squad/u16-17.jpg"},
    'U14-15':{"no": 27, "first": "Brian", "last": "Nzovu Kifalu", "pos": "LW", "age": 13, "sq": "u14", "cap": false, "motto": "", "photo": "assets/img/squad/u16-20.jpg"},
    'U14-16':{"no": 43, "first": "Riziki", "last": "Harrison Charo", "pos": "W", "age": 14, "sq": "u14", "cap": false, "motto": "", "photo": ""},
    'U16-01':{"no": 22, "first": "Mwazuma", "last": "Chitibwa Kumbo", "pos": "GK", "age": 16, "sq": "u16", "cap": false, "motto": "", "photo": "assets/img/squad/u19-29.jpg"},
    'U16-02':{"no": 11, "first": "Joel", "last": "Gharama", "pos": "WB", "age": 16, "sq": "u16", "cap": false, "motto": "", "photo": ""},
    'U16-03':{"no": 14, "first": "Evans", "last": "Emmanuel", "pos": "FB", "age": 16, "sq": "u16", "cap": false, "motto": "", "photo": "assets/img/squad/u19-05.jpg"},
    'U16-04':{"no": 15, "first": "Michael", "last": "Rashid", "pos": "WB", "age": "", "sq": "u16", "cap": false, "motto": "", "photo": "assets/img/squad/u19-15.jpg"},
    'U16-05':{"no": 29, "first": "Hamisi", "last": "Ndoro Kaingu", "pos": "WB", "age": "", "sq": "u16", "cap": false, "motto": "", "photo": "assets/img/squad/u19-02.jpg"},
    'U16-06':{"no": 49, "first": "Kazungu", "last": "Harrison Charo", "pos": "FB", "age": 15, "sq": "u16", "cap": false, "motto": "", "photo": ""},
    'U16-07':{"no": 10, "first": "Edger", "last": "Anderson", "pos": "CM", "age": 15, "sq": "u16", "cap": false, "motto": "", "photo": "assets/img/squad/u16-14.jpg"},
    'U16-08':{"no": 16, "first": "Erick", "last": "Josphat", "pos": "CM", "age": "", "sq": "u16", "cap": false, "motto": "", "photo": ""},
    'U16-09':{"no": 18, "first": "Samuel", "last": "Chengo", "pos": "CM", "age": "", "sq": "u16", "cap": false, "motto": "", "photo": ""},
    'U16-10':{"no": 7, "first": "Frankline", "last": "Baraka", "pos": "ST", "age": 15, "sq": "u16", "cap": false, "motto": "", "photo": "assets/img/squad/u19-03.jpg"},
    'U16-11':{"no": 17, "first": "Hassan", "last": "Juma", "pos": "ST", "age": 15, "sq": "u16", "cap": false, "motto": "", "photo": "assets/img/squad/u19-09.jpg"},
    'U19-01':{"no": 2, "first": "Menza", "last": "Harrison Charo", "pos": "FB", "age": 19, "sq": "u19", "cap": false, "motto": "", "photo": "assets/img/squad/u19-10.jpg"},
    'U19-02':{"no": 12, "first": "Isaac", "last": "Mumo", "pos": "FB", "age": 16, "sq": "u19", "cap": false, "motto": "", "photo": "assets/img/squad/u19-28.jpg"},
    'U19-03':{"no": 25, "first": "Dickson", "last": "Ndawa", "pos": "WB", "age": "", "sq": "u19", "cap": false, "motto": "", "photo": "assets/img/squad/u19-13.jpg"},
    'U19-04':{"no": 28, "first": "Onesmus", "last": "Mbaru", "pos": "CB", "age": "", "sq": "u19", "cap": false, "motto": "", "photo": "assets/img/squad/u19-25.jpg"},
    'U19-05':{"no": 6, "first": "Alii", "last": "Thoya", "pos": "CM", "age": 19, "sq": "u19", "cap": false, "motto": "", "photo": "assets/img/squad/u19-26.jpg"}
  };
  var cfg = window.SP_CONFIG || {};
  var API = (cfg.API_BASE || "").replace(/\/+$/, "");
  var card = document.getElementById("plbCard");
  var missing = document.getElementById("plbMissing");
  var loading = document.getElementById("plbLoading");
  if (!card || !missing || !loading) return;

  var POS = { GK: "Goalkeeper", CB: "Centre Back", FB: "Full Back", WB: "Wing Back", RB: "Right Back",
    LB: "Left Back", RWB: "Right Wing Back", LWB: "Left Wing Back", CM: "Central Midfield",
    DM: "Defensive Midfield", AM: "Attacking Midfield", W: "Winger", LW: "Left Winger",
    RW: "Right Winger", ST: "Striker", DF: "Defender", MF: "Midfielder", FW: "Forward" };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function show(el) {
    loading.hidden = true;
    if (el) el.hidden = false;
  }

  function ref() {
    var m = window.location.search.match(/[?&]ref=([A-Za-z0-9_-]+)/);
    return m ? m[1] : "";
  }

  function render(p) {
    var sq = p.squad || {};

    document.getElementById("plbName").textContent =
      (p.first || "") + " " + (p.last || "");

    var dot = document.getElementById("plbDot");
    if (dot) dot.style.background = sq.accent || "#f59d1e";
    document.getElementById("plbSquad").textContent = sq.label || "Sporting Pearls";

    var img = document.getElementById("plbImg");
    var mono = document.getElementById("plbMono");
    if (p.photo) {
      img.src = p.photo;
      img.alt = "Photo of " + (p.first || "") + " " + (p.last || "");
      img.style.display = "";
      if (mono) mono.style.display = "none";
    } else {
      img.style.display = "none";
      if (mono) {
        mono.style.display = "grid";
        mono.textContent = ((p.first || "?").charAt(0) + (p.last || "?").charAt(0)).toUpperCase();
      }
    }

    var num = document.getElementById("plbNum");
    num.textContent = (p.no != null) ? ("#" + ("0" + p.no).slice(-2)) : "";

    var facts = [];
    if (p.pos) facts.push(["Position", POS[p.pos] || p.pos]);
    if (p.age != null) facts.push(["Age", p.age]);
    if (p.captain) facts.push(["Team role", "Captain"]);
    facts.push(["Profile ref", p.ref || "—"]);
    document.getElementById("plbFacts").innerHTML = facts.map(function (f) {
      return '<div class="pf"><span>' + esc(f[0]) + "</span><b>" + esc(f[1]) + "</b></div>";
    }).join("");

    var motto = document.getElementById("plbMotto");
    if (p.motto) {
      motto.hidden = false;
      motto.textContent = "\u201C" + p.motto + "\u201D";
    }

    var link = document.getElementById("plbSquadLink");
    if (link && sq.key) link.href = "the-squad.html#team-" + sq.key;

    show(card);
  }

  var r = ref();
  if (!r) { show(missing); return; }

  if (!API) {
    /* Demo mode: bundled showcase roster (same data as the squad page).
       Live deployments never reach this branch — and even here an
       unknown ref still fails closed to the honest panel. */
    var dd = DEMO_PROFILES[r.toUpperCase()] || DEMO_PROFILES[r];
    if (!dd) { show(missing); return; }
    var ss = DEMO_SQUADS[dd.sq] || {};
    render({
      ref: r.toUpperCase(),
      first: dd.first, last: dd.last, no: dd.no, pos: dd.pos,
      age: dd.age, captain: dd.cap, motto: dd.motto, photo: dd.photo || "",
      squad: { key: dd.sq, label: ss.label, accent: ss.accent }
    });
    return;
  }

  fetch(API + "/api/players/" + encodeURIComponent(r) + "/", { credentials: "omit" })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (data) {
      if (!data || !data.ok || !data.player) { show(missing); return; }
      render(data.player);
    })
    .catch(function () { show(missing); });
})();
