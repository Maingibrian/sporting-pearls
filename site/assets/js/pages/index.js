/* Sporting Pearls - index.js (verbatim v15) */
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
