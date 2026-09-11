# en-blog

English technical blog at [en.hancic.site](https://en.hancic.site).

Built with [Hugo](https://gohugo.io) + [PaperMod](https://github.com/adityatelange/hugo-PaperMod), self-hosted on a Tencent Cloud lightweight VPS (US) via Docker Compose behind the shared Nginx reverse proxy.

## Stack

- **Hugo** — static site generator; content is plain Markdown in `content/`
- **PaperMod** — theme, vendored under `themes/PaperMod` (no submodule)
- **Nginx (alpine) container** — serves `public/` (Hugo build output); container-internal port `80`
- **my-nginx** (separate repo) — front proxy, terminates TLS with the `*.hancic.site` Let's Encrypt wildcard and proxies `en.hancic.site` → `en-blog` container over the shared `nginx_default` Docker network

## Local dev

```bash
hugo server -D     # hot-reload preview with drafts
hugo new posts/my-post.md
```

## Deploy

```bash
hugo --minify      # build -> public/
rsync -az --delete -e ssh public/ root@<usa>:/opt/en-blog/public/
ssh root@<usa> "cd /opt/en-blog && docker compose up -d --force-recreate"
```

Automated deployment via GitHub Actions (tag-triggered) is planned.

## Layout

| Path | Purpose |
| --- | --- |
| `content/` | articles in Markdown |
| `content/archives.md` | archives page (PaperMod layout) |
| `archetypes/` | front-matter template for new posts |
| `hugo.yaml` | site config (baseURL, theme, taxonomies, params) |
| `docker-compose.yml` | runtime service (nginx serving `public/`) |
| `nginx/static.conf` | in-container nginx config (compression, caching, security headers) |
| `layouts/` | PaperMod overrides: `partials/comments.html` (giscus, legacy path), `_partials/extend_head.html` (diagram CSS), `single.html` (post template without the visible description), `_shortcodes/diagram.html` (inline SVG figures) |
| `assets/diagrams/*.svg` | diagram sources, inlined at build time by the `diagram` shortcode |
| `static/diagrams/*.png` | dev.to copies of those diagrams, colour frozen — generated, see below |
| `tools/devto_mcp.py` | dev.to publishing MCP server — usage in [`tools/README.md`](tools/README.md) |
| `tools/raster/` | SVG→PNG renderer for those copies (resvg, pinned in `package.json`) |
| `tools/README.md` | install, MCP registration and tool reference for the two above |

## Diagrams

Posts embed a diagram with `{{</* diagram "name.svg" "short caption" */>}}`. The shortcode inlines
`assets/diagrams/name.svg` instead of linking to it, so the drawing inherits `currentColor` and
follows the light/dark theme. An `<img>` reference cannot do this: inside an external SVG,
`currentColor` resolves to the SVG's own default, which disappears on the dark theme.

House style:

- `viewBox` width is always 720, which renders near 1:1 in PaperMod's 720px content column.
- Text uses `currentColor` with opacity tiers (0.9 / 0.6 / 0.55), so one drawing works on both themes.
- One accent colour, `#d97706`, and only for strokes and node fills. Never for small text: no single
  colour clears the contrast bar on both `#fff` and `#1d1e20`.
- Budget: about 10 words per diagram and a 3-5 word caption. Relationships and flow come from the
  drawing, not from labels.
- Below 460px the figure scrolls sideways instead of shrinking the text into illegibility.
- Before committing a diagram, check that no text overflows its box or the canvas, that text does not
  overlap other text or node circles, and that the SVG is well-formed XML.

## Comments

Giscus (GitHub Discussions), wired in `layouts/partials/comments.html` and enabled site-wide via `params.comments`.

## dev.to sync

Posts are also published to [dev.to](https://dev.to) by `tools/devto_mcp.py`, an MCP server (stdio) over
the v1 API. It parses the front matter, rewrites relative image paths to `https://en.hancic.site/...`,
expands the `diagram` shortcode into real images, drops the remaining Hugo shortcodes, and sets
`canonical_url` so the dev.to copy carries a visible "Originally published at" link back here.

Install, MCP registration and the full tool reference live in [`tools/README.md`](tools/README.md);
the diagram step it depends on is below.

### Diagrams on dev.to

Two things break there. dev.to renders no shortcode and inherits no `currentColor`, so the
theme-adaptive trick above does not survive. And dev.to proxies every external image through its own
imgproxy, which cannot rasterise SVG: it hands the reader the SVG bytes labelled `image/webp`, so the
request is a 200 but the browser shows nothing.

So `bake_diagrams` renders each diagram to a PNG in `static/diagrams/` — colour frozen to `#1e1e1e`
on a white card, at 2x (1440px wide, matching a retina screen). `sync_post` turns
`{{</* diagram "name.svg" "caption" */>}}` into `![caption](https://en.hancic.site/diagrams/name.png)`
plus an italic caption.

The white card is deliberate: dark ink on a transparent background would be invisible to readers on
dev.to's dark theme, while dark ink on white stays readable on both (it just reads as a card on dark).

The build host has no fonts and no cairo/rsvg/inkscape, so rendering goes through
[resvg](https://github.com/thx/resvg-js) as a pinned npm dependency (see
[`tools/README.md`](tools/README.md) for the one-time setup). Then `bake_diagrams` after adding or
editing a diagram, then deploy — those URLs are what dev.to fetches. The generated PNGs are committed
so a fresh clone still deploys them.

Note the cache trap: the PNGs carry no content hash, yet nginx serves `png` with
`Cache-Control: public, immutable` for 30 days. Re-baking a diagram overwrites the same filename, so
readers and dev.to's proxy can keep serving the old drawing for a while. Adding a content hash to the
filename is the way out if that ever bites.