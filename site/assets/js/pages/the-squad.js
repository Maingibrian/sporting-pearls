/* Sporting Pearls - the-squad.js (v26 — real register import 2026-11-03) */
document.documentElement.classList.add('js');

/* Tactical Formation Coordinate Presets */
var FORM = {
  '4-3-3': [[50,91],[15,75],[38,78],[62,78],[85,75],[25,56],[50,59],[75,56],[20,31],[50,26],[80,31]],
  '4-4-2': [[50,91],[15,75],[38,78],[62,78],[85,75],[13,53],[38,57],[62,57],[87,53],[38,28],[62,28]],
  '4-2-3-1': [[50,91],[15,75],[38,78],[62,78],[85,75],[38,61],[62,61],[18,43],[50,41],[82,43],[50,25]],
  '3-5-2': [[50,91],[25,77],[50,80],[75,77],[10,53],[32,59],[50,55],[68,59],[90,53],[38,27],[62,27]]
};

/* Which formation coordinate belongs to which line — used to place the
   register's real positions onto the board sensibly. */
var BANDS = {
  '4-3-3':   {gk:[0], df:[1,2,3,4], mf:[5,6,7], fw:[8,9,10]},
  '4-4-2':   {gk:[0], df:[1,2,3,4], mf:[5,6,7,8], fw:[9,10]},
  '4-2-3-1': {gk:[0], df:[1,2,3,4], mf:[5,6,7,8,9], fw:[10]},
  '3-5-2':   {gk:[0], df:[1,2,3,4,5], mf:[6,7,8], fw:[9,10]}
};

var ACCENT_HEX = {
  u12:'#2e6f9e',
  u14:'#2f8f83',
  u16:'#1f567e',
  u19:'#f59d1e',
  feminin:'#f59d1e'
};

var ACCENT_VAR = {
  u12:'var(--blue)',
  u14:'var(--lagoon)',
  u16:'var(--blue-2)',
  u19:'var(--amber)',
  feminin:'var(--amber)'
};

/* Squad codes for player profile refs (U12-01 … FEM-01). Every player
   carries their unique QR ref (field 9 of the tuple); a live roster gets
   the real ref straight from /api/players/. */
var SQUAD_CODE = {
  u12:'U12', u14:'U14', u16:'U16', u19:'U19', feminin:'FEM'
};

/* Captains are named by the academy office at the start of each season.
   -1 until confirmed, which keeps the honest #capEmpty state visible. */
var CAPTAINS = {
  u12:-1, u14:-1, u16:-1, u19:-1, feminin:-1
};

var CAP_NAMES = {
  u12:'TBC', u14:'TBC', u16:'TBC', u19:'TBC', feminin:'TBC'
};

/* All official squads — real academy register, season 2026–27.
   Source: SPFA Player Administration System (Excel), imported 2026-11-03.
   Tuple: [no, first, last, pos, age, ht, foot, quote, photo, ref, facts].
   The Féminin roster is not yet published — honest empty state until
   the academy office confirms it. */
