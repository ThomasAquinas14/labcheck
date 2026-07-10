# labcheck Report

- Target: `https://github.com/ageron/handson-ml3`
- Overall Score: **43**
- Severity Mix: **9 high**, **14 medium**, **25 low**

## Review Boundary

This is a static, no-key first-pass audit. It does not execute the project code by default, does not upload source files to a hosted backend, and does not prove scientific validity; use it to prioritize rerun and handoff risks before deeper verification.

## Scores

| Category | Score | What it means |
|---|---:|---|
| Environment Rebuildability | 66 | Can a new person recreate the environment without guesswork? |
| Notebook Determinism | 45 | Will notebooks run cleanly from top to bottom without invisible state? |
| Artifact Availability | 28 | Are referenced inputs and generated artifacts present or clearly accounted for? |
| Portability | 66 | Does the repo avoid machine-specific assumptions and brittle paths? |
| Onboarding Readiness | 44 | How likely is a new contributor to succeed from the docs and structure alone? |

## Top Risks

| Risk | Severity | Scope | First evidence |
|---|---|---|---|
| `LC005` Referenced input artifact missing from repo | `high` | 8 findings across 4 files | 19_training_and_deploying_at_scale.ipynb: Reads 'my_converted_savedmodel.tflite', but that path is not present in the scanned repo. |
| `LC002` Likely hidden notebook state | `high` | 1 finding across 1 file | 08_dimensionality_reduction.ipynb: 3 cells reference names with no visible prior definition; examples: cell 58: rnd_clf_with_pca; cell 60: sgd_clf; cell 62: sgd_clf_with_pca |
| `LC004` Unpinned dependency | `medium` | 5 findings across 1 file | environment.yml: Dependency 'graphviz' in environment.yml does not pin a version. |
| `LC006` Absolute machine-local path | `medium` | 5 findings across 5 files | 05_support_vector_machines.ipynb: Found path-like string '/Users/ageron/miniconda3/env'. |
| `LC007` Randomness used without visible seeding | `medium` | 4 findings across 4 files | 11_training_deep_neural_networks.ipynb: Detected randomness-related APIs, but no obvious seed call in the same file. |

## Understand Finding Codes

Run these commands for plain-language context, why the finding matters, and the expected fix:

- `labcheck explain LC005`
- `labcheck explain LC002`
- `labcheck explain LC004`

## Remediation Plan

1. **Fix LC005 first because it affects 8 findings across 4 files.**
   Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.
   First evidence: `19_training_and_deploying_at_scale.ipynb` - Reads 'my_converted_savedmodel.tflite', but that path is not present in the scanned repo.

2. **Fix LC002 first because it affects 1 finding across 1 file.**
   Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.
   First evidence: `08_dimensionality_reduction.ipynb` - 3 cells reference names with no visible prior definition; examples: cell 58: rnd_clf_with_pca; cell 60: sgd_clf; cell 62: sgd_clf_with_pca

3. **Fix LC004 first because it affects 5 findings across 1 file.**
   Suggested fix: Pin this dependency to an exact or tightly bounded version.
   First evidence: `environment.yml` - Dependency 'graphviz' in environment.yml does not pin a version.

4. **Fix LC006 first because it affects 5 findings across 5 files.**
   Suggested fix: Use project-relative paths, environment variables, or documented configuration.
   First evidence: `05_support_vector_machines.ipynb` - Found path-like string '/Users/ageron/miniconda3/env'.

5. **Fix LC007 first because it affects 4 findings across 4 files.**
   Suggested fix: Set and document seeds for the randomness sources used in this workflow.
   First evidence: `11_training_deep_neural_networks.ipynb` - Detected randomness-related APIs, but no obvious seed call in the same file.


## Next Steps

- Scorecard summary: `labcheck scorecard https://github.com/ageron/handson-ml3`
- Sortable triage CSV: `labcheck scan https://github.com/ageron/handson-ml3 --format csv --output labcheck-findings.csv`
- Shareable audit bundle: `labcheck pack https://github.com/ageron/handson-ml3 --output-dir labcheck-audit --zip`
- Explain top finding: `labcheck explain LC005`

## Provenance Graph

- Nodes: 39
- Edges: 15

| Source | Edge | Target |
|---|---|---|
| `my_converted_savedmodel.tflite` | `reads` | `19_training_and_deploying_at_scale.ipynb` |
| `my_converted_keras_model.tflite` | `reads` | `19_training_and_deploying_at_scale.ipynb` |
| `my_keras_tuner_search.py` | `reads` | `19_training_and_deploying_at_scale.ipynb` |
| `19_training_and_deploying_at_scale.ipynb` | `writes` | `my_converted_savedmodel.tflite` |
| `19_training_and_deploying_at_scale.ipynb` | `writes` | `my_converted_keras_model.tflite` |
| `19_training_and_deploying_at_scale.ipynb` | `writes` | `my_keras_tuner_search.py` |
| `my_square_function.png` | `reads` | `tools_matplotlib.ipynb` |
| `tools_matplotlib.ipynb` | `writes` | `my_square_function.png` |
| `my_array.npy` | `reads` | `tools_numpy.ipynb` |
| `my_array.csv` | `reads` | `tools_numpy.ipynb` |
| `my_arrays.npz` | `reads` | `tools_numpy.ipynb` |
| `my_df.csv` | `reads` | `tools_pandas.ipynb` |
| `tools_pandas.ipynb` | `writes` | `my_df.csv` |
| `tools_pandas.ipynb` | `writes` | `my_df.json` |
| `tools_pandas.ipynb` | `writes` | `my_df.xlsx` |

## Findings

### LC002 - Likely hidden notebook state

