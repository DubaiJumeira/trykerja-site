# trykerja.com

The Kerja website: four static pages (Welcome, How it works, Our promise, Join the beta), the same four in Indonesian under `/id/`, and a 404 page. Plain HTML and CSS, and two small scripts: `assets/site.js` for the mobile menu and the steps of Welcome's map story, and `assets/apply.js` for Join the beta's application form. No build step, no packages, no analytics, no cookies, no storage. The one request to another site is the beta application, sent to Kerja's Supabase function when someone taps Send (see below).

Ready for GitHub Pages: deploy from branch `main`, folder `/ (root)`. Pages builds it with Jekyll, which copies the pages as they are (none has front matter) and, by `_config.yml`, leaves this README and `tools/` off the site (see Security, below).

## Switch the Join the beta page's state

In `download/index.html` and `id/download/index.html` (change both), the `<body>` tag carries the state. It is the only line to change:

```html
<body data-beta="open">
```

- `open` (the default): "The Canggu beta is open. Install in two steps." with the two steps and the TestFlight invite button (and the QR code on a computer)
- `full` (the state today): "The Canggu beta opens soon." with the beta application form in the invite's place (and the QR code to this page on a computer)

Only one state is ever shown. The full state's lines also carry the `hidden` attribute, so leave it on them: `data-beta="full"` is what shows them.

## The beta application form (decisions 5289, 5290)

In the `full` (opens soon) state, `/download/` and `/id/download/` carry one form, `#apply`, where the invite is in the `open` state; On Android's "Go to the form" links to it. The fields, and nothing more: first name, email, which fits you best (Founder, Content creator, Freelancer, Other), how long you're in Canggu (Just arrived, 1–3 months, I live here), one optional Instagram or LinkedIn link, one optional line ("What would you work on next to someone?"), the "I'm 18 or older" and privacy policy ticks, and a hidden honeypot, `website`, which must stay empty. No age, no photo, no phone number.

`assets/apply.js` checks the fields as the function does and sends them as JSON (`lang` from `<html lang>`) to the form's `data-endpoint`, per the contract in `kerja-artifacts/beta-apply/contract.md`. Each field the page or the server (a 400's `fields`) refuses gets its line under it, `aria-invalid`, and a link in the box above the fields, which takes focus. A 429 shows "Too many tries for now"; a 403 (an `Origin` the server doesn't allow), a 500 or no answer "Your application didn't go through"; both with hello@trykerja.com. The link is sent as typed, normalized only as the contract's "link field" says (decision 5301): starting with `@`, unchanged; with a `.` or a `/`, `https://` added when there is no scheme; a bare word gets `@` (an Instagram handle). Whether it is an Instagram or LinkedIn profile is the server's call (its 400 shows the field's line). A 200 replaces the form with "You're on the list." by first name. Without JavaScript, the form is hidden and a line says to email hello@trykerja.com; the Send button stays disabled until the script is ready, so the form is never sent any other way. Every word is in the page, in its language; the script holds none. No cookies, no storage, no analytics.

**The endpoint.** Both pages post to **kerja-prod's** function: `data-endpoint` is `https://eppqufcgcwhoprwzfhxy.supabase.co/functions/v1/submit-application` (decision 5360, the sites audit's A1), the one address the two pages' `connect-src` allows (see Security, below). kerja-prod answers only `https://trykerja.com`, in CORS and on the server, which refuses any other `Origin`, or none, with a 403 (decisions 5301, 5360). kerja-dev's function was used for the G1 tests only; its URL is in no file here, and `tools/csp_check.py` fails if its project ref ever shows up in a published file. Previews never post to Supabase: they use the local mock (below).

