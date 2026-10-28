#!/usr/bin/env python3
"""Checks every published page's Content-Security-Policy and referrer tags, and every published file
for kerja-dev. Standard library only; reads files, changes nothing; needs no git checkout.

  python3 -I tools/csp_check.py [<site folder>]   (this repo by default)
  python3 -I tools/csp_check.py --publish         also fails while the Umami website ID is the placeholder

It walks the folder and checks what GitHub Pages would publish (everything with a .nojekyll file;
otherwise all but names starting with "." or "_" and the `exclude:` list of _config.yml).

Fails (exit 1) when a page:
- hasn't exactly one CSP meta and one referrer meta, before any link, script, style or img tag;
- has a referrer other than exactly "no-referrer";
- has a CSP that isn't exactly the one README.md's "Security" part gives for it (directives in that
  order, whitespace aside): the base policy, with the SHA-256 of each of the page's own inline
  <style> blocks in style-src (none listed when it has none); plus style-src-attr 'unsafe-inline'
  on Welcome (index.html, id/index.html) only; and on Join the beta (download/index.html,
  id/download/index.html) only, kerja-prod's function after connect-src 'self'; then, on every page,
  Umami's collector URL, https://gateway.umami.is/api/send, last in connect-src (5402, Q534). So any
  other source, keyword or directive fails (https:, data: or * in script-src, script-src-attr, style-src-elem, 'unsafe-eval',
  form-action *, a missing directive…);
- has an inline script, an on…= attribute or a javascript: URL;
- has style="" attributes on a page whose policy doesn't allow them, or Welcome's allowance with no
  style attribute to need it;
- has a form whose data-endpoint isn't kerja-prod's function;
- loads anything from another site (src, srcset, a stylesheet, preload, icon or manifest href);
- has a target="_blank" link without rel="noopener";
- hasn't exactly one Umami tracker tag: <script src="…assets/umami.js?v=…" defer> with exactly
  data-website-id (a UUID), data-host-url (the collector), data-do-not-track="true",
  data-domains="trykerja.com", data-exclude-search="true" and data-exclude-hash="true", and no other
  attribute (so no data-performance, data-before-send, data-tag, data-distinct-id…), after site.js
  (whose #kerja-me opt-out must run first);
- has data-umami-event on a link (Umami would hold the tap until its collector answers; links count
  with data-count, through site.js, Q535) or with any name but menu-open, or data-umami-event-* data;
- has a data-count other than the link events, or data-count-* data other than "at" and "lang", or a
  value that isn't a short lowercase word (no data a visitor types or owns);
- (Our promise, EN and ID) hasn't exactly one visitor opt-out line (data-optout-line) with its two
  hidden <button type="button">s, or has data-count or data-umami-event on that line, on any element
  around it or in it (the opt-out must send nothing, decision 5412); or has one on another page.
And when assets/umami.js isn't byte for byte the pinned Umami release (its SHA-256, UMAMI_SHA256: the
copy may not be edited; README.md, "Website statistics", says how to update it), or when a page's
data-website-id is neither Kerja's Umami website ID (UMAMI_WEBSITE_ID) nor, without --publish, the old
placeholder.
And when any published text file (HTML, JS, CSS, SVG, XML, JSON, TXT) names kerja-dev's project ref,
in any case, or a published stylesheet loads from another site (url()) or uses @import.
"""
import base64
import hashlib
import os
import re
import sys
from html.parser import HTMLParser

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
PUBLISH = "--publish" in sys.argv
ROOT = os.path.abspath(ARGS[0] if ARGS else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEV_REF = re.compile(r"oiyjmnsaqefrpfrbopjy", re.I)  # kerja-dev's project ref: never published (decision 5300)
PROD_FUNCTION = "https://eppqufcgcwhoprwzfhxy.supabase.co/functions/v1/submit-application"  # kerja-prod's
WELCOME = {"index.html", "id/index.html"}
JOIN = {"download/index.html", "id/download/index.html"}
REFERRER = "no-referrer"
RESOURCE_TAGS = ("link", "script", "style", "img", "picture", "source")
TEXT_TYPES = (".html", ".htm", ".js", ".mjs", ".css", ".svg", ".xml", ".json", ".txt", ".webmanifest")
# Website statistics (decisions 5402 to 5405): Umami 3.4.1's tracker, from the official image
# ghcr.io/umami-software/umami:3.4.1, /app/public/script.js (tools/umami_fetch.py gets it again).
UMAMI_FILE = "assets/umami.js"
UMAMI_VERSION = "3.4.1"
UMAMI_SHA256 = "654f12c7548be726eba5b71d5ef8bffc2a41a39a0053e2a49a847869ccd7ac3f"
COLLECTOR = "https://gateway.umami.is"  # Umami Cloud's collector origin: the tracker's data-host-url
COLLECTOR_URL = COLLECTOR + "/api/send"  # the one address it posts to: connect-src allows exactly this (Q534, 5409)
UMAMI_WEBSITE_ID = "b33e8625-5183-4fd3-973d-9e1feb90f868"  # trykerja.com in Zayd's Umami Cloud account (5421); public, not a secret
PLACEHOLDER_ID = "00000000-0000-0000-0000-000000000000"  # the branch's stand-in before the account (5405)
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
TRACKER_ATTRS = {"data-host-url": COLLECTOR, "data-do-not-track": "true", "data-domains": "trykerja.com",
                 "data-exclude-search": "true", "data-exclude-hash": "true"}
BUTTON_EVENTS = {"menu-open"}  # data-umami-event: Umami counts a button without holding it (index.ts:370)
LINK_EVENTS = {"apply-open", "lang-switch", "testflight", "testflight-app", "instagram"}  # data-count, counted by site.js
COUNT_DATA = {"data-count-at", "data-count-lang"}
WORD = re.compile(r"^[a-z][a-z0-9_-]{0,23}$")
PROMISE = {"promise/index.html", "id/promise/index.html"}  # where the visitors' opt-out lives (decision 5412)


def expected_csp(page, style_hashes):
    connect = "'self'" + (" " + PROD_FUNCTION if page in JOIN else "") + " " + COLLECTOR_URL
    directives = [
        "default-src 'self'",
        "script-src 'self'",
        " ".join(["style-src 'self'"] + sorted(style_hashes)),
    ]
    if page in WELCOME:
        directives.append("style-src-attr 'unsafe-inline'")
    directives += [
        "img-src 'self' data:",
        "font-src 'self'",
        "connect-src " + connect,
        "form-action 'none'",
        "base-uri 'none'",
        "object-src 'none'",
    ]
    return directives


def normalized(policy):
    return [" ".join(d.split()) for d in policy.split(";") if d.strip()]


def config_lists():
    exclude, include, current = [], [], None
    path = os.path.join(ROOT, "_config.yml")
    if os.path.exists(path):
        for raw in open(path, encoding="utf-8"):
            line = raw.split("#", 1)[0].rstrip()
            m = re.match(r"^(\w+):\s*(.*)$", line)
            if m:
                current = m.group(1)
                if m.group(2).startswith("["):
                    items = [x.strip().strip("'\"") for x in m.group(2).strip("[]").split(",") if x.strip()]
                    (exclude if current == "exclude" else include if current == "include" else []).extend(items)
                continue
            m = re.match(r"^\s+-\s+(.+)$", line)
            if m and current in ("exclude", "include"):
                (exclude if current == "exclude" else include).append(m.group(1).strip().strip("'\"").rstrip("/"))
    return exclude, include


NOJEKYLL = os.path.exists(os.path.join(ROOT, ".nojekyll"))
EXCLUDE, INCLUDE = config_lists()


def published(rel):
    parts = rel.split("/")
    if parts[0] == ".git":
        return False
    if NOJEKYLL:
        return True
    for i in range(len(parts)):
        prefix = "/".join(parts[: i + 1])
        if prefix in INCLUDE:
            continue
        if prefix in EXCLUDE or parts[i].startswith((".", "_", "#")) or parts[i].endswith("~"):
            return False
    return True


def walk():
    out = []
    for d, dirs, names in os.walk(ROOT):
        dirs[:] = sorted(x for x in dirs if x != ".git" and x != "node_modules")
        for n in sorted(names):
            rel = os.path.relpath(os.path.join(d, n), ROOT).replace(os.sep, "/")
            if published(rel):
                out.append(rel)
    return out


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Page(HTMLParser):
    """Every start tag with its attributes, and the indexes of the elements open around it."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags, self.parents, self.stack = [], [], []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        self.parents.append(list(self.stack))
        if tag not in VOID:
            self.stack.append(len(self.tags) - 1)

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        self.parents.append(list(self.stack))

    def handle_endtag(self, tag):
        for k in range(len(self.stack) - 1, -1, -1):
            if self.tags[self.stack[k]][0] == tag:
                del self.stack[k:]
                break


problems = []
notes = set()


def fail(path, msg):
    problems.append(f"FAIL  {path}: {msg}")


FILES = walk()
for page in [f for f in FILES if f.endswith((".html", ".htm"))]:
    src = open(os.path.join(ROOT, page), encoding="utf-8").read()
    p = Page()
    p.feed(src)
    metas = [(i, a) for i, (t, a) in enumerate(p.tags) if t == "meta"]
    csp_tags = [(i, a) for i, a in metas if (a.get("http-equiv") or "").lower() == "content-security-policy"]
    ref_tags = [(i, a) for i, a in metas if (a.get("name") or "").lower() == "referrer"]
    if len(csp_tags) != 1:
        fail(page, f"{len(csp_tags)} CSP meta tags (one expected)")
        continue
    if len(ref_tags) != 1:
        fail(page, f"{len(ref_tags)} referrer meta tags (one expected)")
    elif (ref_tags[0][1].get("content") or "").strip().lower() != REFERRER:
        fail(page, f"referrer is {ref_tags[0][1].get('content')!r}, not {REFERRER!r}")
    first_resource = next((i for i, (t, _) in enumerate(p.tags) if t in RESOURCE_TAGS), len(p.tags))
    if csp_tags[0][0] > first_resource or (ref_tags and ref_tags[0][0] > first_resource):
        fail(page, "a resource tag comes before the CSP or referrer meta")
    # The policy, exactly.
    blocks = re.findall(r"<style[^>]*>(.*?)</style>", src, re.S)
    hashes = {"'sha256-" + base64.b64encode(hashlib.sha256(b.encode("utf-8")).digest()).decode() + "'" for b in blocks}
    want = expected_csp(page, hashes)
    got = normalized(csp_tags[0][1].get("content", ""))
    if got != want:
        extra = [d for d in got if d not in want]
        missing = [d for d in want if d not in got]
        detail = (f"; not allowed: {extra}" if extra else "") + (f"; expected: {missing}" if missing else "")
        fail(page, "the CSP isn't exactly the allowed one" + (detail or "; directives out of order"))
    # Scripts and handlers.
    for t, a in p.tags:
        if t == "script" and "src" not in a:
            fail(page, "an inline <script>")
        for k, v in a.items():
            if k.startswith("on"):
                fail(page, f"an inline handler {k}= on <{t}>")
            if v and k in ("href", "src", "action", "formaction") and v.strip().lower().startswith("javascript:"):
                fail(page, f"a javascript: URL on <{t}>")
        if t == "a" and (a.get("target") or "").lower() == "_blank" and "noopener" not in (a.get("rel") or "").lower().split():
            fail(page, "a target=_blank link without rel=noopener")
    # Style attributes: only on Welcome, which must have them.
    attrs = sum(1 for _, a in p.tags if "style" in a)
    if attrs and page not in WELCOME:
        fail(page, f"{attrs} style attribute(s), and this page's policy doesn't allow them")
    if page in WELCOME and not attrs:
        fail(page, "style-src-attr 'unsafe-inline' with no style attribute to need it")
    # The form's endpoint.
    for t, a in p.tags:
        if t == "form" and a.get("data-endpoint") and a["data-endpoint"] != PROD_FUNCTION:
            fail(page, "the form's data-endpoint isn't kerja-prod's function")
    # Nothing loaded from another site.
    for t, a in p.tags:
        urls = []
        if t in ("img", "script", "source", "iframe", "embed", "audio", "video", "track"):
            urls += [a.get("src") or ""]
            urls += [u.strip().split(" ")[0] for u in (a.get("srcset") or "").split(",") if u.strip()]
        if t == "link" and set((a.get("rel") or "").lower().split()) & {"stylesheet", "preload", "icon", "apple-touch-icon", "modulepreload", "manifest"}:
            urls += [a.get("href") or ""]
        for u in urls:
            if re.match(r"^\s*(https?:)?//", u, re.I):
                fail(page, f"<{t}> loads from another site: {u.split('?')[0]}")
    # The Umami tracker: one tag, exactly these attributes, after site.js.
    scripts = [(i, a) for i, (t, a) in enumerate(p.tags) if t == "script" and a.get("src")]
    trackers = [(i, a) for i, a in scripts if a["src"].split("?")[0].endswith(UMAMI_FILE)]
    events = 0
    if len(trackers) != 1:
        fail(page, f"{len(trackers)} Umami tracker tags (one expected)")
    else:
        i, a = trackers[0]
        if not re.search(r"\?v=[0-9a-f]{8}$", a["src"]) or "defer" not in a:
            fail(page, "the tracker tag isn't a stamped, deferred script")
        site = [j for j, b in scripts if b["src"].split("?")[0].endswith("assets/site.js")]
        if not site or site[0] > i:
            fail(page, "the tracker comes before site.js, whose opt-out must run first")
        extra = sorted(set(a) - set(TRACKER_ATTRS) - {"src", "defer", "data-website-id"})
        if extra:
            fail(page, f"the tracker has other attributes: {extra}")
        for k, v in TRACKER_ATTRS.items():
            if a.get(k) != v:
                fail(page, f"the tracker's {k} is {a.get(k)!r}, not {v!r}")
        wid = a.get("data-website-id") or ""
        if not UUID.match(wid):
            fail(page, "the tracker's data-website-id isn't a UUID")
        elif wid == PLACEHOLDER_ID:
            if PUBLISH:
                fail(page, "the Umami website ID is still the placeholder (README.md, \"Website statistics\")")
            else:
                notes.add("the Umami website ID is the placeholder: replace it before publishing (README.md, \"Website statistics\")")
        elif wid != UMAMI_WEBSITE_ID:
            fail(page, f"the tracker's data-website-id isn't Kerja's Umami website ID ({UMAMI_WEBSITE_ID})")
    # The click events: Umami's attribute on buttons only (it holds links), data-count on links; known
    # names, and only short lowercase words as their data.
    for t, a in p.tags:
        if "data-umami-event" in a:
            events += 1
            if t == "a":
                fail(page, f"a link with data-umami-event={a['data-umami-event']!r}: Umami would hold the tap (use data-count)")
            elif a["data-umami-event"] not in BUTTON_EVENTS:
                fail(page, f"an unknown button event {a['data-umami-event']!r}")
        if "data-count" in a:
            events += 1
            if a["data-count"] not in LINK_EVENTS:
                fail(page, f"an unknown link event {a['data-count']!r}")
        for k, v in a.items():
            if k.startswith("data-umami-event-"):
                fail(page, f"event data {k}={v!r} isn't allowed on data-umami-event")
            if k.startswith("data-count-") and (k not in COUNT_DATA or not WORD.match(v or "") or "data-count" not in a):
                fail(page, f"event data {k}={v!r} isn't allowed")
    # The visitors' opt-out (5412): once on each Our promise page, nowhere else; two hidden <button
    # type="button">s (site.js shows them); and nothing on it, around it or in it that would send.
    lines = [i for i, (t, a) in enumerate(p.tags) if "data-optout-line" in a]
    if page in PROMISE and len(lines) != 1:
        fail(page, f"{len(lines)} opt-out lines (one expected)")
    if page not in PROMISE and lines:
        fail(page, "an opt-out line outside Our promise")
    for i in lines:
        inside = [j for j in range(len(p.tags)) if i in p.parents[j]]
        buttons = [p.tags[j] for j in inside if p.tags[j][0] == "button"]
        if sorted(a.get("data-optout") or "" for _, a in buttons) != ["count", "stop"] or any(a.get("type") != "button" or "hidden" not in a for _, a in buttons):
            fail(page, "the opt-out line needs exactly its two hidden <button type=\"button\"> (stop, count)")
        for j in p.parents[i] + [i] + inside:
            if {"data-count", "data-umami-event"} & set(p.tags[j][1]):
                fail(page, f"the opt-out would send: <{p.tags[j][0]}> on, around or in it carries data-count or data-umami-event")
    if not any(m.startswith(f"FAIL  {page}:") for m in problems):
        print(f"ok    {page}: CSP exactly as allowed, referrer {REFERRER}, {len(blocks)} inline style block(s) hashed, {attrs} style attribute(s), tracker tag as pinned, {events} click event(s)")

# kerja-dev in any published text file; stylesheets load nothing from elsewhere.
for f in FILES:
    if not f.lower().endswith(TEXT_TYPES):
        continue
    text = open(os.path.join(ROOT, f), encoding="utf-8", errors="replace").read()
    if DEV_REF.search(text):
        fail(f, "kerja-dev's project ref is in a published file")
    if f.endswith(".css"):
        for u in re.findall(r"url\(\s*['\"]?([^'\")]+)", text):
            if re.match(r"^\s*(https?:)?//", u, re.I):
                fail(f, f"url() from another site: {u}")
        if re.search(r"@import", text, re.I):
            fail(f, "@import")

# The tracker's copy: byte for byte the pinned release, never edited.
umami_path = os.path.join(ROOT, UMAMI_FILE)
if not os.path.isfile(umami_path):
    fail(UMAMI_FILE, "missing")
else:
    got = hashlib.sha256(open(umami_path, "rb").read()).hexdigest()
    if got != UMAMI_SHA256:
        fail(UMAMI_FILE, f"SHA-256 {got} isn't Umami {UMAMI_VERSION}'s {UMAMI_SHA256}: the copy may not be edited")
    else:
        print(f"ok    {UMAMI_FILE}: Umami {UMAMI_VERSION}, SHA-256 {UMAMI_SHA256}")

for line in problems:
    print(line)
for line in sorted(notes):
    print("NOTE  " + line)
print(f"checked {len(FILES)} published files: " + ("all pass" if not problems else f"{len(problems)} problem(s)"))
sys.exit(1 if problems else 0)
