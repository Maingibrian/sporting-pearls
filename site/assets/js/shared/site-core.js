/* Sporting Pearls - site-core.js (verbatim v15) */
(function(){
"use strict";
var $=function(s,c){return (c||document).querySelector(s)};
var $$=function(s,c){return Array.prototype.slice.call((c||document).querySelectorAll(s))};
var RM=matchMedia('(prefers-reduced-motion: reduce)').matches;
var FINE=matchMedia('(pointer: fine)').matches;
var EASE='cubic-bezier(.16,1,.3,1)';

/* ---------- no loader: mark loaded immediately ---------- */
document.body.classList.add('loaded');

/* ---------- split headings ---------- */
$$('[data-split]').forEach(function(el){
var frag=document.createDocumentFragment();
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
if(idx < words.length - 1){
frag.appendChild(document.createTextNode(' '));
}
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
$$('.wi', el).forEach(function(wi, i){ wi.style.transitionDelay = (i * 70 + 240) + 'ms'; });
$$('.w', el).forEach(function(w, i){ w.style.setProperty('--wd', (i * 70) + 'ms'); });
});

/* ---------- prep stroke-draw paths ---------- */
$$('[data-draw]').forEach(function(p){
try{var L=p.getTotalLength();p.style.strokeDasharray=L;p.style.strokeDashoffset=L;}catch(e){}
});

/* ---------- reveal observer ---------- */
var io=new IntersectionObserver(function(es){
es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});
},{threshold:0,rootMargin:'0px 0px -8% 0px'});
$$('[data-reveal]').forEach(function(el){
if(RM){el.classList.add('in');return;}
io.observe(el);
});
$$('[data-split]').forEach(function(el){
if(el.classList.contains('hero-h'))return;
if(RM){el.classList.add('in');return;}
io.observe(el);
});

/* ---------- draw-on-scroll observer ---------- */
var dio=new IntersectionObserver(function(es){
es.forEach(function(e){
if(!e.isIntersecting)return;
var p=e.target,d=+(p.getAttribute('data-d')||0);
p.style.transition='stroke-dashoffset 1.15s '+EASE+' '+(200+d*180)+'ms';
p.style.strokeDashoffset='0';
dio.unobserve(p);
});
},{threshold:.4});
$$('[data-draw]').forEach(function(p){
if(RM){p.style.strokeDashoffset='0';return;}
dio.observe(p);
});

/* ---------- count-up numbers ---------- */
function animateCount(el){
var target=parseFloat(el.getAttribute('data-count'))||0,dec=+(el.getAttribute('data-dec')||0);
var suf=el.getAttribute('data-suf')||'',pre=el.getAttribute('data-pre')||'';
var dur=+(el.getAttribute('data-dur')||1700),t0=performance.now();
(function step(t){
var p=Math.min(1,(t-t0)/dur),e=1-Math.pow(1-p,3);
var val = target*e;
if(dec === 0) val = Math.round(val);
else val = val.toFixed(dec);
el.textContent=pre+val+suf;
if(p<1)requestAnimationFrame(step);
else el.textContent=pre+(dec===0?target:target.toFixed(dec))+suf;
})(t0);
}
var cio=new IntersectionObserver(function(es){
es.forEach(function(e){if(!e.isIntersecting)return;cio.unobserve(e.target);animateCount(e.target);});
},{threshold:.5});
$$('[data-count]').forEach(function(el){
if(RM){el.textContent=(el.getAttribute('data-pre')||'')+el.getAttribute('data-count')+(el.getAttribute('data-suf')||'');return;}
cio.observe(el);
});

