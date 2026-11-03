/* Sporting Pearls - mask-reveal.js (verbatim v15) */
/* ==== word-split + mask reveal (auto-added) ==== */
(function(){
"use strict";
var RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
function splitEl(el){
  var frag = document.createDocumentFragment();
  function pushWord(txt, isAccent, preSp){
    var words = String(txt).trim().split(/\s+/).filter(Boolean);
    words.forEach(function(w, idx){
    if(preSp && idx === 0){
        frag.appendChild(document.createTextNode(' '));
    }
      var wrapper = document.createElement('span');
      wrapper.className = 'w';
      var inner = document.createElement('span');
      inner.className = 'wi' + (isAccent ? ' it' : '');
      inner.textContent = w;
      wrapper.appendChild(inner);
      frag.appendChild(wrapper);
      if(idx < words.length - 1) frag.appendChild(document.createTextNode(' '));
    });
  }
  var temp = document.createElement('div');
  temp.innerHTML = el.innerHTML;
  var pendSp = false;
  Array.prototype.slice.call(temp.childNodes).forEach(function(n, ni, arr){
    if(n.nodeType === 3){
        if(ni > 0 && /^\s/.test(n.textContent)) pendSp = true;
        pushWord(n.textContent, false, pendSp);
        pendSp = (ni < arr.length - 1) && /\s$/.test(n.textContent);
    }
    else if(n.nodeType === 1){
      var isAccent = n.classList && n.classList.contains('it');
      pushWord(n.textContent, isAccent, pendSp);
      pendSp = false;
    }
  });
  el.textContent = '';
  el.appendChild(frag);
  var ws = Array.prototype.slice.call(el.querySelectorAll('.w'));
  ws.forEach(function(w, i){
    w.style.setProperty('--wd', (i * 70) + 'ms');
    var wi = w.firstElementChild;
    if(wi) wi.style.transitionDelay = (i * 70 + 240) + 'ms';
  });
}
document.querySelectorAll('[data-split]').forEach(splitEl);
var io = new IntersectionObserver(function(es){
  es.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
}, { threshold: .12, rootMargin: '0px 0px -8% 0px' });
document.querySelectorAll('[data-split]').forEach(function(el){
  if(RM){ el.classList.add('in'); return; }
  io.observe(el);
});
})();
