# labcheck Target Fit

- Target: `examples/broken-repo`
- Audience: `general`
- Fit score: **9/10**
- Recommendation: **strong outreach candidate**
- Findings: **14** (`5` high, `7` medium, `2` low)
- Overall score: **39/100**

## Why This Target Fits

- Notebook-heavy workflow: 1 notebook found.
- Code-backed workflow: 1 Python file found.
- Concrete audit hook: 14 findings to discuss.
- Clear handoff risk: 5 high-severity findings.
- Visible improvement room: overall score is 39/100.
- Narrow first angle: weakest area is Notebook Determinism at 3/100.
- General fit: there is a clear first follow-up instead of a vague cold message.

## Best Outreach Hook

- Top risk: `LC001` - Suspicious notebook execution order.
- Scope: 1 finding across 1 file.
- First evidence: notebooks/analysis.ipynb: Execution counts are non-monotonic: [1, 5, 3]

## Suggested Ask

If useful, I can send the scorecard or a zipped audit bundle for review.

## Safe Framing

This is a static, no-key first-pass audit. It does not execute the project code by default, does not upload source files to a hosted backend, and does not prove scientific validity; use it to prioritize rerun and handoff risks before deeper verification.

## Next Commands

- Scorecard: `labcheck scorecard examples/broken-repo`
- Outreach note: `labcheck outreach examples/broken-repo --audience general --output labcheck-outreach-note.md`
- Audit bundle: `labcheck pack examples/broken-repo --output-dir labcheck-audit --zip`