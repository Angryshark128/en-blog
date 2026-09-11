#!/usr/bin/env python3
"""dev.to MCP Server：把 Hugo markdown 文章同步到 dev.to，并管理 dev.to 文章。

依赖：mcp[cli], httpx
鉴权：环境变量 DEVTO_API_KEY（https://dev.to/settings/extensions 生成）
运行：python3 devto_mcp.py（stdio transport）
"""

import os
import re
import json
import urllib.request
import urllib.error

import httpx
from mcp.server.fastmcp import FastMCP

API_KEY = os.environ.get("DEVTO_API_KEY", "")
BASE_URL = "https://dev.to/api"
BLOG_URL = "https://en.hancic.site"

mcp = FastMCP("devto")


class DevtoError(Exception):
    """dev.to API error."""


def _api(method: str, path: str, **kwargs) -> dict | list:
    if not API_KEY:
        raise DevtoError(
            "DEVTO_API_KEY is not set. Generate one at https://dev.to/settings/extensions "
            "and put it in the mcp.json entry for this server."
        )
    headers = {"Content-Type": "application/json", "api-key": API_KEY}
    headers.update(kwargs.pop("headers", {}))
    try:
        resp = httpx.request(method, f"{BASE_URL}{path}", headers=headers, timeout=60, **kwargs)
    except httpx.HTTPError as e:
        raise DevtoError(f"Request failed: {e}") from e
    if resp.status_code >= 400:
        try:
            err = resp.json().get("error", resp.text)
        except Exception:
            err = resp.text[:300]
        raise DevtoError(f"HTTP {resp.status_code}: {err}")
    if resp.status_code == 204:
        return {}
    return resp.json()


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Split YAML frontmatter from body."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    yaml_block = parts[1].strip()
    body = parts[2].lstrip("\n")
    meta = {}
    for line in yaml_block.splitlines():
        line = line.strip()
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key == "tags" and val.startswith("["):
            tags = [t.strip().strip('"').strip("'") for t in val.strip("[]").split(",") if t.strip()]
            meta[key] = tags
        else:
            meta[key] = val
    return meta, body


def _convert_images(body: str, base_url: str) -> str:
    """Convert relative image paths to absolute URLs."""
    def md_img(match):
        alt, url = match.group(1), match.group(2)
        if url.startswith("http"):
            return match.group(0)
        if not url.startswith("/"):
            url = "/" + url
        return f"![{alt}]({base_url}{url})"
    body = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', md_img, body)

    def html_img(match):
        full, src = match.group(0), match.group(1)
        if src.startswith("http"):
            return full
        if not src.startswith("/"):
            src = "/" + src
        return full.replace(match.group(1), f"{base_url}{src}")
    body = re.sub(r'<img[^>]*src=["\']([^"\']+)["\'][^>]*>', html_img, body)
    return body


def _strip_shortcodes(body: str) -> str:
    """Convert Hugo shortcodes to plain markdown, remove the rest."""
    def figure(match):
        inner = match.group(1)
        src = re.search(r'src=["\']([^"\']+)["\']', inner)
        alt = re.search(r'(?:alt|title)=["\']([^"\']+)["\']', inner)
        if src:
            return f"![{alt.group(1) if alt else ''}]({src.group(1)})"
        return ""
    body = re.sub(r'\{\{<\s*figure\s+([^>]+)\s*>\}\}', figure, body)
    body = re.sub(r'\{\{<[^>]*>\}\}', '', body)
    body = re.sub(r'\{\{%[^%]*%\}\}', '', body)
    return body


def _sanitize_tags(tags: list[str]) -> list[str]:
    """dev.to rejects tags holding anything but lowercase letters and digits."""
    out = []
    for tag in tags:
        clean = re.sub(r"[^a-z0-9]", "", tag.lower())
        if clean and clean not in out:
            out.append(clean)
    return out[:4]


# ---------------- Tools ----------------

@mcp.tool(description=(
    "Sync a Hugo markdown post to dev.to. Converts relative image paths to absolute URLs "
    "(https://en.hancic.site/...), strips Hugo shortcodes, adds canonical_url pointing to your blog. "
    "Default: creates a draft. Set publish=true to publish immediately. "
    "Set dry_run=true to preview the converted markdown without posting."
))
def sync_post(
    file_path: str,
    publish: bool = False,
    dry_run: bool = False,
) -> dict:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    meta, body = _parse_frontmatter(content)
    body = _strip_shortcodes(body)
    body = _convert_images(body, BLOG_URL)

    slug = meta.get("slug", "")
    canonical = f"{BLOG_URL}/{slug}/" if slug else BLOG_URL

    title = meta.get("title", "Untitled")
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    tags = _sanitize_tags(tags)

    devto_body = f"---\ntitle: {title}\npublished: {'true' if publish else 'false'}\n"
    if tags:
        devto_body += f"tags: {', '.join(tags)}\n"
    devto_body += f"canonical_url: {canonical}\n---\n\n{body}"

    if dry_run:
        return {
            "dry_run": True,
            "title": title,
            "tags": tags,
            "canonical_url": canonical,
            "publish": publish,
            "body_markdown": devto_body,
        }

    result = _api("POST", "/articles", json={
        "article": {
            "title": title,
            "body_markdown": devto_body,
            "published": publish,
        }
    })
    return {
        "success": True,
        "url": result.get("url", ""),
        "id": result.get("id"),
        "published": publish,
        "canonical_url": canonical,
        "tags": tags,
    }


@mcp.tool(description="List your dev.to articles. Default: published. Set published=false for drafts. Use per_page (max 1000) and page to paginate.")
def list_articles(page: int = 1, per_page: int = 30, published: bool = True) -> list:
    params = {"page": page, "per_page": min(per_page, 1000)}
    # dev.to exposes drafts on a separate endpoint; the `published` query param is not honoured.
    path = "/articles/me/published" if published else "/articles/me/unpublished"
    return _api("GET", path, params=params)


@mcp.tool(description=(
    "Get a single dev.to article by its numeric ID, with full body_markdown. "
    "Published articles only: drafts are not served by this endpoint, list them instead."
))
def get_article(article_id: int) -> dict:
    return _api("GET", f"/articles/{article_id}")


@mcp.tool(description=(
    "Update an existing dev.to article. Pass the article ID and new body_markdown. "
    "Other fields (title, tags, canonical_url, published state) stay unchanged unless you pass them."
))
def update_article(
    article_id: int,
    body_markdown: str,
    title: str = "",
    canonical_url: str = "",
    publish: bool | None = None,
) -> dict:
    article: dict = {"body_markdown": body_markdown}
    if title:
        article["title"] = title
    if canonical_url:
        article["canonical_url"] = canonical_url
    if publish is not None:
        article["published"] = publish
    result = _api("PUT", f"/articles/{article_id}", json={"article": article})
    return {"success": True, "url": result.get("url", ""), "id": result.get("id")}


if __name__ == "__main__":
    mcp.run()
