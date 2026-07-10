# labcheck Report

- Target: `https://github.com/jakevdp/PythonDataScienceHandbook`
- Overall Score: **19**
- Severity Mix: **82 high**, **118 medium**, **120 low**

## Review Boundary

This is a static, no-key first-pass audit. It does not execute the project code by default, does not upload source files to a hosted backend, and does not prove scientific validity; use it to prioritize rerun and handoff risks before deeper verification.

## Scores

| Category | Score | What it means |
|---|---:|---|
| Environment Rebuildability | 57 | Can a new person recreate the environment without guesswork? |
| Notebook Determinism | 0 | Will notebooks run cleanly from top to bottom without invisible state? |
| Artifact Availability | 0 | Are referenced inputs and generated artifacts present or clearly accounted for? |
| Portability | 52 | Does the repo avoid machine-specific assumptions and brittle paths? |
| Onboarding Readiness | 28 | How likely is a new contributor to succeed from the docs and structure alone? |

## Top Risks

| Risk | Severity | Scope | First evidence |
|---|---|---|---|
| `LC002` Likely hidden notebook state | `high` | 67 findings across 67 files | notebooks/02.04-Computation-on-arrays-aggregates.ipynb: 4 cells reference names with no visible prior definition; examples: cell 5: big_array; cell 6: big_array; cell 8: big_array |
| `LC005` Referenced input artifact missing from repo | `high` | 11 findings across 9 files | notebooks/03.10-Working-With-Strings.ipynb: Reads 'data/recipeitems.json', but that path is not present in the scanned repo. |
| `LC001` Suspicious notebook execution order | `high` | 4 findings across 4 files | notebooks/05.08-Random-Forests.ipynb: Execution counts are non-monotonic: [1, 2, 3, 6, 10, 11, 9, 12, 13, 14, 15, 16, 17, 19, 20, 23] |
| `LC007` Randomness used without visible seeding | `medium` | 62 findings across 62 files | notebooks/01.07-Timing-and-Profiling.ipynb: Detected randomness-related APIs, but no obvious seed call in the same file. |
| `LC009` Committed output has no visible producer | `medium` | 41 findings across 41 files | notebooks/figures/02.05-broadcasting.png: 'notebooks/figures/02.05-broadcasting.png' looks like a generated artifact, but no scanned notebook or script visibly writes it. |

## Understand Finding Codes

Run these commands for plain-language context, why the finding matters, and the expected fix:

- `labcheck explain LC002`
- `labcheck explain LC005`
- `labcheck explain LC001`

## Remediation Plan

1. **Fix LC002 first because it affects 67 findings across 67 files.**
   Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.
   First evidence: `notebooks/02.04-Computation-on-arrays-aggregates.ipynb` - 4 cells reference names with no visible prior definition; examples: cell 5: big_array; cell 6: big_array; cell 8: big_array

2. **Fix LC005 first because it affects 11 findings across 9 files.**
   Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.
   First evidence: `notebooks/03.10-Working-With-Strings.ipynb` - Reads 'data/recipeitems.json', but that path is not present in the scanned repo.

3. **Fix LC001 first because it affects 4 findings across 4 files.**
   Suggested fix: Restart the kernel and run all cells before committing the notebook.
   First evidence: `notebooks/05.08-Random-Forests.ipynb` - Execution counts are non-monotonic: [1, 2, 3, 6, 10, 11, 9, 12, 13, 14, 15, 16, 17, 19, 20, 23]

4. **Fix LC007 first because it affects 62 findings across 62 files.**
   Suggested fix: Set and document seeds for the randomness sources used in this workflow.
   First evidence: `notebooks/01.07-Timing-and-Profiling.ipynb` - Detected randomness-related APIs, but no obvious seed call in the same file.

5. **Fix LC009 first because it affects 41 findings across 41 files.**
   Suggested fix: Add or document the generating notebook/script, or move archival outputs behind an explicit exclusion.
   First evidence: `notebooks/figures/02.05-broadcasting.png` - 'notebooks/figures/02.05-broadcasting.png' looks like a generated artifact, but no scanned notebook or script visibly writes it.


