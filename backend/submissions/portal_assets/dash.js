/* Sporting Pearls — Management Portal dashboard script.
 * Externalised in Phase 5 so the CSP can drop
 * script-src 'unsafe-inline' (was an inline block in body-b.html;
 * content unchanged). Expects the #subs-json / #players-json data
 * blocks to be present in the page before this loads.
 */
(function(){
  "use strict";
  var $ = function(s){ return document.querySelector(s); };
  var $$ = function(s){ return Array.prototype.slice.call(document.querySelectorAll(s)); };

  /* ---------- data ---------- */
  var SUBS = JSON.parse(document.getElementById('subs-json').textContent);

  /* ---------- view switching ---------- */
  var TITLES = {
    overview:   ['Overview', 'Everything happening across the academy, at a glance'],
    submissions:['Submissions', 'Every form entry, in one permanent ledger'],
    players:    ['Players', 'The six squads, managed from one place'],
    fixtures:   ['Fixtures', 'What appears on the homepage fixture panel'],
    access:     ['Access & Security', 'Who gets in — and what keeps the bad out'],
    roadmap:    ['Roadmap', 'What the portal can grow into next']
  };
  function show(view){
    if(!TITLES[view]) view = 'overview';
    $$('.view').forEach(function(v){ v.classList.toggle('active', v.id === 'view-'+view); });
    $$('.nav-item').forEach(function(b){ b.classList.toggle('active', b.dataset.view === view); });
    $('#tb-title-h').textContent = TITLES[view][0];
    $('#tb-title-p').textContent = TITLES[view][1];
    history.replaceState(null, '', '#'+view);
    closeSidebar();
    window.scrollTo({top:0, behavior:'smooth'});
  }
  $$('.nav-item').forEach(function(b){
    b.addEventListener('click', function(){ show(b.dataset.view); });
  });

  /* ---------- mobile sidebar ---------- */
  function closeSidebar(){ $('#sidebar').classList.remove('open'); $('#overlay').classList.remove('show'); }
  $('#hamburger').addEventListener('click', function(){
    $('#sidebar').classList.add('open'); $('#overlay').classList.add('show');
  });
  $('#overlay').addEventListener('click', closeSidebar);

  /* ---------- submissions: filter + search ---------- */
  var chip = 'all', query = '';
  var rows = $$('#subs-body tr');
  function applyFilters(){
    var n = 0;
    rows.forEach(function(r){
      var okF = chip === 'all' || r.dataset.f.split(' ').indexOf(chip) !== -1;
      var okQ = !query || r.dataset.search.indexOf(query) !== -1;
      var on = okF && okQ;
      r.style.display = on ? '' : 'none';
      if(on) n++;
    });
    $('#show-n').textContent = n;
  }
  $$('.chip').forEach(function(c){
    c.addEventListener('click', function(){
      $$('.chip').forEach(function(x){ x.classList.remove('on'); });
      c.classList.add('on');
      chip = c.dataset.f;
      applyFilters();
    });
  });
  $('#q').addEventListener('input', function(e){ query = e.target.value.trim().toLowerCase(); applyFilters(); });

  /* ---------- players: squad chips ---------- */
  var pchip = 'all';
  var pcards = $$('#pl-grid .pl-card');
  function applyPFilter(){
    var n = 0;
    pcards.forEach(function(c){
      var on = pchip === 'all' || c.dataset.squad === pchip;
      c.style.display = on ? '' : 'none';
      if(on) n++;
    });
  }
  $$('.pchip').forEach(function(c){
    c.addEventListener('click', function(){
      $$('.pchip').forEach(function(x){ x.classList.remove('on'); });
      c.classList.add('on');
      pchip = c.dataset.pf;
      applyPFilter();
    });
  });

  /* ---------- selection / bulk bar ---------- */
  var bulk = $('#bulkbar');
  function refreshBulk(){
    var sel = $$('.row-check:checked').filter(function(c){ return c.id !== 'check-all'; });
    $('#bulk-n').textContent = sel.length;
    bulk.style.display = sel.length ? 'flex' : 'none';
    $('#check-all').checked = sel.length === rows.length;
  }
  document.addEventListener('change', function(e){
    if(e.target.classList && e.target.classList.contains('row-check')) refreshBulk();
  });
  $('#check-all').addEventListener('change', function(e){
    var on = e.target.checked;
    $$('.row-check').filter(function(c){ return c.id !== 'check-all'; })
      .forEach(function(c){ c.checked = on; });
    refreshBulk();
  });
  $('#bulk-clear').addEventListener('click', function(){
    $$('.row-check').forEach(function(c){ c.checked = false; });
    refreshBulk();
  });

  /* ---------- modal ---------- */
  var modal = $('#modal');
  function openRow(i){
    var s = SUBS[i]; if(!s) return;
    $('#m-name').textContent = s.name || 'Unnamed entry';
    $('#m-ref').textContent = s.ref + '  ·  ' + s.form_label + '  ·  received ' + s.when_full;
    var pills =
      '<span class="pill p-' + s.status + '">' + s.status_label + '</span>' +
      '<span class="pill p-' + s.email_status + '">' + s.email_label + '</span>' +
      invitePillHtml(s);
    $('#m-meta').innerHTML = pills;
    var ans = $('#m-ans'); ans.innerHTML = '';
    if (s.restricted) {
      var note = document.createElement('div');
      note.className = 'a';
      note.style.cssText = 'padding:10px 13px;background:rgba(245,157,30,.12);border-radius:8px;margin-bottom:10px;font-weight:600';
      note.textContent = 'Some answers (medical details, ID numbers) are restricted — visible to portal administrators only. Ask an administrator if you need them for your work.';
      ans.appendChild(note);
    }
    var keys = Object.keys(s.answers || {});
    if(!keys.length){
      var empty = document.createElement('div');
      empty.className = 'a';
      empty.style.cssText = 'padding:10px 13px';
      empty.textContent = 'No form answers recorded.';
      ans.appendChild(empty);
    } else {
      keys.forEach(function(k, idx){
        var v = s.answers[k];
        var val = (v === null || v === undefined || String(v).trim() === '') ? '—' : String(v);
        var q = document.createElement('div'); q.className = 'q' + (idx === keys.length-1 ? ' last-row' : '');
        q.textContent = prettyKey(k);
        var a = document.createElement('div'); a.className = 'a' + (idx === keys.length-1 ? ' last-row' : '');
        a.textContent = val;
        ans.appendChild(q); ans.appendChild(a);
      });
    }
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
    inviteOpen(s);
  }
  function closeModal(){ modal.classList.remove('open'); document.body.style.overflow = ''; }
  $('#m-close').addEventListener('click', closeModal);
  $('#modal-bg').addEventListener('click', closeModal);
  document.addEventListener('keydown', function(e){ if(e.key === 'Escape'){ closeModal(); closeSidebar(); } });
  function prettyKey(k){
    return String(k).replace(/[_-]+/g,' ').replace(/\b\w/g, function(c){ return c.toUpperCase(); }).trim();
  }
  $$('.view-row').forEach(function(b){
    b.addEventListener('click', function(){ openRow(parseInt(b.dataset.idx, 10)); });
  });

  /* ---------- guardian invitation (Parent Portal) ---------- */
  var SQ_LABEL = {FEM:'Féminin',U09:'U9',U13:'U13',U15:'U15',U17:'U17',U19:'U19'};
  $('#inv-rel').innerHTML = [['Mother','Mother'],['Father','Father'],['Guardian','Guardian'],
    ['Other','Other (aunt, uncle, sponsor…)']]
    .map(function(r){ return '<option value="'+r[0]+'">'+r[1]+'</option>'; }).join('');
  $('#inv-new-squad').innerHTML = ['FEM','U09','U13','U15','U17','U19']
    .map(function(c){ return '<option value="'+c+'">'+SQ_LABEL[c]+'</option>'; }).join('');

  var currentSub = null;
  function escAttr(s){
    return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;');
  }
  function inviteDefaults(s){
    var a = s.answers || {};
    function pick(keys){ for(var i=0;i<keys.length;i++){ var v=a[keys[i]]; if(v && String(v).trim()) return String(v).trim(); } return ''; }
    var g = pick(['parent_name','guardian_name']);
    var child = pick(['player_name','child_name']);
    if(!child && !g) child = pick(['name','fullname']);
    var hint = pick(['age_group','child_squad','squad']).toLowerCase();
    var hintCode = '';
    if(hint.indexOf('fem')>-1) hintCode='FEM';
    else if(hl9(hint)) hintCode='U09';
    else if(hint.indexOf('u13')>-1) hintCode='U13';
    else if(hint.indexOf('u15')>-1) hintCode='U15';
    else if(hint.indexOf('u17')>-1) hintCode='U17';
    else if(hint.indexOf('u19')>-1) hintCode='U19';
    function hl9(h){ return /(^|\W)u9(\W|$)/.test(h); }
    return {g:g, child:child, email:(s.email||''),
            phone:pick(['parent_phone','guardian_phone','phone']),
            age:pick(['age']), hintCode:hintCode};
  }
  function matchPlayer(name){
    var n = (name||'').trim().toLowerCase();
    if(!n) return null;
    var all = Object.keys(PLAYERS).map(function(k){ return PLAYERS[k]; });
    var hit = all.filter(function(p){ return (p.first_name+' '+p.last_name).toLowerCase() === n; })[0];
    if(!hit){ var last = n.split(' ').pop();
      hit = all.filter(function(p){ return p.last_name.toLowerCase() === last; })[0]; }
    return hit || null;
  }
  function fillChildOptions(){
    var groups = {};
    Object.keys(PLAYERS).forEach(function(id){ var p=PLAYERS[id]; (groups[p.squad]=groups[p.squad]||[]).push(p); });
    var html = '<option value="">— no child linked for now —</option>';
    ['FEM','U09','U13','U15','U17','U19'].forEach(function(code){
      var g = groups[code]; if(!g) return;
      html += '<optgroup label="'+SQ_LABEL[code]+'">' + g.map(function(p){
        var num = (p.number!==null && p.number!==undefined) ? ' #'+String(p.number).padStart(2,'0') : '';
        return '<option value="'+p.id+'">'+escAttr(p.first_name+' '+p.last_name+num)+'</option>';
      }).join('') + '</optgroup>';
    });
    html += '<option value="new">＋ New player profile from this application</option>';
    $('#inv-child').innerHTML = html;
  }
  function toggleNewFields(){
    var isNew = $('#inv-child').value === 'new';
    $('#inv-new-squad-w').style.display = isNew ? '' : 'none';
    $('#inv-new-age-w').style.display = isNew ? '' : 'none';
  }
  $('#inv-child').addEventListener('change', toggleNewFields);
  function invitePillHtml(s){
    if(s.guardian_active) return '<span class="pill p-sent">Parent active</span>';
    if(s.guardian_invited) return '<span class="pill p-arc">Guardian invited</span>';
    return '';
  }
  function inviteOpen(s){
    currentSub = s;
    var d = inviteDefaults(s);
    $('#inv-name').value = d.g;
    $('#inv-email').value = d.email;
    $('#inv-phone').value = d.phone;
    $('#inv-new-age').value = d.age;
    fillChildOptions();
    var hit = matchPlayer(d.child);
    $('#inv-child').value = hit ? String(hit.id) : (d.child ? 'new' : '');
    $('#inv-new-squad').value = d.hintCode || 'U17';
    toggleNewFields();
    $('#inv-result').innerHTML = '';
    $('#m-invite').disabled = false;
    $('#inv-note').style.display = '';
  }
  $('#m-invite').addEventListener('click', function(){
    if(!currentSub) return;
    var btn = this;
    btn.disabled = true;
    var body = {
      guardian_name: $('#inv-name').value.trim(),
      email: $('#inv-email').value.trim(),
      phone: $('#inv-phone').value.trim(),
      relation: $('#inv-rel').value,
      child_name: inviteDefaults(currentSub).child,
      player_id: $('#inv-child').value || '',
      new_squad: $('#inv-new-squad').value,
      new_age: $('#inv-new-age').value
    };
    api('/portal/submissions/' + encodeURIComponent(currentSub.ref) + '/invite/', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body)
    }).then(function(j){
      if(!j.ok){ btn.disabled = false; toast(j.error || 'Could not send the invite'); return; }
      currentSub.guardian_invited = true;
      var meta = $('#m-meta');
      meta.innerHTML = meta.innerHTML.replace(/<span class="pill p-(sent|arc)">Parent (active|invited)[^<]*<\/span>/g,'')
        + invitePillHtml(currentSub);
      var box = $('#inv-result'); box.innerHTML = '';
      var okBox = document.createElement('div'); okBox.className = 'inv-ok';
      var l1 = document.createElement('b');
      l1.textContent = j.sent ? ('Invite sent to ' + body.email)
                              : 'Invite created — email could not go out, copy the link';
      var l2 = document.createElement('div');
      l2.textContent = 'Activation link · valid until ' + j.expires
        + (j.child ? ' · child: ' + j.child : '');
      okBox.appendChild(l1); okBox.appendChild(l2);
      if(j.link){
        var inp = document.createElement('input');
        inp.className = 'inv-link'; inp.readOnly = true; inp.value = j.link;
        inp.onclick = function(){ this.select(); };
        var cp = document.createElement('button');
        cp.className = 'btn btn-ghost'; cp.textContent = 'Copy link';
        cp.addEventListener('click', function(){
          if(navigator.clipboard){ navigator.clipboard.writeText(j.link).then(function(){ toast('Link copied'); }); }
          else { inp.select(); document.execCommand('copy'); toast('Link copied'); }
        });
        okBox.appendChild(inp); okBox.appendChild(cp);
      }
      box.appendChild(okBox);
      $('#inv-note').style.display = 'none';
      toast(j.sent ? 'Guardian invited — activation email on its way'
                   : 'Invite created — copy the link to the guardian');
    });
  });

  /* ---------- toast + decorative actions ---------- */
  var toastTimer = null;
  function toast(msg){
    $('#toast-msg').textContent = msg;
    var t = $('#toast'); t.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function(){ t.classList.remove('show'); }, 3400);
  }
  document.addEventListener('click', function(e){
    var el = e.target.closest ? e.target.closest('[data-toast]') : null;
    if(el){ toast(el.getAttribute('data-toast')); }
  });

  /* ---------- live actions (real backend calls) ---------- */
  var PLAYERS = {};
  try {
    JSON.parse(document.getElementById('players-json').textContent)
      .forEach(function(p){ PLAYERS[p.id] = p; });
  } catch(e) {}

  var POSITIONS = [['GK','Goalkeeper'],['RB','Right Back'],['CB','Centre Back'],['LB','Left Back'],
    ['DM','Defensive Midfielder'],['CM','Central Midfielder'],['RM','Right Midfielder'],
    ['LM','Left Midfielder'],['AM','Attacking Midfielder'],['RAM','Right Attacking Midfielder'],
    ['CAM','Central Attacking Midfielder'],['LAM','Left Attacking Midfielder'],['RW','Right Winger'],
    ['LW','Left Winger'],['RWB','Right Wing-Back'],['LWB','Left Wing-Back'],['ST','Striker']];
  function fillPos(sel){
    sel.innerHTML = '<option value="">—</option>' +
      POSITIONS.map(function(p){ return '<option value="'+p[0]+'">'+p[1]+'</option>'; }).join('');
  }
  fillPos($('#e-pos')); fillPos($('#a-pos'));

  $('#a-squad').innerHTML = $$('.pchip').filter(function(c){ return c.dataset.pf !== 'all'; })
    .map(function(c){ return '<option value="'+c.dataset.pf+'">'+ c.textContent.replace(/[0-9]+\s*$/,'').trim() +'</option>'; })
    .join('');

  function csrfToken(){ var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? m[1] : ''; }
  function api(url, opts){
    opts = opts || {};
    opts.headers = Object.assign({'X-CSRFToken': csrfToken()}, opts.headers || {});
    opts.credentials = 'same-origin';
    return fetch(url, opts).then(function(r){
      return r.json().then(function(j){ j._status = r.status; return j; })
        .catch(function(){ return {ok:false, error:'Unexpected server response'}; });
    });
  }
  function openM(sel){ $(sel).classList.add('open'); document.body.style.overflow = 'hidden'; }
  function closeM(el){ el.classList.remove('open'); if(!$$('.modal.open').length) document.body.style.overflow = ''; }
  document.addEventListener('click', function(e){
    var c = e.target.closest ? e.target.closest('[data-close]') : null;
    if(c){ var m = c.closest('.modal'); if(m) closeM(m); }
  });
  document.addEventListener('keydown', function(e){
    if(e.key === 'Escape') $$('.modal.open').forEach(closeM);
  });

  function pillHtml(pub){
    return pub ? '<span class="pill p-sent">Live on site</span>' : '<span class="pill p-arc">Draft</span>';
  }
  function metaText(p){
    return [p.position, p.age ? p.age+' yrs' : '', p.height_m ? p.height_m+' m' : '',
      p.foot ? (p.foot==='L'?'Left':'Right')+'-footed' : ''].filter(Boolean).join(' · ') || '—';
  }
  var STAR_SVG = '<svg class="pl-star" viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M12 2l2.9 6.2 6.6.8-4.9 4.6 1.3 6.6L12 17l-5.9 3.2 1.3-6.6L2.5 9l6.6-.8L12 2z"/></svg>';

  function refreshCard(p){
    var card = document.querySelector('.pl-card[data-pid="'+p.id+'"]');
    if(!card) return;
    card.classList.toggle('draft', !p.is_published);
    var pill = card.querySelector('.pl-foot .pill');
    if(pill) pill.outerHTML = pillHtml(p.is_published);
    var h3 = card.querySelector('.pl-body h3');
    if(h3) h3.textContent = p.first_name + ' ' + p.last_name;
    var meta = card.querySelector('.pl-meta');
    if(meta) meta.textContent = metaText(p);
    var motto = card.querySelector('.pl-motto');
    if(motto) motto.textContent = p.motto ? '\u201C' + p.motto + '\u201D' : 'Motto to follow from the data form.';
    var num = card.querySelector('.pl-num');
    if(num) num.textContent = (p.number !== null && p.number !== undefined)
      ? '#' + String(p.number).padStart(2,'0') : '#—';
    var photo = card.querySelector('.pl-photo');
    var star = card.querySelector('.pl-star');
    if(p.is_captain && !star && photo) photo.insertAdjacentHTML('beforeend', STAR_SVG);
    if(!p.is_captain && star) star.remove();
    var tog = card.querySelector('[data-act="toggle"]');
    if(tog) tog.title = p.is_published ? 'Hide from the website' : 'Show on the website';
  }

  function recountPlayers(){
    var all = $$('#pl-grid .pl-card');
    $$('.pchip').forEach(function(ch){
      var code = ch.dataset.pf;
      var n = code === 'all' ? all.length
        : all.filter(function(c){ return c.dataset.squad === code; }).length;
      var cn = ch.querySelector('.cn'); if(cn) cn.textContent = n;
    });
    var badge = document.querySelector('.nav-item[data-view="players"] .nav-badge');
    if(badge) badge.textContent = all.length;
  }

  var currentPid = null;

  $('#pl-grid').addEventListener('click', function(e){
    var btn = e.target.closest('.pl-act');
    if(!btn) return;
    var card = btn.closest('.pl-card');
    var pid = parseInt(card.dataset.pid, 10);
    var p = PLAYERS[pid];
    if(!p) return;
    var act = btn.dataset.act;
    if(act === 'toggle'){
      btn.disabled = true;
      api('/portal/players/' + pid + '/toggle/', {method:'POST'}).then(function(j){
        btn.disabled = false;
        if(!j.ok){ toast(j.error || 'Could not update the player'); return; }
        p.is_published = j.published;
        refreshCard(p);
        toast(j.published ? p.first_name + ' is back on the website'
                          : p.first_name + ' hidden from the website (reversible)');
      });
    } else if(act === 'edit'){
      currentPid = pid;
      $('#e-title').textContent = 'Edit ' + p.first_name + ' ' + p.last_name;
      $('#e-sub').textContent = p.ref + '  ·  ' + p.squad + ' squad  ·  changes go live on save';
      $('#e-first').value = p.first_name; $('#e-last').value = p.last_name;
      $('#e-number').value = p.number === null ? '' : p.number;
      $('#e-pos').value = p.position || '';
      $('#e-age').value = p.age === null ? '' : p.age;
      $('#e-ht').value = p.height_m || '';
      $('#e-foot').value = p.foot || '';
      $('#e-order').value = (p.pitch_order === null || p.pitch_order === undefined) ? '' : p.pitch_order;
      $('#e-motto').value = p.motto || '';
      $('#e-cap').checked = !!p.is_captain;
      $('#e-pub').checked = !!p.is_published;
      openM('#edit-modal');
    } else if(act === 'photo'){
      currentPid = pid;
      $('#p-sub').textContent = p.first_name + ' ' + p.last_name + '  ·  ' + p.ref;
      $('#p-file').value = '';
      $('#p-name').textContent = 'Choose a photo';
      $('#p-save').disabled = true;
      openM('#photo-modal');
    } else if(act === 'delete'){
      currentPid = pid;
      $('#d-sub').textContent = p.first_name + ' ' + p.last_name + '  ·  ' + p.ref + '  —  this cannot be undone';
      openM('#del-modal');
    }
  });

  $('#e-save').addEventListener('click', function(){
    var b = $('#e-save'); b.disabled = true;
    var body = JSON.stringify({
      first_name: $('#e-first').value, last_name: $('#e-last').value,
      number: $('#e-number').value === '' ? null : $('#e-number').value,
      position: $('#e-pos').value,
      age: $('#e-age').value === '' ? null : $('#e-age').value,
      height_m: $('#e-ht').value, foot: $('#e-foot').value,
      pitch_order: $('#e-order').value === '' ? null : $('#e-order').value,
      motto: $('#e-motto').value,
      is_captain: $('#e-cap').checked, is_published: $('#e-pub').checked
    });
    api('/portal/players/' + currentPid + '/edit/',
        {method:'POST', headers:{'Content-Type':'application/json'}, body: body})
      .then(function(j){
        b.disabled = false;
        if(!j.ok){ toast(j.error || 'Could not save'); return; }
        PLAYERS[j.player.id] = j.player;
        refreshCard(j.player);
        closeM(document.getElementById('edit-modal'));
        toast('Saved — ' + j.player.first_name + "'s card is updated on the website");
      });
  });

  $('#p-drop').addEventListener('click', function(){ $('#p-file').click(); });
  $('#p-drop').addEventListener('keydown', function(e){
    if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); $('#p-file').click(); }
  });
  $('#p-file').addEventListener('change', function(e){
    var f = e.target.files[0];
    $('#p-name').textContent = f ? f.name : 'Choose a photo';
    $('#p-save').disabled = !f;
  });
  $('#p-save').addEventListener('click', function(){
    var f = $('#p-file').files[0];
    if(!f) return;
    var b = $('#p-save'); b.disabled = true;
    var fd = new FormData(); fd.append('file', f);
    api('/portal/players/' + currentPid + '/photo/', {method:'POST', body: fd})
      .then(function(j){
        b.disabled = false;
        if(!j.ok){ toast(j.error || 'Upload failed'); return; }
        PLAYERS[j.player.id] = j.player;
        var card = document.querySelector('.pl-card[data-pid="'+j.player.id+'"]');
        if(card){
          var ph = card.querySelector('.pl-photo');
          var img = ph.querySelector('img');
          var ava = ph.querySelector('.ava');
          if(!img){
            img = document.createElement('img');
            img.alt = ''; img.loading = 'lazy';
            img.addEventListener('error', function(){ img.style.display='none'; ava.style.display='grid'; });
            ph.insertBefore(img, ph.firstChild);
          }
          img.src = j.photo; img.style.display = '';
          if(ava) ava.style.display = 'none';
        }
        closeM(document.getElementById('photo-modal'));
        toast('Photo uploaded — the website card is updated');
      });
  });

  $('#d-confirm').addEventListener('click', function(){
    var b = $('#d-confirm'); b.disabled = true;
    api('/portal/players/' + currentPid + '/delete/', {method:'POST'}).then(function(j){
      b.disabled = false;
      if(!j.ok){ toast(j.error || 'Could not delete'); return; }
      var card = document.querySelector('.pl-card[data-pid="'+currentPid+'"]');
      if(card){ card.classList.add('removing'); setTimeout(function(){ card.remove(); recountPlayers(); }, 240); }
      delete PLAYERS[currentPid];
      closeM(document.getElementById('del-modal'));
      toast(j.ref + ' deleted permanently');
    });
  });

  $('#btn-add-player').addEventListener('click', function(){
    ['a-first','a-last','a-number','a-age','a-ht','a-motto'].forEach(function(id){ document.getElementById(id).value = ''; });
    $('#a-pos').value = ''; $('#a-foot').value = ''; $('#a-pub').checked = false;
    openM('#add-modal');
  });
  $('#a-save').addEventListener('click', function(){
    var b = $('#a-save'); b.disabled = true;
    var body = JSON.stringify({
      squad: $('#a-squad').value,
      first_name: $('#a-first').value, last_name: $('#a-last').value,
      number: $('#a-number').value === '' ? null : $('#a-number').value,
      position: $('#a-pos').value,
      age: $('#a-age').value === '' ? null : $('#a-age').value,
      height_m: $('#a-ht').value, foot: $('#a-foot').value, motto: $('#a-motto').value,
      is_published: $('#a-pub').checked
    });
    api('/portal/players/add/', {method:'POST', headers:{'Content-Type':'application/json'}, body: body})
      .then(function(j){
        b.disabled = false;
        if(!j.ok){ toast(j.error || 'Could not add the player'); return; }
        closeM(document.getElementById('add-modal'));
        toast(j.player.ref + ' added — refreshing the squad…');
        setTimeout(function(){ location.reload(); }, 900);
      });
  });

  /* ---------- submissions: real mark-reviewed / archive / reply ---------- */
  var curRow = null;
  document.addEventListener('click', function(e){
    var b = e.target.closest ? e.target.closest('.view-row') : null;
    if(b){ curRow = SUBS[parseInt(b.dataset.idx, 10)] || null; }
  });
  function setStatus(status){
    if(!curRow) return;
    api('/portal/submissions/' + encodeURIComponent(curRow.ref) + '/status/', {
      method:'POST',
      headers:{'Content-Type':'application/x-www-form-urlencoded'},
      body: 'status=' + status
    }).then(function(j){
      if(!j.ok){ toast(j.error || 'Could not update'); return; }
      toast(curRow.name + (status === 'archived' ? ' archived' : ' marked reviewed'));
      closeM(document.getElementById('modal'));
      setTimeout(function(){ location.reload(); }, 800);
    });
  }
  $('#m-review').addEventListener('click', function(){ setStatus('reviewed'); });
  $('#m-archive').addEventListener('click', function(){ setStatus('archived'); });
  $('#m-reply').addEventListener('click', function(e){
    if(curRow && curRow.email){
      e.currentTarget.href = 'mailto:' + curRow.email + '?subject=' +
        encodeURIComponent('Re: ' + curRow.form_label + ' — Sporting Pearls Academy');
      return;
    }
    e.preventDefault();
    toast('No email address on this entry.');
  });

  /* ---------- fixtures: real publish toggle ---------- */
  $$('.fx-toggle[data-fid]').forEach(function(t){
    t.addEventListener('click', function(){
      t.disabled = true;
      api('/portal/fixtures/' + t.dataset.fid + '/toggle/', {method:'POST'}).then(function(j){
        t.disabled = false;
        if(!j.ok){ toast(j.error || 'Could not update the fixture'); return; }
        var card = t.closest('.fx-card');
        if(card) card.classList.toggle('fx-draft', !j.published);
        t.classList.toggle('on', j.published);
        t.classList.toggle('off', !j.published);
        var lb = t.querySelector('.fx-t-label');
        if(lb) lb.textContent = j.published ? 'Published' : 'Draft';
        t.title = j.published ? 'Click to unpublish' : 'Click to publish';
        toast(j.published ? 'Published — the homepage fixture panel is updated'
                          : 'Back to draft — supporters no longer see it');
      });
    });
  });

  /* ---------- entry point ---------- */
  var initial = (location.hash || '#overview').slice(1);
  show(TITLES[initial] ? initial : 'overview');
  applyFilters();
  applyPFilter();
})();

