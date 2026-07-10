from __future__ import annotations

import argparse
from typing import Callable, NamedTuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://thomasaquinas14.github.io/labcheck/"
DEFAULT_TIMEOUT_SECONDS = 10.0
USER_AGENT = "labcheck-public-url-smoke/1.0"


class PublicUrlCheck(NamedTuple):
    path: str
    description: str
    expected_text: tuple[str, ...]


FetchText = Callable[[str, float], tuple[int, str]]


def normalize_base_url(base_url: str) -> str:
    """Return a normalized public site root with exactly one trailing slash."""
    normalized = base_url.strip()
    if not normalized:
        raise ValueError("base URL is required")
    if not normalized.startswith(("https://", "http://")):
        raise ValueError("base URL must start with http:// or https://")
    return normalized.rstrip("/") + "/"


def url_for_path(base_url: str, path: str) -> str:
    """Build a public URL for a static export path."""
    normalized_base = normalize_base_url(base_url)
    return normalized_base + path.lstrip("/")


def build_public_url_checks(base_url: str = DEFAULT_BASE_URL) -> list[PublicUrlCheck]:
    """Return live public URLs and text snippets that should survive deployment."""
    site_root = normalize_base_url(base_url)
    return [
        PublicUrlCheck(
            "",
            "landing page",
            (
                "Find the hidden reasons research repos fail to rerun",
                '"@type": "SoftwareApplication"',
                "No API keys required",
            ),
        ),
        PublicUrlCheck(
            "demo.html",
            "browser demo",
            (
                "bounded public GitHub repos",
                "no-API-key browser demo",
                "labcheck browser demo",
            ),
        ),
        PublicUrlCheck(
            "README.md",
            "public README",
            (
                "# labcheck",
                "No paid APIs. No inference bill. No backend secret to protect.",
                "labcheck demo-repo",
            ),
        ),
        PublicUrlCheck(
            "docs/sample-audits/broken-repo-audit.html",
            "sample HTML audit",
            (
                "Review boundary",
                "labcheck",
                "does not upload source files to a hosted backend",
            ),
        ),
        PublicUrlCheck(
            "docs/sample-audits/broken-repo-target-fit.md",
            "sample target-fit card",
            (
                "# labcheck Target Fit",
                "Fit score:",
                "strong outreach candidate",
            ),
        ),
        PublicUrlCheck(
            "docs/github-action.md",
            "GitHub Action guide",
            (
                "ThomasAquinas14/labcheck@v1",
                "min-score",
                "fail-on",
            ),
        ),
        PublicUrlCheck(
            "docs/public-deploy-guide.md",
            "public deploy guide",
            (
                "Oracle Cloud static hosting",
                "host static assets publicly",
                "no Python runtime is required for the public site",
            ),
        ),
        PublicUrlCheck(
            "sitemap.xml",
            "sitemap",
            (
                f"<loc>{site_root}</loc>",
                f"<loc>{site_root}demo.html</loc>",
                f"<loc>{site_root}llms.txt</loc>",
            ),
        ),
        PublicUrlCheck(
            "llms.txt",
            "llms.txt",
            (
                "# labcheck",
                "No API keys are required.",
                "Browser demo:",
            ),
        ),
    ]


def fetch_text(url: str, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> tuple[int, str]:
    """Fetch a URL as UTF-8-ish text and return status plus body."""
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return int(getattr(response, "status", 200)), body
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return exc.code, body
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise RuntimeError(str(reason)) from exc


def check_public_urls(
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    fetcher: FetchText = fetch_text,
) -> list[str]:
    """Return post-deploy public URL issues for the static `labcheck` site."""
    problems: list[str] = []
    try:
        normalized_base = normalize_base_url(base_url)
    except ValueError as exc:
        return [str(exc)]

    for check in build_public_url_checks(normalized_base):
        url = url_for_path(normalized_base, check.path)
        label = check.path or "/"
        try:
            status, text = fetcher(url, timeout)
        except Exception as exc:  # pragma: no cover - exercised by integration use.
            problems.append(f"{label} fetch failed: {exc}")
            continue
        if status < 200 or status >= 300:
            problems.append(f"{label} returned HTTP {status}: {url}")
            continue
        for expected in check.expected_text:
            if expected not in text:
                problems.append(f"{label} missing expected text: {expected!r}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Smoke-test deployed labcheck public URLs.")
    parser.add_argument("base_url", nargs="?", default=DEFAULT_BASE_URL)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--list", action="store_true", help="List URLs that would be checked without fetching them.")
    args = parser.parse_args(argv)

    try:
        normalized_base = normalize_base_url(args.base_url)
    except ValueError as exc:
        print(f"labcheck public URL smoke failed: {exc}")
        return 2

    checks = build_public_url_checks(normalized_base)
    if args.list:
        for check in checks:
            print(f"{check.description}: {url_for_path(normalized_base, check.path)}")
        return 0

    problems = check_public_urls(normalized_base, args.timeout)
    if problems:
        print("labcheck public URL smoke failed:")
        for problem in problems:
            print(f"- {problem}")
        return 1
    print(f"labcheck public URL smoke OK: {normalized_base}")
    print(f"Checked {len(checks)} public URLs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
