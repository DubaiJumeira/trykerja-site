#!/usr/bin/env python3
"""Gets Umami's tracker, byte for byte, from one release's official image (decision 5402). Standard
library only; never sends anything to Umami's collector. tools/ isn't published.

  python3 -I tools/umami_fetch.py 3.4.1            print the release's script.js size and SHA-256, and
                                                  whether assets/umami.js is that file, byte for byte
  python3 -I tools/umami_fetch.py 3.4.1 --write    also write it to assets/umami.js

Umami's releases on GitHub carry the source only; the built tracker (rollup.tracker.config.js, from
src/tracker/index.ts) ships in the release's image, ghcr.io/umami-software/umami:<version>, as
/app/public/script.js. This reads the image's index anonymously from ghcr.io (GitHub's registry),
downloads, for linux/amd64 and linux/arm64, only the layer that copies /app/public, and takes
app/public/script.js out of it in memory. Both builds must be the same bytes, or it stops.

After --write: put the printed SHA-256 in UMAMI_SHA256 in tools/csp_check.py and in README.md, then
run python3 -I tools/stamp.py and python3 -I tools/csp_check.py (README.md, "Website statistics")."""
import hashlib
import io
import json
import os
import sys
import tarfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "umami-software/umami"
REGISTRY = "https://ghcr.io/v2/" + REPO
TARGET = "app/public/script.js"
INDEX = "application/vnd.oci.image.index.v1+json"
MANIFEST = "application/vnd.oci.image.manifest.v1+json"


def get(url, token, accept=None):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, **({"Accept": accept} if accept else {})})
    with urllib.request.urlopen(req, timeout=120) as res:
        return res.read(), res.headers


def checked(blob, digest):
    got = "sha256:" + hashlib.sha256(blob).hexdigest()
    if got != digest:
        sys.exit(f"stop: a download doesn't match its digest ({got} != {digest})")
    return blob


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit(__doc__)
    version = args[0].lstrip("v")
    with urllib.request.urlopen(f"https://ghcr.io/token?scope=repository:{REPO}:pull", timeout=60) as res:
        token = json.load(res)["token"]
    raw, headers = get(f"{REGISTRY}/manifests/{version}", token, INDEX)
    index_digest = headers.get("Docker-Content-Digest")
    checked(raw, index_digest)
    builds = {}
    for m in json.loads(raw)["manifests"]:
        plat = m.get("platform", {})
        if plat.get("os") != "linux" or plat.get("architecture") not in ("amd64", "arm64"):
            continue  # attestations
        manifest = json.loads(checked(get(f"{REGISTRY}/manifests/{m['digest']}", token, MANIFEST)[0], m["digest"]))
        config = json.loads(checked(get(f"{REGISTRY}/blobs/{manifest['config']['digest']}", token)[0], manifest["config"]["digest"]))
        steps = [h for h in config["history"] if not h.get("empty_layer")]
        layers = [l for l, h in zip(manifest["layers"], steps) if "/app/public ./public" in h.get("created_by", "")]
        if len(layers) != 1:
            sys.exit(f"stop: {plat['architecture']}: {len(layers)} layers copy /app/public (one expected)")
        blob = checked(get(f"{REGISTRY}/blobs/{layers[0]['digest']}", token)[0], layers[0]["digest"])
        with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
            member = tar.getmember(TARGET)
            builds[plat["architecture"]] = tar.extractfile(member).read()
    if set(builds) != {"amd64", "arm64"} or builds["amd64"] != builds["arm64"]:
        sys.exit("stop: the amd64 and arm64 builds of script.js differ, or one is missing")
    data = builds["amd64"]
    sha = hashlib.sha256(data).hexdigest()
    print(f"Umami {version}: ghcr.io/{REPO}:{version} (index {index_digest}), /{TARGET}")
    print(f"  {len(data)} bytes, SHA-256 {sha} (linux/amd64 and linux/arm64 identical)")
    path = os.path.join(ROOT, "assets", "umami.js")
    if "--write" in sys.argv:
        with open(path, "wb") as f:
            f.write(data)
        print("  written to assets/umami.js")
    elif os.path.exists(path):
        same = open(path, "rb").read() == data
        print("  assets/umami.js: " + ("the same bytes" if same else "DIFFERENT"))
        sys.exit(0 if same else 1)


if __name__ == "__main__":
    main()
