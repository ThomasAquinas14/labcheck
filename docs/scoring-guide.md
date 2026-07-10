# Scoring Guide

`labcheck` scores are triage signals for reproducibility and handoff risk. They are not a claim that a paper, model, dataset, or benchmark result is scientifically valid.

The score answers a narrower question:

> If a new student, reviewer, maintainer, or engineer cloned this repo today, how likely are they to rebuild the environment, rerun the workflow, find the required artifacts, and understand what changed?

---

## What The Scores Mean

Use the score as a prioritization aid, not as a badge of truth.

| Score | Interpretation | Suggested action |
| --- | --- | --- |
| 90-100 | Strong handoff candidate | Keep it green with CI, a baseline, and clear artifact policy. |
| 75-89 | Mostly usable | Fix medium-severity issues before a formal lab handoff, PR review, or founder diligence share. |
| 50-74 | Needs cleanup | Start with high-severity findings and missing setup/artifact paths. |
| 0-49 | Not handoff-ready | Expect a new person to get blocked without help from the original author. |

Any high-severity finding should be treated as a blocker for public handoff even if the numeric score is still moderate.

---

## Category Scores

The overall score is built from five categories:

| Category | What it asks |
| --- | --- |
| Environment Rebuildability | Can a new person recreate the runtime without guesswork? |
| Notebook Determinism | Will notebooks run cleanly from top to bottom without hidden state? |
| Artifact Availability | Are referenced inputs and generated artifacts present or clearly accounted for? |
| Portability | Does the repo avoid machine-specific assumptions and brittle paths? |
| Onboarding Readiness | Can the docs and repo structure guide a new contributor without private context? |

The weakest category matters because a repo can look polished in four areas and still be blocked by one missing dataset, runtime conflict, or hidden notebook state.

---

## How The Formula Works

Each finding has a severity penalty:

| Severity | First finding penalty |
| --- | ---: |
| High | 26 points |
| Medium | 14 points |
| Low | 6 points |

Repeated findings from the same check are discounted so one repeated pattern does not drown out every other signal. The first finding from a check receives the full penalty; additional findings from the same check receive 35% of their severity penalty. A single check can subtract at most 72 points from a category.

After category scores are calculated, the overall score weights both breadth and the weakest area:

```text
overall = round(category_average * 0.70 + weakest_category * 0.30)
```

This keeps a repo from getting an overly rosy score when one critical handoff dimension is very weak.

---

## How To Improve A Score Responsibly

Start with the top risks in the scorecard:

```bash
labcheck scorecard .
```

Then fix in this order:

1. High-severity findings that block reruns, artifact access, dependency installation, or unattended execution.
2. Medium-severity drift such as stale README commands, floating dependency references, and CI verification gaps.
3. Low-severity polish that improves reviewer confidence and reduces support questions.

Use suppressions sparingly. A targeted suppression is appropriate for archived, generated, or intentionally unsupported paths:

```toml
[[ignored_findings]]
check_id = "LC010"
path = "archive/old_experiment.py"
reason = "Archival script kept for context, not a supported rerun path."
```

Avoid suppressing inconvenient but real issues. If a future collaborator will hit the problem, fix it or document the tradeoff instead.

---

## What A Good Score Does Not Prove

A high `labcheck` score does not prove:

- the results are correct
- the paper is reproducible end to end
- the model is fair, safe, or performant
- the dataset is licensed correctly
- the workflow has no security risk

It only means the repository looks easier to rerun, review, and hand off based on deterministic evidence available in the files.

For stronger confidence, pair `labcheck` with notebook execution tests, CI, environment lockfiles, data-versioning restore checks, human review, and domain-specific validation.
