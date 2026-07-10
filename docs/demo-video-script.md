# Demo Video Script

Use this to record a 60 to 90 second launch video for GitHub, LinkedIn, X, professor outreach, founder outreach, or a portfolio walkthrough.

The goal is not to show every feature. The goal is to make one thing obvious:

> labcheck finds the boring, painful reasons notebook-heavy research and ML repos fail when someone else tries to rerun them, without requiring API keys or a hosted backend.

---

## Recording Setup

- Open the landing page: `site/index.html` or the hosted static URL.
- Open the browser demo: `site/demo.html`.
- Keep a terminal ready in the repo root.
- Keep the sample HTML audit ready: `docs/sample-audits/broken-repo-audit.html`.
- Use a clean zoom level where text is readable at 1080p.
- Do not show private repos, tokens, `.env` files, or local personal paths.

Suggested terminal commands:

```bash
labcheck scorecard examples/broken-repo
labcheck target-fit examples/broken-repo --audience founder
labcheck issue examples/broken-repo --output labcheck-issue-draft.md
labcheck scan examples/broken-repo --format html --output report.html
labcheck pack examples/broken-repo --output-dir labcheck-audit --zip
```

---

## 75-Second Script

### 0:00-0:08 - Hook

Visual: landing page hero.

Voiceover:

```text
Most research and ML repos do not fail because the idea is bad. They fail because the notebook only worked in one person's machine: hidden state, missing data, interactive prompts, stale README commands, drifting dependencies, and outputs nobody can reproduce.
```

### 0:08-0:18 - Positioning

Visual: landing page "No API keys" promise and browser demo button.

Voiceover:

```text
This is labcheck: a local-first reproducibility auditor for notebook-heavy repos. No API keys, no backend bill, and no hosted clone queue for someone to abuse.
```

### 0:18-0:35 - Browser Demo

Visual: open `site/demo.html`, pause on the "90 second walkthrough" panel, click "Load sample repo snapshot", show scorecards, CSV export, outreach note export, and top risks.

Voiceover:

```text
The browser demo can quick-scan a small repo snapshot entirely client-side. In this broken example, it immediately catches hidden notebook state, a missing input file, a globbed data directory that was never shared, unsorted file discovery, a missing output directory, timestamped output drift, and seed issues.
```

### 0:35-0:52 - CLI Proof

Visual: terminal running `labcheck scorecard examples/broken-repo`.

Voiceover:

```text
For real repos, the CLI gives a compact scorecard, a maintainer-friendly issue draft, a ready-to-edit outreach note, Markdown and HTML reports, CSV, JSON, SARIF, a badge, and a shareable audit pack with a manifest that explains the review boundary and file map. It also works on local folders, zip archives, and public GitHub URLs.
```

### 0:52-1:07 - Report Value

Visual: sample HTML audit with top risks and remediation plan.

Voiceover:

```text
The report is not just a list of complaints. It ranks the first fixes, shows evidence, explains why each issue matters, and gives a concrete remediation path a student, reviewer, founder, or new engineer can act on.
```

### 1:07-1:15 - CTA

Visual: README quickstart or GitHub repo.

Voiceover:

```text
If you maintain notebook-heavy research or ML repos, try labcheck before the next handoff. It is open source, deterministic, and safe to host publicly as a static demo.
```

---

## 30-Second Short

```text
Notebook-heavy repos often fail in boring ways: hidden state, missing input files, interactive prompts, stale README commands, unseeded splits, missing output folders, and results nobody can regenerate.

I built labcheck to catch those handoff risks without API keys or a hosted backend.

Run it locally, in GitHub Actions, or try the static browser demo. It produces a scorecard, target-fit card, issue draft, top risks, remediation plan, HTML report, CSV, JSON, SARIF, and a shareable audit pack with a clear manifest.

If your lab or team hands off research code, run labcheck before the next person loses a day to "works on my machine."
```

---

## Three-Minute Walkthrough

Use this when recording a deeper portfolio video.

1. Show the landing page and explain the no-key constraint.
2. Open the browser demo and load the sample repo snapshot.
3. Explain one high-severity finding: hidden notebook state.
4. Explain one artifact finding: missing input or missing output directory.
5. Explain one determinism finding: seedless NumPy Generator/sklearn/pandas/PyTorch split/DataLoader worker/TensorFlow/XGBoost/Optuna/JAX/Polars drift.
6. Run `labcheck scorecard examples/broken-repo`.
7. Open the sample HTML audit and remediation plan.
8. Show `labcheck init --policy` as the team/lab adoption path.
9. Mention GitHub Action soft-audit mode.
10. Close with the static deployment promise: public demo, no wallet-drain surface.

---

## Screen Checklist

Show these screens in order:

- Landing hero with "Find the hidden reasons research repos fail to rerun."
- Browser demo sample repo snapshot.
- Score cards: overall, environment, determinism, artifacts.
- Top risks list with at least one high-severity finding.
- Provenance graph.
- Terminal scorecard command.
- Sample HTML audit remediation plan.
- README quickstart.
- GitHub Action guide or launch kit.

---

## Good Lines To Reuse

- "A reproducibility auditor for the handoff moment."
- "No API keys. No backend bill. No inference dependency."
- "It finds the failure modes people recognize immediately."
- "The browser demo is public-safe because the files stay local."
- "The CLI is for serious scans; the static demo is for instant trust."
- "It does not prove reproducibility. It surfaces reproducibility and handoff risks."

---

## Things Not To Say

Avoid:

- "This guarantees reproducibility."
- "This proves a paper can be reproduced."
- "This replaces CI, CodeQL, Ruff, or a human reviewer."
- "This uses AI to audit research repos."
- "This needs a hosted backend."

Say instead:

- "first-pass reproducibility audit"
- "handoff risk scorecard"
- "deterministic local checks"
- "common notebook and experiment repo failure modes"
- "static public demo with no secret exposure"

---

## Posting Copy

```text
I built labcheck, a no-key reproducibility auditor for notebook-heavy research and ML repos.

It catches hidden notebook state, missing artifacts, stale README/CI commands, interactive rerun blockers, unpinned Hugging Face artifacts, unseeded randomness, missing output directories, globbed data paths that were never shared, unsorted file discovery, timestamped output drift, and unclear provenance.

No API keys. No hosted backend. No inference bill.

Demo: <demo-url>
GitHub: <repo-url>
Sample audit: <sample-audit-url>
```
