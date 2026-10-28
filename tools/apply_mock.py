#!/usr/bin/env python3
"""The local preview with a mock of the beta application's function (decisions 5289, 5290).
Standard library only. For local previews: the published pages post to kerja-prod (decision 5360), and
a preview never does. Never part of a published page (tools/ isn't published).

  python3 -I tools/apply_mock.py [--port 8091] [--delay 0.6]

It serves this folder on http://127.0.0.1:<port>/ as a static server does, and answers the contract
(kerja-artifacts/beta-apply/contract.md) at /functions/v1/submit-application. In the pages it serves
(and only there: the files on disk never change), the form's data-endpoint is swapped for
http://localhost:<port>/functions/v1/submit-application, and so is kerja-prod's function in the CSP's
connect-src (the sites audit's A3), so the page's own policy lets the preview's request through.
localhost is another origin than 127.0.0.1, so the browser sends the CORS preflight, as it will to
Supabase.

The answers, as the contract's:
  OPTIONS            204, with the CORS headers for http://127.0.0.1:<any port> and http://localhost:<any port>
                     only (as kerja-dev and the local stack allow; never https://trykerja.com, decision 5300)
  an Origin header that isn't one of those, on a POST or OPTIONS
                     403 {"ok": false, "error": "origin"}, before anything else (no Origin: not refused; 5301)
  not POST/OPTIONS   405 {"ok": false, "error": "method"}
  honeypot filled    200 {"ok": true} (dropped, as the function drops it)
  a field wrong      400 {"ok": false, "error": "invalid", "fields": [...]}
  valid              200 {"ok": true}, the same for an email already sent (nothing is stored on disk)
And, to show the other states, by the email's local part (a valid email otherwise):
  toomany@...        429 {"ok": false, "error": "too_many"}
  origin@...         403 {"ok": false, "error": "origin"} (with CORS headers, so the page can read it)
  broken@...         500 {"ok": false, "error": "server"}
  offline@...        the connection closes with no answer (as if the network dropped)

It logs each call's status and the names of the fields it refused; never what anyone typed."""
import argparse
import http.server
import json
import os
import re
import socketserver
import sys
import time
from urllib.parse import urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = "/functions/v1/submit-application"
ORIGIN_OK = re.compile(r"^http://(127\.0\.0\.1|localhost)(:\d{1,5})?$")
ENDPOINT_ATTR = re.compile(r'data-endpoint="[^"]*"')
CSP_META = re.compile(r'(<meta http-equiv="Content-Security-Policy" content=")([^"]*)(")', re.I)
PROD_FUNCTION = "https://eppqufcgcwhoprwzfhxy.supabase.co/functions/v1/submit-application"

URLISH = re.compile(r"(://|www\.|\b[a-z0-9-]+\.(com|net|org|io|co|id|me|app|ly|xyz|info|link)\b)", re.I)
EMAIL = re.compile(r"^[^\s@]+@[^\s@.]+(\.[^\s@.]+)+$")
HANDLE = re.compile(r"^@[A-Za-z0-9._]{1,30}$")
PROFILE = re.compile(r"^https?://([a-z0-9-]+\.)*(instagram\.com|linkedin\.com)/\S+$", re.I)
FITS = {"founder", "content_creator", "freelancer", "other"}
STAY = {"just_arrived", "one_to_three_months", "live_here"}


def refused(b):
    """The contract's fields that are wrong, by key, in the contract's order."""
    bad = []
    s = lambda k: b.get(k) if isinstance(b.get(k), str) else None
    if b.get("lang") not in ("en", "id"):
        bad.append("lang")
    fn = (s("first_name") or "").strip()
    if not (1 <= len(fn) <= 40) or "\n" in fn or "\r" in fn or URLISH.search(fn):
        bad.append("first_name")
    em = (s("email") or "").strip()
    if len(em) > 254 or not EMAIL.match(em):
        bad.append("email")
    if b.get("fits") not in FITS:
        bad.append("fits")
    if b.get("stay") not in STAY:
        bad.append("stay")
    if b.get("link") not in (None, ""):
        ln = s("link")
        if ln is None or len(ln) > 200 or not (HANDLE.match(ln.strip()) or PROFILE.match(ln.strip())):
            bad.append("link")
    if b.get("work_on") not in (None, ""):
        wo = s("work_on")
        if wo is None or len(wo.strip()) > 140 or "\n" in wo or "\r" in wo:
            bad.append("work_on")
    if b.get("adult") is not True:
        bad.append("adult")
    if b.get("privacy") is not True:
        bad.append("privacy")
    return bad