var TEAMS = {
  u12: {
    label: 'U12 Foundation Squad',
    form: '4-4-2',
    squad: [
      [12,'Suleimann','Alii','GK','11','','','','','U12-01',[['Position','Goalkeeper'],['Season','2026–27']]],
      [23,'Brian','Karisa Samuel','GK','10','','','','assets/img/squad/u16-09.jpg','U12-02',[['Position','Goalkeeper'],['Season','2026–27']]],
      [3,'Albert','Oruka','FB','12','','','','','U12-03',[['Position','Full Back'],['Season','2026–27']]],
      [13,'Baruku','Kadiri','FB','','','','','assets/img/squad/u16-06.jpg','U12-04',[['Position','Full Back'],['Season','2026–27']]],
      [14,'Dzuya','Kadiri','WB','','','','','assets/img/squad/u16-05.jpg','U12-05',[['Position','Wing Back'],['Season','2026–27']]],
      [15,'Blessing','Ngala Anderson','WB','13','','','','assets/img/squad/u16-12.jpg','U12-06',[['Position','Wing Back'],['Season','2026–27']]],
      [22,'Edwin','Namriba Dominic','WB','12','','','','','U12-07',[['Position','Wing Back'],['Season','2026–27']]],
      [24,'Moses','Levis Njeru','FB','12','','','','','U12-08',[['Position','Full Back'],['Season','2026–27']]],
      [27,'Edison','Kenga Karima','FB','','','','','','U12-09',[['Position','Full Back'],['Season','2026–27']]],
      [35,'Baraka','Dunga Martin','WB','13','','','','assets/img/squad/u16-11.jpg','U12-10',[['Position','Wing Back'],['Season','2026–27']]],
      [39,'Lewis','Kiti Chigiri','WB','13','','','','','U12-11',[['Position','Wing Back'],['Season','2026–27']]],
      [16,'Ibrahim','Hamisi Chai','CM','11','','','','assets/img/squad/u16-10.jpg','U12-12',[['Position','Central Midfield'],['Season','2026–27']]],
      [11,'Mohammed','Rama','W','','','','','','U12-13',[['Position','Winger'],['Season','2026–27']]],
      [17,'Bryhton','Mwambaru Samuel','ST','10','','','','assets/img/squad/u16-04.jpg','U12-14',[['Position','Striker'],['Season','2026–27']]],
      [25,'Reagan','Mwangala Peter','W','13','','','','','U12-15',[['Position','Winger'],['Season','2026–27']]],
      [26,'Anderson','Ndaa Garama','ST','11','','','','','U12-16',[['Position','Striker'],['Season','2026–27']]],
      [28,'Leonard','Wanje Alii','ST','13','','','','assets/img/squad/u16-23.jpg','U12-17',[['Position','Striker'],['Season','2026–27']]],
      [0,'Michael','Kalu Johnson','','','','','','','U12-18',[['Season','2026–27']]]
    ]
  },
  u14: {
    label: 'U14 Development Squad',
    form: '4-3-3',
    squad: [
      [1,'Elijah','Mwakwekwe Chai','GK','13','','','','assets/img/squad/u16-16.jpg','U14-01',[['Position','Goalkeeper'],['Season','2026–27']]],
      [3,'Amos','Justus Kuto','FB','15','','','','assets/img/squad/u16-18.jpg','U14-02',[['Position','Full Back'],['Season','2026–27']]],
      [5,'Alfred','Dzombo Onesmus','FB','14','','','','assets/img/squad/u16-13.jpg','U14-03',[['Position','Full Back'],['Season','2026–27']]],
      [12,'Arnesta','Ziggy Kambi','FB','14','','','','assets/img/squad/u16-21.jpg','U14-04',[['Position','Full Back'],['Season','2026–27']]],
      [13,'Lenious','Chikodza','FB','13','','','','','U14-05',[['Position','Full Back'],['Season','2026–27']]],
      [15,'Kelvin','Baraka Safari','CB','14','','','','','U14-06',[['Position','Centre Back'],['Season','2026–27']]],
      [19,'Isaac','Murayi Rapando','RB','13','','','','','U14-07',[['Position','Right Back'],['Season','2026–27']]],
      [21,'Ben','Chivatsi Munga','WB','14','','','','','U14-08',[['Position','Wing Back'],['Season','2026–27']]],
      [23,'Rama','Lewa Jonathan','WB','14','','','','','U14-09',[['Position','Wing Back'],['Season','2026–27']]],
      [49,'Feswal','Rama','WB','14','','','','assets/img/squad/u16-22.jpg','U14-10',[['Position','Wing Back'],['Season','2026–27']]],
      [4,'Abdul','Charo Karrisa','CM','12','','','','','U14-11',[['Position','Central Midfield'],['Season','2026–27']]],
      [25,'Nevyline','Mkare Kahindi','CM','14','','','','assets/img/squad/u19-01.jpg','U14-12',[['Position','Central Midfield'],['Season','2026–27']]],
      [8,'Phillip','Karema Kahindi','ST','12','','','','assets/img/squad/u16-15.jpg','U14-13',[['Position','Striker'],['Season','2026–27']]],
      [14,'Joshua','Karisa Samuel','ST','15','','','','assets/img/squad/u16-17.jpg','U14-14',[['Position','Striker'],['Season','2026–27']]],
      [27,'Brian','Nzovu Kifalu','LW','13','','','','assets/img/squad/u16-20.jpg','U14-15',[['Position','Left Winger'],['Season','2026–27']]],
      [43,'Riziki','Harrison Charo','W','14','','','','','U14-16',[['Position','Winger'],['Season','2026–27']]]
    ]
  },
  u16: {
    label: 'U16 Performance Squad',
    form: '3-5-2',
    squad: [
      [22,'Mwazuma','Chitibwa Kumbo','GK','16','','','','assets/img/squad/u19-29.jpg','U16-01',[['Position','Goalkeeper'],['Season','2026–27']]],
      [11,'Joel','Gharama','WB','16','','','','','U16-02',[['Position','Wing Back'],['Season','2026–27']]],
      [14,'Evans','Emmanuel','FB','16','','','','assets/img/squad/u19-05.jpg','U16-03',[['Position','Full Back'],['Season','2026–27']]],
      [15,'Michael','Rashid','WB','','','','','assets/img/squad/u19-15.jpg','U16-04',[['Position','Wing Back'],['Season','2026–27']]],
      [29,'Hamisi','Ndoro Kaingu','WB','','','','','assets/img/squad/u19-02.jpg','U16-05',[['Position','Wing Back'],['Season','2026–27']]],
      [49,'Kazungu','Harrison Charo','FB','15','','','','','U16-06',[['Position','Full Back'],['Season','2026–27']]],
      [10,'Edger','Anderson','CM','15','','','','assets/img/squad/u16-14.jpg','U16-07',[['Position','Central Midfield'],['Season','2026–27']]],
      [16,'Erick','Josphat','CM','','','','','','U16-08',[['Position','Central Midfield'],['Season','2026–27']]],
      [18,'Samuel','Chengo','CM','','','','','','U16-09',[['Position','Central Midfield'],['Season','2026–27']]],
      [7,'Frankline','Baraka','ST','15','','','','assets/img/squad/u19-03.jpg','U16-10',[['Position','Striker'],['Season','2026–27']]],
      [17,'Hassan','Juma','ST','15','','','','assets/img/squad/u19-09.jpg','U16-11',[['Position','Striker'],['Season','2026–27']]]
    ]
  },
  u19: {
    label: 'U19 Senior Squad',
    form: '3-5-2',
    squad: [
      [2,'Menza','Harrison Charo','FB','19','','','','assets/img/squad/u19-10.jpg','U19-01',[['Position','Full Back'],['Season','2026–27']]],
      [12,'Isaac','Mumo','FB','16','','','','assets/img/squad/u19-28.jpg','U19-02',[['Position','Full Back'],['Season','2026–27']]],
      [25,'Dickson','Ndawa','WB','','','','','assets/img/squad/u19-13.jpg','U19-03',[['Position','Wing Back'],['Season','2026–27']]],
      [28,'Onesmus','Mbaru','CB','','','','','assets/img/squad/u19-25.jpg','U19-04',[['Position','Centre Back'],['Season','2026–27']]],
      [6,'Alii','Thoya','CM','19','','','','assets/img/squad/u19-26.jpg','U19-05',[['Position','Central Midfield'],['Season','2026–27']]]
    ]
  },
  feminin: {
    label: 'Sporting Pearls Féminin',
    form: '4-3-3',
    squad: []   /* roster being finalised by the academy office */
  }
};
var SLOT_TXT = {
  GK:'between the posts',RB:'at right back',CB:'in central defence',LB:'at left back',
  RWB:'as right wing-back',LWB:'as left wing-back',FB:'at full back',WB:'at wing back',
  CM:'in central midfield',DM:'as the midfield shield',
  AM:'in the creative hole',CAM:'in the attacking hole',RAM:'on the right flank',LAM:'on the left flank',
  RM:'on the right wing',LM:'on the left wing',RW:'on the right wing',LW:'on the left wing',
  W:'on the wing',ST:'as the spearhead striker'
};

