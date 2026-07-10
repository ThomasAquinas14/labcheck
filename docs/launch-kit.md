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

### Issue labels

Use [issue-labels.md](issue-labels.md) to seed severity, category, finding, workflow, and audience labels before opening public audit requests. The reusable catalog lives at [`.github/labels.yml`](https://github.com/ThomasAquinas14/labcheck/blob/main/.github/labels.yml).

### Public triage board

Use [public-triage-board.md](public-triage-board.md) to track audit requests, false positives, good first issues, and case-study candidates without promising private-code review or scientific validation.

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
- broken requirements/constraints includes
- missing local editable/path dependencies
- missing project-local helper modules imported by notebooks or scripts
- floating Docker base images that can drift between rebuilds
- Dockerfiles that copy the repo but never install the dependency manifest
- undocumented environment variables
- undocumented GPU/CUDA or accelerator requirements
- interactive prompts that block unattended reruns
- inline OS package installs hidden in notebooks or scripts
- conflicting Python runtime declarations
- README commands pointing to missing files, Python modules, Makefile targets, package scripts, or project scripts
- GitHub Actions workflows pointing to missing scripts or dependency files
- GitHub Actions workflows that install/setup but never verify the repo
- GitHub Actions using floating action refs
- GitHub Actions Python versions that disagree with the repo runtime
- unseeded randomness
- ML split/seed drift in NumPy Generator, sklearn, pandas, Polars, PyTorch split/DataLoader/worker flows, TensorFlow, XGBoost, Optuna, and JAX
- output save paths that will fail because the generated directory is missing
- glob/listdir input paths that point at missing data directories
- remote downloads that can hang because no timeout is set
- remote artifacts with no checksum/hash verification
- inline OS package installs such as apt/brew/apk setup hidden in notebook cells
- Dockerfiles that skip requirements/pyproject/Conda install steps
- unsorted glob/listdir/Path.glob discovery that can change input order
- timestamp-derived output filenames that make reruns harder to compare
- Hugging Face model/dataset calls that omit revision pins
- result files with unclear provenance

No API keys, no hosted backend, no inference bill.

Try the browser demo or run:

pip install -e .
labcheck demo-repo
labcheck scorecard labcheck-demo-repo
labcheck scorecard examples/broken-repo
labcheck target-fit https://github.com/owner/repo --audience professor --output labcheck-target-fit.md
labcheck demo-link https://github.com/owner/repo
labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit
labcheck outreach examples/broken-repo --output labcheck-outreach-note.md
labcheck outreach examples/broken-repo --audience professor --output labcheck-professor-note.md
labcheck outreach examples/broken-repo --audience founder --output labcheck-founder-note.md
labcheck issue examples/broken-repo --output labcheck-issue-draft.md

GitHub: <repo-url>
Demo: <demo-url>
```

---

## Professor Outreach Snippet

```text
I built a small open-source tool called labcheck that audits notebook-heavy research repos for reproducibility and handoff issues: hidden notebook state, missing input artifacts, missing globbed data directories, unsorted file discovery, mutable remote data, unbounded remote downloads, remote artifacts with no checksum/hash verification, and unpinned Hugging Face artifacts, unpinned dependencies, moving VCS dependency refs, imports missing from manifests, missing local helper modules, broken requirements includes, missing local path dependencies, missing generated output directories, timestamped output drift, floating Docker/GitHub Actions references, Dockerfiles that skip dependency installs, CI workflows that install but never verify, undocumented environment variables, undocumented GPU/CUDA requirements, interactive rerun blockers, hidden OS package installs, missing setup steps, unpinned inline notebook installs, stale README/CI commands, CI/runtime mismatches, NumPy/ML split/seed drift, and unclear output provenance.

It runs locally or in GitHub Actions without any paid API dependency. I thought it might be useful for lab handoffs, student onboarding, or pre-submission repo checks.

If helpful, I can run it on one of your public repos and send a short scorecard.
```

---

## Founder Outreach Snippet

```text
I built labcheck, a no-key reproducibility and portability auditor for experiment-heavy ML/data repos.

It is meant for the moment before a codebase gets handed to a new engineer, reviewer, contractor, or diligence team. It surfaces hidden notebook state, missing artifacts, globbed input directories that were never shared, unsorted file discovery that can reshuffle inputs, unpinned Hugging Face datasets/models, undocumented GPU/CUDA requirements, unbounded remote downloads, remote artifacts with no checksum/hash verification, hidden OS package installs, Dockerfiles that skip dependency manifests, interactive prompts that block unattended reruns, generated output paths that will fail on a fresh clone, timestamped output paths that drift between reruns, local dependency paths that were never shared, README drift, NumPy/ML split/seed drift, unseeded randomness, and result files with unclear provenance.

If useful, I can run it on one of your public repos and send a compact scorecard.
```

---

## Best Assets To Link

- [Browser demo](../site/demo.html)
- [Demo video script](demo-video-script.md)
- [Sample HTML audit](sample-audits/broken-repo-audit.html)
- [Sample scorecard](sample-audits/broken-repo-scorecard.md)
- [Sample target-fit card](sample-audits/broken-repo-target-fit.md)
- [Sample issue draft](sample-audits/broken-repo-issue-draft.md)
- [Sample labeled issue bundle](sample-audits/broken-repo-labeled-issue.md)
- [Maintainer reply templates](maintainer-reply-templates.md)
- [Public case studies](case-studies.md)
- [Reply-derived case study seed](reply-derived-case-study-seed.md)
- [Reply to case study checklist](reply-to-case-study-checklist.md)
- [Comparison guide](comparison.md)
- [Install guide](install.md)
- [GitHub Action guide](github-action.md)
- [Reproducibility pattern gallery](reproducibility-patterns.md)
- [Launch post after-action checklist](launch-post-after-action.md)
- [Public deploy guide](public-deploy-guide.md)

---

## Launch Order

1. Run `python scripts/release_check.py`.
2. Run `python scripts/check_publish_ready.py`.
3. If you want a separate publish folder, create it with `python scripts/export_standalone_repo.py .tmp-standalone-labcheck`.
4. Create and push the public GitHub repository:
   `gh repo create ThomasAquinas14/labcheck --public --source=. --remote=origin --push`
5. Enable GitHub Pages from the Pages workflow.
6. Run `python scripts/check_public_urls.py https://thomasaquinas14.github.io/labcheck/` after Pages is live.
7. Add the repository description, website, and topics above, or use the commands in [github-publish-guide.md](github-publish-guide.md).
8. Record the short walkthrough using [demo-video-script.md](demo-video-script.md), or at least use it as the launch-post narrative.
9. Pin the sample scorecard/HTML audit in the README and launch post.
10. After posting, record the evidence with [launch-post-after-action.md](launch-post-after-action.md).
11. Follow [launch-week-plan.md](launch-week-plan.md) for the first seven days.
12. Track the first 20 messages with [outreach-tracker-template.md](outreach-tracker-template.md).
13. Collect replies and turn the best feedback into issues or bounded case studies with [reply-to-case-study-checklist.md](reply-to-case-study-checklist.md). Use [reply-derived-case-study-seed.md](reply-derived-case-study-seed.md) for the first conversion format, but replace the seed before claiming real external validation.

The export folder intentionally excludes `dist/`, caches, virtualenvs, local env files, generated audit packs, and parent-project artifacts. Rebuild `dist/site` in CI or with `python scripts/build_static_site.py` after the standalone repo exists, then run `python scripts/check_static_export.py` before publishing the public folder.

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
