/* Kerja website: the beta application form on Join the beta (/download/ and /id/download/),
   decisions 5289 and 5290. It sends the form as JSON to the form's data-endpoint, as the contract
   (kerja-artifacts/beta-apply/contract.md) says, and shows the answer in place:
     200: the form is replaced by "You're on the list" (also for a filled honeypot or an email
          already on the list: the server never tells them apart);
     400: each field the server names gets its error line, as the checks here do;
     429: the "too many tries" line; 500, or no answer at all: the "didn't go through" line.
   Every word the visitor sees is in the page, in its language; this file holds none.
   No cookies, no storage, no analytics, nothing sent anywhere else. */
(function () {
  "use strict";

  var form = document.getElementById("apply-form");
  if (!form || !window.fetch || !window.JSON) return;

  var box = document.getElementById("apply");
  var done = document.getElementById("apply-done");
  var alertBox = document.getElementById("apply-alert");
  var alertFields = document.getElementById("apply-alert-fields");
  var alertList = alertBox.querySelector(".ap-alert-list");
  var alertBusy = document.getElementById("apply-alert-busy");
  var alertFail = document.getElementById("apply-alert-fail");
  var send = form.querySelector('button[type="submit"]');
  var sendLabel = send.textContent;
  var endpoint = form.getAttribute("data-endpoint");
  var lang = document.documentElement.lang === "id" ? "id" : "en";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // The fields, in the page's order, with the contract's keys.
  var KEYS = ["first_name", "email", "fits", "stay", "link", "work_on", "adult", "privacy"];
  var URLISH = /(:\/\/|www\.|\b[a-z0-9-]+\.(com|net|org|io|co|id|me|app|ly|xyz|info|link)\b)/i;
  var EMAIL = /^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$/;
  var HANDLE = /^@[A-Za-z0-9._]{1,30}$/;
  var PROFILE = /^(https?:\/\/)?([a-z0-9-]+\.)*(instagram\.com|linkedin\.com)\/\S+$/i;

  function field(key) { return form.querySelector('[data-field="' + key + '"]'); }
  function controls(key) { return Array.prototype.slice.call(field(key).querySelectorAll("input")); }
  function text(name) { return (form.elements.namedItem(name).value || "").trim(); }
  function chosen(name) {
    var c = form.querySelector('input[name="' + name + '"]:checked');
    return c ? c.value : "";
  }

  // A link as sent: an @handle as typed, a profile URL with https:// added when it was left off.
  function link() {
    var v = text("link");
    if (!v) return "";
    if (HANDLE.test(v)) return v;
    if (PROFILE.test(v)) return /^https?:\/\//i.test(v) ? v : "https://" + v;
    return null;
  }

  // The contract's rules, per field: true when the field is fine.
  var OK = {
    first_name: function () { var v = text("first_name"); return v.length >= 1 && v.length <= 40 && !/[\r\n]/.test(v) && !URLISH.test(v); },
    email: function () { var v = text("email"); return v.length <= 254 && EMAIL.test(v); },
    fits: function () { return !!chosen("fits"); },
    stay: function () { return !!chosen("stay"); },
    link: function () { var v = link(); return v !== null && v.length <= 200; },
    work_on: function () { var v = text("work_on"); return v.length <= 140 && !/[\r\n]/.test(v); },
    adult: function () { return form.elements.namedItem("adult").checked; },
    privacy: function () { return form.elements.namedItem("privacy").checked; }
  };

  function payload() {
    var body = {
      lang: lang,
      first_name: text("first_name"),
      email: text("email"),
      fits: chosen("fits"),
      stay: chosen("stay"),
      adult: true,
      privacy: true,
      website: form.elements.namedItem("website").value
    };
    // The two optional fields are left out when empty.
    var l = link();
    if (l) body.link = l;
    var w = text("work_on");
    if (w) body.work_on = w;
    return body;
  }

  // An error line shows under its field; the field's controls get aria-invalid, and the line joins
  // their description only while it shows.
  function mark(key, bad) {
    var f = field(key);
    var err = f.querySelector(".ap-err");
    err.hidden = !bad;
    f.classList.toggle("is-invalid", bad);
    controls(key).forEach(function (c) {
      var ids = (c.getAttribute("aria-describedby") || "").split(/\s+/).filter(function (x) { return x && x !== err.id; });
      if (bad) {
        c.setAttribute("aria-invalid", "true");
        ids.push(err.id);
      } else {
        c.removeAttribute("aria-invalid");
      }
      if (ids.length) c.setAttribute("aria-describedby", ids.join(" "));
      else c.removeAttribute("aria-describedby");
    });
  }

  function firstControl(key) {
    var cs = controls(key);
    for (var i = 0; i < cs.length; i++) if (cs[i].checked) return cs[i];
    return cs[0];
  }

  function bring(el) {
    el.scrollIntoView({ block: "start", behavior: reduce ? "auto" : "smooth" });
  }

  function hideAlert() {
    alertBox.hidden = true;
    alertFields.hidden = alertBusy.hidden = alertFail.hidden = true;
  }

  // The box above the fields: the list of fields to check (each a link to its field), or one line.
  // It takes focus, so it is read at once and the keyboard starts from it.
  function showAlert(kind, keys) {
    hideAlert();
    if (kind === "fields") {
      alertList.textContent = "";
      keys.forEach(function (key) {
        var c = firstControl(key);
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.className = "ap-a";
        a.href = "#" + (c.id || field(key).querySelector("input").id || "apply");
        a.textContent = field(key).querySelector(".ap-err").textContent;
        a.addEventListener("click", function (e) {
          e.preventDefault();
          var target = firstControl(key);
          target.focus({ preventScroll: true });
          bring(field(key));
        });
        li.appendChild(a);
        alertList.appendChild(li);
      });
      alertFields.hidden = false;
    } else if (kind === "busy") {
      alertBusy.hidden = false;
    } else {
      alertFail.hidden = false;
    }
    alertBox.hidden = false;
    alertBox.focus({ preventScroll: true });
    bring(alertBox);
  }

  // The radios need ids for the summary's links.
  KEYS.forEach(function (key) {
    controls(key).forEach(function (c, i) { if (!c.id) c.id = "apply-" + key.replace(/_/g, "-") + "-" + (i + 1); });
  });

  // Once a field with an error line is put right, its line goes; nothing new is flagged while typing.
  KEYS.forEach(function (key) {
    controls(key).forEach(function (c) {
      c.addEventListener(c.type === "radio" || c.type === "checkbox" ? "change" : "input", function () {
        if (field(key).classList.contains("is-invalid") && OK[key]()) mark(key, false);
      });
    });
  });

  var busy = false;
  form.noValidate = true;
  send.disabled = false;

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (busy) return;
    var bad = KEYS.filter(function (key) { return !OK[key](); });
    KEYS.forEach(function (key) { mark(key, bad.indexOf(key) !== -1); });
    if (bad.length) {
      showAlert("fields", bad);
      return;
    }
    hideAlert();
    busy = true;
    send.textContent = send.getAttribute("data-sending") || sendLabel;
    form.setAttribute("aria-busy", "true");

    var ctrl = window.AbortController ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, 20000) : 0;
    var body = payload();

    fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      credentials: "omit",
      cache: "no-store",
      signal: ctrl ? ctrl.signal : undefined
    })
      .then(function (res) {
        return res.json().then(function (json) { return { status: res.status, json: json || {} }; }, function () { return { status: res.status, json: {} }; });
      })
      .then(function (r) {
        if (r.status === 200 && r.json.ok === true) {
          success(body.first_name);
          return;
        }
        if (r.status === 400 && r.json.fields && r.json.fields.length) {
          var named = KEYS.filter(function (key) { return r.json.fields.indexOf(key) !== -1; });
          if (named.length) {
            KEYS.forEach(function (key) { mark(key, named.indexOf(key) !== -1); });
            showAlert("fields", named);
            return;
          }
        }
        showAlert(r.status === 429 ? "busy" : "fail");
      }, function () {
        showAlert("fail");
      })
      .then(function () {
        clearTimeout(timer);
        busy = false;
        send.textContent = sendLabel;
        form.removeAttribute("aria-busy");
      });
  });

  // "You're on the list": the heading, the form and its note make way for the thanks, by first name.
  function success(name) {
    done.querySelector(".ap-name").textContent = name;
    box.classList.add("is-done");
    box.querySelector(".ap-head").hidden = true;
    form.hidden = true;
    form.reset();
    done.hidden = false;
    box.setAttribute("aria-labelledby", "apply-done-t");
    done.focus({ preventScroll: true });
    bring(done);
  }
})();