## Next Steps

- Scorecard summary: `labcheck scorecard https://github.com/jakevdp/PythonDataScienceHandbook`
- Sortable triage CSV: `labcheck scan https://github.com/jakevdp/PythonDataScienceHandbook --format csv --output labcheck-findings.csv`
- Shareable audit bundle: `labcheck pack https://github.com/jakevdp/PythonDataScienceHandbook --output-dir labcheck-audit --zip`
- Explain top finding: `labcheck explain LC002`

## Provenance Graph

- Nodes: 225
- Edges: 95

| Source | Edge | Target |
|---|---|---|
| `data/president_heights.csv` | `reads` | `notebooks/02.04-Computation-on-arrays-aggregates.ipynb` |
| `data/state-population.csv` | `reads` | `notebooks/03.07-Merge-and-Join.ipynb` |
| `data/state-areas.csv` | `reads` | `notebooks/03.07-Merge-and-Join.ipynb` |
| `data/state-abbrevs.csv` | `reads` | `notebooks/03.07-Merge-and-Join.ipynb` |
| `data/births.csv` | `reads` | `notebooks/03.09-Pivot-Tables.ipynb` |
| `data/recipeitems.json` | `reads` | `notebooks/03.10-Working-With-Strings.ipynb` |
| `FremontBridge.csv` | `reads` | `notebooks/03.11-Working-with-Time-Series.ipynb` |
| `notebooks/04.00-Introduction-To-Matplotlib.ipynb` | `writes` | `my_figure.png` |
| `data/california_cities.csv` | `reads` | `notebooks/04.06-Customizing-Legends.ipynb` |
| `data/births.csv` | `reads` | `notebooks/04.09-Text-and-Annotation.ipynb` |
| `data/marathon-data.csv` | `reads` | `notebooks/04.14-Visualization-With-Seaborn.ipynb` |
| `FremontBridge.csv` | `reads` | `notebooks/05.06-Linear-Regression.ipynb` |
| `SeattleWeather.csv` | `reads` | `notebooks/05.06-Linear-Regression.ipynb` |
| `notebooks/05.10-Manifold-Learning.ipynb` | `writes` | `hello.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/02.05-broadcasting.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/03.08-split-apply-combine.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-classification-1.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-classification-2.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-classification-3.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-regression-1.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-regression-2.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-regression-3.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-regression-4.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-clustering-1.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-clustering-2.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-dimesionality-1.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.01-dimesionality-2.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.02-samples-features.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.03-2-fold-CV.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.03-5-fold-CV.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.03-bias-variance.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.03-bias-variance-2.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.03-validation-curve.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.03-learning-curve.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.05-gaussian-NB.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.06-gaussian-basis.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.08-decision-tree.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.08-decision-tree-levels.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.08-decision-tree-overfitting.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.09-PCA-rotation.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.09-digits-pixel-components.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.09-digits-pca-components.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `hello.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.10-LLE-vs-MDS.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.11-expectation-maximization.png` |
| `notebooks/06.00-Figure-Code.ipynb` | `writes` | `images/05.12-covariance-type.png` |
| `data/president_heights.csv` | `reads` | `notebooks_v1/02.04-Computation-on-arrays-aggregates.ipynb` |
| `data/Seattle2014.csv` | `reads` | `notebooks_v1/02.06-Boolean-Arrays-and-Masks.ipynb` |
| `data/state-population.csv` | `reads` | `notebooks_v1/03.07-Merge-and-Join.ipynb` |
| `data/state-areas.csv` | `reads` | `notebooks_v1/03.07-Merge-and-Join.ipynb` |
| `data/state-abbrevs.csv` | `reads` | `notebooks_v1/03.07-Merge-and-Join.ipynb` |
| `data/births.csv` | `reads` | `notebooks_v1/03.09-Pivot-Tables.ipynb` |
| `recipeitems-latest.json` | `reads` | `notebooks_v1/03.10-Working-With-Strings.ipynb` |
| `[{0}]` | `reads` | `notebooks_v1/03.10-Working-With-Strings.ipynb` |
| `FremontBridge.csv` | `reads` | `notebooks_v1/03.11-Working-with-Time-Series.ipynb` |
| `notebooks_v1/04.00-Introduction-To-Matplotlib.ipynb` | `writes` | `my_figure.png` |
| `data/california_cities.csv` | `reads` | `notebooks_v1/04.06-Customizing-Legends.ipynb` |
| `data/births.csv` | `reads` | `notebooks_v1/04.09-Text-and-Annotation.ipynb` |
| `data/california_cities.csv` | `reads` | `notebooks_v1/04.13-Geographic-Data-With-Basemap.ipynb` |
| `marathon-data.csv` | `reads` | `notebooks_v1/04.14-Visualization-With-Seaborn.ipynb` |
| `FremontBridge.csv` | `reads` | `notebooks_v1/05.06-Linear-Regression.ipynb` |
| `data/BicycleWeather.csv` | `reads` | `notebooks_v1/05.06-Linear-Regression.ipynb` |
| `notebooks_v1/05.10-Manifold-Learning.ipynb` | `writes` | `hello.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/02.05-broadcasting.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/03.08-split-apply-combine.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-classification-1.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-classification-2.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-classification-3.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-regression-1.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-regression-2.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-regression-3.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-regression-4.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-clustering-1.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-clustering-2.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-dimesionality-1.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.01-dimesionality-2.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.02-samples-features.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.03-2-fold-CV.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.03-5-fold-CV.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.03-bias-variance.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.03-bias-variance-2.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.03-validation-curve.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.03-learning-curve.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.05-gaussian-NB.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.06-gaussian-basis.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.08-decision-tree.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.08-decision-tree-levels.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.08-decision-tree-overfitting.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.09-PCA-rotation.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.09-digits-pixel-components.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.09-digits-pca-components.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `hello.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.10-LLE-vs-MDS.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.11-expectation-maximization.png` |
| `notebooks_v1/06.00-Figure-Code.ipynb` | `writes` | `figures/05.12-covariance-type.png` |

