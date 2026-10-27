# trykerja.com

The Kerja website: four static pages (Welcome, How it works, Our promise, Join the beta), the same four in Indonesian under `/id/`, and a 404 page. Plain HTML and CSS, one small script (`assets/site.js`) for the mobile menu, the Copy button and the steps of Welcome's map story. No build step, no packages, no analytics, no cookies, no requests to other sites.

Ready for GitHub Pages: deploy from branch `main`, folder `/ (root)`. `.nojekyll` makes Pages serve the files as they are.

## Switch the Join the beta page's state

In `download/index.html` and `id/download/index.html` (change both), the `<body>` tag carries the state. It is the only line to change:

```html
<body data-beta="open">
```

- `open` (the default): "The Canggu beta is open. Install in two steps." with the two steps and the TestFlight invite button (and the QR code on a computer)
- `full`: "This round is full." with the waitlist in the invite's place, once the beta's cap of 60 testers is reached

Only one state is ever shown. The full state's lines also carry the `hidden` attribute, so leave it on them: `data-beta="full"` is what shows them.

## The invite link

In `download/index.html` (and its Indonesian twin, "Buka undangan beta Canggu", in `id/download/index.html`), the "Open the Canggu beta invite" button has `href="#REPLACE-WITH-CANGGU-TESTERS-LINK"`, with a comment right above it. The page opens in the `open` state, so put the "Canggu testers" public TestFlight link there before the page is published.

## Cache-busting

Every picture, stylesheet and script URL in the pages (the English ones, the 404 and the four under `/id/`) carries `?v=` and the first 8 characters of the file's SHA-256, so a changed file always gets a new URL. After changing any of them, run `python3 -I tools/stamp.py` (and `python3 -I tools/stamp.py --check` lists every URL and fails if one is stale or missing).

## The map story (Welcome, desktop only)

On a screen 1024 px wide or more, with motion allowed, Welcome shows a flat map of Canggu between the hero and "A morning on Kerja": sample people checked in at cafés, a session card and a chat with Nico come in as four short lines scroll past (`.story` in `index.html` and `welcome.css`, the steps in `site.js`). Below 1024 px, or with reduced motion, it isn't shown and the page is as before.

The map is the app's opening view (decisions 5249, 5250, 5256): zoom 15 in the app's projection, a 640 × 620 window, 1 px = 1 app point. The café pins are drawn as the app's map draws them (the orange pill with the cup and up to three faces then "+N", the quiet white cup, the ink "+N" badge for cafés a pin hides, the name under the pointer), with the app's own rule for which pins are drawn and which are counted. On a narrower map the pins keep their size and the rule runs again for that scale (container queries in `welcome.css`). Faces are cast-v3 portraits only, whole, as the app's avatar shows them (`assets/story/face-<first name>-2x.webp` and `-3x.webp`, 52 and 78 px, made with `sips -z` and `cwebp -q 86 -m 6 -sharp_yuv`). The cafés' names are never page text: they are drawn into an image (`assets/story/pin-names-2x.webp` and `-3x.webp`), and the pins, faces and names are hidden from screen readers; the map's one alt is "Illustration of sample profiles checked in at cafés in Canggu".