/* ---------- ecosystem orbital diagram ---------- */
var orbit=$('#ecoOrbit');
if(orbit&&!$('.eco-fallback',orbit)){
var NS='http://www.w3.org/2000/svg',C=350,RX=255,RY=213;
var NODES=[
{a:-90,i:'ball',t:'Football',s:'Player pathways'},
{a:-30,i:'cap',t:'Education',s:'Academics & life skills'},
{a:30,i:'shield',t:'Character',s:'Discipline & values'},
{a:90,i:'users',t:'Girls',s:'Féminin programme'},
{a:150,i:'link',t:'Leadership',s:'Mentorship'},
{a:210,i:'globe',t:'Coaching',s:'Technical development'}
];
var svg=$('.eco-lines',orbit);
if(!svg){
var fb=document.createElement('div');fb.className='eco-fallback';
NODES.forEach(function(n){
fb.innerHTML+='<article class="eco-node"><span class="eco-ic"><svg class="ic"><use href="#i-'+n.i+'"/></svg></span><div><h4>'+n.t+'</h4><p>'+n.s+'</p></div></article>';
});
orbit.appendChild(fb);
} else {
NODES.forEach(function(n,idx){
var rad=n.a*Math.PI/180;
var x=C+RX*Math.cos(rad),y=C+RY*Math.sin(rad);
var mx=(C+x)/2,my=(C+y)/2;
var dx=x-C,dy=y-C,ln=Math.hypot(dx,dy)||1,nx=-dy/ln,ny=dx/ln;
var bow=(idx%2?1:-1)*30;
var d='M'+C+','+C+' Q'+(mx+nx*bow).toFixed(1)+','+(my+ny*bow).toFixed(1)+' '+x.toFixed(1)+','+y.toFixed(1);
var p=document.createElementNS(NS,'path');
p.setAttribute('d',d);p.setAttribute('class','o-path');svg.appendChild(p);
if(!RM){
var dot=document.createElementNS(NS,'circle');
dot.setAttribute('r','4.5');dot.setAttribute('class','o-dot');
var am=document.createElementNS(NS,'animateMotion');
am.setAttribute('dur',(5.5+idx*.8)+'s');
am.setAttribute('begin',(-idx*1.4)+'s');
am.setAttribute('repeatCount','indefinite');
am.setAttribute('path',d);
dot.appendChild(am);svg.appendChild(dot);
}
var w=document.createElement('div');
w.className='eco-pos';
w.style.left=(x/7).toFixed(2)+'%';w.style.top=(y/7).toFixed(2)+'%';
w.style.transitionDelay=(150+idx*90)+'ms';
w.innerHTML='<article class="eco-node"><span class="eco-ic"><svg class="ic"><use href="#i-'+n.i+'"/></svg></span><h4>'+n.t+'</h4><p>'+n.s+'</p></article>';
orbit.appendChild(w);
var card=w.firstElementChild;
if(card){
card.addEventListener('pointerenter',function(){p.classList.add('lit')});
card.addEventListener('pointerleave',function(){p.classList.remove('lit')});
}
});
}
}


/* ---------- scroll handlers ---------- */
var prog=$('#progress'),scTick=false;
function onScroll(){
scTick=false;
var y=window.scrollY,h=document.documentElement.scrollHeight-window.innerHeight;
if(prog)prog.style.transform='scaleX('+(h>0?(y/h).toFixed(4):0)+')';
}
addEventListener('scroll',function(){if(!scTick){scTick=true;requestAnimationFrame(onScroll);}},{passive:true});
onScroll();

/* ---------- parallax ---------- */
var plx=$$('[data-plx]').map(function(el){return{el:el,sp:parseFloat(el.getAttribute('data-plx'))||0}});
if(plx.length&&!RM){
var tick=false;
function run(){
tick=false;var vh=innerHeight;
plx.forEach(function(o){
var r=o.el.getBoundingClientRect();
if(r.bottom<-200||r.top>vh+200)return;
var c=r.top+r.height/2-vh/2;
o.el.style.transform='translate3d(0,'+(-c*o.sp).toFixed(1)+'px,0)';
});
}
addEventListener('scroll',function(){if(!tick){tick=true;requestAnimationFrame(run);}},{passive:true});
run();
}

