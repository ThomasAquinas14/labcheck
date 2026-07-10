# Lab and Team Adoption Guide

`labcheck` is most useful when it becomes a small, repeatable handoff ritual instead of a one-time audit.

This guide is written for research labs, course repos, and ML/data teams that want a lightweight reproducibility standard without adding paid APIs or hosted infrastructure.

---

## Start with a soft audit

Add the config and GitHub Action:

```bash
labcheck init .
```

This creates:

- `.labcheck.toml`
- `.github/workflows/labcheck.yml`

The generated workflow uploads scorecard, target-fit, issue draft, Markdown, CSV, JSON, SARIF, and badge reports without failing CI. It requests only `contents: read`, so the default setup does not need repository secrets or write permissions. Report artifacts use a short retention window and still upload when you later turn on a failing gate.

---

## Add a repo policy

For labs and teams, create a ready-to-edit handoff policy too:

```bash
labcheck init . --policy
```

This adds:

- `docs/reproducibility.md`

Use that document as the repo's agreement for notebook reruns, input artifacts, generated outputs, dependency pinning, runtime metadata, README commands, and review expectations.

---

## Ratchet instead of blocking everything on day one

For existing repos, do not immediately fail every pull request.

Start with visibility:

```yaml
fail-on: none
min-score: ""
```

Then create a baseline:

```bash
labcheck baseline . --config .labcheck.toml --output .labcheck-baseline.json
```

After the team understands the output, turn on a first gate:

```yaml
baseline-path: .labcheck-baseline.json
fail-on: high
```

Later, add a score floor:

```yaml
min-score: "80"
```

---

## Suggested lab policy wording

Copy this into a course, lab, or project README:

> This repository uses `labcheck` as a reproducibility handoff check. Before submitting a final notebook, experiment, or result artifact, run `labcheck scorecard . --config .labcheck.toml` for a quick triage summary and `labcheck scan . --config .labcheck.toml` for the full report. High-severity findings should be fixed or explicitly documented. The goal is not perfection; the goal is that another student, reviewer, or engineer can rebuild the environment, understand required inputs, and rerun the workflow without relying on hidden local state.

---

## Suggested founder/team policy wording

Copy this into an engineering handbook or project README:

> This repository uses `labcheck` to catch experiment handoff risks before they slow down onboarding or due diligence. Pull requests that change notebooks, data-loading code, generated outputs, or setup instructions should include a fresh `labcheck` run. High-severity findings should be fixed before merge unless the missing artifact or external dependency is intentionally documented.

---

## What to review first

When a report is long, review in this order:

1. High-severity top risks
2. Missing input artifacts
3. Saved notebook errors
4. Hidden notebook state
5. README command drift
6. Missing setup or run instructions
7. Python runtime and dependency metadata
8. Orphan outputs and disconnected workflow files

That order keeps the discussion focused on whether a new person can actually rerun the work.