function groupOf(p){
  if(p==='GK') return 'GK';
  if(p==='ST'||p==='RW'||p==='LW'||p==='W') return 'FW';
  if(p==='RB'||p==='CB'||p==='LB'||p==='RWB'||p==='LWB'||p==='FB'||p==='WB') return 'DF';
  if(p==='') return 'X';
  return 'MF';
}

var playersEl = document.getElementById('players');
var pitchEl = document.getElementById('pitch');
var current = 'u12';

function pad2(n){ return (n < 10 ? '0' : '') + n; }

var slotByPlayer = {};   /* squad-index -> formation slot, for the dossier mini-pitch */

function renderTeam(key){
  current = key;
  var t = TEAMS[key];
  var tabs = document.querySelectorAll('.tab');
  for(var i=0; i<tabs.length; i++){
    var on = tabs[i].getAttribute('data-team') === key;
    tabs[i].classList.toggle('active', on);
    tabs[i].setAttribute('aria-selected', on ? 'true' : 'false');
  }

  pitchEl.style.setProperty('--acc', ACCENT_VAR[key]);
  var pm = document.getElementById('pmTeam');
  var pf = document.getElementById('pmForm');
  pm.textContent = t.label;
  pf.textContent = t.form;
  document.getElementById('pmCap').textContent = CAP_NAMES[key] || 'TBC';
  [pm, pf].forEach(function(el){
    el.classList.remove('flip');
    void el.offsetWidth;
    el.classList.add('flip');
  });

  /* Nothing published for this squad (live site, empty roster): show
     the honest "being finalised" panel — never a fabricated XI. */
  if(!t.squad.length){
    playersEl.innerHTML = emptyPitchHTML(key);
    slotByPlayer = {};
    renderBench([]);
    return;
  }

  var formKey = FORM[t.form] ? t.form : '4-3-3';   /* dashboard may set any formation */
  var slots = FORM[formKey];
  var bands = BANDS[formKey] || BANDS['4-3-3'];

  /* Group the register by position line, then fill the formation slots:
     keepers in goal, defenders in defence, and so on. Overflowing players
     fill any remaining line gaps (never the keeper's slot); everyone else
     moves to the bench strip — no registered player disappears. */
  var q = {GK:[], DF:[], MF:[], FW:[], X:[]};
  for(var j=0; j<t.squad.length; j++) q[groupOf(t.squad[j][3])].push(j);

  var placed = {};
  ['gk','df','mf','fw'].forEach(function(b){
    var g = b.toUpperCase();
    bands[b].forEach(function(si){
      var j = q[g].shift();
      if(j !== undefined) placed[si] = j;
    });
  });
  var leftovers = q.DF.concat(q.MF, q.FW);
  bands.df.concat(bands.mf, bands.fw).forEach(function(si){
    if(placed[si] === undefined && leftovers.length) placed[si] = leftovers.shift();
  });

  slotByPlayer = {};
  var onPitch = {};
  Object.keys(placed).forEach(function(si){ slotByPlayer[placed[si]] = +si; onPitch[placed[si]] = true; });

  var html = '';
  Object.keys(placed).map(Number).sort(function(a,b){ return a-b; }).forEach(function(si){
    var j = placed[si], p = t.squad[j], xy = slots[si];
    var cls = 'player';
    if(p[3] === 'GK') cls += ' gk';
    if(j === CAPTAINS[key]) cls += ' cap';
    var delay = (0.12 + si * 0.06) + 's';
    html += '<button class="' + cls + '" style="left:' + xy[0] + '%;top:' + xy[1] + '%;--d:' + delay + '" data-i="' + j + '" aria-label="' + p[1] + ' ' + p[2] + '">'
      + '<span class="p-num">' + (p[0] ? pad2(p[0]) : '·') + '</span>'
      + '<span class="p-name">' + p[1] + '</span></button>';
  });
  playersEl.innerHTML = html;

  var bench = [];
  for(var b=0; b<t.squad.length; b++) if(!onPitch[b]) bench.push(b);
  renderBench(bench);
}

