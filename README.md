# labcheck

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-0f766e)](pyproject.toml)
[![No API keys](https://img.shields.io/badge/no_API_keys-required-a16207)](docs/public-deploy-guide.md)
[![Local-first](https://img.shields.io/badge/local--first-reproducibility-0f766e)](README.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-17202a)](LICENSE)

An open-source reproducibility auditor for research and ML repositories.

`labcheck` answers a simple question:

> If I hand this repo to a smart stranger, can they actually reproduce the results?

![labcheck scorecard preview](docs/assets/scorecard-preview.svg)

It scans notebooks, scripts, manifests, README instructions, and simple data lineage to surface the exact issues that make experiment-heavy repos fragile:

- hidden notebook state
- missing input artifacts
- unpinned dependencies
- absolute machine-local paths
- README drift
- randomness without visible seeding
- committed outputs with no visible producer
- disconnected workflow files

No paid APIs. No inference bill. No backend secret to protect.

Input targets supported right now:

- local folder
- single notebook
- local `.zip` archive
- public GitHub repository URL
- GitHub Actions CI

Zip archives are extracted into a temporary directory with path traversal and symlink checks before scanning.

---

## Why this exists

A lot of repos look fine until a new student, reviewer, or engineer actually tries to run them.

That is where the real problems show up:

- notebooks only work because the original kernel still has invisible state
- datasets are referenced but not committed
- dependencies drift over time
- figures and result files exist, but their provenance is unclear
- README commands point to files that do not exist anymore

`labcheck` is built for that moment.

---

## Who it helps

### Professors and research labs

Use `labcheck` to see whether students and reviewers can rerun a repo without machine-specific assumptions or hidden notebook state.

### ML and data founders

Use `labcheck` to audit whether an experiment-heavy codebase is portable, reproducible, and safe to hand to a new engineer.

### OSS maintainers

Use `labcheck` to catch reproducibility issues before contributors get stuck on setup and broken artifact paths.

---

## What it produces

`labcheck` emits:

- an overall reproducibility score
- category scores
- a top-risk summary for quick review
- a prioritized remediation plan
- actionable findings with severity
- a simple provenance graph
- Markdown, JSON, HTML, and SARIF reports

Current categories:

- Environment Rebuildability
- Notebook Determinism
- Artifact Availability
- Portability
- Onboarding Readiness

Example scorecard:

```text
Overall score: 44/100
Scope: 1 notebook, 1 Python file
Findings: 12 (4 high, 6 medium, 2 low)
Weakest area: Notebook Determinism (3/100)

Top risks:
- LC001 suspicious notebook execution order
- LC002 likely hidden notebook state
- LC005 referenced input artifact missing from repo

Triage signal:
Not handoff-ready yet: fix 4 high-severity findings before sending this
repo to a reviewer, student, or new engineer.
```

---

## Checks implemented so far

- `LC001` suspicious notebook execution order
- `LC002` likely hidden notebook state
- `LC003` missing environment manifest
- `LC004` unpinned dependencies in `requirements.txt`, `pyproject.toml`, and Conda environment files
- `LC005` missing input artifacts
- `LC006` absolute machine-local paths
- `LC007` randomness without visible seeding
- `LC008` README command drift
- `LC009` committed outputs with no visible producer
- `LC010` disconnected workflow nodes
- `LC011` saved notebook error outputs
- `LC012` missing Python runtime version
- `LC013` missing setup or run instructions
- `LC014` notebooks with no saved execution evidence
- `LC015` notebooks missing kernel metadata
- `LC016` scikit-learn splitters and randomized estimators missing `random_state`
- `LC017` pandas sampling missing `random_state`

---

## Quick start

If you only try one path, run the intentionally broken demo repo first. It gives you a compact report with hidden notebook state, missing artifacts, README drift, and unseeded randomness in under a minute.

```bash
git clone https://github.com/ThomasAquinas14/labcheck.git
cd labcheck
python -m pip install -e .

labcheck doctor .
labcheck scorecard examples/broken-repo
labcheck scan examples/broken-repo
labcheck scan examples/broken-repo --format html --output report.html
```

For a real repo:

```bash
labcheck scan .
labcheck scorecard .
labcheck pack . --output-dir labcheck-audit --zip
```

For CI:

```bash
labcheck init .
labcheck init . --policy
```

`labcheck init` creates a starter `.labcheck.toml` plus a soft-audit GitHub Actions workflow. Add `--policy` to also create `docs/reproducibility.md`, a ready-to-edit lab/team handoff policy. It does not overwrite existing files unless you pass `--force`.

For a public no-key demo URL, run:

```bash
python scripts/build_static_site.py
```

Then publish the generated `dist/site` folder. The export includes the landing page, browser demo, README, sample audits, and docs with links rewritten for static hosting.

---

## Command cookbook

The CLI is intentionally broad enough for local use, CI, outreach, and static-site demos:

```bash
labcheck scan examples/broken-repo --format markdown
labcheck scan examples/broken-repo --format markdown --max-findings 50
labcheck scan examples/broken-repo --format json
labcheck scan examples/broken-repo --format markdown --output labcheck-report.md --json-output labcheck-report.json --scorecard-output labcheck-scorecard.md
labcheck pack examples/broken-repo --output-dir labcheck-audit --zip
labcheck scan examples/broken-repo --format sarif --output labcheck-report.sarif
labcheck scan examples/broken-repo --badge-output labcheck-badge.svg
labcheck badge examples/broken-repo --output labcheck-badge.svg
labcheck scan examples/broken-repo --fail-on high
labcheck scan examples/broken-repo --min-score 80
labcheck scan examples/broken-repo --config .labcheck.toml
labcheck baseline examples/broken-repo --output .labcheck-baseline.json
labcheck scan examples/broken-repo --baseline .labcheck-baseline.json --fail-on high --min-score 90
labcheck scan examples/broken-repo.zip
labcheck scan https://github.com/owner/repo
labcheck graph examples/broken-repo
labcheck checks
labcheck explain LC005
python scripts/build_static_site.py
python scripts/build_sample_audits.py
python scripts/release_check.py
```

For local development without installing the console command, run `python -m labcheck.cli ...` with `PYTHONPATH=src`.

Use `labcheck doctor .` when setting up a repo or demo environment. It checks the installed version, Python runtime, target path or public GitHub URL, optional config file, and registered check catalog before you run a full scan.

Use `labcheck checks` to list supported checks, and `labcheck explain LC005` to see what a finding means, why it matters, and how to fix it.

Use `labcheck scorecard .` to create a compact Markdown summary for PR comments, lab handoff notes, founder due-diligence messages, or outreach follow-ups.

Use `labcheck badge . --output labcheck-badge.svg` to generate a static score badge for README files or CI artifacts.

Use `labcheck pack . --output-dir labcheck-audit --zip` to generate a shareable audit folder plus `labcheck-audit.zip` with a scorecard, Markdown, HTML, JSON, SARIF, a badge, and a small index file. This is the easiest format to attach to outreach, release notes, or a lab handoff.

Human-readable reports show the first 100 detailed findings by default so large notebook corpora stay readable in terminals and GitHub job summaries. Use `--max-findings all` when you want every detail. JSON and SARIF outputs remain complete regardless of the human report cap.

You can also inspect the generated sample audits directly:

- [Markdown sample audit](docs/sample-audits/broken-repo-audit.md)
- [HTML sample audit](docs/sample-audits/broken-repo-audit.html)
- [Scorecard sample audit](docs/sample-audits/broken-repo-scorecard.md)
- [Static landing page](site/index.html)
- [Browser local-file demo](site/demo.html)
- [Public case studies](docs/case-studies.md)
- [GitHub publish guide](docs/github-publish-guide.md)
- [GitHub Action guide](docs/github-action.md)
- [Lab and team adoption guide](docs/lab-adoption-guide.md)
- [Launch kit](docs/launch-kit.md)
- [Outreach playbook](docs/outreach-playbook.md)
- [Public deploy guide](docs/public-deploy-guide.md)
- [Release checklist](docs/release-checklist.md)
- [Citation metadata](CITATION.cff)

---

## GitHub Action

`labcheck` ships with a no-key GitHub Action wrapper. Start with a soft audit that uploads reports and writes the Markdown audit to the GitHub job summary without failing CI:

```bash
labcheck init .
labcheck init . --policy
```

The first command creates a starter `.labcheck.toml` and `.github/workflows/labcheck.yml`. The `--policy` variant also writes `docs/reproducibility.md` so a lab or team has a clear handoff standard. You can also wire the Action manually:

```yaml
- uses: actions/checkout@v4
- id: labcheck
  uses: ThomasAquinas14/labcheck@v1
  with:
    target: "."
    report-format: markdown
    report-path: labcheck-report.md
    json-path: labcheck-report.json
    sarif-path: labcheck-report.sarif
    badge-path: labcheck-badge.svg
    scorecard-path: labcheck-scorecard.md
    max-findings: "100"
    fail-on: none
    min-score: ""
```

For existing repos, create a baseline once with `labcheck baseline . --output .labcheck-baseline.json`, commit it, and then set `baseline-path: .labcheck-baseline.json` plus `fail-on: high` or `min-score: "80"` to catch regressions. The Action also writes `labcheck-scorecard.md` for PR summaries and SARIF for optional GitHub code scanning.

The Action exposes outputs such as `${{ steps.labcheck.outputs.overall-score }}`, `${{ steps.labcheck.outputs.findings-count }}`, and `${{ steps.labcheck.outputs.high-count }}` for PR summaries, sticky PR comments, release summaries, or custom workflow logic. The full guide includes copy-paste snippets for `$GITHUB_STEP_SUMMARY` and one-comment-per-PR reporting.

If a repo has archived experiments, generated notebooks, checkpoints, or other intentional noise, add a `.labcheck.toml` file:

```toml
exclude = [
  "archive/**",
  "labcheck-audit/**",
  "notebooks/generated/**",
  ".ipynb_checkpoints/**",
]

# Use sparingly for known intentional patterns that would otherwise dominate
# the report with low-signal findings.
disabled_checks = [
  # "LC010",
]
```

The CLI discovers this file automatically for local folder scans. In GitHub Actions, pass `config-path: .labcheck.toml` to make the exclusion policy explicit.

See the full guide in [docs/github-action.md](docs/github-action.md).

---

## Example findings

From the current broken example repo:

- `LC002` hidden notebook state: cell 3 references `external_state` with no visible prior definition
- `LC011` saved notebook error output: the notebook is committed with a `NameError` traceback
- `LC005` missing artifact: notebook reads `data/train.csv`, but the file is not present in the repo
- `LC008` README drift: `python scripts/train.py` is documented, but that file does not exist
- `LC012` missing Python runtime version: runnable code exists, but the repo does not declare which Python version to use
- `LC010` workflow fragility: `experiment.py` is disconnected from visible lineage

This is exactly the kind of output that is useful in code review, onboarding, lab handoff, and due diligence.

There are also early public-repo case studies in [docs/case-studies.md](docs/case-studies.md).

---

## Project shape

`labcheck` is intentionally CLI-first:

- deterministic checks
- local-first usage
- public-hosting safe
- no per-user inference cost
- lightweight public-repo scanning for real-world trials

That makes it a better fit for:

- GitHub adoption
- CI usage later
- static demo hosting
- cold outreach to labs and founders

---

## Why it is different

Most tooling either lints code or scans dependencies.

`labcheck` focuses on **reproducibility as a system property**:

- can the environment be recreated?
- can the notebook run cleanly from top to bottom?
- are outputs traceable to inputs?
- will the next person actually know what to run?

That makes it much more useful for research and experiment-heavy repos than a generic lint pass.

---

## Current status

This repository is an early but real prototype:

- working CLI
- working tests
- sample Markdown and HTML audits
- top-risk summaries before long finding lists
- prioritized remediation plans for quick fix ordering
- capped human-readable details for large repos, while JSON/SARIF stay complete
- static SVG score badges for README/CI artifacts
- compact Markdown scorecards for PR comments, outreach, and handoff notes
- shareable `labcheck pack` audit bundles for outreach and handoff
- self-explaining check catalog via `labcheck checks` and `labcheck explain LC005`
- inline SVG provenance visualization
- static browser demo for notebooks, selected files, and local folders
- one-click browser sample repo snapshot for no-prep demos
- downloadable browser-side scorecard, Markdown, and JSON reports
- self-contained static export for GitHub Pages, Netlify, Cloudflare Pages, or Oracle Object Storage
- `labcheck init` for one-command repo setup
- optional `labcheck init --policy` lab/team reproducibility policy pack
- no-key GitHub Action wrapper
- baseline-and-ratchet CI workflow
- optional minimum-score CI gate
- SARIF output for GitHub code-scanning integrations
- `.labcheck.toml` excludes and disabled-check controls for archived/generated noise control
- `LC009` orphan output detection for committed results and figures
- CI workflow that tests the package and smoke-tests the Action
- public case studies on real repos
- a narrow, credible product wedge

What is still missing:

- more framework-specific checks
- richer lineage extraction
- better noise control for large educational notebook corpora

---

## Roadmap

Near-term:

- richer notebook hidden-state analysis
- more framework-specific determinism checks beyond sklearn/pandas `random_state`
- more public case studies with cleaner summaries
- GitHub Action marketplace polish

Later:

- richer lab/course policy packs
- VS Code or Jupyter integration

---

## Why this can be deployed publicly

This project was chosen very intentionally:

- no OpenAI/Anthropic/Gemini dependency
- no hidden API-key cost center
- no backend wallet-drain risk
- works well as a static page + local CLI combination

That means you can host a landing page and sample audits publicly without worrying that someone will exploit your inference budget.

---

## Contributing and security

Contributions are welcome, especially small reproducibility checks, false-positive reductions, docs, and public case studies.

- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

Please keep the core promise intact: no API keys, no paid service dependency, no default hosted backend, and deterministic checks that produce concrete evidence.

---

## Citation

If you use `labcheck` in a research, teaching, lab handoff, or reproducibility workflow, please cite it using [CITATION.cff](CITATION.cff).

---

## License

MIT. See [LICENSE](LICENSE).
