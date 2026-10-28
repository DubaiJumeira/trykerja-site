/* Kerja website: the beta application form on Join the beta (/download/ and /id/download/),
   decisions 5289 and 5290. It sends the form as JSON to the form's data-endpoint, as the contract
   (kerja-artifacts/beta-apply/contract.md) says, and shows the answer in place:
     200: the form is replaced by "You're on the list" (also for a filled honeypot or an email
          already on the list: the server never tells them apart);
     400: each field the server names gets its error line, as the checks here do;
     429: the "too many tries" line;
     403 (an Origin the server doesn't allow), 500, anything else, or no answer at all: the
          "didn't go through" line, with hello@trykerja.com.
   Every word the visitor sees is in the page, in its language; this file holds none.
   No cookies, and nothing kept in the browser. Umami counts visits and a few taps (README.md,
   "Website statistics"); from this form, only apply-sent or apply-error with the answer's kind, never a
   field (count(), below). The only storage kept on the site is umami.disabled, written only when someone
   opts out (site.js). Nothing else is sent anywhere.
   Shown in a frame by another page, it does nothing, so Send stays disabled (the sites audit's A6:
   Pages can't send frame-ancestors). */
(function () {
  "use strict";
  if (window.top !== window.self) return;

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
  var SCHEME = /^[a-z][a-z0-9+.-]*:\/\//i;

  function field(key) { return form.querySelector('[data-field="' + key + '"]'); }
  function controls(key) { return Array.prototype.slice.call(field(key).querySelectorAll("input")); }
  function text(name) { return (form.elements.namedItem(name).value || "").trim(); }
  function chosen(name) {
    var c = form.querySelector('input[name="' + name + '"]:checked');
    return c ? c.value : "";
  }

  // The link as sent (the contract's "link field", decision 5301): what was typed, normalized only so:
  // starting with "@", unchanged (an Instagram handle); with a "." or a "/", https:// added when there is
  // no scheme; otherwise (a bare word), "@" added (an Instagram handle). Whether it is an Instagram or
  // LinkedIn profile is the server's rule: its 400 brings the field's line. Never "https://@...".
  function link() {
    var v = text("link");
    if (!v) return "";
    if (v.charAt(0) === "@") return v;
    if (/[.\/]/.test(v)) return SCHEME.test(v) ? v : "https://" + v;
    return "@" + v;
  }

  // The contract's rules, per field: true when the field is fine.
  var OK = {
    first_name: function () { var v = text("first_name"); return v.length >= 1 && v.length <= 40 && !/[\r\n]/.test(v) && !URLISH.test(v); },
    email: function () { var v = text("email"); return v.length <= 254 && EMAIL.test(v); },
    fits: function () { return !!chosen("fits"); },
    stay: function () { return !!chosen("stay"); },
    link: function () { var v = link(); return v.length <= 200 && !/^[a-z][a-z0-9+.-]*:\/\/@/i.test(v); },
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
    // Runs whatever happened (the sites audit's A4), so Send never stays on "Sending…".
    var cleanUp = function () {
      clearTimeout(timer);
      busy = false;
      send.textContent = sendLabel;
      form.removeAttribute("aria-busy");
    };

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
          count("apply-sent");
          success(body.first_name);
          return;
        }
        count("apply-error", r.status === 400 ? "invalid" : r.status === 429 ? "too_many" : r.status === 403 ? "origin" : "server");
        if (r.status === 400 && Array.isArray(r.json.fields) && r.json.fields.length) {
          var named = KEYS.filter(function (key) { return r.json.fields.indexOf(key) !== -1; });
          if (named.length) {
            KEYS.forEach(function (key) { mark(key, named.indexOf(key) !== -1); });
            showAlert("fields", named);
            return;
          }
        }
        showAlert(r.status === 429 ? "busy" : "fail");
      }, function () {
        count("apply-error", "offline");
        showAlert("fail");
      })
      .then(cleanUp, cleanUp);
  });

  // Website statistics (README.md, "Website statistics"; decision 5403): once the server has answered
  // (or the request failed), one Umami event: apply-sent, or apply-error with the kind of answer
  // (invalid, too_many, origin, server or offline). Its only data is that kind, one of the five words
  // above; never a field, a value or anything typed. Without the tracker (blocked, Do Not Track, the
  // #kerja-me opt-out) it does nothing, and nothing here can stop the form.
  function count(name, kind) {
    try {
      var umami = window.umami;
      if (!umami || typeof umami.track !== "function") return;
      var sent = kind ? umami.track(name, { kind: kind }) : umami.track(name);
      if (sent && typeof sent.then === "function") sent.then(null, function () {});
    } catch (e) { /* statistics never touch the form */ }
  }

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