/* Bench strip: every registered player not on the drawn XI stays visible
 * and clickable — the full register is always on the page. */
function renderBench(bench){
  var host = document.getElementById('bench');
  if(!host) return;
  if(!bench.length){ host.hidden = true; host.innerHTML = ''; return; }
  var t = TEAMS[current];
  var html = '<span class="bench-tag">Also in the squad <b>' + bench.length + '</b></span><div class="bench-row" role="list">';
  bench.forEach(function(j){
    var p = t.squad[j];
    html += '<button class="bench-p" data-i="' + j + '" role="listitem" aria-label="' + p[1] + ' ' + p[2] + '">'
      + '<b>' + (p[0] ? pad2(p[0]) : '·') + '</b>'
      + '<span>' + p[1] + ' ' + p[2] + '</span>'
      + (p[3] ? '<i>' + p[3] + '</i>' : '')
      + '</button>';
  });
  html += '</div>';
  host.hidden = false;
  host.innerHTML = html;
}

/* Honest panel shown inside the pitch when a squad has no published
 * players (or the live backend was never reachable). Mirrors the
 * homepage fixtures "Coming Soon" pattern. */
function emptyPitchHTML(key){
  var t = TEAMS[key];
  return '<div class="pitch-empty" role="status">'
    + '<span class="pe-tag">' + (t ? t.label : 'This squad') + ' · Season ahead</span>'
    + '<h3>Squad list being finalised</h3>'
    + '<p>Player profiles appear here once they are confirmed and published by the academy office.</p>'
    + '<a class="pe-cta" href="form-02-trial-application.html">Ask about a trial <span class="ar">→</span></a>'
    + '</div>';
}

/* Captains section: rendered from the same source as the pitch — the
 * bundled showcase data in demo mode, the published roster on a live
 * site. No fabricated children are ever shown on a live deployment. */
