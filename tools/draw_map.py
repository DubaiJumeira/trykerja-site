#!/usr/bin/env python3
"""Draws the Welcome page's flat map of Canggu (assets/story/canggu-map.svg) from OpenStreetMap data
(decision 5230, route 1: our own drawing; no map service, no tiles, nothing fetched by the page).

  python3 -I tools/draw_map.py <overpass.json>

The input is one Overpass API download for the box lon 115.112 to 115.160, lat -8.672 to -8.626
(roads, the coastline, water). The raw data is ODbL and stays out of this repo (it is kept with its
query and download time in kerja-artifacts/build-12/scroll-story/osm/); only this script and the map
it draws (a Produced Work) are committed. The page shows "© OpenStreetMap contributors" on the map,
linked to https://www.openstreetmap.org/copyright, at all times.

What is drawn, in the app's own map style (src/components/map/mapStyle.ts in the app): land in sand
(creamDeep), the sea and the rivers in lagoon at 35%, main roads in cream with a thin ink 12% edge,
smaller roads in plain cream. Nothing else: no names, no cafés or other places, no buildings, no
paths or service lanes. The area names are the page's own HTML labels, laid over the map.
Colours are read from assets/site.css (:root), which takes them from the app's tokens."""
import json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "story", "canggu-map.svg")

# The box (west, south, east, north) and the drawing's size in CSS pixels (the map is shown at this
# size or smaller, so the SVG stays crisp at 2x and 3x).
WEST, SOUTH, EAST, NORTH = 115.112, -8.672, 115.160, -8.626
KX = math.cos(math.radians((SOUTH + NORTH) / 2))  # metres per degree of longitude, relative to latitude
W = 640
H = round(W * (NORTH - SOUTH) / ((EAST - WEST) * KX))
S = W / (EAST - WEST)

# Road classes and how each is drawn: (width in px, with an edge or not, shortest line kept in px).
# The main roads, plus the smaller roads that give Canggu its shape: residential and unclassified
# roads longer than about 200 m. Left out: living streets (the narrow gang lanes), service lanes,
# tracks, paths and footways, which at this size only add noise.
ROADS = [
    ("residential", {"residential"}, 1.5, False, 24),
    ("unclassified", {"unclassified"}, 2.4, False, 0),
    ("major", {"motorway", "trunk", "primary", "secondary", "tertiary",
               "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"}, 5, True, 0),
]
EDGE = 0.9          # the main roads' edge on each side, in px
RIVERS = {"river": 2.0, "stream": 1.1, "tidal_channel": 1.4, "canal": 1.4}
TOLERANCE = 0.3     # Douglas-Peucker tolerance in px


def tokens():
    css = open(os.path.join(ROOT, "assets", "site.css"), encoding="utf-8").read()
    root = css.split("}", 1)[0]
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9A-Fa-f]{6})", root))


def project(geom):
    # x: degrees of longitude to px; y: degrees of latitude to px, stretched by 1/cos(lat) so a
    # kilometre is the same length both ways.
    return [((p["lon"] - WEST) * S, (NORTH - p["lat"]) * S / KX) for p in geom]


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


M = 12  # margin around the box, in px, so lines run off the edges cleanly


def inside(p):
    return -M <= p[0] <= W + M and -M <= p[1] <= H + M


def runs(pts):
    """Splits a line into the runs that touch the box (with its margin)."""
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
    """Sutherland-Hodgman against one edge of the box: edge = (axis, value, keep_greater)."""
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


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    data = json.load(open(sys.argv[1], encoding="utf-8"))
    els = data["elements"]
    t = tokens()
    sand, cream, ink, lagoon = t["sand"], t["cream"], t["ink"], t["lagoon"]

    # The sea: the coastline (land on its left, so the sea is to its right, south-west here),
    # closed far out to the south-west, then cut to the box.
    coast = coast_chain([e for e in els if e["type"] == "way" and e.get("tags", {}).get("natural") == "coastline"])
    cpts = project(coast)
    x0, y0 = cpts[0]
    x1, y1 = cpts[-1]
    far = [(x1, H + 4000), (-4000, H + 4000), (-4000, y0)]
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
        f"<!-- Canggu, from Pererenan to Berawa. Map data © OpenStreetMap contributors (ODbL), "
        f"https://www.openstreetmap.org/copyright. Drawn by tools/draw_map.py. -->",
        f'<rect width="{W}" height="{H}" fill="{sand}"/>',
        f'<g fill="{lagoon}" fill-opacity=".35"><path d="{poly_d(sea)}"/>'
        + "".join(f'<path d="{poly_d(p)}"/>' for p in lakes) + "</g>",
        f'<g fill="none" stroke="{lagoon}" stroke-opacity=".35" stroke-linecap="round" stroke-linejoin="round">'
        + "".join(f'<path stroke-width="{RIVERS[k]}" d="{path(v)}"/>' for k, v in rivers.items()) + "</g>",
        f'<g fill="none" stroke-linecap="round" stroke-linejoin="round">',
    ]
    for name, classes, width, edge, _ in ROADS:
        d = path(roads[name])
        if edge:
            out.append(f'<path stroke="{ink}" stroke-opacity=".12" stroke-width="{width + 2 * EDGE:g}" d="{d}"/>')
        out.append(f'<path stroke="{cream}" stroke-width="{width:g}" d="{d}"/>')
    out.append("</g></svg>")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    svg = "\n".join(out) + "\n"
    open(OUT, "w", encoding="utf-8").write(svg)
    print(f"wrote {os.path.relpath(OUT, ROOT)}: {W} x {H}, {len(svg):,} bytes; "
          + ", ".join(f"{k} {len(v)}" for k, v in roads.items()) + f"; rivers {sum(len(v) for v in rivers.values())}; lakes {len(lakes)}")


if __name__ == "__main__":
    main()
