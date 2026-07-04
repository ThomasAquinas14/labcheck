# labcheck Report

- Target: `examples/broken-repo`
- Overall Score: **44**
- Severity Mix: **4 high**, **6 medium**, **2 low**

## Scores

| Category | Score | What it means |
|---|---:|---|
| Environment Rebuildability | 66 | Can a new person recreate the environment without guesswork? |
| Notebook Determinism | 3 | Will notebooks run cleanly from top to bottom without invisible state? |
| Artifact Availability | 74 | Are referenced inputs and generated artifacts present or clearly accounted for? |
| Portability | 86 | Does the repo avoid machine-specific assumptions and brittle paths? |
| Onboarding Readiness | 80 | How likely is a new contributor to succeed from the docs and structure alone? |

## Top Risks

| Risk | Severity | Scope | First evidence |
|---|---|---|---|
| `LC001` Suspicious notebook execution order | `high` | 1 finding across 1 file | notebooks/analysis.ipynb: Execution counts are non-monotonic: [1, 5, 3] |
| `LC002` Likely hidden notebook state | `high` | 1 finding across 1 file | notebooks/analysis.ipynb: 1 cells reference names with no visible prior definition; examples: cell 3: external_state |
| `LC005` Referenced input artifact missing from repo | `high` | 1 finding across 1 file | notebooks/analysis.ipynb: Reads 'data/train.csv', but that path is not present in the scanned repo. |
| `LC011` Notebook contains saved error output | `high` | 1 finding across 1 file | notebooks/analysis.ipynb: 1 saved error output(s); examples: cell 3: NameError: name 'external_state' is not defined |
| `LC007` Randomness used without visible seeding | `medium` | 2 findings across 2 files | notebooks/analysis.ipynb: Detected randomness-related APIs, but no obvious seed call in the same file. |

## Remediation Plan

1. **Fix LC001 first because it affects 1 finding across 1 file.**
   Suggested fix: Restart the kernel and run all cells before committing the notebook.
   First evidence: `notebooks/analysis.ipynb` - Execution counts are non-monotonic: [1, 5, 3]

2. **Fix LC002 first because it affects 1 finding across 1 file.**
   Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.
   First evidence: `notebooks/analysis.ipynb` - 1 cells reference names with no visible prior definition; examples: cell 3: external_state

3. **Fix LC005 first because it affects 1 finding across 1 file.**
   Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.
   First evidence: `notebooks/analysis.ipynb` - Reads 'data/train.csv', but that path is not present in the scanned repo.

4. **Fix LC011 first because it affects 1 finding across 1 file.**
   Suggested fix: Fix the failing cell, restart the kernel, run all cells, and save the notebook without error outputs.
   First evidence: `notebooks/analysis.ipynb` - 1 saved error output(s); examples: cell 3: NameError: name 'external_state' is not defined

5. **Fix LC007 first because it affects 2 findings across 2 files.**
   Suggested fix: Set and document seeds for the randomness sources used in this workflow.
   First evidence: `notebooks/analysis.ipynb` - Detected randomness-related APIs, but no obvious seed call in the same file.


## Provenance Graph

- Nodes: 4
- Edges: 2

| Source | Edge | Target |
|---|---|---|
| `data/train.csv` | `reads` | `notebooks/analysis.ipynb` |
| `notebooks/analysis.ipynb` | `writes` | `outputs/report.csv` |

## Findings

### LC001 - Suspicious notebook execution order

- Severity: `high`
- Category: `determinism`
- File: `notebooks/analysis.ipynb`
- Evidence: Execution counts are non-monotonic: [1, 5, 3]
- Why it matters: The notebook may rely on hidden runtime state rather than a clean top-to-bottom execution path.
- Suggested fix: Restart the kernel and run all cells before committing the notebook.

### LC015 - Notebook is missing kernel metadata

- Severity: `low`
- Category: `environment`
- File: `notebooks/analysis.ipynb`
- Evidence: Notebook metadata is missing kernelspec.name and language_info.name.
- Why it matters: A notebook handoff is harder when reviewers cannot tell which kernel and language the author intended.
- Suggested fix: Open the notebook with the intended kernel and save it, or add kernelspec and language_info metadata before sharing.

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `notebooks/analysis.ipynb`
- Evidence: 1 cells reference names with no visible prior definition; examples: cell 3: external_state
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC011 - Notebook contains saved error output

- Severity: `high`
- Category: `determinism`
- File: `notebooks/analysis.ipynb`
- Evidence: 1 saved error output(s); examples: cell 3: NameError: name 'external_state' is not defined
- Why it matters: A committed traceback is strong evidence that the notebook was not saved after a clean successful rerun.
- Suggested fix: Fix the failing cell, restart the kernel, run all cells, and save the notebook without error outputs.

### LC012 - Missing Python runtime version

- Severity: `medium`
- Category: `environment`
- File: `.`
- Evidence: Found runnable notebooks or Python files, but no Python runtime version is specified.
- Why it matters: A repo can have pinned packages and still fail to rebuild if users guess the wrong Python version.
- Suggested fix: Declare the Python version with requires-python, .python-version, runtime.txt, Pipfile [requires], setup.cfg python_requires, or a Conda python= dependency.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `requirements.txt`
- Evidence: Dependency 'pandas' in requirements.txt does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `notebooks/analysis.ipynb`
- Evidence: Found path-like string 'C:\\Users\\researcher\\Desktop\\data.csv'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `notebooks/analysis.ipynb`
- Evidence: Reads 'data/train.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC007 - Randomness used without visible seeding

- Severity: `medium`
- Category: `determinism`
- File: `notebooks/analysis.ipynb`
- Evidence: Detected randomness-related APIs, but no obvious seed call in the same file.
- Why it matters: Results may drift between runs even if the code itself executes successfully.
- Suggested fix: Set and document seeds for the randomness sources used in this workflow.

### LC007 - Randomness used without visible seeding

- Severity: `medium`
- Category: `determinism`
- File: `experiment.py`
- Evidence: Detected randomness-related APIs, but no obvious seed call in the same file.
- Why it matters: Results may drift between runs even if the code itself executes successfully.
- Suggested fix: Set and document seeds for the randomness sources used in this workflow.

### LC008 - README command references a missing path

- Severity: `medium`
- Category: `onboarding`
- File: `README.md`
- Evidence: Command 'python scripts/train.py' points to 'scripts/train.py', which is not present.
- Why it matters: Setup instructions lose trust quickly when they point to files that do not exist.
- Suggested fix: Update the README command or restore the missing entrypoint.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `experiment.py`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.