- Severity: `high`
- Category: `determinism`
- File: `08_dimensionality_reduction.ipynb`
- Evidence: 3 cells reference names with no visible prior definition; examples: cell 58: rnd_clf_with_pca; cell 60: sgd_clf; cell 62: sgd_clf_with_pca
- Why it matters: The notebook may only work in the original author's live kernel rather than from a clean rerun.
- Suggested fix: Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `environment.yml`
- Evidence: Dependency 'graphviz' in environment.yml does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `environment.yml`
- Evidence: Dependency 'python-graphviz' in environment.yml does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `environment.yml`
- Evidence: Dependency 'wheel' in environment.yml does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `environment.yml`
- Evidence: Dependency 'keras-core' in environment.yml does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC004 - Unpinned dependency

- Severity: `medium`
- Category: `environment`
- File: `environment.yml`
- Evidence: Dependency 'gymnasium[classic_control,atari]' in environment.yml does not pin a version.
- Why it matters: Environment rebuilds can drift over time when critical dependencies are unpinned.
- Suggested fix: Pin this dependency to an exact or tightly bounded version.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `05_support_vector_machines.ipynb`
- Evidence: Found path-like string '/Users/ageron/miniconda3/env'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `16_nlp_with_rnns_and_attention.ipynb`
- Evidence: Found path-like string '/home/ageron/ten'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `17_autoencoders_gans_and_diffusion_models.ipynb`
- Evidence: Found path-like string '/Users/ageron/miniconda3/env'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `docker/docker-compose.yml`
- Evidence: Found path-like string '/home/devel/hand'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC006 - Absolute machine-local path

- Severity: `medium`
- Category: `portability`
- File: `docker/README.md`
- Evidence: Found path-like string '/home/devel/hand'.
- Why it matters: Hardcoded local paths make the repo brittle on other machines and operating systems.
- Suggested fix: Use project-relative paths, environment variables, or documented configuration.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `19_training_and_deploying_at_scale.ipynb`
- Evidence: Reads 'my_converted_savedmodel.tflite', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `19_training_and_deploying_at_scale.ipynb`
- Evidence: Reads 'my_converted_keras_model.tflite', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `19_training_and_deploying_at_scale.ipynb`
- Evidence: Reads 'my_keras_tuner_search.py', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `tools_matplotlib.ipynb`
- Evidence: Reads 'my_square_function.png', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `tools_numpy.ipynb`
- Evidence: Reads 'my_array.npy', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `tools_numpy.ipynb`
- Evidence: Reads 'my_array.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `tools_numpy.ipynb`
- Evidence: Reads 'my_arrays.npz', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC005 - Referenced input artifact missing from repo

- Severity: `high`
- Category: `artifacts`
- File: `tools_pandas.ipynb`
- Evidence: Reads 'my_df.csv', but that path is not present in the scanned repo.
- Why it matters: A new user may not be able to run the workflow because required inputs are missing.
- Suggested fix: Commit the artifact, document how to obtain it, or make the input contract explicit.

### LC007 - Randomness used without visible seeding

- Severity: `medium`
- Category: `determinism`
- File: `11_training_deep_neural_networks.ipynb`
- Evidence: Detected randomness-related APIs, but no obvious seed call in the same file.
- Why it matters: Results may drift between runs even if the code itself executes successfully.
- Suggested fix: Set and document seeds for the randomness sources used in this workflow.

### LC007 - Randomness used without visible seeding

- Severity: `medium`
- Category: `determinism`
- File: `15_processing_sequences_using_rnns_and_cnns.ipynb`
- Evidence: Detected randomness-related APIs, but no obvious seed call in the same file.
- Why it matters: Results may drift between runs even if the code itself executes successfully.
- Suggested fix: Set and document seeds for the randomness sources used in this workflow.

### LC007 - Randomness used without visible seeding

- Severity: `medium`
- Category: `determinism`
- File: `extra_gradient_descent_comparison.ipynb`
- Evidence: Detected randomness-related APIs, but no obvious seed call in the same file.
- Why it matters: Results may drift between runs even if the code itself executes successfully.
- Suggested fix: Set and document seeds for the randomness sources used in this workflow.

### LC007 - Randomness used without visible seeding

- Severity: `medium`
- Category: `determinism`
- File: `tools_numpy.ipynb`
- Evidence: Detected randomness-related APIs, but no obvious seed call in the same file.
- Why it matters: Results may drift between runs even if the code itself executes successfully.
- Suggested fix: Set and document seeds for the randomness sources used in this workflow.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `01_the_machine_learning_landscape.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `02_end_to_end_machine_learning_project.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `03_classification.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `04_training_linear_models.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `05_support_vector_machines.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `06_decision_trees.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `07_ensemble_learning_and_random_forests.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `08_dimensionality_reduction.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `09_unsupervised_learning.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `10_neural_nets_with_keras.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `11_training_deep_neural_networks.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `12_custom_models_and_training_with_tensorflow.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `13_loading_and_preprocessing_data.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `14_deep_computer_vision_with_cnns.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `15_processing_sequences_using_rnns_and_cnns.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `16_nlp_with_rnns_and_attention.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `17_autoencoders_gans_and_diffusion_models.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `18_reinforcement_learning.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `extra_ann_architectures.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `extra_autodiff.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `extra_gradient_descent_comparison.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `index.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `math_differential_calculus.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `math_linear_algebra.ipynb`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.

### LC010 - Workflow node is disconnected from data lineage

- Severity: `low`
- Category: `onboarding`
- File: `docker/jupyter_notebook_config.py`
- Evidence: This analysis file has no visible input or output edges in the provenance graph.
- Why it matters: Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.
- Suggested fix: Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.
