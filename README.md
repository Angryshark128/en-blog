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
| `layouts/` | PaperMod overrides, e.g. giscus comments |

## Comments

Giscus (GitHub Discussions), wired in `layouts/partials/comments.html` and enabled site-wide via `params.comments`.