/* ---------- form ---------- */
var form=$('#partnerForm'),ok=$('#formSuccess'), statusEl = $('#form-status');
if(form){
$$('.check',form).forEach(function(chk){
var inp=$('input',chk);
if(inp)inp.addEventListener('change',function(){chk.classList.toggle('on',inp.checked)});
});
function announce(msg){
if(statusEl) statusEl.textContent = msg;
}
form.addEventListener('submit',function(e){
e.preventDefault();
if(form.classList.contains('busy'))return;
$$('.field.err, .agree.err', form).forEach(function(f){ f.classList.remove('err'); });
$$('[aria-invalid]', form).forEach(function(f){ f.removeAttribute('aria-invalid'); });
var req=$$('[required]',form).filter(function(f){
if(f.type==='checkbox')return !f.checked;
return !String(f.value).trim();
});
var emailField = $('#f-contactEmail');
var emailInvalid = emailField && emailField.value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailField.value);
if(req.length || emailInvalid){
var errorCount = req.length + (emailInvalid ? 1 : 0);
announce(errorCount + ' field' + (errorCount === 1 ? '' : 's') + ' need attention.');
req.forEach(function(f){
var w=f.closest('.field')||f.closest('.agree');
if(w){w.classList.add('err');}
if(f.setAttribute) f.setAttribute('aria-invalid','true');
});
if(emailInvalid){
var w = emailField.closest('.field');
if(w) w.classList.add('err');
emailField.setAttribute('aria-invalid','true');
if(req.indexOf(emailField) === -1) req.push(emailField);
}
if(req[0] && req[0].focus) req[0].focus();
return;
}
form.classList.add('busy');
announce('Submitting your enquiry...');
var btn=$('.btn-submit',form);if(btn)btn.classList.add('busy');
setTimeout(function(){
form.classList.remove('busy');if(btn)btn.classList.remove('busy');
if(ok){
ok.classList.add('on');
ok.scrollIntoView({behavior:RM?'auto':'smooth',block:'nearest'});
ok.setAttribute('tabindex', '-1');
ok.focus();
announce('Enquiry submitted successfully.');
}
},1300);
});
var reset=$('#okReset');
if(reset)reset.addEventListener('click',function(){
if(ok)ok.classList.remove('on');
form.reset();
$$('.check.on',form).forEach(function(c){c.classList.remove('on')});
var first = form.querySelector('input, select, textarea');
if(first) first.focus();
});
}

