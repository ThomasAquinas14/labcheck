# Public Triage Board Template

Use this when the public repo starts receiving audit requests, false-positive reports, case-study ideas, and small check proposals.

The board is intentionally lightweight: GitHub Issues are the source of truth, labels do the routing, and a GitHub Project is optional. You should be able to run week one from issues, saved searches, and the [issue label guide](issue-labels.md).

---

## Board Name

```text
labcheck public triage
```

Purpose:

```text
Track public audit requests, reproducibility findings, false positives, case studies, and launch-week follow-ups without collecting private repo data or promising scientific validation.
```

---

## Columns

| Column | Meaning | Exit rule |
| --- | --- | --- |
| Inbox | New audit requests, bug reports, check proposals, and outreach replies. | Labeled, scoped, and assigned a next action. |
| Needs Repro | A report needs a public fixture, exact finding ID, or reproduction command. | Someone can reproduce with `labcheck` locally. |
| Ready To Fix | The scope is clear and small enough for one PR or docs change. | PR opened or linked. |
| Waiting On Maintainer | Needs project-owner context, expected-artifact confirmation, or false-positive judgment. | Maintainer replied or issue is closed as out of scope. |
| Case Study Candidate | Public repo teaches something useful for the docs or launch post. | Case-study note added or explicitly skipped. |
| Done / Learned | Closed issues worth summarizing for roadmap or docs. | Lesson captured in docs, roadmap, or release notes. |

Keep the board honest: if an issue cannot be reproduced from public files, keep it in `Needs Repro` or close it rather than guessing.

---

## Fields

| Field | Type | Suggested values |
| --- | --- | --- |
| Status | Single select | Inbox, Needs Repro, Ready To Fix, Waiting On Maintainer, Case Study Candidate, Done / Learned |
| Audience | Single select | Professor/Lab, Founder/ML Team, OSS Maintainer, Contributor |
| Workflow | Single select | CLI, Browser Demo, GitHub Action, Docs, Outreach |
| Severity | Single select | High, Medium, Low, None |
| Category | Single select | Environment, Determinism, Artifacts, Portability, Onboarding, Process |
| Finding ID | Text | `LC002`, `LC005`, `LC035`, or blank for process issues |
| Fit Score | Number | 0-10 launch-week outreach fit |
| Public Repo | Text | `owner/repo` or blank |
| Next Action | Text | One sentence with the next concrete step |

If you only create three fields, create `Status`, `Finding ID`, and `Next Action`.

---

## Labels To Use

Seed labels from [issue-labels.md](issue-labels.md), then keep issue labels minimal:

```text
severity/high
category/artifacts
finding/lc005
audience/maintainer
```

For process issues, use triage/workflow labels instead:

```text
triage/public-audit
workflow/browser-demo
audience/professor
```

Good default rule: one severity, one category or workflow, one finding ID when relevant, and one audience or triage label.

---

## Saved Searches

Use these as GitHub issue filters or Project views:

```text
is:issue is:open label:triage/public-audit
is:issue is:open label:triage/false-positive
is:issue is:open label:triage/baseline-ratchet
is:issue is:open label:workflow/github-action
is:issue is:open label:workflow/browser-demo
is:issue is:open label:severity/high
is:issue is:open label:audience/professor
is:issue is:open label:audience/founder
is:issue is:open label:"good first issue"
```

CLI equivalents:

```bash
gh issue list --label "triage/public-audit" --state open
gh issue list --label "triage/false-positive" --state open
gh issue list --label "severity/high" --state open
gh issue list --label "workflow/github-action" --state open
```

---

## Launch-Week Seed Issues

Create only a few public issues at first. A board with four useful issues feels alive; a board with 30 vague issues feels abandoned.

| Title | Labels | Starting column |
| --- | --- | --- |
| Reduce LC002 noise for tutorial notebooks with shared setup cells | `triage/false-positive`, `category/determinism`, `finding/lc002`, `triage/good-first-audit` | Ready To Fix |
| Add DVC dataset provenance hints | `category/artifacts`, `workflow/cli`, `triage/good-first-audit` | Needs Repro |
| Add policy preset for course repositories | `audience/professor`, `workflow/github-action`, `category/onboarding` | Inbox |
| Convert first useful public audit reply into a case study | `triage/public-audit`, `audience/maintainer` | Case Study Candidate |

---

## Triage Routine

Run this once or twice per week during launch:

1. Open new issues and apply labels from [issue-labels.md](issue-labels.md).
2. Ask for the public repo URL, finding ID, and command output if reproduction is missing.
3. Move real bugs or clear docs gaps to `Ready To Fix`.
4. Move expected findings to `Waiting On Maintainer` and ask whether they should be documented or suppressed.
5. Move useful public examples to `Case Study Candidate`.
6. Close private-code, unsupported-hosted-service, or scientific-validity requests with a kind scope note.
7. Add one sentence to [roadmap.md](roadmap.md), [good-first-issues.md](good-first-issues.md), or a case study when an issue teaches something reusable.

Use [maintainer-reply-templates.md](maintainer-reply-templates.md) for the first reply after a maintainer responds.

Use [reply-to-case-study-checklist.md](reply-to-case-study-checklist.md) before moving a useful public reply from `Case Study Candidate` into [case-studies.md](case-studies.md).
Use [reply-derived-case-study-seed.md](reply-derived-case-study-seed.md) to keep the first conversion bounded until there is real public feedback to cite.

Scope note to reuse:

```text
Thanks for the report. `labcheck` is a no-key static reproducibility and handoff audit, so I can only verify issues from public files and deterministic commands. If this depends on private data, hidden services, or scientific-validity review, I am going to keep the issue scoped to the public reproducibility evidence.
```

---

## Done Criteria

An issue is ready to close when one of these is true:

- A fix landed with a regression test or docs assertion.
- The finding was expected and the exception is documented or suppressed narrowly.
- The request needs private data or scientific judgment outside `labcheck` scope.
- The public repo is no longer accessible.
- The lesson was captured in docs, a case study, or the roadmap.

The board should make the project feel responsive without promising unlimited free consulting.
