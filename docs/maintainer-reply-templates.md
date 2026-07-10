# Maintainer Reply Templates

Use these after a maintainer replies to a public `labcheck` audit issue, audit request, or labeled issue bundle.

The goal is to stay helpful without turning a no-key reproducibility audit into unlimited consulting. Keep the next step concrete, public, and scoped to evidence that `labcheck` can verify.

Related launch artifacts:

- [Labeled audit issue bundle](sample-audits/broken-repo-labeled-issue.md)
- [Public triage board template](public-triage-board.md)
- [Issue label guide](issue-labels.md)
- [First audit guide](first-audit.md)

---

## If They Say "Thanks, This Is Useful"

Reply:

```text
Thanks, glad it was useful. I would keep the next step very small: fix or document the first top-risk item, then rerun:

labcheck scorecard .
labcheck scan . --format markdown --output labcheck-report.md

If you want, I can help turn the first finding into a small PR or a narrower issue. I will keep it scoped to the public reproducibility evidence, not scientific validity or private data.
```

Board update:

```text
Status: Ready To Fix
Next Action: Fix or document the first top-risk item and rerun `labcheck scorecard .`.
Labels: keep `triage/public-audit`; add `triage/good-first-audit` if it is PR-sized.
```

---

## If They Say The Finding Is Expected

Reply:

```text
That makes sense. I will treat this as expected context rather than a bug.

The best next step is to document the exception close to the notebook/script, or add a narrow `.labcheck.toml` suppression so future readers know it is intentional:

[[ignored_findings]]
check_id = "LC002"
path = "notebooks/tutorial.ipynb"
reason = "Tutorial page intentionally starts after setup shown on the previous page."

I would avoid disabling the whole check globally unless the repo has a documented policy for that pattern.
```

Board update:

```text
Status: Waiting On Maintainer or Done / Learned
Next Action: Document the expected finding or add a targeted suppression.
Labels: add `triage/false-positive`; keep the exact `finding/lcXXX` label.
```

---

## If They Ask For Reproduction Steps

Reply:

```text
Absolutely. Here is the smallest local reproduction path:

python -m pip install -e .
labcheck doctor .
labcheck scorecard .
labcheck scan . --format markdown --output labcheck-report.md

For just the finding explanation:

labcheck explain LC005

If you prefer not to install anything first, the browser demo can show a bounded public-repo preview, but the CLI scan is the source of truth for full repo coverage.
```

Board update:

```text
Status: Needs Repro
Next Action: Confirm the maintainer can reproduce the finding with the CLI command.
Labels: add `workflow/cli`; keep severity/category/finding labels.
```

---

## If They Invite A Pull Request

Reply:

```text
Happy to keep it narrow. I will open a small PR that does one of these:

- documents the missing input or setup step
- makes a hidden notebook assumption explicit
- adds a targeted `.labcheck.toml` suppression for expected behavior
- adds or fixes one reproducibility command

I will include the `labcheck scorecard` before/after output in the PR so the change is easy to review.
```

Board update:

```text
Status: Ready To Fix
Next Action: Open a small PR with before/after `labcheck` output.
Labels: add `triage/good-first-audit` if this is beginner-friendly.
```

---

## If They Need Private Data Or Scientific Review

Reply:

```text
Thanks for clarifying. I should keep this issue scoped to what `labcheck` can verify from public files.

`labcheck` does not prove scientific validity and I should not ask for private datasets, credentials, or unreleased code. I can still help document the public input contract, expected data location, or restore command if that would make the repo easier to hand off.
```

Board update:

```text
Status: Done / Learned
Next Action: Close or narrow to public reproducibility documentation.
Labels: remove severity labels if the remaining work is process-only.
```

---

## If They Push Back

Reply:

```text
Totally fair. I may have over-scoped the issue.

I opened it as a lightweight handoff signal, not a demand that every finding is a bug. If the current behavior is intentional, I can either close this or rewrite it as a narrow docs/suppression suggestion so future readers understand the context.
```

Board update:

```text
Status: Waiting On Maintainer
Next Action: Ask whether to close, narrow, or convert to documentation.
Labels: add `triage/false-positive` if the finding is expected.
```

---

## If They Fix Something

Reply:

```text
Nice, thank you. I reran the audit and the top finding is now resolved.

If helpful, the before/after proof note can be generated with:

labcheck scan . --format json --output before-labcheck-report.json
labcheck scan . --format json --output after-labcheck-report.json
labcheck compare before-labcheck-report.json after-labcheck-report.json --output labcheck-compare.md

I will close this if the remaining findings are expected or out of scope.
```

Board update:

```text
Status: Done / Learned or Case Study Candidate
Next Action: Capture the resolved finding in a short case-study note if the repo is public and the maintainer is comfortable with it.
Labels: keep `triage/public-audit`; add `case-study` only when there is a reusable lesson.
```

---

## One Gentle No-Reply Follow-Up

Use one follow-up only:

```text
Quick follow-up in case this was useful. I am happy to close this if the findings are expected or not relevant. If it is useful, the smallest next step is to confirm whether the first top-risk item is real or should be documented as an intentional exception.
```

Board update:

```text
Status: Waiting On Maintainer
Next Action: Wait for one reply, then close or convert to a docs-only note.
```

---

## Close Comment

Use this when closing kindly:

```text
Closing this to keep the issue tracker focused. Thanks for the context.

The useful lesson for `labcheck` is: <one sentence>. I will capture that in docs/tests if it points to a better check or a false-positive reduction.
```

Do not keep bumping public maintainers. The project should feel helpful, not extractive.
