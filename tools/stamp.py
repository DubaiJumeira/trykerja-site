#!/usr/bin/env python3
"""Cache-busting for the site (decision 5225): every picture URL (img/source src and every srcset
candidate) and every stylesheet and script URL gets ?v=<first 8 of the file's SHA-256>, so a changed
file always has a new URL and no browser can keep an old copy.

  python3 -I tools/stamp.py           rewrite the pages' URLs from the files as they are now
  python3 -I tools/stamp.py --check   change nothing; list every URL and fail if one is stale or missing

Run it after any picture, stylesheet or script changes. Fonts are left alone (the stylesheets load them)."""
import hashlib, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES = ["index.html", "how-it-works/index.html", "promise/index.html", "download/index.html", "404.html",
         "id/index.html", "id/how-it-works/index.html", "id/promise/index.html", "id/download/index.html"]
CHECK = "--check" in sys.argv

def digest(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]

def resolve(page, url):
    base = url.split("?", 1)[0].split("#", 1)[0]
    if base.startswith("/"):
        return os.path.join(ROOT, base.lstrip("/"))
    return os.path.normpath(os.path.join(ROOT, os.path.dirname(page), base))

problems, listed = [], []

def stamp(page, url):
    if re.match(r"(data:|https?:|mailto:|#)", url):
        return url
    path = resolve(page, url)
    if not os.path.isfile(path):
        problems.append(f"{page}: missing {url}")
        return url
    want = url.split("?", 1)[0] + "?v=" + digest(path)
    listed.append((page, want, "ok" if url == want else "STALE"))
    if url != want:
        problems.append(f"{page}: stale {url} (want {want})")
    return want

def srcset(page, value):
    out = []
    for cand in value.split(","):
        parts = cand.strip().split()
        if parts:
            out.append(" ".join([stamp(page, parts[0])] + parts[1:]))
    return ", ".join(out)

TAG = re.compile(r"<(img|source|link|script)\b[^>]*>", re.S)

for page in PAGES:
    p = os.path.join(ROOT, page)
    html = open(p, encoding="utf-8").read()
    def fix(m):
        tag = m.group(0); name = m.group(1)
        if name == "link" and not re.search(r'rel="stylesheet"', tag):
            return tag
        if name in ("img", "source", "script"):
            tag = re.sub(r'\ssrc="([^"]*)"', lambda a: f' src="{stamp(page, a.group(1))}"', tag)
        if name in ("img", "source"):
            tag = re.sub(r'\ssrcset="([^"]*)"', lambda a: f' srcset="{srcset(page, a.group(1))}"', tag)
        if name == "link":
            tag = re.sub(r'\shref="([^"]*)"', lambda a: f' href="{stamp(page, a.group(1))}"', tag)
        return tag
    new = TAG.sub(fix, html)
    if not CHECK and new != html:
        open(p, "w", encoding="utf-8").write(new)

if CHECK:
    for page, url, state in listed:
        print(f"{state:5} {page}: {url}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        sys.exit(1)
    print(f"all {len(listed)} URLs current")
else:
    missing = [x for x in problems if "missing" in x]
    if missing:
        print("\n".join(missing), file=sys.stderr)
        sys.exit(1)
    print("stamped")