## Findings

Showing first 100 findings; 220 omitted.

Use `--max-findings all` to include every detail in human-readable reports. JSON, CSV, and SARIF outputs remain complete.

### LC001 - Suspicious notebook execution order

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.08-Random-Forests.ipynb`
- Evidence: Execution counts are non-monotonic: [1, 2, 3, 6, 10, 11, 9, 12, 13, 14, 15, 16, 17, 19, 20, 23]
- Why it matters: The notebook may rely on hidden runtime state rather than a clean top-to-bottom execution path.
- Suggested fix: Restart the kernel and run all cells before committing the notebook.

### LC001 - Suspicious notebook execution order

- Severity: `high`
- Category: `determinism`
- File: `notebooks/06.00-Figure-Code.ipynb`
- Evidence: Execution counts are non-monotonic: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 51, 53, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47]
- Why it matters: The notebook may rely on hidden runtime state rather than a clean top-to-bottom execution path.
- Suggested fix: Restart the kernel and run all cells before committing the notebook.

### LC001 - Suspicious notebook execution order

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.05-Histograms-and-Binnings.ipynb`
- Evidence: Execution counts are non-monotonic: [1, 2, 3, 4, 5, 6, 12, 8, 9, 10]
- Why it matters: The notebook may rely on hidden runtime state rather than a clean top-to-bottom execution path.
- Suggested fix: Restart the kernel and run all cells before committing the notebook.

