# First Audit Guide

This guide is the shortest path from curiosity to a useful `labcheck` artifact you can send to a professor, lab manager, founder, maintainer, or teammate.

`labcheck` does not need API keys and does not execute the target repo by default. Start with a soft audit, read the top risks, and only turn findings into CI gates after you understand the repo context.

---

## Path 1: No Install Demo

Use this when someone asks, "What does it do?"

1. Open the [browser demo](../site/demo.html).
2. Click the sample repo button, choose local files, or paste a public GitHub repository URL. For outreach, use a prefilled demo link such as `demo.html?repo=owner/repo&audience=professor`, or generate one with `labcheck demo-link https://github.com/owner/repo --audience professor`.
3. Download or copy the scorecard, target-fit card, outreach note, or CSV findings table.
4. Open the [sample scorecard](sample-audits/broken-repo-scorecard.md), [sample target-fit card](sample-audits/broken-repo-target-fit.md), and [sample HTML audit](sample-audits/broken-repo-audit.html).

This path is best for a demo video, cold outreach, screenshots, and showing the value without asking anyone to install Python packages.

The browser GitHub path is intentionally bounded: it fetches public text-like files client-side through GitHub's unauthenticated public API and caps file count/size. Within that budget, it prioritizes README/manifests, runtime files, CI workflows, Docker/Make files, notebooks, and Python source before lower-signal docs. Prefilled links wait for the visitor to click Audit; add `&audit=1` only when you intentionally want the bounded browser audit to start automatically. Use the CLI for full scans of large public repos.

---

## Path 2: Local Repo Audit

Use this when you already have a repo on your machine.

```bash
git clone https://github.com/ThomasAquinas14/labcheck.git
cd labcheck
python -m pip install -e .

labcheck doctor /path/to/repo
labcheck checks --category determinism
labcheck scorecard /path/to/repo
labcheck pack /path/to/repo --output-dir labcheck-audit --zip
```

If you installed with `pipx` and do not have a repo ready, create a tiny intentionally broken fixture first:

```bash
labcheck demo-repo
labcheck scorecard labcheck-demo-repo
```

Open `labcheck-audit/MANIFEST.md` first to confirm the review boundary and file map, then `labcheck-audit/README.md`, then `labcheck-audit/labcheck-scorecard.md` and `labcheck-audit/labcheck-target-fit.md`, then the HTML or Markdown report if you need the evidence trail.

---

## Path 3: Public GitHub Repo Audit

Use this for cold outreach, public OSS audits, or a quick diligence pass on a notebook-heavy project.

```bash
labcheck doctor https://github.com/owner/repo
labcheck demo-link https://github.com/owner/repo --audience professor --output labcheck-demo-link.txt
labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit --audience professor --output labcheck-demo-link.md
labcheck target-fit https://github.com/owner/repo --audience professor --output labcheck-target-fit.md
labcheck scorecard https://github.com/owner/repo --output labcheck-scorecard.md
labcheck outreach https://github.com/owner/repo --output labcheck-outreach-note.md
labcheck outreach https://github.com/owner/repo --audience professor --output labcheck-professor-note.md
labcheck outreach https://github.com/owner/repo --audience founder --output labcheck-founder-note.md
labcheck issue https://github.com/owner/repo --output labcheck-issue-draft.md
labcheck scan https://github.com/owner/repo --format csv --output labcheck-findings.csv
labcheck pack https://github.com/owner/repo --output-dir labcheck-audit --zip --max-findings 50
```

This clones a public repository into a temporary workspace, scans it locally, and deletes the temporary clone afterward.

Only audit public repos unless you have explicit permission. Do not paste private code into the browser demo or share generated reports that expose private paths, internal dataset names, or unreleased work.

---

## What To Read First

Start with the scorecard:

- manifest boundary and file map
- overall score and weakest category
- high-severity count
- review boundary
- top risks table
- suggested first fixes

Then open the full HTML or Markdown report if you need line-by-line evidence.

Use the [scoring guide](scoring-guide.md) to interpret the number. A high score means the repo looks easier to rerun and hand off; it does not prove the research result, benchmark, or model is scientifically valid.

