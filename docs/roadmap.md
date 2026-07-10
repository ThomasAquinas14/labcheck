# labcheck Roadmap

`labcheck` is intentionally narrow: no API keys, no hosted backend requirement, no paid inference dependency, and no default execution of untrusted project code.

The goal is to become the easiest way to answer one practical question:

> If I hand this research or ML repo to someone else, can they rerun it?

## Principles

- Keep the core engine deterministic and local-first.
- Prefer evidence-backed findings over broad advice.
- Make every finding explainable, suppressible, and testable.
- Optimize for notebook-heavy research, teaching, ML, and data-science repos.
- Avoid features that turn the project into a hosted clone farm or paid LLM wrapper.

## Now

These are the current launch-week priorities.

- Continue reducing false positives around tutorial notebooks and notebook-specific syntax.
- Refine the `profile = "education"` defaults with real course/lab fixtures.
- Add more public case studies with concise, fair interpretation.
- Improve GitHub Action marketplace polish and example workflow copy.
- Expand runtime checks for Conda edge cases, Docker edge cases, remote data snapshots, inline notebook installs, DVC/Git LFS restore steps, framework-specific seeds, and common lab setup files.
- Improve browser demo copy for folder uploads and sample repo walkthroughs.
- Keep the release gate fast enough that contributors actually run it.

## Next

These are useful once the public repo has early users and issue reports.

- Expand DVC, Git LFS, and data-versioning hints beyond restore-command documentation.
- Deepen generated-figure and result provenance beyond the current output-directory provenance note, checksum/sidecar, orphan-output, timestamp, glob, and write-path checks.
- Add optional Jupyter/VS Code integration experiments.
- Improve baseline workflows for teams that want to ratchet score over time.
- Add more framework-specific determinism checks beyond NumPy Generator seeds, PyTorch random_split/DataLoader/backend/worker drift, TensorFlow seeds, XGBoost/LightGBM/CatBoost estimator seeds, Keras shuffled data sources, Optuna sampler seeds, JAX PRNG key reuse, and Polars sampling seeds.
- Publish a small gallery of good and bad reproducibility patterns.

## Later

These only make sense after the CLI, Action, and static demo have real adoption.

- Package manager plugins for common lab templates.
- Classroom/lab policy starter kits by domain.
- Maintainer dashboard generated from local audit packs.
- Extension APIs for custom checks without changing the core package.

## Not On The Roadmap

These would undermine the core public-hosting promise.

- A required hosted backend.
- User accounts, billing, or multi-tenant SaaS.
- Paid LLM advice as a core feature.
- Executing arbitrary repository code by default.
- Uploading private research repos to a third-party service by default.
- A broad static analyzer that tries to replace Bandit, Ruff, Semgrep, or CodeQL.

## How To Influence The Roadmap

The best roadmap input is a small reproducible example:

- a public repo that `labcheck` handles poorly
- a false positive with the exact file and finding ID
- a missing reproducibility failure mode with a minimal fixture
- a case study that teaches maintainers what changed after the audit

Start with [good first issues](good-first-issues.md) if you want to contribute.
