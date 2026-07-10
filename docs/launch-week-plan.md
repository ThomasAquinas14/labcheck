# Launch Week Plan

Use this after the public GitHub repo and static site are live.

The goal for week one is not "go viral." The goal is to create enough high-quality proof that the project deserves attention:

- a clean public repo
- a working public demo URL
- 20 direct outreach messages
- 3 to 5 useful replies
- 1 to 3 public issue ideas from real feedback
- one launch post with concrete evidence

---

## Day 0: Publish And Smoke Test

Run locally before publishing:

```bash
python scripts/release_check.py
python scripts/check_publish_ready.py
```

Then create/push the repo and metadata using [github-publish-guide.md](github-publish-guide.md).

After GitHub Pages deploys, verify:

- landing page opens
- browser demo opens
- sample HTML audit opens
- README image renders
- `og:image` and `twitter:image` metadata point to the scorecard preview
- JSON-LD structured data identifies `labcheck` as a free no-key developer application
- `action.yml` appears on GitHub
- CI and Pages workflows are green
- the demo-video script has been used or adapted for the first launch clip

Do not start outreach until the public links work.

---

## Day 1: First Public Proof

Post once with concrete evidence, not hype.

Best angle:

```text
I built labcheck, a no-key reproducibility auditor for notebook-heavy research and ML repos.

It catches hidden notebook state, missing input artifacts, missing globbed data directories, unsorted file discovery, unpinned Hugging Face artifacts, interactive rerun blockers, missing generated output directories, timestamped output drift, missing local dependency paths, dependency/CI drift, stale README commands, NumPy/ML split/seed drift, unseeded randomness, and unclear output provenance.

No API keys. No hosted backend. No inference bill.

Demo: <demo-url>
GitHub: <repo-url>
Sample audit: <sample-audit-url>
```

Then add the post URL to [outreach-tracker-template.md](outreach-tracker-template.md) so you can reuse it in follow-ups.

If you are posting video, use [demo-video-script.md](demo-video-script.md) and keep the first version under 90 seconds.

After posting, fill out [launch-post-after-action.md](launch-post-after-action.md) so the first public proof turns into baseline numbers, reply categories, and one concrete follow-up.

---

## Day 2: Professor/Lab Batch

Send 10 messages to labs where the pain is obvious:

- public notebook-heavy repos
- course or lab repos with many `.ipynb` files
- research code that includes datasets, generated figures, or experiment scripts
- labs that publish reproducibility or open-science artifacts

Prioritize people where you can say one specific thing:

```text
I noticed your lab shares notebook-heavy repos publicly; this might be useful as a pre-handoff or pre-release check.
```

Keep the ask small:

```text
If useful, I can run it on one public repo and send a short scorecard.
```

---

## Day 3: Founder/ML-Team Batch

Send 10 messages to founders or ML/data leaders where handoff risk matters:

- data/ML tooling startups
- applied AI teams with public examples
- companies publishing notebooks, tutorials, or benchmark repos
- founders who discuss developer experience, research operations, or ML reliability

Best angle:

```text
This is most useful before onboarding, contractor handoff, technical diligence, or turning an experiment repo into team-owned code.
```

Avoid asking for a meeting first. Offer to run a scorecard on a public repo.

---

## Day 4: Turn Replies Into Issues

For every useful reply, create one small public artifact:

- a GitHub issue
- a roadmap bullet
- a case-study note
- a check proposal
- a false-positive reduction

This makes the repo feel alive without pretending it is more mature than it is.

Good issue titles:

- `Reduce LC002 noise for tutorial notebooks with shared setup cells`
- `Add DVC dataset provenance hints`
- `Add policy preset for course repositories`
- `Replace reply-derived case-study seed with first real public reply`

Use [reply-to-case-study-checklist.md](reply-to-case-study-checklist.md) before turning a maintainer, professor, or founder reply into a public case-study note.
Use [reply-derived-case-study-seed.md](reply-derived-case-study-seed.md) as the seed format until a real public reply exists.

---

## Day 5: Publish A Learning Post

Do not write "please star my repo."

Write something useful:

```text
The 5 most common reproducibility failures I saw while testing labcheck on notebook-heavy repos:

1. Hidden notebook state
2. Missing input artifacts
3. README commands pointing to missing scripts, Python modules, Makefile targets, package scripts, or project scripts
4. Results committed without producer scripts
5. Unseeded sampling/splits
```

Link the repo at the end, after the useful content.

Use the after-action notes from [launch-post-after-action.md](launch-post-after-action.md) to choose the examples. Do not write a vague "we launched" recap if the first post produced sharper evidence.

---

## Day 6: Improve One Thing From Feedback

Pick one fix that makes the tool more trustworthy:

- reduce a noisy finding
- improve a report explanation
- add one framework-specific check
- add one sample audit
- improve the browser demo copy

Ship it publicly and thank the person whose feedback inspired it.

---

## Day 7: Second Outreach Wave

Send another 20 targeted messages, but now include one learning:

```text
I heard from a few researchers that hidden notebook state and missing input files are the most painful first-run failures, so I tightened those checks and added a short scorecard output.
```

That sounds much more credible than a cold "I made a thing."

---

## Target Scoring Rubric

Score each target from 0 to 10 before sending.

| Signal | Points |
|---|---:|
| Public notebook-heavy repo | 2 |
| Clear research/ML/data workflow | 2 |
| Evidence of handoff/onboarding pain | 2 |
| Person/team posts publicly about tooling or reproducibility | 2 |
| You can mention one specific repo or artifact | 2 |

Only send to targets scoring 6 or higher.

---

## Week-One Success Criteria

Week one is successful if:

- the repo is public and CI is green
- the static demo is live
- 20 thoughtful messages were sent
- at least 3 people reply
- at least 1 real feedback item becomes a shipped improvement
- the README and demo still explain the project in under 60 seconds

That is enough signal to decide whether to double down.
