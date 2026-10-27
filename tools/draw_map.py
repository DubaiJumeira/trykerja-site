#!/usr/bin/env python3
"""Draws the Welcome page's map story (decisions 5230, 5249, 5250, 5256): the flat map of Canggu
(assets/story/canggu-map.svg) from OpenStreetMap data, the café pins laid over it in index.html as
the app's map draws them when it opens, and the image that holds the cafés' names.

  python3 -I tools/draw_map.py <overpass.json> <canggu-cafes.csv>
  python3 -I tools/stamp.py

<overpass.json> is the one Overpass API download for the box lon 115.112 to 115.160, lat -8.672 to
-8.626 (roads, the coastline, water). The raw data is ODbL and stays out of this repo (it is kept
with its query and download time in kerja-artifacts/build-12/scroll-story/osm/); only this script
and the map it draws (a Produced Work) are committed. The page shows "© OpenStreetMap contributors",
linked to https://www.openstreetmap.org/copyright, whenever any part of the map is on screen.
<canggu-cafes.csv> is the app's café list (docs/data/canggu-cafes.csv in the app repo). The names'
image needs headless Chrome (CHROME, Google Chrome's path by default) and cwebp.

The view is the app's opening view: zoom 15 (STREET_ZOOM, where the cafés' names show) in the app's
projection (Web Mercator with 512-point tiles, src/components/map/pinLayout.ts's project), a 640 x
620 window centred on CENTRE, inside the box. It holds the two cafés with faces that fit together at
this zoom (5256) and as many others as fit with them. 1 CSS px is 1 app point on the full map.

The drawing, in the app's own map colours (src/components/map/mapStyle.ts): land in sand
(creamDeep), lakes and streams in lagoon at 35% (streams 1.5 pt, the app's width at zoom 15; the
sea when the window reaches it), main roads 12 pt of cream between two 1 pt ink 12% edges (the app's
width at zoom 15), and the residential and unclassified roads over about 200 m thin and plain, for
the shape. No names, no cafés or other places, no buildings, no paths, lanes or service roads.

The pins (index.html and id/index.html, between the "pins" comments; welcome.css draws them): every café of the app's
list whose point is inside the window, with the people the site places there (PEOPLE, cast v3
only). Which pins are drawn, and which are counted into another's "+N" badge, is the app's own rule,
ported below from pinLayout.ts (layoutPins, pinFootprint, faceSlots, pillWidth, labelWidth) and run,
as the app runs it, on every café of the list. The pins are hidden from screen readers, and the
cafés' names are never page text: they are drawn into assets/story/pin-names-2x.webp and -3x.webp
(one 148 x 20 row per café, captionStrong with its halo, by headless Chrome). The map is shown
narrower than 640 px on narrow or short screens: the pins keep their size, the map's scale changes,
and the rule runs again for that scale. It is run here for every width down to MIN_WIDTH; wherever
what the window shows changes, welcome.css gets a container query (between the "pins" comments
there) that hides or shows those pins and sets those badges. The names stay at every width.
Colours are read from assets/site.css (:root), which takes them from the app's tokens."""
import csv, html, json, math, os, re, sys, unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "story", "canggu-map.svg")
# Welcome in English and in Indonesian (/id/, decision 5275): the same pins in both, the Indonesian
# page one folder down, so its pictures' paths start with "../".
PAGES = [("index.html", ""), ("id/index.html", "../")]
CSS = os.path.join(ROOT, "assets", "welcome.css")

# The box of the OSM download (west, south, east, north); the window stays inside it.
WEST, SOUTH, EAST, NORTH = 115.112, -8.672, 115.160, -8.626
# The app's projection and opening zoom (pinLayout.ts: TILE, STREET_ZOOM).
TILE = 512
ZOOM = 15
# The window: its centre (longitude, latitude) and its size in points (CSS px on the full map).
CENTRE = (115.13729, -8.64814)
W, H = 640, 620
# The narrowest map the pins' rule is run for (the map is 640 px wide on most desktop screens and
# 553 px at 1024 px wide; it is narrower only in short windows).
MIN_WIDTH = 240

