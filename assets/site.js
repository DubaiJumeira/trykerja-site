/* Kerja website: the statistics opt-out marker, the statistics tracker's loader, the link counter and
   Our promise's visitor opt-out, the mobile menu and the steps of Welcome's map story.
   Join the beta's form has its own script, apply.js; the statistics tracker is umami.js, which only
   this file adds to a page. */
(function () {
  "use strict";
  var self = document.currentScript; // this file's own tag: the tracker sits beside it in assets/

  // Website statistics (README.md, "Website statistics"; decision 5404): a page opened with #kerja-me
  // tells this browser's Umami tracker never to send anything from this site, by the localStorage flag
  // the tracker itself reads before every send ("umami.disabled"); #kerja-me-off takes the flag away.
  // It runs before the loader below, so the visit that carries the marker doesn't even load the
  // tracker. The marker then leaves the address bar.
  var optOut = function () {
    var mark = location.hash;
    if (mark !== "#kerja-me" && mark !== "#kerja-me-off") return;
    try {
      if (mark === "#kerja-me") localStorage.setItem("umami.disabled", "1");
      else localStorage.removeItem("umami.disabled");
    } catch (e) { /* storage blocked in this browser: nothing to keep */ }
    if (history.replaceState) history.replaceState(null, "", location.pathname + location.search);
  };
  optOut();
  window.addEventListener("hashchange", optOut);

  // The tracker's tag, in this one place (decisions 5402, 5405, 5421, 5431): no page carries it; the
  // loader below adds it. tools/stamp.py keeps the ?v= stamp current; tools/csp_check.py checks the
  // path, the website ID and the six attributes against its pins.
  var TRACKER = {
    src: "umami.js?v=654f12c7",
    attrs: {
      "data-website-id": "b33e8625-5183-4fd3-973d-9e1feb90f868",
      "data-host-url": "https://gateway.umami.is",
      "data-do-not-track": "true",
      "data-domains": "trykerja.com",
      "data-exclude-search": "true",
      "data-exclude-hash": "true"
    }
  };

  // [tracker-loader] Fail closed (decision 5431, the auditor's fix B): Umami is loaded only where the
  // visitor's choice can be kept. The tracker is added only if this browser's localStorage can be
  // written, read back and cleared (a test key, removed at once), and the visitor hasn't opted out
  // (umami.disabled not set; the #kerja-me marker is handled above, first). If any step throws or
  // reads back wrong, nothing is loaded and nothing is counted; without JavaScript, or if this file
  // fails, nothing is loaded either. tools/csp_check.py pins this block's SHA-256: change it on
  // purpose only, test it, then update LOADER_SHA256 there.
  var FLAG = "umami.disabled";
  var writableStorage = function () {
    try {
      var s = window.localStorage, probe = "kerja.storage-check";
      s.setItem(probe, "1");
      var back = s.getItem(probe);
      s.removeItem(probe);
      return back === "1" && s.getItem(probe) === null ? s : null;
    } catch (e) { return null; }
  };
  (function () {
    var s = writableStorage(), counted = false;
    try { counted = !!s && s.getItem(FLAG) === null; } catch (e) { counted = false; }
    if (!counted || !self || !self.src) return;
    try {
      var tag = document.createElement("script");
      tag.src = new URL(TRACKER.src, self.src).href;
      tag.defer = true;
      for (var k in TRACKER.attrs) tag.setAttribute(k, TRACKER.attrs[k]);
      document.head.appendChild(tag);
    } catch (e) { /* not loaded: nothing is counted */ }
  })();
  // [/tracker-loader]

  // Counting a tap on a link (decisions 5403, 5409): a link with data-count="<event>" (and data-count-at,
  // data-count-lang) is counted with umami.track(), which starts its request at once, with fetch's
  // keepalive, so it can finish after the page has gone (Umami 3.4.1, src/tracker/index.ts:384-399).
  // This never calls preventDefault and waits for nothing: the link opens at once, and a count that
  // doesn't make it is lost rather than the tap delayed. Links never carry Umami's own data-umami-event,
  // which holds a link until Umami has answered (index.ts:349-365); the menu button keeps it, as Umami
  // doesn't hold a button (index.ts:370). Without the tracker (blocked, Do Not Track, #kerja-me), nothing.
  document.addEventListener("click", function (e) {
    var el = e.target && e.target.closest ? e.target.closest("[data-count]") : null;
    var umami = window.umami;
    if (!el || !umami || typeof umami.track !== "function") return;
    var data = {}, any = false;
    for (var i = 0; i < el.attributes.length; i++) {
      var a = el.attributes[i];
      if (a.name.indexOf("data-count-") === 0) { data[a.name.slice(11)] = a.value; any = true; }
    }
    try {
      var sent = any ? umami.track(el.getAttribute("data-count"), data) : umami.track(el.getAttribute("data-count"));
      if (sent && typeof sent.then === "function") sent.then(null, function () {});
    } catch (err) { /* a count never stops a tap */ }
  }, true);

  // The visitors' own opt-out, on Our promise (decision 5412; the auditor's words are in
  // kerja-artifacts/promise-text.md). "Don’t count my visits" sets the same flag as #kerja-me
  // (localStorage "umami.disabled", read by the tracker before every send); "Count them again" removes
  // it, as #kerja-me-off does. The line swaps only once the flag has been saved and read back, and the
  // page opens on the line that matches the flag. Where storage can't be written and read (the same
  // test as the loader's, so nothing is counted there either), the buttons stay hidden and the first
  // sentence shows alone, as without JavaScript: a tap couldn't keep the choice. The
  // buttons, and every element around them, carry no data-count or data-umami-event (csp_check.py
  // fails if one does), so a tap sends nothing; it writes nothing but the flag.
  var line = document.querySelector("[data-optout-line]");
  var stopBtn = line && line.querySelector('[data-optout="stop"]');
  var countBtn = line && line.querySelector('[data-optout="count"]');
  if (stopBtn && countBtn) {
    var onText = document.getElementById(stopBtn.getAttribute("aria-describedby"));
    var offText = document.getElementById(countBtn.getAttribute("aria-describedby"));
    var show = function (off, focus) {
      onText.hidden = stopBtn.hidden = off;
      offText.hidden = countBtn.hidden = !off;
      if (focus) (off ? countBtn : stopBtn).focus();
    };
    var render = function () {
      var s = writableStorage();
      if (s) show(!!s.getItem(FLAG), false);
    };
    var choose = function (off) {
      var s = writableStorage(), saved = false;
      try {
        if (s) {
          if (off) s.setItem(FLAG, "1");
          else s.removeItem(FLAG);
          saved = off ? s.getItem(FLAG) === "1" : s.getItem(FLAG) === null;
        }
      } catch (e) { saved = false; }
      if (saved) { show(off, true); return; }
      // Not saved: no button can work here, so none stays; the first sentence shows alone.
      stopBtn.hidden = countBtn.hidden = offText.hidden = true;
      onText.hidden = false;
    };
    stopBtn.addEventListener("click", function () { choose(true); });
    countBtn.addEventListener("click", function () { choose(false); });
    render();
    window.addEventListener("hashchange", render);
  }

  // Menu: <button class="menu-btn" aria-controls="menu" aria-expanded="false"> opens <dialog id="menu">.
  var btn = document.querySelector(".menu-btn");
  var menu = document.getElementById("menu");
  if (btn && menu && typeof menu.showModal === "function") {
    btn.addEventListener("click", function () {
      menu.showModal();
      btn.setAttribute("aria-expanded", "true");
    });
    menu.addEventListener("close", function () {
      btn.setAttribute("aria-expanded", "false");
      btn.focus();
    });
    var close = menu.querySelector(".menu-close");
    if (close) close.addEventListener("click", function () { menu.close(); });
    // A tap on the scrim (outside the sheet) closes it too.
    menu.addEventListener("click", function (e) { if (e.target === menu) menu.close(); });
  }

  // The map story on Welcome (welcome.css): desktop only, with motion allowed. As each step's line
  // passes 60% of the screen's height, the section gets s1 to s4 and that step's part of the map
  // comes in. Normal scrolling: IntersectionObservers, no scroll handler, nothing but classes.
  // Without IntersectionObserver (or without JavaScript), the section never goes "live" and every
  // part simply shows.
  var story = document.querySelector(".story");
  if (story && "IntersectionObserver" in window && window.matchMedia) {
    var mq = window.matchMedia("(min-width: 1024px) and (prefers-reduced-motion: no-preference)");
    var steps = story.querySelectorAll("[data-step]");
    var observers = [];
    var at = -1;
    var update = function () {
      var line = window.innerHeight * 0.6, n = 0;
      for (var i = 0; i < steps.length; i++) {
        if (steps[i].getBoundingClientRect().top <= line) n = i + 1;
      }
      if (n === at) return;
      at = n;
      for (var k = 1; k <= steps.length; k++) story.classList.toggle("s" + k, k <= n);
    };
    var start = function () {
      if (!mq.matches) {
        observers.forEach(function (o) { o.disconnect(); });
        observers = [];
        story.classList.remove("live");
        return;
      }
      if (observers.length) return;
      // The first state is set without a transition (one style flush, while "settle" turns them
      // off), then the parts move only as the lines pass.
      story.classList.add("settle");
      at = -1;
      update();
      story.classList.add("live");
      void story.offsetWidth;
      story.classList.remove("settle");
      // A thin band at 60% of the screen: a step's line crossing it changes the step. The second
      // observer catches jumps (Home, End, a link) that skip the band, a screen before the story
      // comes back into view, so its parts never visibly undo themselves.
      var band = new IntersectionObserver(update, { rootMargin: "-58% 0px -40% 0px" });
      Array.prototype.forEach.call(steps, function (s) { band.observe(s); });
      var whole = new IntersectionObserver(update, { rootMargin: "100% 0px 100% 0px" });
      whole.observe(story);
      observers = [band, whole];
    };
    start();
    if (mq.addEventListener) mq.addEventListener("change", start);
    else if (mq.addListener) mq.addListener(start);
  }
})();