`tools/draw_map.py` makes all of it: the drawing `assets/story/canggu-map.svg` (our own drawing of OpenStreetMap data: roads, water, in the app's map colours, with no names, cafés or buildings), the pins between the `pins` comments in `index.html` and `id/index.html` (the window, who is where, which pins are drawn) and in `welcome.css` (the narrower maps), and the names' image (with headless Chrome and `cwebp`). The data is one Overpass download for the box lon 115.112 to 115.160, lat -8.672 to -8.626; it is ODbL and stays out of this repo (it's kept with its query and download time in `kerja-artifacts/build-12/scroll-story/osm/`). To redraw, run `python3 -I tools/draw_map.py <that file> <the app's docs/data/canggu-cafes.csv>`, then `python3 -I tools/stamp.py`. The page makes no call to any map service.

"Sample profiles and sessions. An illustration, not live activity at these cafés." and "© OpenStreetMap contributors" (linked to https://www.openstreetmap.org/copyright) are on the map's top left and again just under its bottom edge, so one of each is fully on screen whenever any of the map is: while the map comes in from below, the top note rides the screen's bottom edge just above the map; while it leaves at the top, the copy under its bottom edge is on screen.

## Bahasa Indonesia (`/id/`)

The four pages are also in Indonesian, with the same structure: `/id/`, `/id/how-it-works/`, `/id/promise/` and `/id/download/` (decisions 5273 to 5275). They use the same `assets/` through relative paths (`../assets/`, `../../assets/`): no copies of CSS, JavaScript or pictures. English stays the default at the current URLs, and is always the first page anyone sees.

- **The switch, "EN / ID":** in the bar (from 1080 px, between the nav and the pill), in the phone menu (under the links) and in the footer of every page, the 404 included. Each language links to the same page in the other one; the current one is ink, isn't a link and carries `aria-current="page"`; the other is a text link (orangeShadow). No redirect by browser language or place, no cookie, no storage, nothing remembered. Styles: `.lang` in `site.css`.
- **Head tags:** `<html lang="en">` or `<html lang="id">`; a self canonical; `hreflang` links `en`, `id` and `x-default` (English) to the absolute `https://trykerja.com/…` URLs, the same three on both versions of a page; `og:locale` (`en_US` / `id_ID`) with the other as `og:locale:alternate`, and `og:url`. `sitemap.xml` lists all eight pages with the same alternates. The 404 has no Indonesian twin, so no `hreflang`.
- **The words:** every Indonesian string, beside its English one, is in `kerja-artifacts/site-id-strings.md` (outside this repo), grouped by page and kind. Change an English line, change its Indonesian line and that file too. Informal "kamu", sentence case, and the word rules of 5273 (no dating, whereabouts, status, hiring or money words; names, never "dia", in lines about a member).
- **What stays English:** "Kerja", "Say hi", the app's screenshots, and the map story's session card and chat (copies of app screens, marked `lang="en"`); the app's own button and screen names, quoted as the app shows them ("Work here", "I'm here", "Who's here"…); "© OpenStreetMap contributors" (the licensor's required credit); the legal pages, whose links on `/id/` read "… (dalam bahasa Inggris)". Alts describe the English screenshots in Indonesian, quoting their labels.
- **Join the beta:** the waitlist email's subject is "Kerja waitlist (ID)", so the inbox can tell the two apart; the body's field labels and the copy panel are in Indonesian. The WhatsApp text links `https://trykerja.com/id/download`. The Copy button reads its "copied" word from `data-copied` (`site.js`; "Copied" when absent).
- **The second QR code:** `assets/qr-download-id.svg`, to https://trykerja.com/id/download, made with `node tools/qr.mjs https://trykerja.com/id/download assets/qr-download-id.svg`. The script needs `toqr` 0.1.1 (MIT, "Tiny QR code encoder", a dependency of Expo's CLI), which it imports in place, read only, from the app repo's `~/dev/kerja/node_modules/toqr` (or the path in `TOQR`); nothing is installed for the site. It draws as `assets/qr-download.svg` is drawn (EC level M, 4-module quiet zone, white and ink). After making one, run `stamp.py` and decode it in a browser.
- **The 404** stays English (GitHub Pages serves one `/404.html` for every missing path, `/id/…` included), with one Indonesian line and a link to `/id/`.

## The domain

`CNAME` is in: one line, `trykerja.com`, for GitHub Pages' custom domain.

Pages link to each other with relative paths, so they also work on a preview address before the switch. `404.html` uses root-absolute paths (`/assets/...`), because Pages serves it at any depth; on a preview address under a sub-path it shows unstyled.

## Where things are

- `assets/site.css`: colours (once, on `:root`, from the app's tokens), fonts and the shared parts (top bar, menu, footer, pills, links, lists, Coming soon, last call, the 404 block).
- `assets/welcome.css`, `assets/how.css`, `assets/promise.css`, `assets/download.css`: each page's own layout, loaded after `site.css`.
- `assets/fonts/`: Latin subsets of Bricolage Grotesque and Plus Jakarta Sans (WOFF2), with their OFL licences.
- `assets/screens/`: the app screens, each a whole 9:20 screen from a 1080 × 2400 master (status bar to bottom space) taken from the app on Android with sample profiles only, as WebP at 1x, 2x and 3x of the 252 px phone screen (`-1x` 252 × 560, `-2x` 504 × 1120, `-3x` 756 × 1680). The pages show them in the CSS phone outline (`.device` in `site.css`), whole, never cropped or zoomed.
- `assets/story/`: the map story's map of Canggu, the sample faces and the cafés' names (see above).
- `tools/stamp.py`: the cache-busting stamps; `tools/draw_map.py`: draws the map story's map and pins; `tools/qr.mjs`: draws a QR code (needs `toqr`, see above).
- `id/`: the four pages in Indonesian (see above).
- `assets/og.jpg`: the share preview (1200 × 630), used by both languages. `assets/qr-download.svg`: the QR code to https://trykerja.com/download; `assets/qr-download-id.svg`: the one to https://trykerja.com/id/download.