# Who is working where (decisions 5249, 5250 and 5256): cast v3 only, each person at one café, one
# café with four people so the app's "+N" shows; faces only at Miel Specialty Coffee and B Work Bali
# (the window holds both) and one more café. Their faces are assets/story/face-<first name>-2x.webp
# and -3x.webp (26 pt at 2x and 3x: the cast-v3 portrait, whole, as the app's Avatar shows it).
PEOPLE = {
    "B Work Bali": ["Daria Novak", "Elena Castell", "Nico Albers", "Tobias Lund"],
    "Miel Specialty Coffee": ["Amira Khalil"],
    "Barboa Bali": ["Imani Brooks"],
}
# The cafés' names are drawn into an image (decision 5256: never page text): one row per name, in
# the app's label style, rendered by headless Chrome at 2x and 3x and saved as WebP.
NAMES = os.path.join(ROOT, "assets", "story", "pin-names")
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# Road classes and how each is drawn: (width in px, with an edge or not, shortest line kept in px).
ROADS = [
    ("residential", {"residential"}, 2.0, False, 85),
    ("unclassified", {"unclassified"}, 3.0, False, 0),
    ("major", {"motorway", "trunk", "primary", "secondary", "tertiary",
               "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"}, 12, True, 0),
]
EDGE = 1            # the main roads' edge on each side, in px
RIVERS = {"river": 1.5, "stream": 1.5, "tidal_channel": 1.5, "canal": 1.5}
TOLERANCE = 0.3     # Douglas-Peucker tolerance in px


def world(lon, lat):
    """pinLayout.ts's project(): a coordinate in points of the whole world at ZOOM."""
    size = TILE * 2 ** ZOOM
    phi = math.radians(lat)
    return ((lon + 180) / 360 * size, (1 - math.log(math.tan(math.pi / 4 + phi / 2)) / math.pi) / 2 * size)


CX, CY = world(*CENTRE)
LEFT, TOP = CX - W / 2, CY - H / 2


def to_window(lon, lat):
    x, y = world(lon, lat)
    return (x - LEFT, y - TOP)


def check_window():
    bx0, by0 = world(WEST, NORTH)
    bx1, by1 = world(EAST, SOUTH)
    if not (bx0 <= LEFT and LEFT + W <= bx1 and by0 <= TOP and TOP + H <= by1):
        raise SystemExit("the window is not inside the box of the download")


def tokens():
    css = open(os.path.join(ROOT, "assets", "site.css"), encoding="utf-8").read()
    root = css.split("}", 1)[0]
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})", root))


def project(geom):
    return [to_window(p["lon"], p["lat"]) for p in geom]


def simplify(pts, tol=TOLERANCE):
    if len(pts) < 3:
        return pts
    keep = [False] * len(pts)
    keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1
        n = math.hypot(dx, dy) or 1e-9
        best, bi = -1.0, -1
        for i in range(a + 1, b):
            x, y = pts[i]
            d = abs(dy * (x - x1) - dx * (y - y1)) / n
            if d > best:
                best, bi = d, i
        if best > tol:
            keep[bi] = True
            stack += [(a, bi), (bi, b)]
    return [p for p, k in zip(pts, keep) if k]


M = 16  # margin around the window, in px, so lines (the main roads are 14 px with their edges) run off cleanly


def inside(p):
    return -M <= p[0] <= W + M and -M <= p[1] <= H + M


def runs(pts):
    """Splits a line into the runs that touch the window (with its margin)."""
    out, cur = [], []
    for i, p in enumerate(pts):
        near = inside(p) or (i > 0 and inside(pts[i - 1])) or (i + 1 < len(pts) and inside(pts[i + 1]))
        if near:
            cur.append(p)
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return [r for r in out if len(r) > 1]


def path(lines):
    """One path's d: each line as an absolute move, then relative steps at 0.1 px."""
    parts = []
    for line in lines:
        q = [(round(x * 10), round(y * 10)) for x, y in line]
        seg = [f"M{q[0][0] / 10:g} {q[0][1] / 10:g}"]
        steps = []
        for (x0, y0), (x1, y1) in zip(q, q[1:]):
            if (x1, y1) != (x0, y0):
                steps.append(f"{(x1 - x0) / 10:g} {(y1 - y0) / 10:g}")
        if not steps:
            continue
        seg.append("l" + " ".join(steps).replace(" -", "-"))
        parts.append("".join(seg))
    return "".join(parts)


def clip(poly, edge):
    """Sutherland-Hodgman against one edge of the window: edge = (axis, value, keep_greater)."""
    axis, v, greater = edge
    def ins(p):
        return p[axis] >= v if greater else p[axis] <= v
    def cross(a, b):
        t = (v - a[axis]) / (b[axis] - a[axis])
        return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
    out = []
    for i, cur in enumerate(poly):
        prev = poly[i - 1]
        if ins(cur):
            if not ins(prev):
                out.append(cross(prev, cur))
            out.append(cur)
        elif ins(prev):
            out.append(cross(prev, cur))
    return out


