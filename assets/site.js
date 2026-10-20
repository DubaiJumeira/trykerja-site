/* Kerja website: the mobile menu and the Copy button. Nothing else uses JavaScript. */
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
  var buttons = document.querySelectorAll("[data-copy]");
  Array.prototype.forEach.call(buttons, function (b) {
    var label = b.textContent;
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
        b.textContent = "Copied";
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
})();
