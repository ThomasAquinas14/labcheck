# Outreach Playbook

This document is for turning `labcheck` from a neat repo into something people actually reply to, share, and try.

The goal is not to pitch "my project."

The goal is to pitch:

> a useful reproducibility and onboarding tool that solves a real pain point for research and ML-heavy repos.

---

## What to send

When you reach out, do not dump the whole repo.

Send one or two sharp assets:

- the static landing page
- the browser demo for local files or bounded public GitHub URLs
- one generated outreach note
- one compact scorecard
- one sample HTML audit
- one relevant case study

Best starting set:

1. [site/index.html](../site/index.html)
2. [site/demo.html](../site/demo.html)
3. [broken-repo-audit.html](sample-audits/broken-repo-audit.html)
4. [case-studies.md](case-studies.md)
5. [demo-video-script.md](demo-video-script.md)
6. [launch-week-plan.md](launch-week-plan.md)
7. [outreach-tracker-template.md](outreach-tracker-template.md)

Generate a ready-to-edit first draft with:

```bash
labcheck demo-link https://github.com/owner/repo --audience professor --output labcheck-demo-link.txt
labcheck target-fit https://github.com/owner/repo --audience professor --output labcheck-target-fit.md
labcheck outreach https://github.com/owner/repo --output labcheck-outreach-note.md
labcheck outreach https://github.com/owner/repo --audience professor --output labcheck-professor-note.md
labcheck outreach https://github.com/owner/repo --audience founder --output labcheck-founder-note.md
```

Read `labcheck-target-fit.md` before sending anything. It scores whether the repo has enough static evidence for a respectful message and gives the safest first hook. Edit the generated note before sending. Use `--audience professor`, `--audience founder`, or `--audience maintainer` to change the opening and ask without changing the underlying audit evidence. It is intentionally cautious: the score is framed as a handoff/readiness signal, not a claim about scientific validity.

---

## Outreach principles

### 1. Lead with their pain, not your effort

Bad:

"I built this cool open-source tool and wanted to share it."

Better:

"I built a reproducibility auditor for notebook-heavy repos because students and engineers keep losing time to hidden state, missing artifacts, interactive prompts, and broken setup paths."

### 2. Keep the ask tiny

Do not ask for a call immediately.

Better asks:

- "Would love your reaction if this seems relevant."
- "Curious whether this matches pain you see in your lab/team."
- "If useful, I can run it on one of your public repos and send the report."
- "If you prefer, you can open an Audit request issue with a public repo URL and any context I should respect."

### 3. Use one concrete example

A short example lands better than a feature list.

Example:

"On the demo repo it catches hidden notebook state, a missing input artifact, unclear output provenance, and a README command pointing to a file that no longer exists."

### 4. Respect nuance

This tool is heuristic. Say that clearly.

That makes you sound more credible, not less.

---

## Audience 1: Professors and labs

### What they care about

- whether students can rerun old work
- whether a reviewer can make sense of a repo
- whether notebook-heavy workflows rely on invisible local state
- whether onboarding a new student is going to be messy

### Best framing

"An open-source reproducibility auditor for research and ML repositories."

### Stronger version

"A tool that checks whether a student or reviewer can actually rerun a notebook-heavy repo without hidden state, missing files, interactive prompts, or broken setup instructions."

### Sample email

Subject:

`Tool for auditing reproducibility in notebook-heavy research repos`

Body:

`Hi Professor <Name>,`

`I built a small open-source tool called labcheck that audits research and ML repositories for the kinds of issues that make them hard to rerun: hidden notebook state, missing input artifacts, interactive prompts, unpinned dependencies, orphan outputs, and README/setup drift.`

`It runs without any paid API dependency and can generate a report from a local repo, zip file, public GitHub repo, or no-key GitHub Action. There is also a browser demo that quick-scans notebooks, small selected repo folders, or bounded public GitHub URLs entirely client-side. For a very low-friction ask, I can send a prefilled demo link like demo.html?repo=owner/repo&audience=professor so the repo and target-fit audience are already queued up when you open it.`

`I thought it might be relevant if your lab deals with notebook-heavy workflows or student handoffs. If useful, I would be happy to run it on one of your public repos and send over the report. If an issue is easier than email, the repo has an Audit request template for public repositories.`

`Links:`

- [Landing page](../site/index.html)
- [Browser demo](../site/demo.html)
- Prefilled demo pattern: `../site/demo.html?repo=owner/repo&audience=professor`
- CLI helper: `labcheck demo-link https://github.com/owner/repo --audience professor`
- Paste-ready Markdown helper: `labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit --audience professor`
- [Sample audit](sample-audits/broken-repo-audit.html)
- [GitHub Action guide](github-action.md)

`Best,`

### Best follow-up angle