def mock_connect(policy, mock):
    """The CSP with kerja-prod's function swapped for the mock's in connect-src, and nothing else changed."""
    out = []
    for d in policy.split(";"):
        if d.split() and d.split()[0].lower() == "connect-src":
            d = d.replace(PROD_FUNCTION, mock)
        out.append(d)
    return ";".join(out)


class Handler(http.server.SimpleHTTPRequestHandler):
    delay = 0.0
    port = 8091
    seen = set()

    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, fmt, *args):
        pass

    def note(self, status, extra=""):
        sys.stderr.write(f"{time.strftime('%H:%M:%S')} {self.command} {urlsplit(self.path).path} {status}{extra}\n")

    def cors(self):
        o = self.headers.get("Origin", "")
        if ORIGIN_OK.match(o):
            self.send_header("Access-Control-Allow-Origin", o)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def answer(self, status, body, extra=""):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)
        self.note(status, extra)

    def is_fn(self):
        return urlsplit(self.path).path.rstrip("/") == PATH

    def bad_origin(self):
        o = self.headers.get("Origin")
        return o is not None and not ORIGIN_OK.match(o)

    # The function.
    def do_OPTIONS(self):
        if not self.is_fn():
            return self.answer(405, {"ok": False, "error": "method"})
        if self.bad_origin():
            return self.answer(403, {"ok": False, "error": "origin"}, " (origin not allowed)")
        self.send_response(204)
        self.cors()
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()
        self.note(204)

    def do_POST(self):
        if not self.is_fn():
            return self.answer(405, {"ok": False, "error": "method"})
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        if self.bad_origin():
            return self.answer(403, {"ok": False, "error": "origin"}, " (origin not allowed)")
        time.sleep(self.delay)
        try:
            b = json.loads(raw or b"null")
        except ValueError:
            b = None
        if not isinstance(b, dict):
            return self.answer(400, {"ok": False, "error": "invalid", "fields": []})
        if isinstance(b.get("website"), str) and b["website"].strip():
            return self.answer(200, {"ok": True}, " (honeypot: dropped)")
        bad = refused(b)
        if bad:
            return self.answer(400, {"ok": False, "error": "invalid", "fields": bad}, " " + ",".join(bad))
        email = b["email"].strip().lower()
        local = email.split("@", 1)[0]
        if local == "toomany":
            return self.answer(429, {"ok": False, "error": "too_many"})
        if local == "origin":
            return self.answer(403, {"ok": False, "error": "origin"})
        if local == "broken":
            return self.answer(500, {"ok": False, "error": "server"})
        if local == "offline":
            self.note("dropped")
            self.close_connection = True
            self.connection.shutdown(2)
            return
        again = email in self.seen
        self.seen.add(email)
        return self.answer(200, {"ok": True}, " (again: no second auto-reply)" if again else "")

    def do_PUT(self):
        self.answer(405, {"ok": False, "error": "method"})

    do_DELETE = do_PATCH = do_PUT

    # The site: the files as they are, but the form's endpoint is the mock's.
    def do_GET(self):
        if self.is_fn():
            return self.answer(405, {"ok": False, "error": "method"})
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        if path.endswith(".html") and os.path.isfile(path) and urlsplit(self.path).path.endswith(("/", ".html")):
            html = open(path, encoding="utf-8").read()
            mock = f"http://localhost:{self.port}{PATH}"
            html = ENDPOINT_ATTR.sub(f'data-endpoint="{mock}"', html)
            html = CSP_META.sub(lambda m: m.group(1) + mock_connect(m.group(2), mock) + m.group(3), html)
            data = html.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            return
        return super().do_GET()

    def do_HEAD(self):
        if self.is_fn():
            return self.answer(405, {"ok": False, "error": "method"})
        return super().do_HEAD()


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--port", type=int, default=8091)
    ap.add_argument("--delay", type=float, default=0.6, help="seconds before the function answers (default 0.6)")
    a = ap.parse_args()
    Handler.delay, Handler.port = a.delay, a.port
    with Server(("127.0.0.1", a.port), Handler) as httpd:
        sys.stderr.write(f"preview http://127.0.0.1:{a.port}/  mock function http://localhost:{a.port}{PATH}\n")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