### LC001 - Suspicious notebook execution order

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.14-Visualization-With-Seaborn.ipynb`
- Evidence: Execution counts are non-monotonic: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 38, 37]
- Why it matters: The notebook may rely on hidden runtime state rather than a clean top-to-bottom execution path.
- Suggested fix: Restart the kernel and run all cells before committing the notebook.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/02.04-Computation-on-arrays-aggregates.ipynb`
- Evidence: 4 cells reference names with no visible prior definition; examples: cell 5: big_array; cell 6: big_array; cell 8: big_array
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/02.05-Computation-on-arrays-broadcasting.ipynb`
- Evidence: 1 cells reference names with no visible prior definition; examples: cell 23: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/02.06-Boolean-Arrays-and-Masks.ipynb`
- Evidence: 1 cells reference names with no visible prior definition; examples: cell 3: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/02.07-Fancy-Indexing.ipynb`
- Evidence: 2 cells reference names with no visible prior definition; examples: cell 17: plt; cell 24: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/02.08-Sorting.ipynb`
- Evidence: 1 cells reference names with no visible prior definition; examples: cell 22: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/03.11-Working-with-Time-Series.ipynb`
- Evidence: 6 cells reference names with no visible prior definition; examples: cell 28: plt; cell 29: plt; cell 30: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/03.12-Performance-Eval-and-Query.ipynb`
- Evidence: 18 cells reference names with no visible prior definition; examples: cell 3: x, y; cell 4: x, y; cell 5: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.01-Simple-Line-Plots.ipynb`
- Evidence: 14 cells reference names with no visible prior definition; examples: cell 2: plt; cell 3: np, plt; cell 4: np, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.02-Simple-Scatter-Plots.ipynb`
- Evidence: 7 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 3: np, plt; cell 4: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.03-Errorbars.ipynb`
- Evidence: 4 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 3: plt; cell 4: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.04-Density-and-Contour-Plots.ipynb`
- Evidence: 6 cells reference names with no visible prior definition; examples: cell 3: np; cell 4: plt; cell 5: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.05-Histograms-and-Binnings.ipynb`
- Evidence: 9 cells reference names with no visible prior definition; examples: cell 2: data, plt; cell 3: data, plt; cell 4: plt, rng
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.06-Customizing-Legends.ipynb`
- Evidence: 4 cells reference names with no visible prior definition; examples: cell 3: np; cell 7: np; cell 10: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.07-Customizing-Colorbars.ipynb`
- Evidence: 2 cells reference names with no visible prior definition; examples: cell 3: np; cell 9: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.08-Multiple-Subplots.ipynb`
- Evidence: 8 cells reference names with no visible prior definition; examples: cell 2: plt; cell 3: np, plt; cell 4: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.09-Text-and-Annotation.ipynb`
- Evidence: 6 cells reference names with no visible prior definition; examples: cell 3: np, pd; cell 4: plt; cell 5: mpl, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.10-Customizing-Ticks.ipynb`
- Evidence: 8 cells reference names with no visible prior definition; examples: cell 2: plt; cell 5: np, plt; cell 6: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.11-Settings-and-Stylesheets.ipynb`
- Evidence: 13 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 3: plt; cell 4: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.12-Three-Dimensional-Plotting.ipynb`
- Evidence: 13 cells reference names with no visible prior definition; examples: cell 3: plt; cell 4: np, plt; cell 5: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/04.14-Visualization-With-Seaborn.ipynb`
- Evidence: 22 cells reference names with no visible prior definition; examples: cell 2: np, pd, plt; cell 3: sns; cell 4: sns
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.03-Hyperparameters-and-Model-Validation.ipynb`
- Evidence: 6 cells reference names with no visible prior definition; examples: cell 13: plt; cell 14: X_test, plt; cell 15: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.04-Feature-Engineering.ipynb`
- Evidence: 3 cells reference names with no visible prior definition; examples: cell 11: np, plt, x, y; cell 13: plt, x, y; cell 14: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.05-Naive-Bayes.ipynb`
- Evidence: 4 cells reference names with no visible prior definition; examples: cell 2: plt; cell 4: np; cell 5: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.06-Linear-Regression.ipynb`
- Evidence: 9 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 3: np, plt; cell 5: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.07-Support-Vector-Machines.ipynb`
- Evidence: 15 cells reference names with no visible prior definition; examples: cell 2: plt; cell 3: np, plt; cell 4: np, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.08-Random-Forests.ipynb`
- Evidence: 5 cells reference names with no visible prior definition; examples: cell 2: plt; cell 10: np, plt; cell 11: np, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.09-Principal-Component-Analysis.ipynb`
- Evidence: 10 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 6: np, plt; cell 8: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.10-Manifold-Learning.ipynb`
- Evidence: 16 cells reference names with no visible prior definition; examples: cell 3: plt; cell 4: plt; cell 6: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.11-K-Means.ipynb`
- Evidence: 13 cells reference names with no visible prior definition; examples: cell 2: plt; cell 4: plt; cell 5: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.12-Gaussian-Mixtures.ipynb`
- Evidence: 8 cells reference names with no visible prior definition; examples: cell 3: plt; cell 6: np; cell 7: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.13-Kernel-Density-Estimation.ipynb`
- Evidence: 10 cells reference names with no visible prior definition; examples: cell 3: plt; cell 5: np; cell 6: np, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/05.14-Image-Features.ipynb`
- Evidence: 7 cells reference names with no visible prior definition; examples: cell 2: plt; cell 6: np; cell 7: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/06.00-Figure-Code.ipynb`
- Evidence: 2 cells reference names with no visible prior definition; examples: cell 40: sns; cell 41: sns
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/02.04-Computation-on-arrays-aggregates.ipynb`
- Evidence: 4 cells reference names with no visible prior definition; examples: cell 5: big_array; cell 6: big_array; cell 8: big_array
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/02.05-Computation-on-arrays-broadcasting.ipynb`
- Evidence: 1 cells reference names with no visible prior definition; examples: cell 23: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/02.06-Boolean-Arrays-and-Masks.ipynb`
- Evidence: 1 cells reference names with no visible prior definition; examples: cell 3: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/02.07-Fancy-Indexing.ipynb`
- Evidence: 2 cells reference names with no visible prior definition; examples: cell 17: plt; cell 24: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/02.08-Sorting.ipynb`
- Evidence: 1 cells reference names with no visible prior definition; examples: cell 23: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/03.11-Working-with-Time-Series.ipynb`
- Evidence: 7 cells reference names with no visible prior definition; examples: cell 29: plt; cell 30: plt; cell 31: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/03.12-Performance-Eval-and-Query.ipynb`
- Evidence: 16 cells reference names with no visible prior definition; examples: cell 3: x, y; cell 4: x, y; cell 5: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.01-Simple-Line-Plots.ipynb`
- Evidence: 15 cells reference names with no visible prior definition; examples: cell 2: plt; cell 3: np, plt; cell 4: np, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.02-Simple-Scatter-Plots.ipynb`
- Evidence: 7 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 3: np, plt; cell 4: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.03-Errorbars.ipynb`
- Evidence: 4 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 3: plt; cell 4: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.04-Density-and-Contour-Plots.ipynb`
- Evidence: 6 cells reference names with no visible prior definition; examples: cell 3: np; cell 4: plt; cell 5: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.05-Histograms-and-Binnings.ipynb`
- Evidence: 9 cells reference names with no visible prior definition; examples: cell 2: data, plt; cell 3: data, plt; cell 4: np, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.06-Customizing-Legends.ipynb`
- Evidence: 4 cells reference names with no visible prior definition; examples: cell 3: np; cell 7: np; cell 9: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.07-Customizing-Colorbars.ipynb`
- Evidence: 2 cells reference names with no visible prior definition; examples: cell 3: np; cell 10: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.08-Multiple-Subplots.ipynb`
- Evidence: 8 cells reference names with no visible prior definition; examples: cell 2: plt; cell 3: np, plt; cell 4: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.09-Text-and-Annotation.ipynb`
- Evidence: 5 cells reference names with no visible prior definition; examples: cell 2: np, pd; cell 3: plt; cell 4: mpl, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.10-Customizing-Ticks.ipynb`
- Evidence: 8 cells reference names with no visible prior definition; examples: cell 2: plt; cell 5: np, plt; cell 6: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.11-Settings-and-Stylesheets.ipynb`
- Evidence: 13 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 3: plt; cell 4: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.12-Three-Dimensional-Plotting.ipynb`
- Evidence: 13 cells reference names with no visible prior definition; examples: cell 3: plt; cell 4: np, plt; cell 5: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.13-Geographic-Data-With-Basemap.ipynb`
- Evidence: 10 cells reference names with no visible prior definition; examples: cell 2: Basemap, plt; cell 3: Basemap, plt; cell 5: Basemap, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/04.14-Visualization-With-Seaborn.ipynb`
- Evidence: 12 cells reference names with no visible prior definition; examples: cell 2: np; cell 3: plt; cell 5: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.03-Hyperparameters-and-Model-Validation.ipynb`
- Evidence: 6 cells reference names with no visible prior definition; examples: cell 13: plt; cell 14: X_test, plt; cell 15: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.04-Feature-Engineering.ipynb`
- Evidence: 3 cells reference names with no visible prior definition; examples: cell 11: np, plt, x, y; cell 13: plt, x, y; cell 14: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.05-Naive-Bayes.ipynb`
- Evidence: 4 cells reference names with no visible prior definition; examples: cell 2: plt; cell 4: np; cell 5: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.06-Linear-Regression.ipynb`
- Evidence: 9 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 3: np, plt; cell 5: np
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.07-Support-Vector-Machines.ipynb`
- Evidence: 14 cells reference names with no visible prior definition; examples: cell 2: plt; cell 3: np, plt; cell 4: np, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.08-Random-Forests.ipynb`
- Evidence: 5 cells reference names with no visible prior definition; examples: cell 2: plt; cell 10: np, plt; cell 11: np, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.09-Principal-Component-Analysis.ipynb`
- Evidence: 9 cells reference names with no visible prior definition; examples: cell 2: np, plt; cell 6: np, plt; cell 8: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.10-Manifold-Learning.ipynb`
- Evidence: 16 cells reference names with no visible prior definition; examples: cell 3: plt; cell 4: plt; cell 6: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.11-K-Means.ipynb`
- Evidence: 13 cells reference names with no visible prior definition; examples: cell 2: plt; cell 4: plt; cell 5: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.12-Gaussian-Mixtures.ipynb`
- Evidence: 8 cells reference names with no visible prior definition; examples: cell 3: plt; cell 6: np; cell 7: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.13-Kernel-Density-Estimation.ipynb`
- Evidence: 12 cells reference names with no visible prior definition; examples: cell 3: plt; cell 5: np; cell 6: np, plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/05.14-Image-Features.ipynb`
- Evidence: 7 cells reference names with no visible prior definition; examples: cell 2: plt; cell 5: np; cell 6: plt
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks_v1/06.00-Figure-Code.ipynb`
- Evidence: 2 cells reference names with no visible prior definition; examples: cell 40: sns; cell 41: sns
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `requirements.txt`
- Evidence: Dependency 'jupyter' in requirements.txt does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `requirements.txt`
- Evidence: Dependency 'notebook' in requirements.txt does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `requirements.txt`
- Evidence: Dependency 'line_profiler' in requirements.txt does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `requirements.txt`
- Evidence: Dependency 'memory_profiler' in requirements.txt does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `requirements.txt`
- Evidence: Dependency 'numexpr' in requirements.txt does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `requirements.txt`
- Evidence: Dependency 'pandas-datareader' in requirements.txt does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `requirements.txt`
- Evidence: Dependency 'netcdf4' in requirements.txt does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `notebooks/01.01-Help-And-Documentation.ipynb`
- Evidence: Found path-like string '/Users/jakevdp/PythonDataScienceHandbook'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `notebooks/01.05-IPython-And-Shell-Commands.ipynb`
- Evidence: Found path-like string '/Users/jakevdp/notebook'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `notebooks/01.06-Errors-and-Debugging.ipynb`
- Evidence: Found path-like string 'm:/u001b[0m/u001b[0;34m/u001b[0m/u001b[0m/n/u001b[0;32m----> 2/u001b[0;31m     /u001b[0;32mreturn/u001b[0m /u001b[0ma/u001b[0m /u001b[0;34m//u001b[0m /u001b[0mb/u001b[0m/u001b[0;34m/u001b[0m/u001b[0m/n/u001b[0m/u001b[1;32m      3/u001b[0m /u001b[0;34m/u001b[0m/u001b[0m/n/u001b[1;32m      4/u001b[0m /u001b[0;32mdef/u001b[0m /u001b[0mfunc2/u001b[0m/u001b[0;34m(/u001b[0m/u001b[0mx/u001b[0m/u001b[0;34m)/u001b[0m/u001b[0;34m:/u001b[0m/u001b[0;34m/u001b[0m/u001b[0m/n/u001b[1;32m      5/u001b[0m     /u001b[0ma/u001b[0m /u001b[0;34m=/u001b[0m /u001b[0mx/u001b[0m/u001b[0;34m/u001b[0m/u001b[0m/n'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `notebooks/01.07-Timing-and-Profiling.ipynb`
- Evidence: Found path-like string '/Users/jakevdp/github/jakevdp/PythonDataScienceHandbook/notebook'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `notebooks_v1/01.00-IPython-Beyond-Normal-Python.ipynb`
- Evidence: Found path-like string '/Users/jakevdp/PythonDataScienceHandbook'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `notebooks_v1/01.05-IPython-And-Shell-Commands.ipynb`
- Evidence: Found path-like string '/Users/jakevdp/notebook'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `notebooks_v1/03.01-Introducing-Pandas-Objects.ipynb`
- Evidence: Found path-like string '/Users/jakevdp/anaconda/lib/python3.5/'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `notebooks_v1/03.04-Missing-Values.ipynb`
- Evidence: Found path-like string '/Users/jakevdp/anaconda/lib/python3.5/'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks/03.10-Working-With-Strings.ipynb`
- Evidence: Reads 'data/recipeitems.json', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks/03.11-Working-with-Time-Series.ipynb`
- Evidence: Reads 'FremontBridge.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks/04.06-Customizing-Legends.ipynb`
- Evidence: Reads 'data/california_cities.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks/04.14-Visualization-With-Seaborn.ipynb`
- Evidence: Reads 'data/marathon-data.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks/05.06-Linear-Regression.ipynb`
- Evidence: Reads 'FremontBridge.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks/05.06-Linear-Regression.ipynb`
- Evidence: Reads 'SeattleWeather.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks_v1/03.10-Working-With-Strings.ipynb`
- Evidence: Reads 'recipeitems-latest.json', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks_v1/03.10-Working-With-Strings.ipynb`
- Evidence: Reads '[{0}]', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks_v1/03.11-Working-with-Time-Series.ipynb`
- Evidence: Reads 'FremontBridge.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks_v1/04.14-Visualization-With-Seaborn.ipynb`
- Evidence: Reads 'marathon-data.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks_v1/05.06-Linear-Regression.ipynb`
- Evidence: Reads 'FremontBridge.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC009 - Committed output has no visible producer

