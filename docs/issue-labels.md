# Issue Label Guide

Use these labels when turning a `labcheck` report into GitHub issues, public audit requests, good first issues, or maintainer follow-ups.

The goal is simple triage, not bureaucracy: every issue should be understandable from its severity, category, and one concrete next action.

---

## Label Families

| Family | Examples | Use when |
| --- | --- | --- |
| Severity | `severity/high`, `severity/medium`, `severity/low` | The issue tracks one or more findings from a `labcheck` report. |
| Category | `category/environment`, `category/determinism`, `category/artifacts`, `category/portability`, `category/onboarding` | The issue maps to a `labcheck` finding category. |
| Finding | `finding/lc002`, `finding/lc005` | A repeated finding deserves its own focused issue. |
| Triage | `triage/public-audit`, `triage/false-positive`, `triage/baseline-ratchet` | The issue is about process, suppressions, baseline movement, or public handoff. |
| Workflow | `workflow/cli`, `workflow/browser-demo`, `workflow/github-action` | The work affects a specific surface. |
| Audience | `audience/professor`, `audience/founder`, `audience/maintainer` | The issue supports a specific outreach or adoption path. |

The checked-in catalog lives at [`.github/labels.yml`](https://github.com/ThomasAquinas14/labcheck/blob/main/.github/labels.yml).

---

## Recommended Minimal Labels

For a maintainer issue generated from `labcheck issue`, start with:

```text
severity/high
category/artifacts
finding/lc005
audience/maintainer
```

For a public audit request:

```text
triage/public-audit
audience/professor
workflow/browser-demo
```

For a known expected finding:

```text
triage/false-positive
category/determinism
finding/lc002
```

For a CI baseline cleanup:

```text
triage/baseline-ratchet
workflow/github-action
severity/high
```

Avoid adding every possible label to every issue. If an issue has more than six labels, split it or remove labels that do not change the next action.

---

## Create Labels With GitHub CLI

If you do not use a label-sync tool, create the core labels manually:

```bash
gh label create "severity/high" --color b60205 --description "Blocks reruns, artifact access, install, or unattended execution."
gh label create "severity/medium" --color d93f0b --description "Important reproducibility drift or handoff friction."
gh label create "severity/low" --color fbca04 --description "Polish or metadata that improves reviewer confidence."
gh label create "category/environment" --color 1d76db --description "Runtime, dependency, CI, container, or install reproducibility."
gh label create "category/determinism" --color 5319e7 --description "Notebook order, hidden state, randomness, or unstable ordering."
gh label create "category/artifacts" --color 0e8a16 --description "Inputs, outputs, generated files, data, or provenance."
gh label create "triage/public-audit" --color c2e0c6 --description "Request or result from a public no-key labcheck audit."
gh label create "triage/false-positive" --color fef2c0 --description "Finding may be expected, archival, generated, or too noisy."
gh label create "workflow/github-action" --color 0052cc --description "GitHub Action, SARIF, CI gate, or job summary workflow."
```

Then add finding-specific labels only when they help group repeated work:

```bash
gh label create "finding/lc002" --color ededed --description "Likely hidden notebook state."
gh label create "finding/lc005" --color ededed --description "Referenced input artifact missing from repo."
```

---

## Triage Examples

| Scenario | Suggested labels |
| --- | --- |
| Hidden notebook state in one tutorial notebook | `severity/high`, `category/determinism`, `finding/lc002`, `triage/false-positive` |
| Missing training data path in an audit report | `severity/high`, `category/artifacts`, `finding/lc005`, `audience/maintainer` |
| Add a GitHub Action baseline for an old lab repo | `triage/baseline-ratchet`, `workflow/github-action`, `audience/professor` |
| Improve the browser demo copy flow | `workflow/browser-demo`, `audience/founder`, `triage/good-first-audit` |
| Public repo audit request from a professor | `triage/public-audit`, `audience/professor`, `workflow/browser-demo` |

When in doubt, choose one severity, one category, and one next-action label.

---

## Maintainer Notes

- Keep `finding/lcXXX` labels lowercase so issue search is predictable.
- Prefer category labels for broad cleanup issues and finding labels for narrow repeated failures.
- Use `triage/false-positive` only when the issue documents why the finding is expected.
- Use `triage/baseline-ratchet` for work that lowers or regenerates a committed baseline.
- Do not use labels to imply scientific validity; `labcheck` is a first-pass reproducibility and handoff audit.