**The local mock.** `python3 -I tools/apply_mock.py --port 8091` serves the site on http://127.0.0.1:8091/ and answers the contract at `/functions/v1/submit-application` (standard library only). In the pages it serves, and only there, `data-endpoint` becomes `http://localhost:8091/functions/v1/submit-application` (another origin, so the browser's CORS preflight runs as it will against Supabase). A valid application gets 200; a filled honeypot 200 (dropped); a refused field 400 with `fields`; an `Origin` other than `http://127.0.0.1:<port>` or `http://localhost:<port>` 403. The email's local part shows the other answers: `toomany@…` 429, `origin@…` 403, `broken@…` 500, `offline@…` no answer at all. It logs statuses and field names only. Use a plain static server (`python3 -I -m http.server`) to see the pages as they are.

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
- **What stays English:** "Kerja", "Say hi", the app's screenshots, Welcome's hero session card, and the map story's session card and chat (copies of app screens, marked `lang="en"`); the app's own buttons, labels, options and statuses, exactly as the app shows them ("Work here", "I'm here", "Who's here", the five session types, How it works' reason line…); "© OpenStreetMap contributors" (the licensor's required credit); the legal pages, whose links on `/id/` read "… (dalam bahasa Inggris)". Alts describe the English screenshots in Indonesian, quoting their labels.
- **Join the beta:** the application form's labels, choices, hints, error lines, 429 and 500 lines and "You're on the list." are in Indonesian in the page (`apply.js` holds no words), and the form sends `lang: "id"`, so the reply comes in Indonesian. Every form string, English beside Indonesian, is in `kerja-artifacts/beta-apply/site-apply-strings.md`. The WhatsApp text links `https://trykerja.com/id/download`.
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
- `assets/apply.js`: Join the beta's application form (see above), loaded by the two download pages only.
- `tools/stamp.py`: the cache-busting stamps; `tools/draw_map.py`: draws the map story's map and pins; `tools/qr.mjs`: draws a QR code (needs `toqr`, see above); `tools/apply_mock.py`: the local preview with the form's mock function.
- `tools/csp_check.py`: checks every page's Content-Security-Policy and referrer tags against the page (see Security, below).
- `_config.yml`: what Pages leaves off the site (see Security, below).
- `id/`: the four pages in Indonesian (see above).
- `assets/og.jpg`: the share preview (1200 × 630), used by both languages. `assets/qr-download.svg`: the QR code to https://trykerja.com/download; `assets/qr-download-id.svg`: the one to https://trykerja.com/id/download.

## Security

The security audit of 28 October 2026 (decisions 5329 to 5334). Every finding, with its severity and whether it is done, is in `kerja-artifacts/sec-audit/sites.md`.

**The Content-Security-Policy.** Every page carries these two tags right after the viewport tag, before anything it loads:

```html
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self'; style-src 'self' 'sha256-ftlsA0RZH98RbIQI+AjVCQ3J902Of/2USl+6/hI5cNg='; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'none'; base-uri 'none'; object-src 'none'">
<meta name="referrer" content="no-referrer">
```

- `script-src 'self'`: `assets/site.js` only. No inline script, no `on…=` attribute, no `eval`, no `javascript:` link.
- `style-src 'self'` and one hash: the stylesheets in `assets/`, and the one inline block, `<noscript><style>.menu-btn,.copy-btn{display:none!important}</style></noscript>` (it only applies with JavaScript off). Change that block and its hash must change with it.
- **Welcome only** (`index.html`, `id/index.html`) adds `style-src-attr 'unsafe-inline'`, for the map story's 13 `style=""` attributes that `tools/draw_map.py` writes (each pin's `--x`, `--y` and `--more`, the pills' widths, the names' offsets). It is the only `unsafe-inline`: style attributes on those two pages, never a script or a `<style>` block.
- `img-src 'self' data:`: the pictures in `assets/`, and the 1 × 1 GIF in two `<picture>` fallbacks (Welcome's hero phone under 600 px, the story's map under 1024 px or with reduced motion).
- `font-src 'self'`: the WOFF2 files in `assets/fonts/`.
- `connect-src 'self'`: no page fetches anything, but Chrome's DevTools and Lighthouse fetch through the page (DevTools' `/.well-known/appspecific/com.chrome.devtools.json`, Lighthouse's `robots.txt`); with `'none'` those showed as CSP violations in the console whenever DevTools was open and failed Lighthouse's robots.txt audit (SEO 100 to 92). **Join the beta** (`download/`, `id/download/`) also allows exactly one other address, kerja-prod's function `https://eppqufcgcwhoprwzfhxy.supabase.co/functions/v1/submit-application`, for the beta application form after G2. Never kerja-dev's.
- `form-action 'none'`, `base-uri 'none'`, `object-src 'none'`: no form is ever submitted by the browser itself, no `<base>`, no plugins.
- `no-referrer`: no page needs a `Referer`. A `fetch` to another site still carries the page's `Origin` (checked in Chrome and Safari), which is what the beta function checks.
- A meta tag can't carry `frame-ancestors`, `report-uri`, `report-to` or `sandbox`, so none is there (browsers would ignore them and log a warning).

