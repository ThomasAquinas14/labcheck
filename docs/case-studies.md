# Public Case Studies

These are early `labcheck` case studies generated from public repositories.

They are useful for demonstrating the product direction, but they should be read as:

- heuristic audits
- snapshot-in-time outputs
- examples of the kinds of reproducibility issues `labcheck` can surface

They are **not** claims that a repo is "bad" or unmaintained.

---

## 1. `ageron/handson-ml3`

Repo:

- [https://github.com/ageron/handson-ml3](https://github.com/ageron/handson-ml3)

Generated audit:

- [handson-ml3-audit.md](sample-audits/handson-ml3-audit.md)

Why this is interesting:

- It is a well-known notebook-heavy ML repository.
- It exercises exactly the sort of workflow `labcheck` is built for.
- The audit surfaces repeated notebook-state assumptions, portability issues, and workflow lineage signals.

Notable findings:

- after the latest hidden-state and deduplication cleanup, the scan now condenses to `9 high`, `9 medium`, and `25 low` findings instead of spraying many synthetic notebook-state warnings
- the current overall score is `48`, with a visible `Artifact Availability` score that explains why missing generated files drive much of the risk
- the top-risk table makes the audit skimmable before someone reads the full findings list
- the remaining high-signal issues are mostly missing generated artifacts and one notebook that still references unseen setup state
- lineage edges are visible for generated artifacts and intermediate files, which makes the report easy to explain in a demo

Interpretation:

This is now a stronger showcase repo for `labcheck`: it is notebook-heavy enough to be interesting, but the output is concise enough to feel credible. The audit reads less like a brittle lint pass and more like a real reproducibility handoff review.

---

## 2. `jakevdp/PythonDataScienceHandbook`

Repo:

- [https://github.com/jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook)

Generated audit:

- [python-data-science-handbook-audit.md](sample-audits/python-data-science-handbook-audit.md)

Why this is interesting:

- It is a famous notebook-first learning resource.
- It contains a rich mix of data inputs, generated artifacts, and historical notebook structure.
- It stresses the provenance and notebook-state parts of the engine.

Important caveat:

This scan still produces a very large number of findings. That is useful as a stress test, but it should not yet be the lead marketing example for the project.

What the latest run suggests:

- the current overall score is `23`, so this is still clearly a stress-test scan rather than the hero demo
- many findings look legitimate rather than synthetic because the notebooks often reference `np`, `plt`, datasets, or helper state without visible setup in the saved notebook order
- the repo is large enough that onboarding and portability findings compound very quickly
- the top-risk table helps make this large report readable even though the full finding list is intentionally long
- this case study is best used to prove scale and stress-test behavior, not to communicate polish

Interpretation:

This case study is most useful as evidence that the core detection ideas scale to real repositories, not yet as the cleanest showcase of final product polish. It is a good technical proof point, but `handson-ml3` and the local broken demo are currently better first impressions.

---

## 3. Local Broken Demo Repo

Generated audits:

- [broken-repo-audit.md](sample-audits/broken-repo-audit.md)
- [broken-repo-audit.html](sample-audits/broken-repo-audit.html)

Why this is still important:

- It is the sharpest visual demo today.
- It shows every major category of issue in a compact, easy-to-understand way.
- It is the best artifact for screenshots, demos, and first-contact outreach.

---

## What these case studies prove

Even in its current prototype stage, `labcheck` can already:

- scan real public repositories
- produce structured reports without any paid API dependency
- extract simple lineage edges
- surface notebook-state, artifact, portability, and onboarding risks
- improve its signal quality iteratively with deterministic heuristics instead of model tuning or prompt changes

That is the core reason this project is a better candidate for public hosting and outreach than an API-key-dependent app.
