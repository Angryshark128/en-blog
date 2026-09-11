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
| `static/diagrams/*.svg` | dev.to copies of those diagrams, colour frozen — generated, see below |
| `tools/devto_mcp.py` | dev.to publishing MCP server — see below |

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

`tools/devto_mcp.py` is an MCP server (stdio) that publishes a post to [dev.to](https://dev.to) through
the v1 API. It parses the front matter, rewrites relative image paths to `https://en.hancic.site/...`,
expands the `diagram` shortcode into real images, drops the remaining Hugo shortcodes, and sets
`canonical_url` so the dev.to copy points back here.

| Tool | Purpose |
| --- | --- |
| `sync_post` | Send one post. Draft by default; `publish=true` goes live, `dry_run=true` returns the converted markdown without posting |
| `bake_diagrams` | Regenerate `static/diagrams/` from `assets/diagrams/` — see below |
| `list_articles` | List your dev.to articles (published by default, `published=false` for drafts) |
| `get_article` | Read one article by numeric ID — published only, dev.to does not serve drafts here |
| `update_article` | Update an existing article; fields you do not pass keep their current value |

- Auth: `DEVTO_API_KEY`, generated at <https://dev.to/settings/extensions> and passed through the MCP
  server's `env` block (see `~/.kimi-code/mcp.json`)
- Deps: `mcp[cli]` and `httpx`
- Tags are lowercased and stripped to alphanumerics, because dev.to answers 422 on anything else:
  `distributed-systems` in the front matter arrives as `distributedsystems`. Max 4, first wins.
- `sync_post` reports `diagram_warnings` for any diagram the blog does not serve yet (404) or whose
  published copy lags `assets/`. An empty list means both are fine.

### Diagrams on dev.to

dev.to renders no shortcode and inherits no `currentColor`, so the theme-adaptive trick above does not
survive there. `bake_diagrams` writes a second copy of each diagram into `static/diagrams/` with the
colour frozen to `#1e1e1e` on a white card, and `sync_post` turns
`{{</* diagram "name.svg" "caption" */>}}` into `![caption](https://en.hancic.site/diagrams/name.svg)`
plus an italic caption.

The white card is deliberate: dark ink on a transparent background would be invisible to readers on
dev.to's dark theme, while dark ink on white stays readable on both (it just reads as a card on dark).

Run `bake_diagrams` after adding or editing a diagram, then deploy, because the URLs are the ones
dev.to will fetch. The generated copies are committed so that a fresh clone still deploys them.