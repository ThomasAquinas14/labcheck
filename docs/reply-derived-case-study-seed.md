# Reply-Derived Case Study Seed

This is the first reply-derived case-study seed for `labcheck`.

It is **not a real external reply yet**. Use it as the public format for the first useful maintainer, professor, founder, or OSS reply after launch. Once a real public reply exists, replace the source note with the reply URL and update the interpretation with the actual lesson.

The goal is to avoid a cold-start problem: when someone says "this finding is useful/noisy/interesting," the project already has a respectful format for turning that signal into a bounded public case study.

---

## Source Signal

Current seed signal:

```text
Likely launch reply:
"Are missing generated tutorial artifacts actually a reproducibility problem, or just expected outputs?"
```

Public evidence used for the seed:

- [case-studies.md](case-studies.md)
- [handson-ml3-audit.md](sample-audits/handson-ml3-audit.md)
- [reply-to-case-study-checklist.md](reply-to-case-study-checklist.md)

Safety status:

- Public repo only.
- No private maintainer context.
- No private data.
- No claim that the source project is bad or scientifically invalid.
- Treats the finding as a handoff question, not an accusation.

---

## Case Study Type

Finding spotlight plus audience lesson.

The reusable question is:

```text
When should generated artifacts be committed, regenerated, ignored, or documented?
```

That is a strong `labcheck` use case because it matters to:

- professors handing a repo to students
- maintainers receiving reproducibility questions
- founders evaluating whether an experiment repo can be handed to a new engineer
- reviewers trying to understand whether a missing file blocks rerun or is expected output

---

## Public Repo

`ageron/handson-ml3`

Repo:

- [https://github.com/ageron/handson-ml3](https://github.com/ageron/handson-ml3)

Generated audit:

- [sample-audits/handson-ml3-audit.md](sample-audits/handson-ml3-audit.md)

Command used:

```bash
labcheck scan https://github.com/ageron/handson-ml3 --format markdown --output docs/sample-audits/handson-ml3-audit.md
```

---

## What The Reply Teaches

The best interpretation is not "generated artifacts are always wrong."

The better interpretation is:

```text
Generated artifacts need an explicit contract.
```

For a notebook-heavy learning or research repo, a missing generated file can mean several different things:

- The file is intentionally generated during the tutorial.
- The file is too large or inappropriate to commit.
- The file is expected to be downloaded from somewhere else.
- The file is historical output that should not be regenerated.
- The file is genuinely missing and blocks a new reader.

`labcheck` cannot know which explanation is true from static files alone. Its value is that it surfaces the ambiguity early, with enough path-level evidence for a maintainer or reviewer to decide.

---

## What Felt Fair

- The audit names concrete paths instead of making a vague reproducibility complaint.
- The report frames findings under a review boundary rather than claiming scientific invalidity.
- The generated-artifact ambiguity is useful for onboarding because a new reader needs to know whether to regenerate, download, ignore, or commit the file.

---

## What Needs Human Judgment

- Tutorial repositories often generate outputs during normal learning flow.
- Some artifacts may be intentionally excluded because they are large, derived, or environment-specific.
- A maintainer might reasonably document the generation step rather than commit the output.

That caveat should stay visible in any public post, issue, or case-study note.

---

## Follow-Up Artifact

A respectful follow-up issue or docs note should ask for clarification, not demand a fix:

```text
Would it be useful to document which generated artifacts are expected outputs versus required inputs for a fresh rerun?
```

If the answer is yes, the smallest useful improvement is one of:

- add a README note for generated artifacts
- add a script or notebook cell that recreates them
- add a `.gitignore` comment for intentionally excluded outputs
- add an artifact manifest that says where large files come from
- suppress the finding narrowly if the artifact is expected and documented

---

## Tiny Launch Post Angle

```text
One thing I learned while testing labcheck: missing generated files are not automatically "bugs." They are often handoff questions. A reviewer or new student needs to know whether to regenerate, download, ignore, or commit them. labcheck is useful when it turns that ambiguity into concrete paths and a bounded follow-up.
```

---

## Replacement Checklist For The First Real Reply

When the first real reply arrives:

1. Replace the likely launch reply with the public reply URL or a private-note summary.
2. Confirm the repo and command are reproducible from public files.
3. Update the case-study type in [reply-to-case-study-checklist.md](reply-to-case-study-checklist.md).
4. Add the actual finding IDs and command output.
5. Keep the caveat visible before the conclusion.
6. If the person is named, make sure the public context is fair and permission-safe.

Do not pretend this seed is real external validation. Its job is to make the first real conversion faster, cleaner, and more respectful.
