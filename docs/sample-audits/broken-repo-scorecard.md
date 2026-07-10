# labcheck Scorecard

- Target: `examples/broken-repo`
- Overall score: **39/100**
- Scope: **1 notebook**, **1 Python file**
- Findings: **14** (`5` high, `7` medium, `2` low)
- Weakest area: **Notebook Determinism** (3/100) - Will notebooks run cleanly from top to bottom without invisible state?

## Triage Signal

Not handoff-ready yet: fix 5 high-severity findings before sending this repo to a reviewer, student, or new engineer.

## Review Boundary

This is a static, no-key first-pass audit. It does not execute the project code by default, does not upload source files to a hosted backend, and does not prove scientific validity; use it to prioritize rerun and handoff risks before deeper verification.

## Top Risks

| Risk | Severity | Scope | First evidence |
|---|---|---|---|
| `LC001` Suspicious notebook execution order | `high` | 1 finding across 1 file | notebooks/analysis.ipynb: Execution counts are non-monotonic: [1, 5, 3] |
| `LC002` Likely hidden notebook state | `high` | 1 finding across 1 file | notebooks/analysis.ipynb: 1 cells reference names with no visible prior definition; examples: cell 3: external_state |
| `LC005` Referenced input artifact missing from repo | `high` | 1 finding across 1 file | notebooks/analysis.ipynb: Reads 'data/train.csv', but that path is not present in the scanned repo. |

## First Fixes

1. Fix LC001 first because it affects 1 finding across 1 file.
   Suggested fix: Restart the kernel and run all cells before committing the notebook.
2. Fix LC002 first because it affects 1 finding across 1 file.
   Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.
3. Fix LC005 first because it affects 1 finding across 1 file.
   Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

## Next Steps

- Full Markdown report: `labcheck scan examples/broken-repo --format markdown`
- Scorecard summary: `labcheck scorecard examples/broken-repo`
- Sortable triage CSV: `labcheck scan examples/broken-repo --format csv --output labcheck-findings.csv`
- Shareable audit bundle: `labcheck pack examples/broken-repo --output-dir labcheck-audit --zip`
- Explain top finding: `labcheck explain LC001`