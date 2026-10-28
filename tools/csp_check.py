#!/usr/bin/env python3
"""Checks every page's Content-Security-Policy and referrer meta tags against the page itself.
Standard library only; reads the pages, changes nothing.

  python3 -I tools/csp_check.py [<site folder>]   (this repo by default)

Fails (exit 1) when a page:
- misses the CSP or referrer meta, or has a resource tag (link, script, style, img) before them;
- loosens what README.md's "Security" part allows: default-src other than 'self'; 'unsafe-eval'
  anywhere; 'unsafe-inline' in script-src or style-src; no base-uri 'none', object-src 'none' or
  form-action;
- has an inline <style> whose SHA-256 isn't in style-src, or a hash in style-src no block matches;
- has an inline script, an on* handler or a javascript: URL;
- has style="" attributes without style-src-attr 'unsafe-inline', or that allowance with no attribute;
- names kerja-dev (its project ref) in the CSP or anywhere in the page, or has a form whose
  data-endpoint the CSP's connect-src doesn't allow;
- loads anything from another site (src, srcset, stylesheet, preload or icon href), or in a stylesheet
  (url() or @import);
- has a target="_blank" link without rel="noopener".
"""
import base64
import hashlib
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEV_REF = "oiyjmnsaqefrpfrbopjy"  # kerja-dev's project ref: never on a published page (decision 5300)
RESOURCE_TAGS = ("link", "script", "style", "img", "picture", "source")


def files(pattern):
    out = subprocess.run(["git", "-C", ROOT, "ls-files", pattern], capture_output=True, text=True, check=True)
    return [f for f in out.stdout.split() if f]


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []  # (tag, attrs dict, position index)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    handle_startendtag = handle_starttag


def parse_csp(value):
    policy = {}
    for part in value.split(";"):
        bits = part.split()
        if bits:
            policy[bits[0].lower()] = bits[1:]
    return policy


def allowed(sources, url):
    for s in sources:
        if s.startswith("'"):
            continue
        if url == s or (s.endswith("/") and url.startswith(s)) or ("/" not in s.split("://", 1)[-1] and url.startswith(s + "/")):
            return True
    return False


problems = []


def fail(page, msg):
    problems.append(f"FAIL  {page}: {msg}")


for page in files("*.html"):
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
    first_resource = next((i for i, (t, _) in enumerate(p.tags) if t in RESOURCE_TAGS), len(p.tags))
    if csp_tags[0][0] > first_resource or (ref_tags and ref_tags[0][0] > first_resource):
        fail(page, "a resource tag comes before the CSP or referrer meta")
    csp = parse_csp(csp_tags[0][1].get("content", ""))
    if csp.get("default-src") != ["'self'"]:
        fail(page, "default-src isn't 'self'")
    for d, v in csp.items():
        if "'unsafe-eval'" in v:
            fail(page, f"'unsafe-eval' in {d}")
    for d in ("script-src", "style-src", "default-src"):
        if "'unsafe-inline'" in csp.get(d, []):
            fail(page, f"'unsafe-inline' in {d}")
    for d, want in (("base-uri", ["'none'"]), ("object-src", ["'none'"])):
        if csp.get(d) != want:
            fail(page, f"{d} isn't 'none'")
    if "form-action" not in csp:
        fail(page, "no form-action")
    # Inline styles: each block's hash in style-src, and no hash left over.
    blocks = re.findall(r"<style[^>]*>(.*?)</style>", src, re.S)
    hashes = {"'sha256-" + base64.b64encode(hashlib.sha256(b.encode("utf-8")).digest()).decode() + "'" for b in blocks}
    listed = {s for s in csp.get("style-src", []) if s.startswith("'sha")}
    for h in sorted(hashes - listed):
        fail(page, f"an inline <style> whose hash {h} isn't in style-src")
    for h in sorted(listed - hashes):
        fail(page, f"style-src lists {h}, which no inline <style> on the page matches")
    # Scripts and handlers.
    for t, a in p.tags:
        if t == "script" and "src" not in a:
            fail(page, "an inline <script>")
        for k, v in a.items():
            if k.startswith("on"):
                fail(page, f"an inline handler {k}= on <{t}>")
            if v and k in ("href", "src", "action", "formaction") and v.strip().lower().startswith("javascript:"):
                fail(page, f"a javascript: URL on <{t}>")
        if t == "a" and (a.get("target") or "").lower() == "_blank" and "noopener" not in (a.get("rel") or ""):
            fail(page, "a target=_blank link without rel=noopener")
    # Style attributes.
    attrs = sum(1 for _, a in p.tags if "style" in a)
    loose = "'unsafe-inline'" in csp.get("style-src-attr", [])
    if attrs and not loose:
        fail(page, f"{attrs} style attributes, and no style-src-attr 'unsafe-inline'")
    if loose and not attrs:
        fail(page, "style-src-attr 'unsafe-inline' with no style attribute to need it")
    # kerja-dev, and the form's endpoint.
    if DEV_REF in src:
        fail(page, "kerja-dev's project ref is in the page")
    for t, a in p.tags:
        if t == "form" and a.get("data-endpoint") and not allowed(csp.get("connect-src", []), a["data-endpoint"]):
            fail(page, "the form's data-endpoint isn't allowed by connect-src")
    # Nothing loaded from another site.
    for t, a in p.tags:
        urls = []
        if t in ("img", "script", "source", "iframe", "embed", "audio", "video", "track"):
            urls += [a.get("src") or ""]
            urls += [u.strip().split(" ")[0] for u in (a.get("srcset") or "").split(",") if u.strip()]
        if t == "link" and set((a.get("rel") or "").lower().split()) & {"stylesheet", "preload", "icon", "apple-touch-icon", "modulepreload", "manifest"}:
            urls += [a.get("href") or ""]
        for u in urls:
            if re.match(r"^(https?:)?//", u):
                fail(page, f"<{t}> loads from another site: {u.split('?')[0]}")
    if not any(m.startswith(f"FAIL  {page}:") for m in problems):
        print(f"ok    {page}: CSP, referrer ({ref_tags[0][1].get('content') if ref_tags else '-'}), "
              f"{len(blocks)} inline style block(s) hashed, {attrs} style attribute(s)")

for css in files("*.css"):
    text = open(os.path.join(ROOT, css), encoding="utf-8").read()
    for u in re.findall(r"url\(\s*['\"]?([^'\")]+)", text):
        if re.match(r"^(https?:)?//", u):
            fail(css, f"url() from another site: {u}")
    if re.search(r"@import", text):
        fail(css, "@import")

for line in problems:
    print(line)
print("all pages pass" if not problems else f"{len(problems)} problem(s)")
sys.exit(1 if problems else 0)
