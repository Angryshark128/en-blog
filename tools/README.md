# dev.to publishing tools

`devto_mcp.py` is an MCP server (stdio) that publishes posts to [dev.to](https://dev.to) over the v1
API. `raster/` is the SVG→PNG renderer it needs for diagrams.

Both are specific to this repo rather than a general-purpose package: the server derives the repo root
from its own location and reads `content/posts/`, `assets/diagrams/` and `static/diagrams/` directly.

## Requirements

- Python 3.10+ with `mcp[cli]` and `httpx`
- Node 18+, plus `npm install --prefix tools/raster` — only `bake_diagrams` needs it
- `DEVTO_API_KEY`, generated at <https://dev.to/settings/extensions>

The two Inter faces the renderer uses are fetched into `tools/raster/fonts/` on the first bake. The
host has no system fonts, which is also why the faces ship with the tool.

## Register it

Any MCP client that speaks stdio works the same way. For kimi-code, add to `~/.kimi-code/mcp.json`:

```json
{
  "mcpServers": {
    "devto": {
      "command": "python3",
      "args": ["/root/repos/en-blog/tools/devto_mcp.py"],
      "env": { "DEVTO_API_KEY": "your-key" }
    }
  }
}
```

MCP servers are read when a session starts, so restart the client after editing the file.

## Tools

| Tool | Parameters | What it does |
| --- | --- | --- |
| `sync_post` | `file_path`, `publish=false`, `dry_run=false` | Convert one post and POST it as a draft. `publish=true` goes live; `dry_run=true` returns the converted markdown without posting. Reports `diagrams` and `diagram_warnings`. |
| `bake_diagrams` | — | Render every `assets/diagrams/*.svg` to a PNG in `static/diagrams/`, and delete orphans left by renamed diagrams. Run it after adding or editing a diagram, then deploy. |
| `list_articles` | `page=1`, `per_page=30`, `published=true` | List your articles. `published=false` lists drafts. |
| `get_article` | `article_id` | Read one article with its `body_markdown`. Published only — a draft answers 404 here. |
| `update_article` | `article_id`, `body_markdown`, `title=""`, `canonical_url=""`, `publish=None` | Update a post. Fields you leave out keep their current value. |

## Typical run

1. Write `content/posts/my-post.md`, put any diagrams in `assets/diagrams/`.
2. `bake_diagrams` — only when a diagram was added or changed.
3. `hugo --minify` and deploy: dev.to fetches these images over HTTP, so they have to be live first.
4. `sync_post(file_path, dry_run=True)` — read the converted markdown, the tags, the `canonical_url`
   and `diagram_warnings`.
5. `sync_post(file_path)` — creates a draft. Review it on dev.to.
6. `update_article(id, body_markdown, publish=True)` — goes live.

Step 4's output is meant to be handed to step 5 or 6 as-is, so regenerate it with the same `publish`
value you intend to use (see the `published` gotcha below).

## What the conversion does

- front matter → `title`, `tags`, and `canonical_url` pointing at `<blog>/<slug>/`
- tags → lowercased with non-alphanumerics dropped, at most 4, first wins
- `![](relative)` and `<img src="relative">` → absolute URLs on the blog
- `{{< diagram "name.svg" "caption" >}}` → `![caption](…/diagrams/name.png)` plus an italic caption
- every other Hugo shortcode is dropped

## Gotchas, learned the hard way

- **Tags.** dev.to answers `422 Tag "x" contains non-alphanumeric…` for anything but lowercase letters
  and digits, so `distributed-systems` arrives as `distributedsystems`.
- **Publishing.** dev.to gives the `published` field in the body's front matter priority over the API
  field. A body produced by `sync_post(dry_run=True, publish=False)` carries `published: false`, and
  sending it with `publish=true` updates the post and reports success while leaving it a draft.
  `update_article` rewrites that line when `publish` is passed; regenerating the body with a matching
  flag is the other half of the fix.
- **Drafts.** `get_article` serves published articles only. List drafts with
  `list_articles(published=false)` — dev.to silently ignores `/articles/me?published=false`, drafts
  live on `/articles/me/unpublished`.
- **Diagrams must be raster.** dev.to proxies every external image through its own imgproxy, which
  cannot rasterise SVG: it returns the SVG bytes labelled `Content-Type: image/webp`, so the request is
  a 200 and the reader sees nothing. That is the whole reason for the PNG step.
- **Re-hosting.** Once a post is published, dev.to copies each image onto its own
  `dev-to-uploads.s3.amazonaws.com` storage and serves it from there. The published post therefore no
  longer depends on this blog staying up, but re-baking a diagram will not retroactively update an
  already published post.
