# trykerja.com

The Kerja website: four static pages (Welcome, How it works, Our promise, Join the beta) and a 404 page. Plain HTML and CSS, one small script (`assets/site.js`) for the mobile menu and the Copy button. No build step, no packages, no analytics, no cookies, no requests to other sites.

Ready for GitHub Pages: deploy from branch `main`, folder `/ (root)`. `.nojekyll` makes Pages serve the files as they are.

## Switch the Join the beta page's state

In `download/index.html`, the `<body>` tag carries the state. It is the only line to change:

```html
<body data-beta="open">
```

- `open` (the default): "The Canggu beta is open. Install in two steps." with the two steps and the TestFlight invite button (and the QR code on a computer)
- `full`: "This round is full." with the waitlist in the invite's place, once the beta's cap of 60 testers is reached

Only one state is ever shown. The full state's lines also carry the `hidden` attribute, so leave it on them: `data-beta="full"` is what shows them.

## The invite link

In `download/index.html`, the "Open the Canggu beta invite" button has `href="#REPLACE-WITH-CANGGU-TESTERS-LINK"`, with a comment right above it. The page opens in the `open` state, so put the "Canggu testers" public TestFlight link there before the page is published.

## The domain

`CNAME` is in: one line, `trykerja.com`, for GitHub Pages' custom domain.

Pages link to each other with relative paths, so they also work on a preview address before the switch. `404.html` uses root-absolute paths (`/assets/...`), because Pages serves it at any depth; on a preview address under a sub-path it shows unstyled.

## Where things are

- `assets/site.css`: colours (once, on `:root`, from the app's tokens), fonts and the shared parts (top bar, menu, footer, pills, links, lists, Coming soon, last call, the 404 block).
- `assets/welcome.css`, `assets/how.css`, `assets/promise.css`, `assets/download.css`: each page's own layout, loaded after `site.css`.
- `assets/fonts/`: Latin subsets of Bricolage Grotesque and Plus Jakarta Sans (WOFF2), with their OFL licences.
- `assets/screens/`: the app screens, each a full 9:19.5 screen (WebP, 480 px wide and a 240 px `-sm`, from 1080 × 2340 masters taken from the app on Android with sample profiles only; the Say hi sheet kept from its top down). The pages show them inside the CSS phone frame (`.device` in `site.css`).
- `assets/og.jpg`: the share preview (1200 × 630). `assets/qr-download.svg`: the QR code to https://trykerja.com/download.
