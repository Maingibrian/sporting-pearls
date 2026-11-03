/* Sporting Pearls - institutional-blueprint.js (verbatim v15) */
document.documentElement.classList.add('js');
var reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;

var prog=document.getElementById('progress');
var crMarker=document.getElementById('crMarker'),crYear=document.getElementById('crYear');
var ticking=false;
window.addEventListener('scroll',function(){
  if(!ticking){requestAnimationFrame(function(){
    var h=document.documentElement;
    var p=scrollY/(h.scrollHeight-innerHeight);
    prog.style.width=(p*100)+'%';
    if(crMarker){crMarker.style.left=(p*100)+'%';crYear.textContent=Math.round(2026+p*100);}
    ticking=false;
  });ticking=true;}
},{passive:true});

document.addEventListener('keydown',function(e){if(e.key==='Escape'&&document.body.classList.contains('menu-open'))document.body.classList.remove('menu-open');});

/* word-mask split */
document.querySelectorAll('[data-words]').forEach(function(el){
  var nodes=Array.prototype.slice.call(el.childNodes);el.innerHTML='';var i=0;
  function mkWord(content,isEl){
    var w=document.createElement('span');w.className='w';
    var inner=document.createElement('span');var d=(i++)*70;inner.style.transitionDelay=(d+240)+'ms';w.style.setProperty('--wd',d+'ms');
    if(isEl){inner.appendChild(content);}else{inner.textContent=content;}
    w.appendChild(inner);el.appendChild(w);el.appendChild(document.createTextNode(' '));
  }
  nodes.forEach(function(n){
    if(n.nodeType===3){n.textContent.split(/\s+/).filter(Boolean).forEach(function(w){mkWord(w,false);});}
    else{mkWord(n,true);}
  });
});

/* scramble */
(function(){
  var el=document.getElementById('scrambleTag');if(!el)return;
  var span=el.querySelector('span'),orig=el.getAttribute('data-text'),chars='█▓▒░<>/+=*';
  if(reduceMotion){span.textContent=orig;return;}
  var started=false;
  var so=new IntersectionObserver(function(es){es.forEach(function(e){
    if(e.isIntersecting&&!started){started=true;so.unobserve(el);
      var f=0,total=26;
      (function tick(){f++;var out='';for(var i=0;i<orig.length;i++){out+=(i<(f/total)*orig.length)?orig[i]:(orig[i]===' '?' ':chars[Math.floor(Math.random()*chars.length)]);}span.textContent=out;if(f<total)setTimeout(tick,40);else span.textContent=orig;})();
    }});},{threshold:.5});
  so.observe(el);
})();

/* reveal observer */
var io=new IntersectionObserver(function(es){es.forEach(function(e){if(e.isIntersecting){e.target.classList.add('in');io.unobserve(e.target);}});},{threshold:0,rootMargin:'0px 0px -40px 0px'});
document.querySelectorAll('[data-reveal],.wr,.gov-svg,.fin-list,.ok,.dial-wrap').forEach(function(el){io.observe(el);});

/* drag-scroll roadmap */
var strip=document.getElementById('roadStrip');
if(strip){
  var isDown=false,startX,startScroll;
  strip.addEventListener('mousedown',function(e){isDown=true;strip.style.cursor='grabbing';startX=e.pageX;startScroll=strip.scrollLeft;});
  ['mouseleave','mouseup'].forEach(function(ev){strip.addEventListener(ev,function(){isDown=false;strip.style.cursor='grab';});});
  strip.addEventListener('mousemove',function(e){if(!isDown)return;e.preventDefault();strip.scrollLeft=startScroll-(e.pageX-startX)*1.4;});
}

