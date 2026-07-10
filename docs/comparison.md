# Comparison Guide

`labcheck` is not trying to replace linters, dependency scanners, notebook runners, data-versioning tools, or human review.

It fills a narrower gap:

> a no-key, first-pass reproducibility and handoff audit for notebook-heavy research and ML repos.

Use this page when someone asks, "Isn't this just CI, a linter, or a notebook test?"

---

## Quick Positioning

| Tool category | What it is good at | What it usually misses | Where `labcheck` fits |
| --- | --- | --- | --- |
| Linters and formatters | Style, syntax, maintainability, import hygiene | Missing data files, hidden notebook state, stale run commands, unclear output provenance | Finds repo-level handoff risks before someone tries to rerun the work. |
| Security/dependency scanners | Known vulnerabilities, risky dependencies, license or supply-chain signals | Whether the repo can actually be rebuilt and rerun | Complements security scanning with reproducibility evidence. |
| CI and notebook execution | Proves selected commands or notebooks run in a controlled environment | What is undocumented, missing, stale, machine-local, or fragile before CI exists | Helps teams decide what CI should verify first. |
| DVC, Git LFS, and data-versioning tools | Storing, versioning, or restoring data artifacts | Whether restore steps are documented and connected to notebooks/scripts | Flags missing restore instructions and lineage gaps. |
| Containers and environment managers | Rebuilding a runtime when the environment spec is complete | Hidden notebook state, stale README commands, missing artifacts, nondeterministic paths | Audits whether the repo's handoff story is complete enough to use those tools well. |
| Manual README review | Human judgment and project context | Easy-to-miss stale paths, missing files, repeated notebook issues, CI drift | Produces a concrete checklist and evidence trail for reviewers. |

---

## What labcheck Is Best At

`labcheck` is strongest when the repo contains:

- notebooks
- scripts that read/write local artifacts
- dependency manifests
- README setup/run commands
- GitHub Actions workflows
- Dockerfiles
- public data/model URLs
- generated figures or result files

It answers practical questions:

- Can a new person infer what to install?
- Do documented commands point to files or modules that exist?
- Do notebooks show clean top-to-bottom execution evidence?
- Are input artifacts present or documented?
- Are generated outputs connected to producer code?
- Are random splits, samples, and ML workflows visibly seeded?
- Are CI workflows actually verifying anything?
- Is the repo relying on machine-local paths, hidden setup cells, or interactive prompts?

---

## What labcheck Does Not Claim

`labcheck` does not prove that:

- a paper is scientifically reproducible
- a model result is valid
- every finding is definitely a bug
- a high score means the repo is production-ready
- a low score means the repo is low-quality

It gives a first-pass reproducibility signal with evidence. The best use is to start a focused review, not to end one.

---

## When To Use Each Tool

Use `labcheck` when:

- you are handing a repo to a student, reviewer, maintainer, contractor, or new engineer
- you need a quick scorecard before deeper setup work
- you want a soft GitHub Action report before turning on gates
- you need a public, no-key demo or outreach artifact
- you want to identify the first CI checks worth adding

Use a notebook execution tool when:

- the environment already installs
- input artifacts are available
- the repo has a clear execution order
- you want to prove the notebooks actually run

Use data-versioning tools when:

- datasets are large
- artifacts need versioned storage
- restore commands are part of the workflow

Use linters and security scanners when:

- code quality, style, security, or vulnerability signals are the priority

These workflows stack well. A healthy repo can use all of them.

---

## Good Outreach Framing

Accurate:

> `labcheck` is a no-key reproducibility handoff audit. It finds common reasons notebook-heavy repos fail for the next person before they spend hours trying to rerun them.

Avoid:

> `labcheck` proves the project is reproducible.

Better:

> `labcheck` gives a concrete first-pass scorecard, top risks, and evidence so a reviewer or team can decide what to fix or verify next.