"I noticed your lab shares notebooks publicly; this might be useful as a quick pre-release or pre-handoff check."

---

## Audience 2: Founders and ML/data leaders

### What they care about

- whether a codebase can be handed to a new engineer
- whether experiment repos are actually reproducible
- whether technical due diligence reveals hidden workflow fragility
- whether docs and lineage are good enough to move quickly

### Best framing

"A reproducibility and portability audit for experiment-heavy repos."

### Sample email

Subject:

`Quick tool for auditing reproducibility in ML repos`

Body:

`Hi <Name>,`

`I built an open-source tool called labcheck that audits notebook-heavy and experiment-heavy repos for the specific issues that make them hard to hand off: hidden notebook state, missing artifacts, globbed data directories that were never shared, unsorted file discovery that can reshuffle inputs, unpinned Hugging Face models/datasets, interactive prompts that block unattended reruns, output save paths that fail on fresh clones, timestamped output drift, dependency/CI drift, NumPy/ML split/seed drift, orphan result files, unseeded randomness, README drift, and disconnected workflow files.`

`It is deterministic, runs without any paid API dependency, and works on local repos, zip archives, public GitHub URLs, and CI via GitHub Actions.`

`I thought it might be relevant if your team deals with internal experiments, research code, or onboarding ML work from contractors or new hires.`

`If useful, I can run it on one of your public repos and send over the report. If an issue is easier than email, the repo has an Audit request template for public repositories.`

`Links:`

- [Landing page](../site/index.html)
- [Browser demo](../site/demo.html)
- Prefilled demo pattern: `../site/demo.html?repo=owner/repo&audience=founder`
- CLI helper: `labcheck demo-link https://github.com/owner/repo --audience founder`
- [Case studies](case-studies.md)
- [GitHub Action guide](github-action.md)

`Best,`

### Best follow-up angle

"This is most useful before onboarding, handoff, or due diligence, not after a repo has already burned time."

---

## Which asset to send first

### If the person is technical but busy

Send:

- landing page
- one sample audit

### If the person is curious but non-technical

Send:

- landing page
- browser demo

### If the person is deeply technical

Send:

- README
- one case study
- CLI command examples

### If you want to send a complete audit attachment

Run:

```bash
labcheck demo-link https://github.com/owner/repo --audience professor --output labcheck-demo-link.txt
labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit --audience professor --output labcheck-demo-link.md
labcheck target-fit https://github.com/owner/repo --audience maintainer --output labcheck-target-fit.md
labcheck scorecard https://github.com/owner/repo --output labcheck-scorecard.md
labcheck issue https://github.com/owner/repo --output labcheck-issue-draft.md
labcheck pack https://github.com/owner/repo --output-dir labcheck-audit --zip
```

Use `labcheck-target-fit.md` as your private go/no-go card before outreach. Paste `labcheck-scorecard.md` into the email or PR comment when you want the shortest possible read. Use `labcheck-outreach-note.md` or `labcheck-issue-draft.md` for public GitHub targets when you want the generated message to include a bounded browser-demo link automatically. Use `labcheck-issue-draft.md` when a maintainer explicitly prefers GitHub issues; it includes caveats so the report stays respectful and easy to scope. Send the generated `labcheck-audit/labcheck-report.html` for a deeper skim, attach `labcheck-audit/labcheck-report.csv` when they want a sortable triage sheet with status/owner columns, or attach `labcheck-audit.zip` when they want the manifest, CSV, JSON, SARIF, badge, and full evidence trail too.

---

## What not to do

- do not oversell the tool as "solving reproducibility"
- do not present heuristic findings as absolute truth
- do not make the first message too long
- do not lead with GitHub stars or ambitions
- do not pitch it as "AI for research"

---

## Best proof points today

Right now, the strongest proof points are:

- it works with no paid API dependency
- it already scans public GitHub repos
- it has a zero-backend browser demo for local files and bounded public GitHub URLs
- it can generate a lab/team reproducibility policy with `labcheck init --policy`
- it can produce a shareable audit folder and zip archive with `labcheck pack --zip`
- it can produce a compact handoff scorecard with `labcheck scorecard`
- it can score outreach target fit before you write the first message with `labcheck target-fit`
- it can produce a maintainer-friendly issue draft with `labcheck issue`
- it has an Audit request issue template for public repos
- it produces HTML audits that are easy to skim
- it has a ready-to-record demo script for public launch clips
- it surfaces problems that people instantly recognize as painful

That combination is much stronger than "I built a tool with many features."

---

## Week-one operating system

Use [launch-week-plan.md](launch-week-plan.md) for the first seven days after publishing.

Use [outreach-tracker-template.md](outreach-tracker-template.md) to track the first 20 messages without storing private contact details in the public repo.
