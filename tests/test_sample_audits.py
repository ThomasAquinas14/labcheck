from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_builder():
    script_path = Path("scripts/build_sample_audits.py")
    spec = importlib.util.spec_from_file_location("build_sample_audits", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sample_audit_builder_writes_public_artifacts(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = tmp_path / "sample-audits"

    written = builder.build_sample_audits(output_dir)

    names = {path.name for path in written}
    assert names == {
        "broken-repo-scorecard.md",
        "broken-repo-audit.md",
        "broken-repo-audit.html",
    }
    scorecard = (output_dir / "broken-repo-scorecard.md").read_text(encoding="utf-8")
    markdown = (output_dir / "broken-repo-audit.md").read_text(encoding="utf-8")
    html = (output_dir / "broken-repo-audit.html").read_text(encoding="utf-8")

    assert "# labcheck Scorecard" in scorecard
    assert "Overall score: **44/100**" in scorecard
    assert "# labcheck Report" in markdown
    assert "Overall Score: **44**" in markdown
    assert "<html" in html
    assert "labcheck Report" in html
