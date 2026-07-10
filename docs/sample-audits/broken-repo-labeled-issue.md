# Labeled Audit Issue Bundle

This bundle shows how to turn the generated [broken repo issue draft](broken-repo-issue-draft.md) into a public GitHub issue with labels, board fields, and a narrow next action.

Use it as a model for launch-week public audits. Keep the language respectful: `labcheck` is a no-key static reproducibility and handoff audit, not a scientific-validity judgment.

---

## Issue Metadata

Suggested title:

```text
Reproducibility handoff gaps in `examples/broken-repo`
```

Suggested labels:

```text
severity/high
category/determinism
category/artifacts
finding/lc001
finding/lc002
finding/lc005
audience/maintainer
triage/public-audit
```

Suggested public triage board fields:

| Field | Value |
| --- | --- |
| Status | Ready To Fix |
| Audience | OSS Maintainer |
| Workflow | CLI |
| Severity | High |
| Category | Determinism |
| Finding ID | `LC001`, `LC002`, `LC005` |
| Fit Score | 8 |
| Public Repo | `examples/broken-repo` |
| Next Action | Confirm whether the hidden state and missing input artifact are expected; if not, fix the first top-risk notebook. |

---

## Create The Issue With GitHub CLI

```bash
gh issue create \
  --title "Reproducibility handoff gaps in examples/broken-repo" \
  --body-file docs/sample-audits/broken-repo-issue-draft.md \
  --label "severity/high" \
  --label "category/determinism" \
  --label "category/artifacts" \
  --label "finding/lc001" \
  --label "finding/lc002" \
  --label "finding/lc005" \
  --label "audience/maintainer" \
  --label "triage/public-audit"
```

If the issue is too broad, split it into the first concrete finding:

```text
Title: Make `notebooks/analysis.ipynb` rerun cleanly from a fresh kernel
Labels: severity/high, category/determinism, finding/lc001, finding/lc002, audience/maintainer
Next action: Restart the kernel, run all cells top-to-bottom, and make the `external_state` setup explicit.
```

---

## Comment To Add After Opening

```text
I opened this from a local `labcheck` run and kept the labels narrow:

- `severity/high` because the notebook currently depends on hidden runtime state and a missing input artifact.
- `category/determinism` for the execution-order and hidden-state findings.
- `category/artifacts` for the missing `data/train.csv` input.
- `triage/public-audit` because this is a public no-key handoff review.

If any finding is expected or intentionally out of scope, I can update the issue with a targeted suppression example instead of treating it as a bug.
```

---

## Board Placement

Put the issue in the [public triage board](../public-triage-board.md):

- Start in `Ready To Fix` if this is your own example repo or a maintainer has already asked for fixes.
- Start in `Waiting On Maintainer` if you are opening it on someone else's project and need context.
- Move to `Case Study Candidate` only after the maintainer reply teaches a reusable lesson.

Close the issue when the first top-risk item is fixed, documented as expected, or intentionally split into a smaller issue.

When a maintainer replies, use the [maintainer reply templates](../maintainer-reply-templates.md) to keep the follow-up scoped and respectful.
