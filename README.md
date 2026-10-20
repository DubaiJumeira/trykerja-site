# trykerja.com

The Kerja website: four static pages (Welcome, How it works, Our promise, Join the beta) and a 404 page. Plain HTML and CSS, one small script (`assets/site.js`) for the mobile menu and the Copy button. No build step, no packages, no analytics, no cookies, no requests to other sites.

Ready for GitHub Pages: deploy from branch `main`, folder `/ (root)`. `.nojekyll` makes Pages serve the files as they are.

## Switch the Join the beta page's state

In `download/index.html`, the `<body>` tag carries the state. It is the only line to change:

```html
<body data-beta="soon">
```

- `soon`: "The Canggu beta opens soon." (shipped now, until Apple approves the first version)
- `open`: "Join the Canggu beta." with the TestFlight invite button (and the QR code on a computer)
- `full`: "This round is full."

## The invite link

In `download/index.html`, the "Open the Canggu beta invite" button has `href="#REPLACE-WITH-CANGGU-TESTERS-LINK"`, with a comment right above it. Put the "Canggu testers" public TestFlight link there once Apple approves, then switch the state to `open`.

## The domain

There is no `CNAME` file yet. It goes in at the domain switch, with one line: `trykerja.com`.

Pages link to each other with relative paths, so they also work on a preview address before the switch. `404.html` uses root-absolute paths (`/assets/...`), because Pages serves it at any depth; on a preview address under a sub-path it shows unstyled.

## Where things are

- `assets/site.css`: colours (once, on `:root`, from the app's tokens), fonts, the shared parts, Welcome and How it works.
- `assets/promise.css`, `assets/download.css`: Our promise and Join the beta.
- `assets/fonts/`: Latin subsets of Bricolage Grotesque and Plus Jakarta Sans (WOFF2), with their OFL licences.
- `assets/screens/`: the app screens (WebP, drawn for the site, sample profiles only).
- `assets/og.jpg`: the share preview (1200 × 630). `assets/qr-download.svg`: the QR code to https://trykerja.com/download.