function renderCaptains(){
  var host = document.getElementById('capList');
  if(!host) return;
  var cards = '';
  var idx = 0;
  var order = ['u12','u14','u16','u19','feminin'];
  for(var o=0; o<order.length; o++){
    var key = order[o];
    var t = TEAMS[key];
    var ci = CAPTAINS[key];
    if(!t || typeof ci !== 'number' || ci < 0 || !t.squad[ci]) continue;
    var p = t.squad[ci];
    idx++;
    var accent = ACCENT_HEX[key] || '#f59d1e';
    var photo = p[8]
      ? '<img src="' + p[8] + '" alt="" loading="lazy">'
      : '<span class="cap-mono">' + ((p[1]||'').charAt(0) + (p[2]||'').charAt(0)).toUpperCase() + '</span>';
    var pos = p[3] || '';
    var stats = '<div class="cap-stats">'
      + (p[0] ? '<div><b>#' + p[0] + '</b><span>Shirt</span></div>' : '')
      + (pos ? '<div><b>' + pos + '</b><span>Position</span></div>' : '')
      + (p[4] ? '<div><b>' + p[4] + '</b><span>Age</span></div>' : '')
      + '</div>';
    cards += '<article class="cap-row' + (idx % 2 === 0 ? ' rev' : '') + '" style="--tc:' + accent + '" data-reveal="' + (idx % 2 === 0 ? 'right' : 'left') + '">'
      + '<div class="cap-visual">'
      + (p[0] ? '<span class="cap-num" aria-hidden="true">' + p[0] + '</span>' : '')
      + '<div class="cap-frame" aria-hidden="true"></div>'
      + '<div class="cap-photo">' + photo + '</div>'
      + '<div class="armband" aria-hidden="true"><span class="ab-c">C</span><span class="ab-strap"></span></div>'
      + '<span class="cap-cap">' + t.label + '</span>'
      + '</div>'
      + '<div class="cap-body">'
      + '<span class="cap-idx" aria-hidden="true">' + (idx < 10 ? '0' + idx : idx) + '</span>'
      + '<div class="cap-tags"><span class="cap-team">' + t.label + '</span></div>'
      + '<h3><span class="first">' + p[1] + '</span>' + p[2] + '</h3>'
      + (p[7] ? '<p class="cap-quote">' + p[7] + '</p>' : '')
      + stats
      + '</div></article>';
  }
  if(cards){
    host.innerHTML = cards;
    var fresh = host.querySelectorAll('[data-reveal]');
    for(var n=0; n<fresh.length; n++){
      if(typeof io !== 'undefined' && io && io.observe){ io.observe(fresh[n]); }
      else { fresh[n].classList.add('in'); }
    }
  }
  /* no captains published yet -> the honest #capEmpty state stays */
}

var allTabs = document.querySelectorAll('.tab');
for(var ti=0; ti<allTabs.length; ti++){
  allTabs[ti].addEventListener('click', function(){
    renderTeam(this.getAttribute('data-team'));
  });
}

playersEl.addEventListener('click', function(e){
  var el = e.target.closest('.player');
  if(el) openModal(parseInt(el.getAttribute('data-i'), 10));
});

var benchEl = document.getElementById('bench');
if(benchEl){
  benchEl.addEventListener('click', function(e){
    var el = e.target.closest('.bench-p');
    if(el) openModal(parseInt(el.getAttribute('data-i'), 10));
  });
}

