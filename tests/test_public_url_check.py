from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker():
    script_path = Path("scripts/check_public_urls.py")
    spec = importlib.util.spec_from_file_location("check_public_urls", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_public_url_checks_cover_launch_assets() -> None:
    checker = _load_checker()

    checks = checker.build_public_url_checks("https://example.com/labcheck")
    paths = {check.path for check in checks}

    assert "" in paths
    assert "demo.html" in paths
    assert "README.md" in paths
    assert "docs/sample-audits/broken-repo-audit.html" in paths
    assert "docs/sample-audits/broken-repo-target-fit.md" in paths
    assert "docs/github-action.md" in paths
    assert "docs/public-deploy-guide.md" in paths
    assert "sitemap.xml" in paths
    assert "llms.txt" in paths


def test_public_url_checker_accepts_expected_content_without_network() -> None:
    checker = _load_checker()
    base_url = "https://example.com/labcheck"
    normalized_base = checker.normalize_base_url(base_url)
    checks = checker.build_public_url_checks(normalized_base)
    payloads = {
        checker.url_for_path(normalized_base, check.path): "\n".join(check.expected_text)
        for check in checks
    }

    def fake_fetch(url: str, timeout: float) -> tuple[int, str]:
        assert timeout == 3.0
        return 200, payloads[url]

    assert checker.check_public_urls(base_url, timeout=3.0, fetcher=fake_fetch) == []


def test_public_url_checker_reports_bad_status_and_missing_text() -> None:
    checker = _load_checker()
    base_url = "https://example.com/labcheck/"
    normalized_base = checker.normalize_base_url(base_url)
    checks = checker.build_public_url_checks(normalized_base)
    payloads = {
        checker.url_for_path(normalized_base, check.path): "\n".join(check.expected_text)
        for check in checks
    }
    payloads[checker.url_for_path(normalized_base, "")] = "partial landing page"

    def fake_fetch(url: str, timeout: float) -> tuple[int, str]:
        if url.endswith("/demo.html"):
            return 404, "not found"
        return 200, payloads[url]

    problems = checker.check_public_urls(base_url, fetcher=fake_fetch)

    assert "/ missing expected text: 'Find the hidden reasons research repos fail to rerun'" in problems
    assert "demo.html returned HTTP 404: https://example.com/labcheck/demo.html" in problems


def test_public_url_checker_rejects_non_http_base_url() -> None:
    checker = _load_checker()

    assert checker.check_public_urls("thomasaquinas14.github.io/labcheck") == [
        "base URL must start with http:// or https://"
    ]


def test_public_url_checker_lists_urls_without_fetching(capsys) -> None:
    checker = _load_checker()

    exit_code = checker.main(["--list", "https://example.com/labcheck"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "landing page: https://example.com/labcheck/" in captured.out
    assert "browser demo: https://example.com/labcheck/demo.html" in captured.out
    assert "sample target-fit card: https://example.com/labcheck/docs/sample-audits/broken-repo-target-fit.md" in captured.out
    assert "llms.txt: https://example.com/labcheck/llms.txt" in captured.out
