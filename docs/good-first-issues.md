# Good First Issues

This guide turns the roadmap into concrete starter contributions. Each idea is designed to preserve the project promise: no API keys, no hosted service requirement, deterministic checks, and evidence a maintainer can verify.

Before opening a pull request:

- Run `pytest -q`.
- Run `python scripts/release_check.py` for public-facing docs, CLI, Action, sample-audit, or static-site changes.
- Add or update tests for any new check behavior.
- Keep findings suppressible through `.labcheck.toml` when false positives are plausible.

## Starter Issue Ideas

| Idea | Labels | Difficulty | Files to inspect | Acceptance criteria |
| --- | --- | --- | --- | --- |
| Reduce false positives for tutorial-style notebooks | `good first issue`, `notebooks`, `false-positive` | Medium | `src/labcheck/source_analysis.py`, `src/labcheck/scanner.py`, `tests/test_source_analysis.py` | A notebook that intentionally introduces examples out of order has a small fixture and either avoids noisy LC002 findings or documents why the finding is still useful. |

## Issue Template

When opening one of these, include:

```text
Problem:
Expected behavior:
Small fixture or public repo:
Finding ID, if relevant:
Suggested acceptance test:
```

## Maintainer Preference

Small PRs are better than heroic PRs. A single check with a fixture, one test, and clear docs is easier to review and more likely to land.

If a contribution adds a dependency, explain why the project still stays no-key, local-first, and safe to run in CI.
