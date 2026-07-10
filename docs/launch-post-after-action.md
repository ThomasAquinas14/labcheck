# Launch Post After-Action Checklist

Use this immediately after the first public launch post, demo-video post, Hacker News comment, LinkedIn post, X thread, Reddit post, or targeted founder/professor share.

The goal is not to squeeze the post for vanity metrics. The goal is to turn one public moment into useful evidence:

- what people understood
- what confused them
- which links they clicked or asked for
- which finding types created real interest
- which follow-up issue or docs change should happen next

---

## 1. Save The Proof Links

Record these before editing copy or replying widely:

```text
Launch post URL:
GitHub repo URL:
Static demo URL:
Sample audit URL:
Sample scorecard URL:
Demo video URL:
Date/time posted:
Channel:
```

If the post includes a video or screenshot, save the final file name and thumbnail. A launch is easier to learn from when the artifact does not keep changing underneath the numbers.

---

## 2. Capture The Baseline

Take one snapshot before the post and another after 24 hours.

```text
Before:
- GitHub stars:
- Forks:
- Open issues:
- CI status:
- Pages/static site status:

After 24 hours:
- GitHub stars:
- Forks:
- Open issues:
- Useful replies:
- Direct messages:
- Public audit requests:
- Concrete bug reports:
- Concrete false-positive reports:
```

Do not obsess over precision. A small, honest baseline is better than a fuzzy story later.

---

## 3. Check Whether The Message Was Clear

Score the launch post from 0 to 2 for each signal.

| Signal | Score |
|---|---:|
| A reader can understand "no API keys, no hosted backend" in 10 seconds | 0-2 |
| The post shows concrete findings, not generic AI/tooling claims | 0-2 |
| The post links a working demo or sample audit | 0-2 |
| The post says what labcheck does not prove | 0-2 |
| The post gives one clear next action | 0-2 |

If the total is below 7, improve the next post before sending more outreach.

---

## 4. Triage Replies

Classify every useful reply into one bucket.

| Reply Type | Follow-Up |
|---|---|
| "This is useful" | Ask whether one finding category would make it more useful for their workflow. |
| "This finding is noisy" | Ask for the smallest public example and record it as a false-positive issue. |
| "Can it run in CI?" | Link the [GitHub Action guide](github-action.md). |
| "Can I try it locally?" | Link the [install guide](install.md) and one `labcheck demo-repo` command. |
| "Does it prove reproducibility?" | Link the [privacy and safety model](privacy-and-safety.md) and clarify that it is a first-pass handoff signal. |
| "Can you scan our repo?" | Only accept public repos or repos they have permission to share. |
| "I found a bug" | Ask for OS, Python version, command, and repo shape; then open a focused issue. |

Use [maintainer-reply-templates.md](maintainer-reply-templates.md) when replying under a public issue or audit request.

---

## 5. Convert Attention Into One Public Artifact

Within 48 hours, ship one small follow-up that proves the project is alive.

Good options:

- a bug fix with a regression test
- a false-positive reduction
- a new example in [reproducibility-patterns.md](reproducibility-patterns.md)
- a new public audit request in [public-triage-board.md](public-triage-board.md)
- a reply-derived case study using [reply-to-case-study-checklist.md](reply-to-case-study-checklist.md)
- a small docs clarification in [first-audit.md](first-audit.md)
- a new issue labeled with [issue-labels.md](issue-labels.md)

Avoid turning early attention into a huge rewrite. The best public follow-up is small, specific, and obviously connected to feedback.

---

## 6. Write The After-Action Note

Copy this into a private notes file, issue, or launch tracker.

```text
# labcheck launch after-action

Post:
Date:
Channel:

What people understood fastest:

What confused people:

Most clicked/shared asset:

Most useful reply:

Most credible target audience:

Finding category that resonated:

False-positive or bug reported:

One shipped follow-up:

Next post angle:
```

Keep this boring. Boring notes become useful launch judgment.

---

## 7. Safe Follow-Up Post

Use this only if you shipped a real follow-up from feedback.

```text
Small follow-up from the first labcheck launch feedback:

Someone pointed out that <specific thing> was confusing/noisy/useful, so I added <small change>.

The project is still intentionally local-first and no-key: no hosted backend, no inference bill, no repo secrets.

Change: <link>
Demo/sample: <link>
```

Do not write a follow-up just to revive the post. Write it only when there is a concrete improvement or useful lesson.

---

## 8. What Not To Do

- Do not ask strangers to star the repo as the main call to action.
- Do not imply labcheck proves a paper, benchmark, or scientific result is reproducible.
- Do not scan private code or attach private findings to a public issue.
- Do not keep bumping a post that did not get traction.
- Do not hide false positives; use them as evidence that the tool is being sharpened.

The launch is successful if it produces one stronger project artifact, not just one louder announcement.
