from __future__ import annotations

from pathlib import Path

from labcheck.reporters import render_html, render_markdown, render_scorecard
from labcheck.scanner import scan_path


SAMPLE_TARGET = "examples/broken-repo"
DEFAULT_OUTPUT_DIR = Path("docs/sample-audits")


def build_sample_audits(output_dir: Path = DEFAULT_OUTPUT_DIR) -> list[Path]:
    """Regenerate checked-in sample audits from the current scanner/reporters."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report = scan_path(SAMPLE_TARGET)
    files = [
        (output_dir / "broken-repo-scorecard.md", render_scorecard(report)),
        (output_dir / "broken-repo-audit.md", render_markdown(report)),
        (output_dir / "broken-repo-audit.html", render_html(report)),
    ]
    written: list[Path] = []
    for path, content in files:
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    written = build_sample_audits()
    print("Built sample audits:")
    for path in written:
        print(f"- {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
