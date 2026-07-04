from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


CONFIG_TEMPLATE = """# labcheck configuration
# Keep exclusions narrow so the audit still reflects the repo's real reproducibility.
exclude = [
  ".ipynb_checkpoints/**",
  "labcheck-audit/**",
  # "archive/**",
  # "notebooks/generated/**",
  # "scratch/**",
]

# Disable checks only when a repo has an intentional pattern that would otherwise
# create repeated low-signal findings.
disabled_checks = [
  # "LC010",
]
"""

WORKFLOW_TEMPLATE = """name: labcheck

on:
  pull_request:
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: labcheck
        name: Run labcheck
        uses: ThomasAquinas14/labcheck@v1
        with:
          target: "."
          config-path: .labcheck.toml
          report-format: markdown
          report-path: labcheck-report.md
          json-path: labcheck-report.json
          sarif-path: labcheck-report.sarif
          badge-path: labcheck-badge.svg
          scorecard-path: labcheck-scorecard.md
          max-findings: "100"
          fail-on: none
          min-score: ""

      - name: Upload labcheck reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: labcheck-report
          path: |
            labcheck-report.md
            labcheck-report.json
            labcheck-report.sarif
            labcheck-badge.svg
            labcheck-scorecard.md
"""


POLICY_TEMPLATE = """# Reproducibility Policy

This repo uses `labcheck` as a lightweight reproducibility and onboarding gate.

The goal is not to prove that every result is scientifically valid. The goal is to make sure a new collaborator can understand, rebuild, and rerun the repository without relying on hidden local state.

## Expected handoff standard

Before a notebook, experiment, or result artifact is considered ready to hand off:

- notebooks should run top-to-bottom from a fresh kernel
- committed notebooks should not contain saved traceback outputs
- required input artifacts should be committed or clearly documented
- generated outputs should have an obvious producer notebook or script
- dependencies should be pinned or intentionally bounded
- the Python runtime version should be declared
- README commands should point to files that exist
- randomness should use visible seeds when deterministic comparison matters
- machine-local paths should be replaced with project-relative paths or documented configuration

## Local check

Run this before opening a pull request or handing the repo to a new collaborator:

```bash
labcheck scorecard . --config .labcheck.toml
labcheck scan . --config .labcheck.toml --format markdown
```

For stricter local gating:

```bash
labcheck scan . --config .labcheck.toml --fail-on high --min-score 80
```

## CI policy

Start with a soft audit that uploads reports and writes a job summary. Once the baseline noise is understood, turn on one of these gates:

```yaml
fail-on: high
min-score: "80"
```

For existing repos, create a baseline once:

```bash
labcheck baseline . --config .labcheck.toml --output .labcheck-baseline.json
```

Then ratchet down the baseline as real issues are fixed.

## Triage guidance

Treat findings as reproducibility signals, not blame.

- Fix high-severity findings first.
- Prefer documenting unavoidable external artifacts over silently ignoring them.
- Use `.labcheck.toml` exclusions for archived, generated, or intentionally noisy paths.
- Disable checks only when the repo has a deliberate pattern that would otherwise create repeated low-signal findings.

## Reviewer checklist

- [ ] `labcheck scan . --config .labcheck.toml` has been run.
- [ ] Any high-severity findings are fixed or explained.
- [ ] New notebooks were restarted and run top-to-bottom before commit.
- [ ] New input data contracts are documented.
- [ ] New generated outputs have visible producer code.
- [ ] New setup instructions were tested from a clean checkout.
"""


@dataclass(slots=True)
class InitResult:
    root: Path
    created: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)


def _write_template(path: Path, content: str, force: bool, result: InitResult) -> None:
    if path.exists() and not force:
        result.skipped.append(path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    result.created.append(path)


def init_project(
    root: Path,
    force: bool = False,
    include_workflow: bool = True,
    include_policy: bool = False,
) -> InitResult:
    resolved_root = root.resolve()
    if not resolved_root.exists() or not resolved_root.is_dir():
        raise FileNotFoundError(f"labcheck init target must be an existing directory: {root}")

    result = InitResult(root=resolved_root)
    _write_template(resolved_root / ".labcheck.toml", CONFIG_TEMPLATE, force, result)
    if include_workflow:
        _write_template(resolved_root / ".github" / "workflows" / "labcheck.yml", WORKFLOW_TEMPLATE, force, result)
    if include_policy:
        _write_template(resolved_root / "docs" / "reproducibility.md", POLICY_TEMPLATE, force, result)
    return result