If someone asks what `labcheck` actually looks for, use `labcheck checks --category determinism`, `labcheck checks --severity high`, or `labcheck checks --search seed` instead of dumping the full catalog. Then use `labcheck explain LC005` for a concrete finding-level explanation, or `labcheck explain LC005 --format markdown` when you want paste-ready issue, PR, or outreach text.

---

## What To Send Someone

For a short message, attach or paste:

- `labcheck-scorecard.md`
- `labcheck-target-fit.md`
- `labcheck-issue-draft.md`
- `labcheck-outreach-note.md`
- one sentence about why you chose the repo
- one sentence naming the top risk
- `labcheck-findings.csv` if the recipient wants a sortable triage sheet with `status`, `owner`, and `suggested_owner` columns
- a link to the [scoring guide](scoring-guide.md)

For public GitHub targets, `labcheck-outreach-note.md` and `labcheck-issue-draft.md` include a bounded browser-demo link automatically. Use `--audience professor`, `--audience founder`, or `--audience maintainer` when you want the generated note to match the recipient's context. Read `labcheck-target-fit.md` before sending anything so the first message has a concrete hook. Keep the browser link when you want the recipient to click before installing anything; keep the scorecard or audit pack when they want the full local scan evidence.

For a deeper review, send:

- `labcheck-audit.zip`
- `labcheck-audit/MANIFEST.md`
- the scorecard
- the HTML report
- any context about external datasets, archived notebooks, or intentionally unsupported paths

For outreach wording, use the [outreach playbook](outreach-playbook.md).

---

## When To Add CI

Do not start by failing CI on an old repo. Start soft:

```bash
labcheck init /path/to/repo
```

Then create a baseline:

```bash
labcheck baseline /path/to/repo --output /path/to/repo/.labcheck-baseline.json
```

After the team agrees on the standard, enable gates such as:

```bash
labcheck scan /path/to/repo --baseline /path/to/repo/.labcheck-baseline.json --fail-on high --min-score 80
```

When you fix issues, keep the JSON reports and generate a before/after proof note:

```bash
labcheck scan /path/to/repo --format json --output before-labcheck-report.json
# make fixes
labcheck scan /path/to/repo --format json --output after-labcheck-report.json
labcheck compare before-labcheck-report.json after-labcheck-report.json --output labcheck-compare.md
```

Use that compare note in PRs, lab handoff updates, founder diligence follow-ups, or release notes.

For setup details, see the [GitHub Action guide](github-action.md).

---

## If The First Audit Looks Noisy

Noise is normal in old notebooks, teaching repos, generated examples, and archived experiments.

Use `.labcheck.toml` to exclude paths that are not part of the supported rerun surface:

```toml
exclude = [
  "archive/**",
  "notebooks/generated/**",
  ".ipynb_checkpoints/**",
]

[[ignored_findings]]
check_id = "LC010"
path = "archive/old_experiment.py"
reason = "Archival script kept for context, not a supported rerun path."
```

When a finding is expected, say why in maintainer-facing language before suppressing it:

```text
This `LC002` finding is expected for `notebooks/tutorial.ipynb`: the notebook
intentionally starts mid-lesson, and the setup cell is introduced on the
previous page. I am keeping that teaching structure, documenting the assumption,
and adding a targeted `labcheck` suppression rather than disabling hidden-state
checks globally.
```

Then keep the suppression narrow:

```toml
[[ignored_findings]]
check_id = "LC002"
path = "notebooks/tutorial.ipynb"
reason = "Tutorial page intentionally starts after setup shown on the previous page."
```

Do not suppress real blockers that a future collaborator will hit. Fix them, document the tradeoff, or keep them visible as known risks.

---

## Useful Next Links

- [FAQ](faq.md)
- [Scoring guide](scoring-guide.md)
- [Privacy and safety model](privacy-and-safety.md)
- [GitHub Action guide](github-action.md)
- [Lab adoption guide](lab-adoption-guide.md)
- [Outreach playbook](outreach-playbook.md)
- [Public deploy guide](public-deploy-guide.md)