/* ═══════ NAVBAR PRO LOGIC ═══════ */
(() => {
  const nav = document.getElementById("spNavPro");
  if (!nav) return;

  const $ = (s, c = nav) => c.querySelector(s);
  const $$ = (s, c = nav) => [...c.querySelectorAll(s)];
  const fallbackImg = "feminin-hero.jpg";
  $$(".sp-nav-preview-img").forEach(im=>im.addEventListener("error",()=>{if(!im.src.endsWith("feminin-hero.jpg"))im.src=fallbackImg;}));
  const isFinePointer = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const desktopQuery = matchMedia("(min-width: 1100px)");
  
  const triggers = $$(".sp-nav-trigger");
  const dropdowns = $$(".sp-nav-dropdown");
  const burger = $("#spNavBurger");
  const mobile = $("#spNavMobile");
  const mobileBody = $("#spNavMobileBody");

  let closeTimer;

  const closeDropdowns = () => {
    triggers.forEach(t => { t.classList.remove("active"); t.setAttribute("aria-expanded", "false"); });
    dropdowns.forEach(d => { d.classList.remove("active"); d.setAttribute("aria-hidden", "true"); });
  };

  const setPreview = (dropdown, item, instant) => {
    const media = $(".sp-nav-preview-img", dropdown);
    const caption = $(".sp-nav-preview-caption", dropdown);
    if (!media || !caption || !item) return;

    const { img: src = fallbackImg, title = "", copy = "", kicker = "Preview" } = item.dataset;
    if (media.dataset.current === src && caption.dataset.current === title) return;

    const applyCaption = () => {
      $(".sp-nav-preview-kicker", caption).textContent = kicker;
      $(".sp-nav-preview-title", caption).textContent = title;
      $(".sp-nav-preview-copy", caption).textContent = copy;
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
    const loader = new Image();
    loader.onload = () => swap(loader.src);
    loader.onerror = () => swap(fallbackImg);
    loader.src = src;
    setTimeout(() => swap(src), 1200);
  };

  const openDropdown = (id) => {
    clearTimeout(closeTimer); closeDropdowns();
    const trigger = $(`.sp-nav-trigger[data-menu="${id}"]`);
    const dropdown = $(`.sp-nav-dropdown[data-menu="${id}"]`);
    if (!trigger || !dropdown) return;

    trigger.classList.add("active"); trigger.setAttribute("aria-expanded", "true");
    dropdown.classList.add("active"); dropdown.setAttribute("aria-hidden", "false");
    setPreview(dropdown, $(".sp-nav-item.is-active", dropdown) || $(".sp-nav-item", dropdown), true);
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
      $$(".sp-nav-item", dropdown).forEach(l => l.classList.toggle("is-active", l === item));
      setPreview(dropdown, item);
    };
    dropdown.addEventListener("mouseover", activateItem);
    dropdown.addEventListener("focusin", activateItem);
  });

  if (mobileBody) {
    const directLinks = $$(".sp-nav-desktop > .sp-nav-link");
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
      const trigger = $(`.sp-nav-trigger[data-menu="${dropdown.dataset.menu}"]`);
      const title = trigger?.dataset.label || dropdown.dataset.menu;
      html += `
        <div class="sp-nav-mobile-group">
          <button type="button" class="sp-nav-mobile-trigger" aria-expanded="false">
            <span>${title}</span><span><svg><use href="#icon-chevron"/></svg></span>
          </button>
          <div class="sp-nav-mobile-panel">
            ${$$(".sp-nav-item", dropdown).map(item => `
              <a class="sp-nav-mobile-link" href="${item.getAttribute('href') || '#'}">
                <img class="sp-nav-mobile-thumb" alt="" loading="lazy" src="${item.dataset.img || fallbackImg}" data-fb="${fallbackImg}">
                <span class="sp-nav-mobile-text">
                  <strong>${item.dataset.title || ""}</strong>
                  <small>${$("small", item)?.textContent.trim() || ""}</small>
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

  const onScroll = () => {
    nav.classList.toggle("is-scrolled", window.scrollY > 20);
    if (window.scrollY > 80) closeDropdowns();
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  const onBreakpointChange = () => { if (desktopQuery.matches) { setMobile(false); closeDropdowns(); } };
  desktopQuery.addEventListener?.("change", onBreakpointChange) || desktopQuery.addListener?.(onBreakpointChange);
})();
