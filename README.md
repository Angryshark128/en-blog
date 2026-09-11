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
drops Hugo shortcodes, and sets `canonical_url` so the dev.to copy points back here.

| Tool | Purpose |
| --- | --- |
| `sync_post` | Send one post. Draft by default; `publish=true` goes live, `dry_run=true` returns the converted markdown without posting |
| `list_articles` | List your dev.to articles (published by default) |
| `get_article` / `update_article` | Read or update an existing article by numeric ID |

- Auth: `DEVTO_API_KEY`, generated at <https://dev.to/settings/extensions> and passed through the MCP
  server's `env` block (see `~/.kimi-code/mcp.json`)
- Deps: `mcp[cli]` and `httpx`
- Known gap: the `diagram` shortcode used above is stripped, so illustrated posts reach dev.to without
  their figures. Plain Markdown/HTML images are rewritten and survive.