def clip_box(poly):
    for edge in [(0, 0, True), (0, W, False), (1, 0, True), (1, H, False)]:
        poly = clip(poly, edge)
        if not poly:
            break
    return poly


def coast_chain(ways):
    """Joins the coastline's ways end to end (OSM coastlines run with the land on their left)."""
    ways = [w["geometry"] for w in ways]
    chain = ways.pop(0)
    changed = True
    while ways and changed:
        changed = False
        for w in list(ways):
            if (w[0]["lat"], w[0]["lon"]) == (chain[-1]["lat"], chain[-1]["lon"]):
                chain = chain + w[1:]
            elif (w[-1]["lat"], w[-1]["lon"]) == (chain[0]["lat"], chain[0]["lon"]):
                chain = w[:-1] + chain
            else:
                continue
            ways.remove(w)
            changed = True
    if ways:
        raise SystemExit(f"coastline: {len(ways)} way(s) did not join")
    return chain


def draw_map(els):
    t = tokens()
    sand, cream, ink, lagoon = t["sand"], t["cream"], t["ink"], t["lagoon"]

    # The sea: the coastline (land on its left, so the sea is to its right, south-west here),
    # closed far out to the south-west, then cut to the window.
    coast = coast_chain([e for e in els if e["type"] == "way" and e.get("tags", {}).get("natural") == "coastline"])
    cpts = project(coast)
    x0, y0 = cpts[0]
    x1, y1 = cpts[-1]
    far = [(x1, H + 8000), (-8000, H + 8000), (-8000, y0)]
    sea = clip_box(cpts + far)
    sea = simplify(sea, 0.2)  # an open ring: its first and last points differ, poly_d closes it

    # Lakes and ponds (natural=water, ways and multipolygon relations' outer rings).
    lakes = []
    for e in els:
        tg = e.get("tags", {})
        if tg.get("natural") != "water":
            continue
        rings = [e["geometry"]] if e["type"] == "way" else [m["geometry"] for m in e.get("members", []) if m.get("role") == "outer" and m.get("geometry")]
        for r in rings:
            p = clip_box(project(r))
            if len(p) > 2:
                lakes.append(simplify(p))

    rivers = {}
    for e in els:
        tg = e.get("tags", {})
        k = tg.get("waterway")
        if e["type"] == "way" and k in RIVERS:
            for r in runs(project(e["geometry"])):
                rivers.setdefault(k, []).append(simplify(r))

    roads = {name: [] for name, *_ in ROADS}
    for e in els:
        hw = e.get("tags", {}).get("highway")
        if e["type"] != "way" or not hw:
            continue
        for name, classes, _, _, shortest in ROADS:
            if hw in classes:
                line = project(e["geometry"])
                if sum(math.dist(a, b) for a, b in zip(line, line[1:])) < shortest:
                    continue
                for r in runs(line):
                    roads[name].append(simplify(r))

    def poly_d(p):
        q = [(round(x * 10) / 10, round(y * 10) / 10) for x, y in p]
        return path([q + [q[0]]]) + "z"

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        f"<!-- Canggu, from Batu Bolong to Berawa, at zoom 15. Map data © OpenStreetMap contributors (ODbL), "
        f"https://www.openstreetmap.org/copyright. Drawn by tools/draw_map.py. -->",
        f'<rect width="{W}" height="{H}" fill="{sand}"/>',
        f'<g fill="{lagoon}" fill-opacity=".35">'
        + "".join(f'<path d="{poly_d(p)}"/>' for p in ([sea] if len(sea) > 2 else []) + lakes) + "</g>",
        f'<g fill="none" stroke="{lagoon}" stroke-opacity=".35" stroke-linecap="round" stroke-linejoin="round">'
        + "".join(f'<path stroke-width="{RIVERS[k]:g}" d="{path(v)}"/>' for k, v in rivers.items()) + "</g>",
        f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">',
    ]
    for name, classes, width, edge, _ in ROADS:
        d = path(roads[name])
        if not d:
            continue
        if edge:
            out.append(f'<path stroke="{ink}" stroke-opacity=".12" stroke-width="{width + 2 * EDGE:g}" d="{d}"/>')
        out.append(f'<path stroke="{cream}" stroke-width="{width:g}" d="{d}"/>')
    out.append("</g></svg>")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    svg = "\n".join(out) + "\n"
    open(OUT, "w", encoding="utf-8").write(svg)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {W} x {H}, {len(svg):,} bytes; "
          + ", ".join(f"{k} {len(v)}" for k, v in roads.items()) + f"; rivers {sum(len(v) for v in rivers.values())}; lakes {len(lakes)}")


