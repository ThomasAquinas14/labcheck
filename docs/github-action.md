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
- `.github/workflows/labcheck.yml` with a soft audit that uploads scorecard, target-fit, issue draft, Markdown, CSV, JSON, SARIF, and badge reports

The generated workflow requests only `contents: read`. It does not need repository secrets or write permissions unless you add optional comment/code-scanning steps yourself.

For labs, course repos, or ML teams, add a reproducibility handoff policy at the same time:

```bash
labcheck init . --policy
```

That also creates `docs/reproducibility.md`, a ready-to-edit policy for notebook reruns, input artifacts, generated outputs, dependency pinning, runtime metadata, README commands, and review expectations.

The command is conservative: it skips existing files unless you pass `--force`.

---

## Soft Audit

This workflow generates a compact scorecard, outreach target-fit card, maintainer issue draft, Markdown, CSV, JSON, SARIF, and badge reports without failing CI. By default, the scorecard, target-fit card, and Markdown report are appended to the GitHub Actions job summary. It is the best starting point for existing labs, course repos, and experiment-heavy codebases.

```yaml
name: labcheck

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

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
          csv-path: labcheck-report.csv
          sarif-path: labcheck-report.sarif
          badge-path: labcheck-badge.svg
          scorecard-path: labcheck-scorecard.md
          target-fit-path: labcheck-target-fit.md
          issue-draft-path: labcheck-issue-draft.md
          max-findings: "100"
          fail-on: none

      - name: Upload labcheck reports
        uses: actions/upload-artifact@v4
        with:
          name: labcheck-report
          if-no-files-found: warn
          retention-days: 14
          path: |
            labcheck-report.md
            labcheck-report.json
            labcheck-report.csv
            labcheck-report.sarif
            labcheck-badge.svg
            labcheck-scorecard.md
            labcheck-target-fit.md
            labcheck-issue-draft.md
```

---

## Reproducibility Gate

Once a repo has cleaned up its baseline, set `fail-on` to `high`, `medium`, or `low`, or use `min-score` to require an overall reproducibility score.

```yaml
name: labcheck gate

on:
  pull_request:

permissions:
  contents: read

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
          csv-path: labcheck-report.csv
          sarif-path: labcheck-report.sarif
          badge-path: labcheck-badge.svg
          scorecard-path: labcheck-scorecard.md
          target-fit-path: labcheck-target-fit.md
          issue-draft-path: labcheck-issue-draft.md
          max-findings: "100"
          fail-on: high
          min-score: "80"

      - name: Upload labcheck reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: labcheck-report
          if-no-files-found: warn
          retention-days: 14
          path: |
            labcheck-report.md
            labcheck-report.json
            labcheck-report.csv
            labcheck-report.sarif
            labcheck-badge.svg
            labcheck-scorecard.md
            labcheck-target-fit.md
            labcheck-issue-draft.md
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

permissions:
  contents: read

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
          csv-path: labcheck-report.csv
          sarif-path: labcheck-report.sarif
          badge-path: labcheck-badge.svg
          scorecard-path: labcheck-scorecard.md
          target-fit-path: labcheck-target-fit.md
          issue-draft-path: labcheck-issue-draft.md
          max-findings: "100"
          fail-on: high
          min-score: "90"

      - name: Upload labcheck reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: labcheck-report
          if-no-files-found: warn
          retention-days: 14
          path: |
            labcheck-report.md
            labcheck-report.json
            labcheck-report.csv
            labcheck-report.sarif
            labcheck-badge.svg
            labcheck-scorecard.md
            labcheck-target-fit.md
            labcheck-issue-draft.md
```

When you intentionally fix old issues, regenerate the baseline in the same pull request so the repo ratchets toward a cleaner state.

---

## Monorepo Matrix Ratchet

For monorepos, avoid one giant root baseline owned by nobody. Give each supported package, course folder, or research workflow its own target, config, baseline, score floor, and uploaded artifact name:

```yaml
name: labcheck monorepo ratchet

on:
  pull_request:

permissions:
  contents: read

jobs:
  audit:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        include:
          - name: notebooks
            target: notebooks
            config: notebooks/.labcheck.toml
            baseline: notebooks/.labcheck-baseline.json
            min_score: "85"
          - name: ml-service
            target: services/ml
            config: services/ml/.labcheck.toml
            baseline: services/ml/.labcheck-baseline.json
            min_score: "90"

    steps:
      - uses: actions/checkout@v4

      - id: labcheck
        name: Run labcheck for ${{ matrix.name }}
        uses: ThomasAquinas14/labcheck@v1
        with:
          target: ${{ matrix.target }}
          config-path: ${{ matrix.config }}
          baseline-path: ${{ matrix.baseline }}
          report-path: labcheck-${{ matrix.name }}.md
          json-path: labcheck-${{ matrix.name }}.json
          csv-path: labcheck-${{ matrix.name }}.csv
          sarif-path: labcheck-${{ matrix.name }}.sarif
          badge-path: labcheck-${{ matrix.name }}-badge.svg
          scorecard-path: labcheck-${{ matrix.name }}-scorecard.md
          target-fit-path: labcheck-${{ matrix.name }}-target-fit.md
          issue-draft-path: labcheck-${{ matrix.name }}-issue-draft.md
          fail-on: high
          min-score: ${{ matrix.min_score }}

      - name: Upload ${{ matrix.name }} labcheck reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: labcheck-${{ matrix.name }}
          if-no-files-found: warn
          retention-days: 14
          path: |
            labcheck-${{ matrix.name }}.md
            labcheck-${{ matrix.name }}.json
            labcheck-${{ matrix.name }}.csv
            labcheck-${{ matrix.name }}.sarif
            labcheck-${{ matrix.name }}-badge.svg
            labcheck-${{ matrix.name }}-scorecard.md
            labcheck-${{ matrix.name }}-target-fit.md
            labcheck-${{ matrix.name }}-issue-draft.md
```

