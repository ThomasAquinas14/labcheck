# Launch Kit

Use this when creating the public GitHub repository, publishing the static site, or sending the first outreach messages.

The goal is to make `labcheck` instantly legible:

> a no-key reproducibility auditor for notebook-heavy research and ML repos.

---

## GitHub Repository Setup

### Repository name

`labcheck`

### Description

```text
No-key reproducibility audits for notebook-heavy research and ML repos.
```

### Website

Use the published static site URL after GitHub Pages, Netlify, Cloudflare Pages, or OCI static hosting is enabled.

### Topics

```text
reproducibility
jupyter-notebook
machine-learning
research-software
data-science
github-action
static-analysis
notebook
ci
open-source
```

### README hero promise

```text
Find the hidden reasons research repos fail to rerun.
```

---

## Pre-Launch Gate

Run this before tagging, posting, or sending outreach:

```bash
python scripts/release_check.py
python scripts/check_publish_ready.py
```

The gate proves:

- tests pass
- sample audits regenerate
- static site export builds
- self-scan scores 100
- clean example scores 100
- broken example fails the high-severity gate

If this fails, fix the failure before launching.

---

## First Launch Post

```text
I built labcheck: an open-source reproducibility auditor for research and ML repos.

It catches the boring-but-painful things that make notebook-heavy repos hard to hand off:

- hidden notebook state
- missing input artifacts
- unpinned dependencies
- README commands pointing to missing files
- unseeded randomness
- result files with unclear provenance

No API keys, no hosted backend, no inference bill.

Try the browser demo or run:

pip install -e .
labcheck scorecard examples/broken-repo

GitHub: <repo-url>
Demo: <demo-url>
```

---

## Professor Outreach Snippet

```text
I built a small open-source tool called labcheck that audits notebook-heavy research repos for reproducibility and handoff issues: hidden notebook state, missing input artifacts, unpinned dependencies, stale README commands, and unclear output provenance.

It runs locally or in GitHub Actions without any paid API dependency. I thought it might be useful for lab handoffs, student onboarding, or pre-submission repo checks.

If helpful, I can run it on one of your public repos and send a short scorecard.
```

---

## Founder Outreach Snippet

```text
I built labcheck, a no-key reproducibility and portability auditor for experiment-heavy ML/data repos.

It is meant for the moment before a codebase gets handed to a new engineer, reviewer, contractor, or diligence team. It surfaces hidden notebook state, missing artifacts, README drift, unseeded randomness, and result files with unclear provenance.

If useful, I can run it on one of your public repos and send a compact scorecard.
```

---

## Best Assets To Link

- [Browser demo](../site/demo.html)
- [Sample HTML audit](sample-audits/broken-repo-audit.html)
- [Sample scorecard](sample-audits/broken-repo-scorecard.md)
- [Public case studies](case-studies.md)
- [GitHub Action guide](github-action.md)
- [Public deploy guide](public-deploy-guide.md)

---

## Launch Order

1. Run `python scripts/release_check.py`.
2. Run `python scripts/check_publish_ready.py`.
3. If you want a separate publish folder, create it with `python scripts/export_standalone_repo.py .tmp-standalone-labcheck`.
4. Create and push the public GitHub repository:
   `gh repo create ThomasAquinas14/labcheck --public --source=. --remote=origin --push`
5. Enable GitHub Pages from the Pages workflow.
6. Add the repository description, website, and topics above, or use the commands in [github-publish-guide.md](github-publish-guide.md).
7. Pin the sample scorecard/HTML audit in the README and launch post.
8. Follow [launch-week-plan.md](launch-week-plan.md) for the first seven days.
9. Track the first 20 messages with [outreach-tracker-template.md](outreach-tracker-template.md).
10. Collect replies and turn the best feedback into issues.

The export folder intentionally excludes `dist/`, caches, virtualenvs, local env files, generated audit packs, and parent-project artifacts. Rebuild `dist/site` in CI or with `python scripts/build_static_site.py` after the standalone repo exists.

---

## What Not To Claim

Avoid saying:

- "solves reproducibility"
- "proves a paper is reproducible"
- "guarantees the repo can rerun"

Say instead:

- "surfaces reproducibility and handoff risks"
- "finds common notebook and experiment repo failure modes"
- "gives reviewers and new team members a first-pass scorecard"

That framing is more accurate and more trustworthy.
