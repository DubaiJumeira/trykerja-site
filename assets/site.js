/* Kerja website: the mobile menu, the Copy button, the waitlist's "No email app?" panel and the steps
   of Welcome's map story. Nothing else uses JavaScript. */
(function () {
  "use strict";

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

  // Copy: <button class="copy-btn" data-copy="#some-id">Copy</button> copies the text of #some-id.
  // data-copied="…" is the word it shows once copied, in the page's language (Copied by default).
  var buttons = document.querySelectorAll("[data-copy]");
  Array.prototype.forEach.call(buttons, function (b) {
    var label = b.textContent;
    var copied = b.getAttribute("data-copied") || "Copied";
    var timer = 0;
    b.addEventListener("click", function () {
      var target = document.querySelector(b.getAttribute("data-copy"));
      if (!target) return;
      var text = target.innerText.trim();
      function select() {
        var range = document.createRange();
        range.selectNodeContents(target);
        var sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
      }
      function done() {
        b.textContent = copied;
        clearTimeout(timer);
        timer = setTimeout(function () { b.textContent = label; }, 2000);
      }
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, select);
      } else {
        select();
      }
    });
  });

  // Join the waitlist (decision 5348): its buttons are mailto: links, and where no mail app answers
  // (a computer without one, an in-app browser) a tap shows nothing. So a click on a mailto: link in a
  // .waitlist block (a tap, or Enter on the focused link) also opens that block's "No email app?"
  // panel. The mailto goes as before: nothing is prevented, nothing scrolls or takes focus, no timer.
  document.addEventListener("click", function (e) {
    var link = e.target && e.target.closest ? e.target.closest('.waitlist a[href^="mailto:"]') : null;
    var block = link && link.closest(".waitlist");
    var panel = block && block.querySelector("details.noemail");
    if (panel) panel.open = true;
  });

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
