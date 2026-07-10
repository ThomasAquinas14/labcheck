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
        "broken-repo-target-fit.md",
        "broken-repo-outreach-note.md",
        "broken-repo-issue-draft.md",
        "broken-repo-audit.md",
        "broken-repo-audit.html",
    }
    scorecard = (output_dir / "broken-repo-scorecard.md").read_text(encoding="utf-8")
    target_fit = (output_dir / "broken-repo-target-fit.md").read_text(encoding="utf-8")
    outreach_note = (output_dir / "broken-repo-outreach-note.md").read_text(encoding="utf-8")
    issue_draft = (output_dir / "broken-repo-issue-draft.md").read_text(encoding="utf-8")
    markdown = (output_dir / "broken-repo-audit.md").read_text(encoding="utf-8")
    html = (output_dir / "broken-repo-audit.html").read_text(encoding="utf-8")

    assert "# labcheck Scorecard" in scorecard
    assert "Overall score: **39/100**" in scorecard
    assert "## Review Boundary" in scorecard
    assert "does not prove scientific validity" in scorecard
    assert "Explain top finding: `labcheck explain LC001`" in scorecard
    assert "# labcheck Target Fit" in target_fit
    assert "Fit score: **9/10**" in target_fit
    assert "strong outreach candidate" in target_fit
    assert "Safe Framing" in target_fit
    assert "## Review Boundary" in markdown
    assert "does not upload source files to a hosted backend" in markdown
    assert "## Understand Finding Codes" in markdown
    assert "`labcheck explain LC001`" in markdown
    assert "## Next Steps" in markdown
    assert "Scorecard summary: `labcheck scorecard examples/broken-repo`" in markdown
    assert "# labcheck Outreach Note" in outreach_note
    assert "This is not a scientific-validity judgment" in outreach_note
    assert "# labcheck Issue Draft" in issue_draft
    assert "Please treat this as a lightweight maintainer handoff signal" in issue_draft
    assert "# labcheck Report" in markdown
    assert "Overall Score: **39**" in markdown
    assert "<html" in html
    assert "labcheck Report" in html
    assert "Review boundary" in html
    assert "Next steps" in html


def test_checked_in_sample_audits_match_current_generator(tmp_path: Path) -> None:
    builder = _load_builder()
    output_dir = tmp_path / "sample-audits"

    written = builder.build_sample_audits(output_dir)

    for generated_path in written:
        checked_in_path = Path("docs/sample-audits") / generated_path.name
        assert generated_path.read_text(encoding="utf-8") == checked_in_path.read_text(encoding="utf-8")
