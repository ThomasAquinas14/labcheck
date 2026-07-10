from __future__ import annotations

from html import escape
import re
from urllib.parse import quote, urlparse


DEFAULT_DEMO_URL = "https://thomasaquinas14.github.io/labcheck/demo.html"
DEFAULT_DEMO_LINK_LABEL = "Try this repo in labcheck"
DEMO_LINK_AUDIENCES = frozenset({"general", "professor", "founder", "maintainer"})
GITHUB_REPO_SLUG_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def github_repo_slug(value: str) -> str | None:
    """Return owner/repo for supported GitHub repository inputs."""
    raw = value.strip()
    if not raw:
        return None
    candidate = raw
    if candidate.startswith("github.com/"):
        candidate = f"https://{candidate}"
    if candidate.startswith(("http://", "https://")):
        parsed = urlparse(candidate)
        if parsed.netloc.lower() != "github.com":
            return None
        parts = [part for part in parsed.path.strip("/").split("/") if part]
        if len(parts) < 2:
            return None
        candidate = f"{parts[0]}/{parts[1]}"
    candidate = candidate.removesuffix(".git")
    if not GITHUB_REPO_SLUG_PATTERN.match(candidate):
        return None
    return candidate


def build_demo_link(
    target: str,
    base_url: str = DEFAULT_DEMO_URL,
    auto_audit: bool = False,
    audience: str = "general",
) -> str:
    """Build a prefilled public browser-demo URL for a GitHub repository."""
    slug = github_repo_slug(target)
    if slug is None:
        raise ValueError("demo-link target must be owner/repo or a public GitHub repository URL")
    if audience not in DEMO_LINK_AUDIENCES:
        options = ", ".join(sorted(DEMO_LINK_AUDIENCES))
        raise ValueError(f"demo-link audience must be one of: {options}")
    separator = "&" if "?" in base_url else "?"
    link = f"{base_url}{separator}repo={quote(slug, safe='')}"
    if auto_audit:
        link = f"{link}&audit=1"
    if audience != "general":
        link = f"{link}&audience={quote(audience, safe='')}"
    return link


def render_demo_link(link: str, output_format: str) -> str:
    """Render a demo link as a raw URL, Markdown link, or HTML anchor."""
    if output_format == "url":
        return link
    if output_format == "markdown":
        return f"[{DEFAULT_DEMO_LINK_LABEL}]({link.replace(')', '%29')})"
    if output_format == "html":
        return f'<a href="{escape(link, quote=True)}">{escape(DEFAULT_DEMO_LINK_LABEL)}</a>'
    raise ValueError(f"Unsupported demo-link format: {output_format}")
