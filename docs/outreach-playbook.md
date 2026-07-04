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
- the browser local-file demo
- one compact scorecard
- one sample HTML audit
- one relevant case study

Best starting set:

1. [site/index.html](../site/index.html)
2. [site/demo.html](../site/demo.html)
3. [broken-repo-audit.html](sample-audits/broken-repo-audit.html)
4. [case-studies.md](case-studies.md)

---

## Outreach principles

### 1. Lead with their pain, not your effort

Bad:

"I built this cool open-source tool and wanted to share it."

Better:

"I built a reproducibility auditor for notebook-heavy repos because students and engineers keep losing time to hidden state, missing artifacts, and broken setup paths."

### 2. Keep the ask tiny

Do not ask for a call immediately.

Better asks:

- "Would love your reaction if this seems relevant."
- "Curious whether this matches pain you see in your lab/team."
- "If useful, I can run it on one of your public repos and send the report."

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

"A tool that checks whether a student or reviewer can actually rerun a notebook-heavy repo without hidden state, missing files, or broken setup instructions."

### Sample email

Subject:

`Tool for auditing reproducibility in notebook-heavy research repos`

Body:

`Hi Professor <Name>,`

`I built a small open-source tool called labcheck that audits research and ML repositories for the kinds of issues that make them hard to rerun: hidden notebook state, missing input artifacts, unpinned dependencies, orphan outputs, and README/setup drift.`

`It runs without any paid API dependency and can generate a report from a local repo, zip file, public GitHub repo, or no-key GitHub Action. There is also a browser demo that quick-scans notebooks or a small selected repo folder entirely client-side.`

`I thought it might be relevant if your lab deals with notebook-heavy workflows or student handoffs. If useful, I would be happy to run it on one of your public repos and send over the report.`

`Links:`

- [Landing page](../site/index.html)
- [Browser demo](../site/demo.html)
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

`I built an open-source tool called labcheck that audits notebook-heavy and experiment-heavy repos for the specific issues that make them hard to hand off: hidden notebook state, missing artifacts, orphan result files, unseeded randomness, README drift, and disconnected workflow files.`

`It is deterministic, runs without any paid API dependency, and works on local repos, zip archives, public GitHub URLs, and CI via GitHub Actions.`

`I thought it might be relevant if your team deals with internal experiments, research code, or onboarding ML work from contractors or new hires.`

`If useful, I can run it on one of your public repos and send over the report.`

`Links:`

- [Landing page](../site/index.html)
- [Browser demo](../site/demo.html)
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
labcheck scorecard https://github.com/owner/repo --output labcheck-scorecard.md
labcheck pack https://github.com/owner/repo --output-dir labcheck-audit --zip
```

Paste `labcheck-scorecard.md` into the email or PR comment when you want the shortest possible read. Send the generated `labcheck-audit/labcheck-report.html` for a deeper skim, or attach `labcheck-audit.zip` when they want JSON/SARIF/badge artifacts too.

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
- it has a zero-backend browser local-file demo
- it can generate a lab/team reproducibility policy with `labcheck init --policy`
- it can produce a shareable audit folder and zip archive with `labcheck pack --zip`
- it can produce a compact handoff scorecard with `labcheck scorecard`
- it produces HTML audits that are easy to skim
- it surfaces problems that people instantly recognize as painful

That combination is much stronger than "I built a tool with many features."
