# Outreach Tracker Template

Copy this table into a spreadsheet, Notion page, issue, or private notes file for the first launch batch.

Do not track private personal information in the public repository. Keep real emails, DMs, and private notes outside the repo.

---

## Columns

| Column | Purpose |
|---|---|
| `status` | `queued`, `sent`, `replied`, `followed_up`, `declined`, `converted` |
| `audience` | `professor`, `lab`, `founder`, `ml_lead`, `maintainer` |
| `name_or_team` | Public name of the person, lab, company, or repo owner |
| `public_link` | Public website, GitHub repo, lab page, or company page |
| `fit_score` | 0 to 10 using the rubric in [launch-week-plan.md](launch-week-plan.md) |
| `why_relevant` | One specific reason this person/team is a good fit |
| `asset_sent` | `demo`, `sample_audit`, `scorecard`, `case_study`, `github_action` |
| `message_angle` | One-line angle used in the message |
| `sent_date` | Date sent |
| `follow_up_date` | Usually 5 to 7 days after `sent_date` |
| `reply_summary` | Short non-sensitive summary of the reply |
| `next_action` | `run_scorecard`, `open_issue`, `send_docs`, `thank`, `none` |

---

## Template

| status | audience | name_or_team | public_link | fit_score | why_relevant | asset_sent | message_angle | sent_date | follow_up_date | reply_summary | next_action |
|---|---|---|---|---:|---|---|---|---|---|---|---|
| queued | professor |  |  |  | Public notebook-heavy research repo | sample_audit | Can I run a reproducibility scorecard on one public repo? |  |  |  | run_scorecard |
| queued | lab |  |  |  | Lab publishes notebooks or course repos | demo | Pre-handoff check for students/reviewers |  |  |  | run_scorecard |
| queued | founder |  |  |  | ML/data team likely hands off experiment repos | scorecard | Reproducibility and portability audit before onboarding |  |  |  | run_scorecard |
| queued | maintainer |  |  |  | Notebook-heavy OSS examples | github_action | Soft CI audit without API keys or service accounts |  |  |  | send_docs |

---

## Message Angles

### Professor or lab

```text
I noticed your lab shares notebook-heavy work publicly. I built a no-key reproducibility auditor that catches hidden notebook state, missing input files, stale setup commands, and unclear output provenance. If useful, I can run it on one public repo and send a short scorecard.
```

### Founder or ML/data lead

```text
I built a no-key reproducibility and portability auditor for experiment-heavy ML/data repos. It is useful before onboarding, contractor handoff, technical diligence, or turning a notebook workflow into team-owned code. If helpful, I can run it on one public repo and send a compact scorecard.
```

### OSS maintainer

```text
I built a no-key GitHub Action/CLI that audits notebook-heavy repos for hidden state, missing artifacts, stale README commands, and unseeded randomness. It can start as a soft report artifact without failing CI. Curious if this would be useful for your examples or contributor onboarding.
```

---

## Follow-Up Timing

Use one follow-up only unless they reply.

Wait 5 to 7 days, then send:

```text
Quick follow-up in case this was useful. The smallest way to try it is the browser demo, or I can run a scorecard on one public repo and send the result. No worries if not relevant.
```

Do not guilt, pressure, or keep nudging. The project should feel useful, not needy.

---

## Conversion Events

Count these as wins:

- someone stars the repo
- someone asks for a scorecard
- someone suggests a check
- someone opens an issue
- someone tries the GitHub Action
- someone asks to use it in a lab/team workflow
- someone says the pain is real even if they do not adopt yet

Week one is about signal, not vanity.