# ---------- The pins: pinLayout.ts's geometry and rule, ported ----------

PILL_HEIGHT = 36
PILL_PAD_LEFT = 9
PILL_PAD_RIGHT = 5
CUP_WIDTH = 16
CUP_GAP = 6
QUIET = 34
POINTER_HEIGHT = 7
POINTER_OVERLAP = 1
QUIET_POINTER_HEIGHT = 6
FACE = 26
FACE_OVERLAP = 6
MAX_FACES = 3
MORE_CHARACTER = 6.5
MORE_PAD = 8
LABEL_GAP = 2
LABEL_HEIGHT = 14
LABEL_CHARACTER = 6.0
LABEL_MAX = 140
PIN_GAP = 2


def face_slots(count, listed):
    """faceSlots(): how a count splits into faces, blank circles and the "+N" after them."""
    faces = min(MAX_FACES, listed, count)
    blanks = min(MAX_FACES - faces, max(0, count - listed))
    return faces, blanks, max(0, count - faces - blanks)


def faces_width(count):
    if count <= 0:
        return 0
    circles = min(MAX_FACES, count)
    more = count - circles
    more_width = max(FACE, MORE_PAD * 2 + MORE_CHARACTER * len(f"+{more}")) if more > 0 else 0
    return FACE + (circles - 1) * (FACE - FACE_OVERLAP) + (more_width - FACE_OVERLAP if more > 0 else 0)


def pill_width(count):
    return PILL_PAD_LEFT + CUP_WIDTH + CUP_GAP + faces_width(count) + PILL_PAD_RIGHT


def label_width(name):
    return min(LABEL_MAX, math.ceil(len(name.strip()) * LABEL_CHARACTER))


def pointer_drop(count):
    return POINTER_HEIGHT - POINTER_OVERLAP if count > 0 else QUIET_POINTER_HEIGHT


def footprint(pin):
    """pinFootprint(): what a pin covers, from its tip (never selected: the site has no selection)."""
    body = pill_width(pin["count"]) if pin["count"] > 0 else QUIET
    half = max(body / 2, label_width(pin["name"]) / 2 if pin["labelled"] else 0)
    height = (PILL_HEIGHT if pin["count"] > 0 else QUIET) + pointer_drop(pin["count"])
    return (-half, -height, half, LABEL_GAP + LABEL_HEIGHT if pin["labelled"] else 0)


def locale_key(name):
    # String.prototype.localeCompare for these names: case and accents only matter last.
    base = "".join(c for c in unicodedata.normalize("NFD", name) if unicodedata.category(c) != "Mn")
    return (base.casefold(), name)


def placement_order(pins):
    # layoutPins(): every café with people (most people first, then by name), then the quiet ones.
    order = sorted(pins, key=lambda p: (-p["count"], locale_key(p["name"])))
    return [p for p in order if p["count"] > 0] + [p for p in order if p["count"] == 0]


def layout(pins, scale):
    """layoutPins() with no selection and no area labels, at the map's scale (1 at 640 px):
    {each drawn pin's name: [the names of the pins it counts in its "+N"]}."""
    placed, shown = [], {}
    for pin in placement_order(pins):
        x, y = pin["x"] * scale, pin["y"] * scale
        l, t, r, b = footprint(pin)
        rect = (x + l - PIN_GAP, y + t - PIN_GAP, x + r + PIN_GAP, y + b + PIN_GAP)
        under = next((name for name, p in placed
                      if p[0] < rect[2] and rect[0] < p[2] and p[1] < rect[3] and rect[1] < p[3]), None)
        if under:
            shown[under].append(pin["name"])
            continue
        placed.append((pin["name"], rect))
        shown[pin["name"]] = []
    return shown


def first(name):
    return name.split()[0].lower()


def all_cafes(csv_path):
    """Every café of the app's list, at its point on the full map (the window's points)."""
    pins = []
    for row in csv.DictReader(open(csv_path, encoding="utf-8")):
        x, y = to_window(float(row["longitude"]), float(row["latitude"]))
        # cafeSheet.ts's order with no viewer (no good fits): by name, lower case.
        people = sorted(PEOPLE.get(row["name"], []), key=str.lower)
        pins.append({"name": row["name"], "x": x, "y": y, "count": len(people), "people": people, "labelled": True})
    unknown = set(PEOPLE) - {p["name"] for p in pins}
    if unknown:
        raise SystemExit(f"people placed at cafés not in the list: {sorted(unknown)}")
    return pins