- Severity: `medium`
- Category: `artifacts`
- File: `notebooks/figures/02.05-broadcasting.png`
- Evidence: 'notebooks/figures/02.05-broadcasting.png' looks like a generated artifact, but no scanned notebook or script visibly writes it.
- Why it matters: Committed results are harder to trust when the repo does not show how to regenerate them.
- Suggested fix: Add or document the generating notebook/script, or move archival outputs behind an explicit exclusion.

### LC009 - Committed output has no visible producer

- Severity: `medium`
- Category: `artifacts`
- File: `notebooks/figures/03.08-split-apply-combine.png`
- Evidence: 'notebooks/figures/03.08-split-apply-combine.png' looks like a generated artifact, but no scanned notebook or script visibly writes it.
- Why it matters: Committed results are harder to trust when the repo does not show how to regenerate them.
- Suggested fix: Add or document the generating notebook/script, or move archival outputs behind an explicit exclusion.

### LC009 - Committed output has no visible producer

- Severity: `medium`
- Category: `artifacts`
- File: `notebooks/figures/05.01-classification-1.png`
- Evidence: 'notebooks/figures/05.01-classification-1.png' looks like a generated artifact, but no scanned notebook or script visibly writes it.
- Why it matters: Committed results are harder to trust when the repo does not show how to regenerate them.
- Suggested fix: Add or document the generating notebook/script, or move archival outputs behind an explicit exclusion.
