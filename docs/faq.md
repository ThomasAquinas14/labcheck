# FAQ

This page answers the questions people usually ask before trusting or sharing `labcheck`.

---

## Does labcheck require an API key?

No.

`labcheck` does not call OpenAI, Anthropic, Gemini, hosted embeddings, or any paid inference service.

The core scanner is deterministic static analysis over notebooks, Python files, manifests, README instructions, and simple file lineage.

---

## Does labcheck execute my code?

No.

`labcheck` does not run notebooks, import project modules, execute scripts, or evaluate arbitrary repo code. It reads files as text/JSON and extracts evidence from the saved artifact.

That is intentional:

- safer for public repos
- safer for CI
- no sandbox required for the core workflow
- no surprise compute bill
- no dependency on the target repo successfully installing

---

## Does the browser demo upload files?

No.

The static browser demo runs in the browser tab. It can inspect a notebook or selected local files without sending them to a backend.

The browser demo is intentionally lighter than the CLI. Use it for quick triage and screenshots; use the CLI or GitHub Action for real repo scans.

---

## What kinds of issues does it catch?

The first version focuses on high-signal reproducibility and handoff risks:

- hidden notebook state
- out-of-order notebook execution
- missing input artifacts
- unpinned dependencies
- missing Python runtime metadata
- conflicting exact Python runtime metadata
- README commands pointing to missing files, Python modules, Makefile targets, package scripts, or project scripts
- GitHub Actions workflow commands pointing to missing scripts, dependency files, or Makefile targets
- GitHub Actions Python versions that conflict with project runtime metadata
- GitHub Actions workflows that install/setup but never run tests, notebooks, `labcheck`, or reproduce/check commands
- absolute machine-local paths, including Colab/Kaggle notebook paths
- unseeded randomness
- NumPy Generator seed gaps, sklearn/pandas/XGBoost `random_state` gaps, Optuna sampler seed gaps, JAX PRNG key reuse, PyTorch split/DataLoader generator and worker seed gaps, TensorFlow seed gaps, Polars sampling seed gaps, and output directories missing before save/write calls
- inline notebook `%pip` / `!pip` installs without package pins
- inline `apt-get`, `brew`, `apk`, `yum`, or similar OS package installs hidden in notebooks or scripts
- dependency manifests with no README install/setup step
- requirements or constraints files that include missing local files
- editable, file, wheelhouse, or local path dependencies that are missing from the shared repo
- common imported packages missing from dependency manifests
- project-local helper imports that are missing from the shared repo
- floating Docker base image tags such as `latest` or untagged images
- Python Dockerfiles that copy the repo but skip dependency manifest installation
- project-specific environment variables with no README or `.env.example`
- interactive `input()` / `getpass()` prompts that block unattended reruns
- GPU/CUDA or accelerator-specific code with no documented hardware requirement or CPU fallback
- mutable remote data URLs such as raw GitHub branch links used in reads or download calls
- remote download calls that have no explicit timeout and can hang in CI or reviewer reruns
- stable-looking remote artifacts that are read or downloaded without checksum/hash verification
- Hugging Face model, dataset, and Hub download calls without `revision=` pins
- glob/listdir input directories that are missing from the shared repo
- unsorted glob/listdir/Path.glob input discovery that can reshuffle rows or batches
- timestamp-derived output filenames that make rerun artifacts harder to compare
- DVC/Git LFS restore-step gaps
- floating GitHub Action references such as `owner/action@main`
- committed outputs with no visible producer
- disconnected workflow files

---

## Is this a replacement for running the repo?

No.

`labcheck` is a first-pass reproducibility audit. It tells you where a repo is likely fragile before someone spends hours trying to rerun it.

It complements:

- CI
- notebook execution tests
- environment lockfiles
- data/versioning tools
- human review

It does not prove a paper, benchmark, or model is reproducible.

---

## How should I interpret findings?

Findings are evidence-backed heuristics.

They are meant to answer:

> What will slow down the next student, reviewer, maintainer, or engineer?

Some findings may be intentional. For example, a teaching repo might clear notebook outputs by policy, or a generated figure might be committed only for documentation.

Use `.labcheck.toml` to exclude archived/generated paths or disable checks that are noisy for your repo.

For the score formula, score bands, and what a high score does not prove, see the [scoring guide](scoring-guide.md).

For small before/after examples of common repo handoff failures, see the [reproducibility pattern gallery](reproducibility-patterns.md).

---

## How do I avoid false positives?

Start with a soft audit:

```bash
labcheck scan . --format markdown
```

Then add a `.labcheck.toml` file for intentional noise:

```toml
exclude = [
  "archive/**",
  "notebooks/generated/**",
  ".ipynb_checkpoints/**",
  "labcheck-audit/**",
]

disabled_checks = [
  # "LC010",
]

[[ignored_findings]]
check_id = "LC010"
path = "archive/old_experiment.py"
reason = "Archival script kept for context, not a supported rerun path."
```

For CI, create a baseline first and then ratchet:

```bash
labcheck baseline . --output .labcheck-baseline.json
labcheck scan . --baseline .labcheck-baseline.json --fail-on high
```

---

## What is the safest way to try it in a repo?

Use a soft report first:

```bash
labcheck scorecard .
labcheck scan . --format markdown --output labcheck-report.md
```

If the report is useful, generate a shareable bundle:

```bash
labcheck pack . --output-dir labcheck-audit --zip
```

If the repo is public and CI-friendly, add the GitHub Action in soft mode before enabling gates.

---

## Why not just use a linter?

Most linters focus on code style, syntax, or package security.

`labcheck` focuses on reproducibility as a system property:

- can the environment be rebuilt?
- do notebooks show a clean execution path?
- are input files present or documented?
- are outputs traceable to scripts/notebooks?
- do setup instructions still match the repo?

That makes it useful during handoff, review, onboarding, teaching, and diligence.

For a side-by-side positioning table against linters, CI, notebook execution, data-versioning tools, containers, and manual review, see the [comparison guide](comparison.md).

---

## Who is this for?

`labcheck` is most useful for:

- research labs
- professors and students
- ML/data teams
- notebook-heavy OSS maintainers
- founders evaluating experiment-heavy repos
- reviewers checking whether an artifact is handoff-ready

---

## Can I run it in GitHub Actions?

Yes.

`labcheck` ships with a no-key GitHub Action wrapper. Start with `fail-on: none` so it produces reports without blocking PRs. After a repo has a clean baseline, use `fail-on: high` or `min-score`.

See [github-action.md](github-action.md).

---

## Can I cite it?

Yes.

Use [CITATION.cff](../CITATION.cff) if `labcheck` helps a research, teaching, reproducibility, or handoff workflow.

---

## What should I not claim?

Do not claim that `labcheck` proves reproducibility.

Better wording:

- "surfaces reproducibility and handoff risks"
- "finds common notebook and experiment repo failure modes"
- "gives reviewers and new team members a first-pass scorecard"

That framing is accurate and more trustworthy.