def in_window(pin):
    return 0 <= pin["x"] <= W and 0 <= pin["y"] <= H


def bands(pins):
    """The rule's result (run on every café, as the app runs it) at every map width from W down
    to MIN_WIDTH, as [(below this width, result)], the first entry being the full map's."""
    def at(width):
        return layout(pins, width / W)
    out = [(W + 1, at(W))]
    width = W
    while width > MIN_WIDTH:
        nxt = width - 0.5
        if at(nxt) != out[-1][1]:
            hi, lo = width, nxt          # the change lies between these two widths
            for _ in range(30):
                mid = (hi + lo) / 2
                if at(mid) == out[-1][1]:
                    hi = mid
                else:
                    lo = mid
            out.append((math.floor(hi * 100) / 100, at(nxt)))
        width = nxt
    return out


def render_names(names):
    """The names' image: one 148 x 20 row per name (the 140 pt label with room for its halo), drawn
    by headless Chrome with the site's own Jakarta Bold, at 2x and 3x, as lossless WebP."""
    import base64, shutil, subprocess, tempfile
    t = tokens()
    font = base64.b64encode(open(os.path.join(ROOT, "assets", "fonts", "jakarta-700.woff2"), "rb").read()).decode()
    rows = "".join(f"<div>{html.escape(n, quote=False)}</div>" for n in names)
    page = ("<!doctype html><meta charset=\"utf-8\"><style>"
            f"@font-face {{ font-family: J; src: url(data:font/woff2;base64,{font}) format(\"woff2\"); font-weight: 700; }}"
            "html, body { margin: 0; background: transparent; overflow: hidden; }"
            # captionStrong (Jakarta Bold 11/14), ink, one line, at most 140 wide, cut with an ellipsis,
            # the halo in the map's land colour (CafePin.tsx's label).
            "div { box-sizing: border-box; width: 148px; height: 20px; padding: 3px 4px; text-align: center;"
            f" font: 700 11px/14px J; letter-spacing: 0; color: {t['ink']}; text-shadow: 0 0 3px {t['map-land']};"
            " white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }"
            f"</style><body>{rows}<script>document.fonts.ready.then(() => document.title = 'ready')</script>")
    tmp = tempfile.mkdtemp(prefix="kerja-names-")
    try:
        src = os.path.join(tmp, "names.html")
        open(src, "w", encoding="utf-8").write(page)
        for scale in (2, 3):
            png = os.path.join(tmp, f"names-{scale}x.png")
            subprocess.run([CHROME, "--headless=new", f"--user-data-dir={tmp}/profile", "--no-first-run",
                            "--hide-scrollbars", "--disable-gpu", f"--force-device-scale-factor={scale}",
                            f"--window-size=148,{20 * len(names)}", "--default-background-color=00000000",
                            "--virtual-time-budget=4000", f"--screenshot={png}", "file://" + src],
                           check=True, capture_output=True)
            subprocess.run(["cwebp", "-quiet", "-lossless", "-z", "9", png, "-o", f"{NAMES}-{scale}x.webp"], check=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"wrote {os.path.relpath(NAMES, ROOT)}-2x.webp and -3x.webp: {len(names)} names")


CUP = '<svg class="pin-cup" width="16" height="16" aria-hidden="true"><use href="#pin-cup"/></svg>'


def img(src, w, h, extra=""):
    return (f'<img src="{src}-2x.webp" srcset="{src}-2x.webp 2x, {src}-3x.webp 3x" width="{w}" height="{h}" '
            f'alt="" aria-hidden="true" loading="lazy" decoding="async"{extra}>')


def pin_html(i, row, rows, pin, shown, badged):
    """One pin, all of it hidden from screen readers (decision 5256): the body, the badge, the name."""
    count, people = pin["count"], pin["people"]
    drawn = pin["name"] in shown
    hidden = len(shown.get(pin["name"], []))
    style = f"--x: {pin['x']:.1f}; --y: {pin['y']:.1f}"
    if hidden:
        style += f"; --more: '+{hidden}'"
    badge = f'<span class="pin-badge"{"" if hidden else " hidden"}></span>' if pin["name"] in badged else ""
    if count:
        faces, blanks, more = face_slots(count, len(people))
        stack = "".join(img(f"assets/story/face-{first(n)}", 26, 26) for n in people[:faces])
        if more:
            stack += f'<span class="pin-more">+{more}</span>'
        body = f'<span class="pin-pill" style="width: {pill_width(count):g}px">{CUP}<span class="pin-faces">{stack}</span>{badge}</span>'
    else:
        body = f'<span class="pin-quiet">{CUP}{badge}</span>'
    name = f'<span class="pin-name">{img("assets/story/pin-names", 148, 20 * rows, f' style="top: -{20 * row}px"')}</span>'
    return (f'<li class="pin" data-pin="{i}" style="{style}"><span class="pin-mark"{"" if drawn else " hidden"}>'
            f"{body}{name}</span></li>")


