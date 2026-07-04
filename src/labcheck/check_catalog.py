from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CheckDefinition:
    check_id: str
    title: str
    default_severity: str
    category: str
    detects: str
    why_it_matters: str
    suggested_fix: str


CHECKS: tuple[CheckDefinition, ...] = (
    CheckDefinition(
        check_id="LC001",
        title="Suspicious notebook execution order",
        default_severity="high",
        category="determinism",
        detects="Notebook execution counts that are not cleanly increasing.",
        why_it_matters="The notebook may rely on hidden runtime state rather than a clean top-to-bottom execution path.",
        suggested_fix="Restart the kernel and run all cells before committing the notebook.",
    ),
    CheckDefinition(
        check_id="LC002",
        title="Likely hidden notebook state",
        default_severity="high",
        category="determinism",
        detects="Notebook cells that reference names with no visible prior definition.",
        why_it_matters="The notebook may only work in the original author's live kernel rather than from a clean rerun.",
        suggested_fix="Make setup cells explicit and ensure the notebook runs top-to-bottom from a fresh kernel.",
    ),
    CheckDefinition(
        check_id="LC003",
        title="Missing environment manifest",
        default_severity="high",
        category="environment",
        detects="Runnable notebooks or Python files without a dependency manifest at the repo root.",
        why_it_matters="A new user cannot reliably recreate the environment needed to run the project.",
        suggested_fix="Add requirements.txt, pyproject.toml, environment.yml, or another clear environment manifest.",
    ),
    CheckDefinition(
        check_id="LC004",
        title="Unpinned dependency",
        default_severity="medium",
        category="environment",
        detects="Loose dependencies in requirements.txt, pyproject.toml, and Conda environment files.",
        why_it_matters="Environment rebuilds can drift over time when critical dependencies are unpinned.",
        suggested_fix="Pin this dependency to an exact or tightly bounded version.",
    ),
    CheckDefinition(
        check_id="LC005",
        title="Referenced input artifact missing from repo",
        default_severity="high",
        category="artifacts",
        detects="Code that reads local input files that are not present in the scanned repo.",
        why_it_matters="A new user may not be able to run the workflow because required inputs are missing.",
        suggested_fix="Commit the artifact, document how to obtain it, or make the input contract explicit.",
    ),
    CheckDefinition(
        check_id="LC006",
        title="Absolute machine-local path",
        default_severity="medium",
        category="portability",
        detects="Hardcoded paths such as C:\\Users\\..., /Users/..., /home/..., or /mnt/....",
        why_it_matters="Hardcoded local paths make the repo brittle on other machines and operating systems.",
        suggested_fix="Use project-relative paths, environment variables, or documented configuration.",
    ),
    CheckDefinition(
        check_id="LC007",
        title="Randomness used without visible seeding",
        default_severity="medium",
        category="determinism",
        detects="Randomness-related APIs without an obvious seed call in the same file.",
        why_it_matters="Results may drift between runs even if the code itself executes successfully.",
        suggested_fix="Set and document seeds for the randomness sources used in this workflow.",
    ),
    CheckDefinition(
        check_id="LC008",
        title="README command references a missing path",
        default_severity="medium",
        category="onboarding",
        detects="Documented README commands that point to files that do not exist.",
        why_it_matters="Setup instructions lose trust quickly when they point to files that do not exist.",
        suggested_fix="Update the README command or restore the missing entrypoint.",
    ),
    CheckDefinition(
        check_id="LC009",
        title="Committed output has no visible producer",
        default_severity="medium",
        category="artifacts",
        detects="Committed files under output-like folders when no scanned source visibly writes them.",
        why_it_matters="Committed results are harder to trust when the repo does not show how to regenerate them.",
        suggested_fix="Add or document the generating notebook/script, or move archival outputs behind an explicit exclusion.",
    ),
    CheckDefinition(
        check_id="LC010",
        title="Workflow node is disconnected from data lineage",
        default_severity="low",
        category="onboarding",
        detects="Notebook or Python workflow files with no visible input or output graph edges.",
        why_it_matters="Disconnected workflow files are hard for new contributors to place in the actual experiment pipeline.",
        suggested_fix="Document whether this file is archival, illustrative, or part of the real workflow, or connect it to visible inputs and outputs.",
    ),
    CheckDefinition(
        check_id="LC011",
        title="Notebook contains saved error output",
        default_severity="high",
        category="determinism",
        detects="Committed notebook cells with saved traceback/error outputs.",
        why_it_matters="A committed traceback is strong evidence that the notebook was not saved after a clean successful rerun.",
        suggested_fix="Fix the failing cell, restart the kernel, run all cells, and save the notebook without error outputs.",
    ),
    CheckDefinition(
        check_id="LC012",
        title="Missing Python runtime version",
        default_severity="medium",
        category="environment",
        detects="Runnable notebooks or Python files without an explicit Python runtime version.",
        why_it_matters="A repo can have dependency files and still be hard to rebuild if users guess the wrong Python version.",
        suggested_fix="Declare the Python version with requires-python, .python-version, runtime.txt, Pipfile [requires], setup.cfg python_requires, or a Conda python= dependency.",
    ),
    CheckDefinition(
        check_id="LC013",
        title="Missing setup or run instructions",
        default_severity="medium",
        category="onboarding",
        detects="Runnable notebooks or Python files without a README quickstart or run command.",
        why_it_matters="A repo can contain runnable code but still be hard to hand off if the next person does not know which command to start with.",
        suggested_fix="Add a short Quick start section with environment setup and the command or notebook needed to reproduce the main workflow.",
    ),
    CheckDefinition(
        check_id="LC014",
        title="Notebook has no saved execution evidence",
        default_severity="low",
        category="determinism",
        detects="Multi-cell notebooks where every code cell has an empty execution count.",
        why_it_matters="A cleared notebook may be intentional, but it gives reviewers no saved evidence that it was rerun from a clean kernel.",
        suggested_fix="If outputs are intentionally stripped, document the rerun command or CI check; otherwise restart the kernel, run all cells, and save the notebook.",
    ),
    CheckDefinition(
        check_id="LC015",
        title="Notebook is missing kernel metadata",
        default_severity="low",
        category="environment",
        detects="Code notebooks missing kernelspec.name or language_info.name metadata.",
        why_it_matters="A notebook handoff is harder when reviewers cannot tell which kernel and language the author intended.",
        suggested_fix="Open the notebook with the intended kernel and save it, or add kernelspec and language_info metadata before sharing.",
    ),
    CheckDefinition(
        check_id="LC016",
        title="Scikit-learn randomness lacks random_state",
        default_severity="medium",
        category="determinism",
        detects="Common sklearn splitters and randomized estimators without a random_state argument.",
        why_it_matters="Train/test splits and randomized model fits can drift between runs even when dependency versions are pinned.",
        suggested_fix="Pass a documented random_state value to train/test splits, shuffled splitters, and randomized sklearn estimators.",
    ),
    CheckDefinition(
        check_id="LC017",
        title="Pandas sampling lacks random_state",
        default_severity="medium",
        category="determinism",
        detects="Pandas sample() calls without a random_state argument.",
        why_it_matters="Notebook samples and train/eval subsets can drift between runs even when the code appears deterministic.",
        suggested_fix="Pass a documented random_state value to pandas sample() calls used in reproducible workflows.",
    ),
)

CHECK_BY_ID = {definition.check_id: definition for definition in CHECKS}


def get_check(check_id: str) -> CheckDefinition | None:
    return CHECK_BY_ID.get(check_id.upper())