Create each baseline from the same target before enabling the matrix:

```bash
labcheck baseline notebooks --config notebooks/.labcheck.toml --output notebooks/.labcheck-baseline.json
labcheck baseline services/ml --config services/ml/.labcheck.toml --output services/ml/.labcheck-baseline.json
```

This keeps ownership clear: the notebooks team can lower its baseline without waiting for the service team, and each package can ratchet toward a stricter `min-score` at its own pace. Leave unsupported or archived directories out of the matrix until someone agrees to own their findings.

---

## Before/After Compare In CI

If your workflow has access to an earlier `labcheck-report.json`, the Action can generate a before/after improvement note from the previous JSON and the current JSON report:

```yaml
- id: labcheck
  uses: ThomasAquinas14/labcheck@v1
  with:
    target: "."
    json-path: labcheck-report.json
    compare-base-json-path: previous-labcheck-report.json
    compare-path: labcheck-compare.md
```

The compare note shows score deltas, severity deltas, resolved findings, and new findings. Use it in PRs, release notes, lab handoff updates, or founder diligence follow-ups. The Action does not download old artifacts by itself; keep the previous JSON in the repo, generate it in an earlier workflow step, or download it with your own no-secret artifact step before running `labcheck`.

---

## Action Inputs

| Input | Default | Purpose |
|---|---|---|
| `target` | `.` | Folder, notebook, zip archive, or public GitHub repo URL to scan. |
| `report-format` | `markdown` | Report format: `text`, `markdown`, `json`, `csv`, `html`, or `sarif`. |
| `report-path` | `labcheck-report.md` | Where to write the human-readable report. |
| `json-path` | `labcheck-report.json` | Where to write the machine-readable report. |
| `csv-path` | `labcheck-report.csv` | Where to write the spreadsheet-friendly findings table. |
| `sarif-path` | `labcheck-report.sarif` | Where to write SARIF results for code-scanning integrations. |
| `badge-path` | `labcheck-badge.svg` | Where to write the static SVG score badge. |
| `scorecard-path` | `labcheck-scorecard.md` | Where to write the compact Markdown scorecard. |
| `target-fit-path` | `labcheck-target-fit.md` | Where to write the outreach target-fit card. |
| `issue-draft-path` | `labcheck-issue-draft.md` | Where to write the maintainer-friendly GitHub issue draft. |
| `compare-base-json-path` | empty | Optional earlier `labcheck-report.json` to compare against the current JSON report. |
| `compare-path` | `labcheck-compare.md` | Where to write the before/after comparison note when `compare-base-json-path` is provided. |
| `baseline-path` | empty | Optional baseline JSON. Matching known findings are ignored. |
| `config-path` | empty | Optional `.labcheck.toml` config. Use it to exclude archived/generated paths or disable intentionally noisy checks. |
| `max-findings` | `100` | Maximum detailed findings to include in text, Markdown, and HTML reports. Use `all` for every detail. JSON, CSV, and SARIF stay complete. |
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
    echo "triage=${{ steps.labcheck.outputs.triage-signal }}"
    echo "top-risk=${{ steps.labcheck.outputs.top-risk-id }} ${{ steps.labcheck.outputs.top-risk-title }}"
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
      echo "| Triage | ${{ steps.labcheck.outputs.triage-signal }} |"
      echo "| Top risk | ${{ steps.labcheck.outputs.top-risk-id }} ${{ steps.labcheck.outputs.top-risk-title }} |"
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
            | Low | ${{ steps.labcheck.outputs.low-count }} |
            | Triage | ${{ steps.labcheck.outputs.triage-signal }} |
            | Top risk | ${{ steps.labcheck.outputs.top-risk-id }} ${{ steps.labcheck.outputs.top-risk-title }} |`;

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
| `triage-status` | Compact handoff status: `strong`, `blocked`, `mostly-usable`, or `needs-work`. |
| `triage-signal` | Human-readable handoff signal derived from the score and severity mix. |
| `top-risk-id` | Finding ID for the highest-priority grouped risk, or empty when no findings remain. |
| `top-risk-title` | Title for the highest-priority grouped risk, or empty when no findings remain. |
| `top-risk-severity` | Severity for the highest-priority grouped risk, or empty when no findings remain. |
| `top-risk-file` | First affected file for the highest-priority grouped risk, or empty when no findings remain. |
| `top-risk-count` | Number of findings in the highest-priority grouped risk. |
| `scorecard-path` | Path to the compact Markdown scorecard. |
| `target-fit-path` | Path to the outreach target-fit card. |
| `issue-draft-path` | Path to the maintainer-friendly GitHub issue draft. |
| `compare-path` | Path to the before/after comparison note, when generated. |

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

[[ignored_findings]]
check_id = "LC010"
path = "archive/old_experiment.py"
reason = "Archival script kept for context, not a supported rerun path."
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
  --csv-output labcheck-report.csv \
  --sarif-output labcheck-report.sarif \
  --badge-output labcheck-badge.svg \
  --scorecard-output labcheck-scorecard.md \
  --target-fit-output labcheck-target-fit.md \
  --issue-output labcheck-issue-draft.md \
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