def replace_between(text, start, end, body, what):
    a, b = text.find(start), text.find(end)
    if a < 0 or b < a:
        raise SystemExit(f"{what}: the markers {start!r} and {end!r} are missing")
    return text[:a + len(start)] + body + text[b:]


def write_pins(csv_path):
    every = all_cafes(csv_path)
    steps = bands(every)
    full = steps[0][1]
    # The page shows the cafés whose point is inside the window, every one of them.
    pins = [p for p in placement_order(every) if in_window(p)]
    away = set(PEOPLE) - {p["name"] for p in pins}
    if away:
        raise SystemExit(f"people placed at cafés outside the window: {sorted(away)}")
    names = [p["name"] for p in pins]
    badged = {n for _, shown in steps for n, hid in shown.items() if hid and n in names}
    ids = {n: i + 1 for i, n in enumerate(names)}

    render_names(names)
    items = "".join("          " + pin_html(ids[p["name"]], ids[p["name"]] - 1, len(names), p, full, badged) + "\n" for p in pins)
    for rel, up in PAGES:
        path = os.path.join(ROOT, rel)
        body = items.replace('src="assets/', f'src="{up}assets/').replace('srcset="assets/', f'srcset="{up}assets/')
        body = body.replace(", assets/", f", {up}assets/")
        page = open(path, encoding="utf-8").read()
        page = replace_between(page, "<!-- pins: start -->\n", "          <!-- pins: end -->", body, rel)
        open(path, "w", encoding="utf-8").write(page)

    # Narrower maps: the pins whose state differs from the full map's, per band of widths (a band
    # is written only where what the window shows changes).
    def seen(shown):
        return {n: len(shown[n]) for n in names if n in shown}
    kept = [steps[0]]
    for step in steps[1:]:
        if seen(step[1]) != seen(kept[-1][1]):
            kept.append(step)
    steps = kept
    rules = []
    for below, shown in steps[1:]:
        sel = []
        for p in pins:
            n, i = p["name"], ids[p["name"]]
            hid, was = len(shown.get(n, [])), len(full.get(n, []))
            if (n in shown) != (n in full):
                sel.append(f'.pin[data-pin="{i}"] .pin-mark {{ display: {"block" if n in shown else "none"}; }}')
            if (hid > 0) != (was > 0):
                sel.append(f'.pin[data-pin="{i}"] .pin-badge {{ display: {"flex" if hid else "none"}; }}')
            if hid and hid != was:
                sel.append(f".pin[data-pin=\"{i}\"] {{ --more: '+{hid}'; }}")
        if sel:
            rules.append(f"  @container (width < {below:g}px) {{\n" + "".join(f"    {s}\n" for s in sel) + "  }\n")
    css = open(CSS, encoding="utf-8").read()
    css = replace_between(css, "  /* pins: start */\n", "  /* pins: end */", "".join(rules), "welcome.css")
    open(CSS, "w", encoding="utf-8").write(css)

    lon, lat = CENTRE
    print(f"window: centre {lon}, {lat}, zoom {ZOOM}, {W} x {H}; {len(pins)} cafés in it")
    for p in pins:
        n = p["name"]
        state = ("drawn, its +N counts " + ", ".join(full[n]) if full[n] else "drawn") if n in full else "counted in a +N"
        print(f"  {ids[n]} {n} at {p['x']:.1f}, {p['y']:.1f}; {p['count']} here {p['people']}; {state}")
    for below, shown in steps[1:]:
        print(f"  below {below:g} px: " + json.dumps({k: v for k, v in shown.items() if v and k in names}, ensure_ascii=False)
              + "; drawn: " + ", ".join(str(ids[k]) for k in shown if k in ids))


def main():
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    check_window()
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    draw_map(data["elements"])
    write_pins(sys.argv[2])


if __name__ == "__main__":
    main()