var lastFocus = null;
function openModal(i){
  var t = TEAMS[current];
  var p = t.squad[i];
  var si = slotByPlayer[i];
  var slots = FORM[FORM[t.form] ? t.form : '4-3-3'];
  var xy = (si != null && slots[si]) ? slots[si] : [50,50];
  var hex = ACCENT_HEX[current];
  lastFocus = document.activeElement;

  document.getElementById('mVisual').style.setProperty('--acc', ACCENT_VAR[current]);
  document.getElementById('mWater').textContent = p[0] ? pad2(p[0]) : '··';
  document.getElementById('mBadge').textContent = t.label;
  document.getElementById('mRole').textContent = (p[3] ? p[3] + ' · ' : '') + t.label;
  document.getElementById('mName').innerHTML = '<span class="first">' + p[1] + '</span>' + p[2];
  document.getElementById('mNum').textContent = p[0] ? pad2(p[0]) : '—';
  document.getElementById('mAge').textContent = (p[4] !== '' && p[4] != null) ? p[4] : '—';
  document.getElementById('mPos').textContent = p[3] || '—';
  document.getElementById('mFoot').innerHTML = p[6] ? p[6] + '<em>.</em>' : '—';
  var mQuote = document.getElementById('mQuote');
  if(p[7]){ mQuote.textContent = p[7]; mQuote.style.display = ''; }
  else { mQuote.style.display = 'none'; }

  /* Factual dossier chips (real register fields) — never fabricated
     attribute ratings. Field 10 carries [label, value] pairs. */
  var attrsHtml = '';
  var facts = p[10] || [];
  for(var a=0; a<facts.length; a++){
    attrsHtml += '<span class="attr"><strong>' + facts[a][0] + '</strong>' + facts[a][1] + '</span>';
  }
  var mAttrs = document.getElementById('mAttrs');
  mAttrs.innerHTML = attrsHtml;
  mAttrs.style.display = attrsHtml ? '' : 'none';

  var dot = document.getElementById('mDot');
  dot.setAttribute('cx', xy[0]);
  dot.setAttribute('cy', xy[1]);
  dot.setAttribute('fill', hex);
  document.getElementById('mSlot').textContent = (si != null)
    ? (SLOT_TXT[p[3]] || 'in the XI')
    : 'in the extended squad';
  document.getElementById('mFormTxt').textContent = t.form;

  var photoBox = document.getElementById('mPhotoBox');
  var photoImg = document.getElementById('mPhotoImg');
  var jerseyEl = document.getElementById('mJersey');

  function showJersey(){
    photoBox.style.display = 'none';
    jerseyEl.style.display = 'block';
    var jerseyHtml = '<svg viewBox="0 0 120 120">'
      + '<path d="M38 14 L20 26 L8 50 L24 58 L30 46 L30 110 L90 110 L90 46 L96 58 L112 50 L100 26 L82 14 C76 24 68 28 60 28 C52 28 44 24 38 14 Z" fill="#f3efe7" stroke="#14284b" stroke-width="2.5"/>'
      + '<path d="M38 14 C44 24 52 28 60 28 C68 28 76 24 82 14" fill="none" stroke="' + hex + '" stroke-width="4"/>'
      + '<text x="60" y="82" text-anchor="middle" font-family="Fraunces, serif" font-weight="700" font-size="42" fill="#14284b">' + (p[0] ? pad2(p[0]) : '–') + '</text>'
      + '</svg>';
    jerseyEl.classList.remove('jersey');
    void jerseyEl.offsetWidth;
    jerseyEl.classList.add('jersey');
    jerseyEl.innerHTML = jerseyHtml;
  }
  photoImg.onerror = function(){ showJersey(); };
  if(p[8]){
    photoImg.src = p[8];
    photoImg.alt = p[1] + ' ' + p[2];
    photoBox.style.display = 'block';
    jerseyEl.style.display = 'none';
  } else {
    showJersey();
  }

  /* Unique per-player QR → public profile (player.html?ref=…).
     Live roster: the ref comes from the API (p[9]). Demo mode: derived
     from the squad code + shirt order, matching player_seed.json. */
  var qrBox = document.getElementById('mQr');
  var qrLink = document.getElementById('mQrLink');
  if(qrBox && qrLink){
    var pref = p[9] || (SQUAD_CODE[current] ? SQUAD_CODE[current] + '-' + pad2(i + 1) : '');
    var qrOk = false;
    if(pref && window.qrcode){
      try{
        var profileUrl = new URL('player.html?ref=' + encodeURIComponent(pref), window.location.href).href;
        var qc = window.qrcode(0, 'M');
        qc.addData(profileUrl);
        qc.make();
        qrBox.innerHTML = qc.createSvgTag({cellSize:4, margin:0});
        qrLink.href = profileUrl;
        qrLink.setAttribute('aria-label', 'Open ' + p[1] + ' ' + p[2] + "'s public profile (QR link)");
        qrOk = true;
      }catch(e){ /* QR unavailable — hide the card, never a dead link */ }
    }
    if(!qrOk){
      qrBox.innerHTML = '';
      qrLink.style.display = 'none';
      qrLink.removeAttribute('href');
    } else {
      qrLink.style.display = '';
    }
  }

  document.body.classList.add('modal-open');
  document.getElementById('pitchHint').classList.add('gone');
  setTimeout(function(){ document.getElementById('modalClose').focus(); }, 120);
}

function closeModal(){
  document.body.classList.remove('modal-open');
  if(lastFocus) lastFocus.focus();
}

document.getElementById('modalClose').addEventListener('click', closeModal);
document.getElementById('modalBackdrop').addEventListener('click', closeModal);

document.addEventListener('keydown', function(e){
  if(e.key === 'Escape'){
    if(document.body.classList.contains('modal-open')) closeModal();
    else if(document.body.classList.contains('menu-open')) document.body.classList.remove('menu-open');
  }
});

/* Scroll Chrome Interaction */
var prog = document.getElementById('progress');
var heroBg = document.getElementById('heroBg');
var ticking = false;