**After changing any page,** run `python3 -I tools/csp_check.py` (or `python3 -I tools/csp_check.py <folder>`; it walks the folder, so it needs no git checkout and sees new, uncommitted pages). It checks what Pages would publish (the rule below) and fails when a page hasn't exactly one CSP meta and one referrer meta before anything it loads; when the referrer isn't exactly `no-referrer`; when the CSP isn't exactly the one above for that page, directive by directive and in that order (style-src lists the hash of each of the page's own inline `<style>` blocks, and none if it has none; Welcome adds `style-src-attr 'unsafe-inline'`; Join the beta adds kerja-prod's function to `connect-src`), so any other source, keyword or directive fails; when a page has an inline script, an `on…=` attribute or a `javascript:` URL, style attributes anywhere but Welcome (or Welcome without them), a form whose `data-endpoint` isn't kerja-prod's function, anything loaded from another site, or a `target="_blank"` link without `rel="noopener"`; when any published HTML, JS, CSS, SVG, XML, JSON or TXT file names kerja-dev's project ref, in any case; and when a published stylesheet loads from another site or uses `@import`.

**What GitHub Pages can't do.** Pages sends no security headers and can't be told to (no `_headers` file, no settings): no `Strict-Transport-Security` (http:// does get a 301 to https://, as "Enforce HTTPS" is on, but browsers aren't told to remember it, and the domain can't be preloaded), no CSP header and so no `frame-ancestors`, no `X-Frame-Options`, no `X-Content-Type-Options: nosniff`, no `Referrer-Policy` header, no `Permissions-Policy`, no `Cross-Origin-Opener-Policy`. The cache is always `max-age=600`, every answer says `Server: GitHub.com` and carries `Access-Control-Allow-Origin: *`. The meta tags cover the CSP (all but `frame-ancestors`) and the referrer. The rest would need a proxy in front of Pages (Cloudflare, for example): Zayd's decision, not a change in this repo. Without `frame-ancestors`, another site can show these pages in a frame; they have no account, sign-in or button that acts for anyone.

**What Pages publishes.** Pages builds `main` with Jekyll (there is no `.nojekyll`): a file without front matter is copied as it is, so every page, stylesheet, script and picture is served byte for byte; names starting with `.` or `_` are left out (`.gitattributes`, `_config.yml`); and `_config.yml` leaves out `README.md` and `tools/` (the scripts, and the form's local mock once it is here). `theme: null` stops Pages adding its default theme (Primer) and the `/assets/css/style.css` that comes with it, which isn't in this repo (legal.trykerja.com, with no theme line, serves one). `robots.txt`, `sitemap.xml`, the favicons and the fonts' OFL licences are public on purpose, and so, probably, is `CNAME`: Pages' build leaves it out only through its default `exclude` list, which a custom `exclude` replaces (legal.trykerja.com, with no `exclude`, answers 404 for it). It only holds the domain name, and the domain works either way. Never start a file with a `---` line unless Jekyll is meant to build it. Before decision 5331, a `.nojekyll` file had Pages serve every file of the repo, so `README.md`, `tools/draw_map.py`, `tools/stamp.py`, `tools/qr.mjs`, `.gitattributes` and `.nojekyll` were all reachable on trykerja.com. (The repo itself is public on GitHub, so nothing secret was ever in them; it is about not serving notes and tools under the site's name.) If a Jekyll build ever failed, Pages would keep the last good site; putting `.nojekyll` back undoes this.

**Third parties: none.** Every page loads only its own files (no fonts, scripts, styles, maps or pictures from elsewhere), so there is nothing to pin with Subresource Integrity. No analytics, no cookies, no storage. The links to other sites (OpenStreetMap's copyright page, TestFlight on the App Store, WhatsApp's share link, legal.trykerja.com, `mailto:`) load nothing until clicked, and none opens a new window.

**Scripts.** `assets/site.js` writes text only with `textContent` and never `innerHTML`, `insertAdjacentHTML`, `document.write`, `eval` or `new Function`. The `mailto:` and WhatsApp links are written out percent-encoded in the pages.
