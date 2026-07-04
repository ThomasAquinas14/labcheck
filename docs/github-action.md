# GitHub Action

`labcheck` can run as a no-key GitHub Action. It does not call an LLM, does not need a service account, and does not need a paid API.

Use it when you want every pull request or release branch to leave behind a reproducibility audit.

---

## Fastest Setup

From the repository you want to audit:

```bash
labcheck init .
```

This creates:

- `.labcheck.toml` with narrow starter exclusions
- `.github/workflows/labcheck.yml` with a soft audit that uploads scorecard, Markdown, JSON, SARIF, and badge reports

For labs, course repos, or ML teams, add a reproducibility handoff policy at the same time:

```bash
labcheck init . --policy
```

That also creates `docs/reproducibility.md`, a ready-to-edit policy for notebook reruns, input artifacts, generated outputs, dependency pinning, runtime metadata, README commands, and review expectations.

The command is conservative: it skips existing files unless you pass `--force`.

---

## Soft Audit

This workflow generates a compact scorecard plus Markdown, JSON, SARIF, and badge reports without failing CI. By default, the scorecard and Markdown report are appended to the GitHub Actions job summary. It is the best starting point for existing labs, course repos, and experiment-heavy codebases.

```yaml
name: labcheck

on:
  pull_request:
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: labcheck
        name: Run labcheck
        uses: ThomasAquinas14/labcheck@v1
        with:
          target: "."
          config-path: .labcheck.toml
          report-format: markdown
          report-path: labcheck-report.md
          json-path: labcheck-report.json
          sarif-path: labcheck-report.sarif
          badge-path: labcheck-badge.svg
          scorecard-path: labcheck-scorecard.md
          max-findings: "100"
          fail-on: none

      - name: Upload labcheck reports
        uses: actions/upload-artifact@v4
        with:
          name: labcheck-report
          path: |
            labcheck-report.md
            labcheck-report.json
            labcheck-report.sarif
            labcheck-badge.svg
            labcheck-scorecard.md
```

---

## Reproducibility Gate

Once a repo has cleaned up its baseline, set `fail-on` to `high`, `medium`, or `low`, or use `min-score` to require an overall reproducibility score.

```yaml
name: labcheck gate

on:
  pull_request:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: labcheck
        name: Run labcheck with high-severity gate
        uses: ThomasAquinas14/labcheck@v1
        with:
          target: "."
          report-format: markdown
          report-path: labcheck-report.md
          json-path: labcheck-report.json
          sarif-path: labcheck-report.sarif
          badge-path: labcheck-badge.svg
          scorecard-path: labcheck-scorecard.md
          max-findings: "100"
          fail-on: high
          min-score: "80"

      - name: Upload labcheck reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: labcheck-report
          path: |
            labcheck-report.md
            labcheck-report.json
            labcheck-report.sarif
            labcheck-badge.svg
            labcheck-scorecard.md
```

---

## Baseline And Ratchet

For existing repositories, you usually do not want to fail CI on every known historical issue. Create a baseline once, commit it, and then fail only on new findings.

Create the baseline locally:

```bash
labcheck baseline . --output .labcheck-baseline.json
```

Then use it in CI:

```yaml
name: labcheck ratchet

on:
  pull_request:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: labcheck
        name: Run labcheck against baseline
        uses: ThomasAquinas14/labcheck@v1
        with:
          target: "."
          baseline-path: .labcheck-baseline.json
          report-format: markdown
          report-path: labcheck-report.md
          json-path: labcheck-report.json
          sarif-path: labcheck-report.sarif
          badge-path: labcheck-badge.svg
          scorecard-path: labcheck-scorecard.md
          max-findings: "100"
          fail-on: high
          min-score: "90"

      - name: Upload labcheck reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: labcheck-report
          path: |
            labcheck-report.md
            labcheck-report.json
            labcheck-report.sarif
            labcheck-badge.svg
            labcheck-scorecard.md
```

When you intentionally fix old issues, regenerate the baseline in the same pull request so the repo ratchets toward a cleaner state.

---

## Action Inputs

| Input | Default | Purpose |
|---|---|---|
| `target` | `.` | Folder, notebook, zip archive, or public GitHub repo URL to scan. |
| `report-format` | `markdown` | Human report format: `text`, `markdown`, `json`, or `html`. |
| `report-path` | `labcheck-report.md` | Where to write the human-readable report. |
| `json-path` | `labcheck-report.json` | Where to write the machine-readable report. |
| `sarif-path` | `labcheck-report.sarif` | Where to write SARIF results for code-scanning integrations. |
| `badge-path` | `labcheck-badge.svg` | Where to write the static SVG score badge. |
| `scorecard-path` | `labcheck-scorecard.md` | Where to write the compact Markdown scorecard. |
| `baseline-path` | empty | Optional baseline JSON. Matching known findings are ignored. |
| `config-path` | empty | Optional `.labcheck.toml` config. Use it to exclude archived/generated paths or disable intentionally noisy checks. |
| `max-findings` | `100` | Maximum detailed findings to include in text, Markdown, and HTML reports. Use `all` for every detail. JSON and SARIF stay complete. |
| `job-summary` | `true` | Appends the Markdown report to the GitHub Actions job summary. |
| `fail-on` | `none` | Fails the job when findings exist at or above `high`, `medium`, or `low`. |
| `min-score` | empty | Optional minimum overall reproducibility score from `0` to `100`. |
| `python-version` | `3.11` | Python version used by the action. |

---

## Action Outputs

Give the Action step an `id` to use score and finding outputs in later workflow steps:

```yaml
- id: labcheck
  uses: ThomasAquinas14/labcheck@v1
  with:
    target: "."

- name: Print labcheck summary
  run: |
    echo "score=${{ steps.labcheck.outputs.overall-score }}"
    echo "findings=${{ steps.labcheck.outputs.findings-count }}"
    echo "high=${{ steps.labcheck.outputs.high-count }}"
```

### Copy-paste PR summary

Use the outputs to add a compact scorecard to the GitHub Actions job summary. This keeps the result visible on every PR without extra tokens, secrets, or write permissions:

```yaml
- id: labcheck
  uses: ThomasAquinas14/labcheck@v1
  with:
    target: "."
    config-path: .labcheck.toml
    baseline-path: .labcheck-baseline.json
    fail-on: high
    min-score: "80"

- name: Add labcheck PR summary
  if: always()
  run: |
    {
      echo "## labcheck reproducibility score"
      echo ""
      echo "| Metric | Value |"
      echo "|---|---:|"
      echo "| Overall score | ${{ steps.labcheck.outputs.overall-score }} |"
      echo "| Findings | ${{ steps.labcheck.outputs.findings-count }} |"
      echo "| High | ${{ steps.labcheck.outputs.high-count }} |"
      echo "| Medium | ${{ steps.labcheck.outputs.medium-count }} |"
      echo "| Low | ${{ steps.labcheck.outputs.low-count }} |"
    } >> "$GITHUB_STEP_SUMMARY"
```

### Optional sticky PR comment

If you want the score directly in the pull request conversation, use the built-in `GITHUB_TOKEN` and update one sticky comment instead of creating a new comment on every push:

```yaml
permissions:
  contents: read
  pull-requests: write

jobs:
  labcheck:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - id: labcheck
        uses: ThomasAquinas14/labcheck@v1
        with:
          target: "."
          config-path: .labcheck.toml
          baseline-path: .labcheck-baseline.json
          fail-on: high
          min-score: "80"

      - name: Comment labcheck score on PR
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v7
        with:
          script: |
            const marker = '<!-- labcheck-summary -->';
            const body = `${marker}
            ## labcheck reproducibility score

            | Metric | Value |
            |---|---:|
            | Overall score | ${{ steps.labcheck.outputs.overall-score }} |
            | Findings | ${{ steps.labcheck.outputs.findings-count }} |
            | High | ${{ steps.labcheck.outputs.high-count }} |
            | Medium | ${{ steps.labcheck.outputs.medium-count }} |
            | Low | ${{ steps.labcheck.outputs.low-count }} |`;

            const { owner, repo } = context.repo;
            const issue_number = context.payload.pull_request.number;
            const { data: comments } = await github.rest.issues.listComments({
              owner,
              repo,
              issue_number,
              per_page: 100,
            });
            const existing = comments.find((comment) =>
              comment.user?.type === 'Bot' && comment.body?.includes(marker)
            );

            if (existing) {
              await github.rest.issues.updateComment({
                owner,
                repo,
                comment_id: existing.id,
                body,
              });
            } else {
              await github.rest.issues.createComment({
                owner,
                repo,
                issue_number,
                body,
              });
            }
```

Available outputs:

| Output | Meaning |
|---|---|
| `overall-score` | Overall reproducibility score. |
| `environment-score` | Environment Rebuildability score. |
| `determinism-score` | Notebook Determinism score. |
| `artifact-score` | Artifact Availability score. |
| `portability-score` | Portability score. |
| `onboarding-score` | Onboarding Readiness score. |
| `findings-count` | Total findings after baseline filtering. |
| `high-count` | High-severity findings after baseline filtering. |
| `medium-count` | Medium-severity findings after baseline filtering. |
| `low-count` | Low-severity findings after baseline filtering. |
| `scorecard-path` | Path to the compact Markdown scorecard. |

---

## Excluding Intentional Noise

Create a `.labcheck.toml` file when a repo has archived experiments, generated notebooks, vendored examples, or teaching materials that should not affect the reproducibility score.

```toml
exclude = [
  "archive/**",
  "labcheck-audit/**",
  "notebooks/generated/**",
  ".ipynb_checkpoints/**",
  "scratch.py",
]

# Use sparingly for known intentional patterns that would otherwise dominate
# the report with low-signal findings.
disabled_checks = [
  # "LC010",
]
```

The CLI discovers `.labcheck.toml` automatically when scanning a local folder. In CI, pass it explicitly with `config-path` so the Action behavior is obvious in workflow reviews:

```yaml
with:
  target: "."
  config-path: .labcheck.toml
```

---

## Local Equivalent

The action is intentionally just a thin wrapper around the CLI:

```bash
labcheck scan . \
  --format markdown \
  --output labcheck-report.md \
  --json-output labcheck-report.json \
  --sarif-output labcheck-report.sarif \
  --badge-output labcheck-badge.svg \
  --scorecard-output labcheck-scorecard.md \
  --max-findings 100 \
  --config .labcheck.toml \
  --baseline .labcheck-baseline.json \
  --fail-on high \
  --min-score 90
```

That makes the GitHub Action easy to debug locally and safe to run in public repositories.

If you want a single shareable folder for outreach, release notes, or a lab handoff, use the equivalent pack command:

```bash
labcheck pack . \
  --output-dir labcheck-audit \
  --zip \
  --config .labcheck.toml \
  --baseline .labcheck-baseline.json \
  --fail-on high \
  --min-score 90
```

---

## Optional Code Scanning Upload

If your repository has GitHub code scanning enabled, upload the generated SARIF report in a follow-up step:

```yaml
permissions:
  security-events: write

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run labcheck
        uses: ThomasAquinas14/labcheck@v1
        with:
          target: "."
          sarif-path: labcheck-report.sarif
          fail-on: none

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: labcheck-report.sarif
```