/* ═══════════════════════════════════════════
NAVIGATION (SPORTING PEARLS PRO - ORIGINAL JS)
═══════════════════════════════════════════ */
const nav = document.getElementById("spNavPro");
if (nav) {
const $nav = (s, c = nav) => c.querySelector(s);
const $$nav = (s, c = nav) => [...c.querySelectorAll(s)];
const fallbackImg = "feminin-hero.jpg";
  $$(".sp-nav-preview-img").forEach(im=>im.addEventListener("error",()=>{if(!im.src.endsWith("feminin-hero.jpg"))im.src=fallbackImg;}));
const isFinePointer = matchMedia("(hover: hover) and (pointer: fine)").matches;
const desktopQuery = matchMedia("(min-width: 1100px)");
const triggers = $$nav(".sp-nav-trigger");
const dropdowns = $$nav(".sp-nav-dropdown");
const burger = $nav("#spNavBurger");
const mobile = $nav("#spNavMobile");
const mobileBody = $nav("#spNavMobileBody");
let closeTimer;
const closeDropdowns = () => {
triggers.forEach(t => { t.classList.remove("active"); t.setAttribute("aria-expanded", "false"); });
dropdowns.forEach(d => { d.classList.remove("active"); d.setAttribute("aria-hidden", "true"); });
};
const setPreview = (dropdown, item, instant) => {
const media = $nav(".sp-nav-preview-img", dropdown);
const caption = $nav(".sp-nav-preview-caption", dropdown);
if (!media || !caption || !item) return;
const { img: src = fallbackImg, title = "", copy = "", kicker = "Preview" } = item.dataset;
if (media.dataset.current === src && caption.dataset.current === title) return;
const applyCaption = () => {
$nav(".sp-nav-preview-kicker", caption).textContent = kicker;
$nav(".sp-nav-preview-title", caption).textContent = title;
$nav(".sp-nav-preview-copy", caption).textContent = copy;
caption.dataset.current = title;
};
let resolved = false;
const swap = (finalSrc) => {
if (resolved) return; resolved = true;
media.src = finalSrc; media.dataset.current = finalSrc; applyCaption();
requestAnimationFrame(() => { media.classList.remove("is-switching"); caption.classList.remove("is-switching"); });
};
if (instant) return swap(src);
media.classList.add("is-switching"); caption.classList.add("is-switching");
const loaderImg = new Image();
loaderImg.onload = () => swap(loaderImg.src);
loaderImg.onerror = () => swap(fallbackImg);
loaderImg.src = src;
setTimeout(() => swap(src), 1200);
};
const openDropdown = (id) => {
clearTimeout(closeTimer); closeDropdowns();
const trigger = $nav(`.sp-nav-trigger[data-menu="${id}"]`);
const dropdown = $nav(`.sp-nav-dropdown[data-menu="${id}"]`);
if (!trigger || !dropdown) return;
trigger.classList.add("active"); trigger.setAttribute("aria-expanded", "true");
dropdown.classList.add("active"); dropdown.setAttribute("aria-hidden", "false");
setPreview(dropdown, $nav(".sp-nav-item.is-active", dropdown) || $nav(".sp-nav-item", dropdown), true);
};
triggers.forEach(trigger => {
const id = trigger.dataset.menu;
const open = () => openDropdown(id);
const scheduleClose = () => { closeTimer = setTimeout(closeDropdowns, 140); };
if (isFinePointer) {
trigger.addEventListener("mouseenter", open);
trigger.addEventListener("mouseleave", scheduleClose);
}
trigger.addEventListener("click", e => {
if (!isFinePointer) { e.preventDefault(); trigger.classList.contains("active") ? closeDropdowns() : open(); }
});
trigger.addEventListener("focus", open);
});
dropdowns.forEach(dropdown => {
dropdown.addEventListener("mouseenter", () => clearTimeout(closeTimer));
dropdown.addEventListener("mouseleave", () => { closeTimer = setTimeout(closeDropdowns, 140); });
const activateItem = (e) => {
const item = e.target.closest(".sp-nav-item");
if (!item) return;
$$nav(".sp-nav-item", dropdown).forEach(l => l.classList.toggle("is-active", l === item));
setPreview(dropdown, item);
};
dropdown.addEventListener("mouseover", activateItem);
dropdown.addEventListener("focusin", activateItem);
});
if (mobileBody) {
const directLinks = $$nav(".sp-nav-desktop > .sp-nav-link");
let html = "";
if (directLinks.length) {
html += `<div class="sp-nav-mobile-direct">${
directLinks.map(link => `<a class="sp-nav-mobile-direct-link" href="${link.href}">
<span>${link.dataset.label || link.textContent.trim()}</span>
<span class="sp-nav-mobile-arrow"><svg><use href="#icon-arrow"/></svg></span>
</a>`).join('')
}</div>`;
}
dropdowns.forEach(dropdown => {
const trigger = $nav(`.sp-nav-trigger[data-menu="${dropdown.dataset.menu}"]`);
const title = trigger?.dataset.label || dropdown.dataset.menu;
html += `
<div class="sp-nav-mobile-group">
<button type="button" class="sp-nav-mobile-trigger" aria-expanded="false">
<span>${title}</span><span><svg><use href="#icon-chevron"/></svg></span>
</button>
<div class="sp-nav-mobile-panel">
${$$nav(".sp-nav-item", dropdown).map(item => `
<a class="sp-nav-mobile-link" href="${item.getAttribute('href') || '#'}">
<img class="sp-nav-mobile-thumb" alt="" loading="lazy" src="${item.dataset.img || fallbackImg}" data-fb="${fallbackImg}">
<span class="sp-nav-mobile-text">
<strong>${item.dataset.title || ""}</strong>
<small>${$nav("small", item)?.textContent.trim() || ""}</small>
</span>
<span class="sp-nav-mobile-arrow"><svg><use href="#icon-arrow"/></svg></span>
</a>`).join('')}
</div>
</div>`;
});
mobileBody.innerHTML = html;
}
const setMobile = (open) => {
nav.classList.toggle("sp-nav-open", open);
document.body.classList.toggle("sp-nav-lock", open);
burger?.classList.toggle("active", open);
burger?.setAttribute("aria-expanded", String(open));
mobile?.setAttribute("aria-hidden", String(!open));
if (open) closeDropdowns();
};
burger?.addEventListener("click", () => setMobile(!nav.classList.contains("sp-nav-open")));
nav.addEventListener("click", e => {
const groupTrigger = e.target.closest(".sp-nav-mobile-trigger");
if (groupTrigger) {
const group = groupTrigger.closest(".sp-nav-mobile-group");
if (group) {
const open = group.classList.toggle("open");
groupTrigger.setAttribute("aria-expanded", String(open));
}
return;
}
if (e.target.closest(".sp-nav-mobile a")) setMobile(false);
});
document.addEventListener("click", e => { if (!nav.contains(e.target)) closeDropdowns(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") { closeDropdowns(); setMobile(false); } });
const onScrollNav = () => {
nav.classList.toggle("is-scrolled", window.scrollY > 20);
if (window.scrollY > 80) closeDropdowns();
};
window.addEventListener("scroll", onScrollNav, { passive: true });
onScrollNav();
const onBreakpointChange = () => { if (desktopQuery.matches) { setMobile(false); closeDropdowns(); } };
desktopQuery.addEventListener?.("change", onBreakpointChange) || desktopQuery.addListener?.(onBreakpointChange);
}
})();
