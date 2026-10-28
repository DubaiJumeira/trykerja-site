#!/usr/bin/env python3
"""Checks every published page's Content-Security-Policy and referrer tags, and every published file
for kerja-dev. Standard library only; reads files, changes nothing; needs no git checkout.

  python3 -I tools/csp_check.py [<site folder>]   (this repo by default)

It walks the folder and checks what GitHub Pages would publish (everything with a .nojekyll file;
otherwise all but names starting with "." or "_" and the `exclude:` list of _config.yml).

Fails (exit 1) when a page:
- hasn't exactly one CSP meta and one referrer meta, before any link, script, style or img tag;
- has a referrer other than exactly "no-referrer";
- has a CSP that isn't exactly the one README.md's "Security" part gives for it (directives in that
  order, whitespace aside): the base policy, with the SHA-256 of each of the page's own inline
  <style> blocks in style-src (none listed when it has none); plus style-src-attr 'unsafe-inline'
  on Welcome (index.html, id/index.html) only; and on Join the beta (download/index.html,
  id/download/index.html) only, kerja-prod's function after connect-src 'self'. So any other
  source, keyword or directive fails (https:, data: or * in script-src, script-src-attr,
  style-src-elem, 'unsafe-eval', form-action *, a missing directive…);
- has an inline script, an on…= attribute or a javascript: URL;
- has style="" attributes on a page whose policy doesn't allow them, or Welcome's allowance with no
  style attribute to need it;
- has a form whose data-endpoint isn't kerja-prod's function;
- loads anything from another site (src, srcset, a stylesheet, preload, icon or manifest href);
- has a target="_blank" link without rel="noopener".
And when any published text file (HTML, JS, CSS, SVG, XML, JSON, TXT) names kerja-dev's project ref,
in any case, or a published stylesheet loads from another site (url()) or uses @import.
"""
import base64
import hashlib
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEV_REF = re.compile(r"oiyjmnsaqefrpfrbopjy", re.I)  # kerja-dev's project ref: never published (decision 5300)
PROD_FUNCTION = "https://eppqufcgcwhoprwzfhxy.supabase.co/functions/v1/submit-application"  # kerja-prod's
WELCOME = {"index.html", "id/index.html"}
JOIN = {"download/index.html", "id/download/index.html"}
REFERRER = "no-referrer"
RESOURCE_TAGS = ("link", "script", "style", "img", "picture", "source")
TEXT_TYPES = (".html", ".htm", ".js", ".mjs", ".css", ".svg", ".xml", ".json", ".txt", ".webmanifest")


def expected_csp(page, style_hashes):
    connect = "'self'" + (" " + PROD_FUNCTION if page in JOIN else "")
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


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    handle_startendtag = handle_starttag


problems = []


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
    if not any(m.startswith(f"FAIL  {page}:") for m in problems):
        print(f"ok    {page}: CSP exactly as allowed, referrer {REFERRER}, {len(blocks)} inline style block(s) hashed, {attrs} style attribute(s)")

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

for line in problems:
    print(line)
print(f"checked {len(FILES)} published files: " + ("all pass" if not problems else f"{len(problems)} problem(s)"))
sys.exit(1 if problems else 0)
