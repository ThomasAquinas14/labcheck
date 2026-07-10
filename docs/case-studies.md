# Public Case Studies

These are early `labcheck` case studies generated from public repositories.

Use [reply-to-case-study-checklist.md](reply-to-case-study-checklist.md) before converting a public reply, audit request, or maintainer comment into a new case study.
Use [reply-derived-case-study-seed.md](reply-derived-case-study-seed.md) as the first safe format for converting a useful launch reply into a bounded public note.

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

Command used:

```bash
labcheck scan https://github.com/ageron/handson-ml3 --format markdown --output docs/sample-audits/handson-ml3-audit.md
```

Why this is interesting:

- It is a well-known notebook-heavy ML repository.
- It exercises exactly the sort of workflow `labcheck` is built for.
- The audit surfaces repeated notebook-state assumptions, portability issues, and workflow lineage signals.

Notable findings:

- the checked-in audit currently reports score `43`, with `9 high`, `14 medium`, and `25 low` findings
- the visible `Artifact Availability` score explains why missing generated files drive much of the risk
- the top-risk table makes the audit skimmable before someone reads the full findings list
- the remaining high-signal issues are mostly missing generated artifacts and one notebook that still references unseen setup state
- lineage edges are visible for generated artifacts and intermediate files, which makes the report easy to explain in a demo

What felt fair:

- `LC005` is useful because the top finding names concrete missing generated/model artifacts, not vague "data may be missing" language.
- `LC002` is useful because it narrows hidden-state risk to one notebook and specific unresolved names.
- The lineage table makes the story teachable: generated files such as `my_converted_savedmodel.tflite` appear as both read and write edges, which is exactly the handoff ambiguity a reviewer would ask about.

What was noisy or needs human judgment:

- Some missing generated artifacts may be intentional tutorial outputs rather than files that should be committed.
- The absolute-path findings catch real portability smell, but a few are likely harmless saved environment strings rather than run-blocking paths.
- Unpinned dependencies in an educational environment file are a useful warning, not an automatic request to freeze every package forever.

Interpretation:

This is now a stronger showcase repo for `labcheck`: it is notebook-heavy enough to be interesting, but the output is concise enough to feel credible. The audit reads less like a brittle lint pass and more like a real reproducibility handoff review.

Tiny outreach angle:

```text
I ran a no-key static handoff audit on one public notebook-heavy ML repo to test whether labcheck produces useful reviewer notes. The strongest signal was not "this repo is bad"; it was "these generated artifacts and hidden-state assumptions are the first things a new reader would need clarified."
```

---

## 2. `jakevdp/PythonDataScienceHandbook`

Repo:

- [https://github.com/jakevdp/PythonDataScienceHandbook](https://github.com/jakevdp/PythonDataScienceHandbook)

Generated audit:

- [python-data-science-handbook-audit.md](sample-audits/python-data-science-handbook-audit.md)

Command used:

```bash
labcheck scan https://github.com/jakevdp/PythonDataScienceHandbook --format markdown --output docs/sample-audits/python-data-science-handbook-audit.md
```

Why this is interesting:

- It is a famous notebook-first learning resource.
- It contains a rich mix of data inputs, generated artifacts, and historical notebook structure.
- It stresses the provenance and notebook-state parts of the engine.

Important caveat:

This scan still produces a very large number of findings. That is useful as a stress test, but it should not yet be the lead marketing example for the project.

What the latest run suggests:

- the checked-in audit currently reports score `19`, with `82 high`, `118 medium`, and `120 low` findings
- this is still clearly a stress-test scan rather than the hero demo
- many findings look legitimate rather than synthetic because the notebooks often reference `np`, `plt`, datasets, or helper state without visible setup in the saved notebook order
- the repo is large enough that onboarding and portability findings compound very quickly
- the top-risk table helps make this large report readable even though the full finding list is intentionally long
- this case study is best used to prove scale and stress-test behavior, not to communicate polish

What felt fair:

- The top `LC002` group correctly highlights that many notebooks depend on names such as `big_array`, `np`, or `plt` that are not visible in the saved local execution path.
- `LC005` points to concrete missing inputs such as `data/recipeitems.json`, which is actionable for a first-run handoff.
- `LC009` is useful as a provenance prompt because committed figures are present without visible producers in the scanned notebook/script graph.

What was noisy or needs human judgment:

- Tutorial books often rely on shared chapter setup, prose context, or intentionally historical notebook state, so hidden-state findings need maintainer interpretation.
- A large teaching repository can produce many repeated warnings; this is useful for stress testing but too loud for a first outreach screenshot.
- Some generated figure findings may be archival book assets rather than reproducibility defects.

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

---

## Adding the next case study

Do not add a case study just because a repo produced many findings. Add one when it teaches a reusable handoff pattern, false-positive lesson, cleanup story, or audience insight.

Before publishing:

- follow [reply-to-case-study-checklist.md](reply-to-case-study-checklist.md)
- replace the seed in [reply-derived-case-study-seed.md](reply-derived-case-study-seed.md) only when a real public reply exists
- keep the source repo public and reproducible from public files
- include the exact `labcheck` command used
- show what felt fair and what still needs human judgment
- avoid claiming scientific validity or repo quality