window.addEventListener('scroll', function(){
  if(!ticking){
    window.requestAnimationFrame(function(){
      var h = document.documentElement;
      var pct = window.scrollY / (h.scrollHeight - window.innerHeight) * 100;
      prog.style.width = pct + '%';
      if(heroBg) heroBg.style.transform = 'translateY(' + (window.scrollY * 0.22) + 'px)';
      ticking = false;
    });
    ticking = true;
  }
}, {passive:true});

/* Intersection Observers */
var io = new IntersectionObserver(function(entries){
  entries.forEach(function(e){
    if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); }
  });
}, {threshold:0, rootMargin:'0px 0px -40px 0px'});
document.querySelectorAll('[data-reveal],.lines-t').forEach(function(el){ io.observe(el); });

var pio = new IntersectionObserver(function(entries){
  entries.forEach(function(e){
    if(e.isIntersecting){ e.target.classList.add('drawn'); pio.unobserve(e.target); }
  });
}, {threshold:0.25});
pio.observe(pitchEl);

var cio = new IntersectionObserver(function(entries){
  entries.forEach(function(e){
    if(!e.isIntersecting) return;
    cio.unobserve(e.target);
    var el = e.target, end = parseInt(el.getAttribute('data-count'), 10), t0 = performance.now();
    function step(n){
      var k = Math.min((n - t0) / 1400, 1);
      el.textContent = Math.round(end * (1 - Math.pow(1 - k, 3)));
      if(k < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  });
}, {threshold:0.6});

document.querySelectorAll('[data-count]').forEach(function(el){
  el.setAttribute('data-count', el.textContent.trim());
  el.textContent = '0';
  cio.observe(el);
});

// Initial boot
renderTeam('u12');
renderCaptains();   /* captains re-render from live data once published */

/* Phase 7 — deep links: #team-<key> opens that squad's tab directly
   (used by the public player profile page's "View the full squad").
   Runs AFTER the initial boot render (which opens the first tab) and
   BEFORE the live-roster fetch resolves — the fetch re-renders
   `current`, so setting current here survives it. */
(function(){
  var m = window.location.hash.match(/^#team-([a-z0-9]+)$/);
  if(!m) return;
  var key = m[1];
  for(var i=0;i<allTabs.length;i++){
    if(allTabs[i].getAttribute('data-team') === key){
      renderTeam(key);
      return;
    }
  }
})();

/* ── Live roster, captains & technical team ─────────────────────────────
 * The academy dashboard is the source of truth for the six squads,
 * the captains and the technical team. DEMO MODE (no API_BASE) keeps
 * the bundled showcase squads above. On a LIVE site the bundled
 * players are never shown: if the backend is reachable we render its
 * published roster; if not, the last good payload from localStorage;
 * if never fetched, an honest "being finalised" panel — fictional
 * placeholder children are never served to visitors as real squads.
 */
(function(){
  var BASE = (window.SP_CONFIG && window.SP_CONFIG.API_BASE) || '';
  if(!BASE){ document.documentElement.dataset.rosterSource = 'fallback'; return; }

  function goHonest(){
    Object.keys(TEAMS).forEach(function(k){
      TEAMS[k].squad = [];
      CAPTAINS[k] = -1;
      CAP_NAMES[k] = 'TBC';
    });
    renderTeam(current);
    renderCaptains();
    var stat = document.getElementById('statRoster');
    if(stat){ stat.textContent = '—'; }
  }

  var url = BASE.replace(/\/$/, '') + '/api/players/';
  var ctrl = ('AbortController' in window) ? new AbortController() : null;
  var timer = setTimeout(function(){ if(ctrl) ctrl.abort(); }, 3500);

  fetch(url, {signal: ctrl ? ctrl.signal : undefined})
    .then(function(r){ if(!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function(j){
      clearTimeout(timer);
      if(!j || !j.ok || !j.squads || !j.squads.length) throw new Error('bad payload');
      applyRoster(j.squads);
      document.documentElement.dataset.rosterSource = 'live';
      try { localStorage.setItem('sp-roster-v1', JSON.stringify(j)); } catch(e){}
      renderTeam(current);
      renderCaptains();
      var stat = document.getElementById('statRoster');
      if(stat){ stat.textContent = j.count > 0 ? String(j.count) : '—'; }
    })
    .catch(function(){
      clearTimeout(timer);
      var usedCache = false;
      try {
        var c = JSON.parse(localStorage.getItem('sp-roster-v1') || 'null');
        if(c && c.ok && c.squads && c.squads.length){
          applyRoster(c.squads);
          renderTeam(current);
          renderCaptains();
          var stat = document.getElementById('statRoster');
          if(stat){ stat.textContent = c.count > 0 ? String(c.count) : '—'; }
          usedCache = true;
        }
      } catch(e){}
      if(!usedCache){ goHonest(); }
      document.documentElement.dataset.rosterSource = usedCache ? 'cache' : 'unavailable';
    });

  function applyRoster(squads){
    var seen = {};
    squads.forEach(function(s){
      if(!TEAMS[s.key]) return;                     /* only the site's six tabs */
      seen[s.key] = true;
      if(!FORM[s.form]) s.form = '4-3-3';
      TEAMS[s.key] = {
        label: s.label || TEAMS[s.key].label,
        form: s.form,
        squad: (s.players || []).map(function(p){
          return [p.no || 0, p.first || '', p.last || '', p.pos || '',
                  p.age || '', p.ht || '', p.foot || '', p.motto || '', p.photo || '',
                  p.ref || ''];
        })
      };
      CAPTAINS[s.key] = (typeof s.captain === 'number') ? s.captain : -1;
      var cap = (s.captain >= 0 && s.players && s.players[s.captain]) ? s.players[s.captain] : null;
      CAP_NAMES[s.key] = cap ? (cap.first + ' ' + cap.last) : 'TBC';
      if(s.accent){ ACCENT_HEX[s.key] = s.accent; ACCENT_VAR[s.key] = s.accent; }
    });
    /* QA-found bug fix: a squad MISSING from the payload must not keep
     * the bundled showcase data on a live site — empty it honestly. */
    Object.keys(TEAMS).forEach(function(k){
      if(!seen[k]){
        TEAMS[k].squad = [];
        CAPTAINS[k] = -1;
        CAP_NAMES[k] = 'TBC';
      }
    });
  }
})();

/* ── Technical team (admin-settable coaching staff, Phase 4) ──────────
 * /api/coaches/ serves published coaches only. Until the academy
 * publishes its technical team, the honest #staffEmpty state stays —
 * no fabricated staff profiles. Demo mode (no API_BASE) shows the
 * honest state too; the backend carries no demo coaches.
 */
(function(){
  var BASE = (window.SP_CONFIG && window.SP_CONFIG.API_BASE) || '';
  if(!BASE) return;
  var host = document.getElementById('staffList');
  if(!host) return;
  var url = BASE.replace(/\/$/, '') + '/api/coaches/';
  var ctrl = ('AbortController' in window) ? new AbortController() : null;
  var timer = setTimeout(function(){ if(ctrl) ctrl.abort(); }, 3500);

  fetch(url, {signal: ctrl ? ctrl.signal : undefined})
    .then(function(r){ if(!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
    .then(function(j){
      clearTimeout(timer);
      if(!j || !j.ok || !j.coaches || !j.coaches.length) return;  /* keep honest state */
      var cards = '';
      j.coaches.forEach(function(c){
        var initials = (c.name || '?').split(/\s+/).map(function(w){ return w.charAt(0); }).join('').slice(0,2).toUpperCase();
        var squadTag = c.squad ? '<span class="st-squad">' + c.squad + '</span>' : '';
        var photo = c.photo
          ? '<img src="' + c.photo + '" alt="" loading="lazy" data-mono="' + initials + '">'
          : '<span class="st-mono">' + initials + '</span>';
        cards += '<article class="st-card" data-reveal="up">'
          + '<div class="st-photo">' + photo + '</div>'
          + '<h3>' + c.name + '</h3>'
          + '<span class="st-role">' + c.role + '</span>'
          + squadTag
          + (c.bio ? '<p class="st-bio">' + c.bio + '</p>' : '')
          + '</article>';
      });
      host.innerHTML = cards;
      var fresh = host.querySelectorAll('[data-reveal]');
      for(var n=0; n<fresh.length; n++){
        if(typeof io !== 'undefined' && io && io.observe){ io.observe(fresh[n]); }
        else { fresh[n].classList.add('in'); }
      }
      /* monogram fallback when a coach photo fails to load (CSP-safe:
         programmatic listener, no inline handler) */
      var imgs = host.querySelectorAll('img[data-mono]');
      for(var i=0; i<imgs.length; i++){
        (function(img){
          img.addEventListener('error', function(){
            var mono = document.createElement('span');
            mono.className = 'st-mono';
            mono.textContent = img.getAttribute('data-mono') || '?';
            img.parentNode.replaceChild(mono, img);
          });
        })(imgs[i]);
      }
    })
    .catch(function(){ clearTimeout(timer); /* keep the honest state */ });
})();
