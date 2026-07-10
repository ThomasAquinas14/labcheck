# Reply To Case Study Checklist

Use this when a public launch reply, audit request, maintainer comment, founder question, or professor response looks useful enough to become a public `labcheck` case study.

The goal is to turn real feedback into credible proof without overclaiming, embarrassing maintainers, or publishing private context.

If you do not have a real public reply yet, use [reply-derived-case-study-seed.md](reply-derived-case-study-seed.md) as a clearly labeled seed. Do not present the seed as external validation.

---

## 1. Confirm It Is Safe To Publish

Only convert a reply into a case study when all of these are true:

- The repository is public.
- The `labcheck` command can be reproduced from public files.
- The case study does not include private emails, private datasets, private benchmark results, tokens, screenshots from private systems, or unshared maintainer context.
- The write-up is framed as a first-pass reproducibility and handoff audit, not a scientific-validity judgment.
- The maintainer, professor, founder, or reporter is not being used as a punchline.

If any item is uncertain, keep the note private or ask before publishing.

---

## 2. Capture The Source Reply

Save a short source note before writing the public version:

```text
Source reply URL or private note:
Public repo:
Person/audience:
Original question or concern:
Finding IDs involved:
Command used:
What changed my understanding:
Permission needed before naming anyone:
```

If the source is a private message, do not quote it publicly. Translate the lesson into a generic pattern instead.

---

## 3. Reproduce The Evidence

Run the smallest public command that supports the case study.

```bash
labcheck target-fit https://github.com/owner/repo --audience maintainer --output labcheck-target-fit.md
labcheck scorecard https://github.com/owner/repo --output labcheck-scorecard.md
labcheck scan https://github.com/owner/repo --format markdown --output labcheck-report.md
labcheck issue https://github.com/owner/repo --output labcheck-issue-draft.md
```

For cleanup or false-positive follow-up, capture before/after evidence:

```bash
labcheck compare before-labcheck-report.json after-labcheck-report.json --output labcheck-compare.md
```

Do not publish claims that are not visible in the report, issue, scorecard, or public repo.

---

## 4. Decide The Case Study Type

| Type | Use When | Public Artifact |
|---|---|---|
| Finding spotlight | One finding type explains a common handoff failure. | A short section in [case-studies.md](case-studies.md). |
| False-positive lesson | The tool was too noisy and needs a narrower rule. | A labeled issue plus a docs note. |
| Before/after cleanup | A maintainer fixed something and the score changed. | A compare report and thank-you note. |
| Audience lesson | A professor/founder clarified why the output is useful or confusing. | A generic launch-week learning note. |
| Stress test | A famous or large repo shows scale limits. | A caveated case study, not the hero demo. |

If the lesson is mostly "this repo is broken," do not publish it. A good case study teaches a reusable pattern.

---

## 5. Public Case Study Template

````markdown
## `<owner/repo>`

Repo:

- <public repo URL>

Generated audit:

- <report link>

Command used:

```bash
labcheck scan https://github.com/<owner>/<repo> --format markdown --output docs/sample-audits/<repo>-audit.md
```

Why this is interesting:

- <one sentence about workflow fit>
- <one sentence about the finding pattern>
- <one sentence about what a new maintainer/reviewer learns>

What felt fair:

- <specific finding or scorecard signal>

What was noisy or needs human judgment:

- <specific caveat>

Interpretation:

<Bounded paragraph. Do not say the repo is bad. Do not say the scientific result is invalid.>

Tiny outreach angle:

```text
<One respectful sentence that could be reused in outreach or a launch post.>
```
````

Keep the final public note shorter than the audit. The case study is a reader-friendly doorway, not a second full report.

---

## 6. Labels And Board Placement

If the case study came from an issue or public audit request, put it in the [public triage board](public-triage-board.md):

```text
Status: Case Study Candidate
Audience: Professor/Lab or Founder/ML Team or OSS Maintainer
Workflow: CLI or Browser Demo or GitHub Action
Severity: High/Medium/Low/None
Category: Environment/Determinism/Artifacts/Portability/Onboarding/Process
Finding ID: LC002, LC005, LC035, or blank
Next Action: Publish a bounded case-study note with caveats
```

Useful labels:

```text
triage/public-audit
triage/false-positive
category/artifacts
category/determinism
audience/professor
audience/founder
audience/maintainer
```

Use [issue-labels.md](issue-labels.md) for the reusable label catalog.

---

## 7. Publish Decision

Before publishing, answer these questions:

- Does the case study make `labcheck` look useful without making the target repo look foolish?
- Is the strongest claim directly backed by a command, report, scorecard, issue, or public file?
- Is the caveat visible before the reader reaches the conclusion?
- Would a maintainer feel fairly represented if they saw the link?
- Does this create a reusable lesson for professors, founders, maintainers, or contributors?

If the answer to any question is "no," rewrite or keep it private.

---

## 8. Safe Follow-Up Reply

Use this after publishing a case study based on someone else's public feedback:

```text
Thanks again for the signal here. I turned the reusable part into a small public case-study note:

<link>

I kept it scoped to public files and framed it as a first-pass handoff/reproducibility signal, not a judgment about the project or result. If anything feels unfairly represented, I am happy to revise or remove it.
```

The best case study makes the project more credible and makes the other person feel respected.
