from __future__ import annotations

import json
from pathlib import Path
import re


def _json_ld_documents(html: str) -> list[dict]:
    matches = re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S)
    assert matches
    return [json.loads(match) for match in matches]


def _audit_snapshot(audit_path: str) -> tuple[str, str, str, str]:
    audit = Path(audit_path).read_text(encoding="utf-8")
    score = re.search(r"Overall Score: \*\*(\d+)\*\*", audit)
    severity = re.search(r"Severity Mix: \*\*(\d+) high\*\*, \*\*(\d+) medium\*\*, \*\*(\d+) low\*\*", audit)
    assert score is not None
    assert severity is not None
    return score.group(1), severity.group(1), severity.group(2), severity.group(3)


def test_browser_demo_supports_multi_file_local_audits() -> None:
    demo = Path("site/demo.html").read_text(encoding="utf-8")
    assert 'id="folder-input"' in demo
    assert 'id="github-url-input"' in demo
    assert 'id="audit-github-url"' in demo
    assert 'id="copy-github-demo-link"' in demo
    assert 'id="github-status"' in demo
    assert 'id="copy-scorecard"' in demo
    assert 'id="download-scorecard"' in demo
    assert 'id="target-fit-audience"' in demo
    assert 'id="copy-target-fit"' in demo
    assert 'id="download-target-fit"' in demo
    assert 'id="copy-issue-draft"' in demo
    assert 'id="download-issue-draft"' in demo
    assert 'id="copy-outreach-note"' in demo
    assert 'id="download-outreach-note"' in demo
    assert 'id="download-csv"' in demo
    assert 'id="demo-walkthrough-title"' in demo
    assert 'aria-live="polite"' in demo
    assert "90 second walkthrough" in demo
    assert "What to try first" in demo
    assert "Load the sample repo" in demo
    assert "Read the top risks" in demo
    assert "Share the right artifact" in demo
    assert "Safe sharing rule" in demo
    assert "does not upload selected local files to a labcheck backend" in demo
    assert "Folder mode" in demo
    assert "choose your repo root when the browser asks for a directory" in demo
    assert "Selected local files stay in this browser tab" in demo
    assert "Browser folder selection works best in Chrome or Edge" in demo
    assert "run the CLI for a complete local scan" in demo
    assert "../docs/first-audit.md" in demo
    assert "../docs/scoring-guide.md" in demo
    assert "function analyzeFileSet" in demo
    assert "function parseGitHubRepoUrl" in demo
    assert "function fetchPublicGitHubRepo" in demo
    assert "function githubCandidateRank" in demo
    assert "function sortGitHubBrowserCandidates" in demo
    assert 'normalized.startsWith(".github/workflows/")' in demo
    assert 'suffix === "ipynb"' in demo
    assert "GITHUB_BROWSER_FILE_LIMIT" in demo
    assert "GITHUB_BROWSER_FILE_SIZE_LIMIT" in demo
    assert "https://api.github.com/repos/" in demo
    assert "function toScorecard" in demo
    assert "function selectedTargetFitAudience" in demo
    assert "function targetFitScore" in demo
    assert "function toTargetFit" in demo
    assert "function toIssueDraft" in demo
    assert "function toOutreachNote" in demo
    assert "function toCsv" in demo
    assert "function pushFindingCodeExplanations" in demo
    assert "## Review Boundary" in demo
    assert "## Next Steps" in demo
    assert "## Understand Finding Codes" in demo
    assert "Suggested fix: ${markdownCell(risk.fix)}" in demo
    assert "does not prove scientific validity" in demo
    assert "Download the CSV findings table" in demo
    assert 'return lines.join("\\n")' in demo
    assert "function copyScorecardToClipboard" in demo
    assert 'id="load-sample-repo"' in demo
    assert "sampleRepoFiles" in demo
    assert "built-in sample repo snapshot" in demo
    assert "labcheck-browser-scorecard.md" in demo
    assert "labcheck-browser-target-fit-${audience}.md" in demo
    assert "labcheck-browser-issue-draft.md" in demo
    assert "labcheck-browser-outreach-note.md" in demo
    assert "labcheck-browser-findings.csv" in demo
    assert "Scorecard copied" in demo
    assert "Target-fit card copied" in demo
    assert "Professor fit" in demo
    assert "Founder fit" in demo
    assert "Maintainer fit" in demo
    assert "Issue draft copied" in demo
    assert "Outreach note copied" in demo
    assert "Copy Scorecard" in demo
    assert "Copy Target Fit" in demo
    assert "Copy Issue Draft" in demo
    assert "Copy Outreach Note" in demo
    assert "Download Scorecard" in demo
    assert "Download Target Fit" in demo
    assert "Download Issue Draft" in demo
    assert "Download Outreach Note" in demo
    assert "Download CSV" in demo
    assert "No backend, no token, no paid API" in demo
    assert "function meltanoReferenceFromCommand" in demo
    assert "function meltanoJobNames" in demo
    assert "Meltano job" in demo
    assert "function flyteReferenceFromCommand" in demo
    assert "function flyteTargetsFromSource" in demo
    assert "Flyte workflow/task" in demo
    assert "function argoReferenceFromCommand" in demo
    assert "function argoWorkflowEntrypointAndTemplates" in demo
    assert "Argo entrypoint" in demo
    assert "function tektonReferenceFromCommand" in demo
    assert "function tektonResourceNames" in demo
    assert "Tekton manifest" in demo
    assert "function rayReferenceFromCommand" in demo
    assert "Ray job" in demo
    assert "function daggerReferenceFromCommand" in demo
    assert "Dagger function" in demo
    assert "function bazelReferenceFromCommand" in demo
    assert "Bazel target" in demo
    assert "function pantsReferenceFromCommand" in demo
    assert "Pants target spec" in demo
    assert "function nixReferenceFromCommand" in demo
    assert "Nix flake output" in demo
    assert "function dockerComposeReferenceFromCommand" in demo
    assert "Docker Compose service" in demo
    assert "function isLocalDockerComposeEnvFile" in demo
    assert "Docker Compose env-file" in demo
    assert "function isLocalDockerComposeProjectDir" in demo
    assert "Docker Compose project dir" in demo
    assert "function isLocalDockerComposeProfile" in demo
    assert "Docker Compose profile" in demo
    assert "function dockerComposeVolumeSourceFindings" in demo
    assert "Docker Compose bind source" in demo
    assert "function dockerComposeBuildPathFindings" in demo
    assert "Docker Compose build context" in demo
    assert "function dockerComposeDependsOnFindings" in demo
    assert "Docker Compose depends_on service" in demo
    assert "function dockerComposeNetworkFindings" in demo
    assert "Docker Compose network" in demo
    assert "function dockerComposeHealthcheckFindings" in demo
    assert "Docker Compose healthcheck script" in demo
    assert "function dockerComposeResourceFileFindings" in demo
    assert "Docker Compose secret/config file" in demo
    assert "function dockerComposeServiceEnvFileFindings" in demo
    assert "Docker Compose service env_file" in demo
    assert "function dockerComposeExtendsFindings" in demo
    assert "Docker Compose extends service target" in demo
    assert "function dockerComposeIncludeFileFindings" in demo
    assert "Docker Compose include file" in demo
    assert "function dockerComposeServiceLabelFileFindings" in demo
    assert "Docker Compose service label_file" in demo
    assert "function dockerComposeDevelopWatchFindings" in demo
    assert "Docker Compose develop watch path" in demo
    assert "function dockerBuildReferenceFromCommand" in demo
    assert "Docker build stage" in demo
    assert "function helmReferenceFromCommand" in demo
    assert "Helm chart path" in demo
    assert "function kustomizeReferenceFromCommand" in demo
    assert "Kustomize path" in demo
    assert "function kubernetesManifestReferenceFromCommand" in demo
    assert "Kubernetes manifest path" in demo
    assert "function terraformReferenceFromCommand" in demo
    assert "Terraform working dir" in demo
    assert "function pulumiReferenceFromCommand" in demo
    assert "Pulumi project dir" in demo
    assert "function ansibleReferenceFromCommand" in demo
    assert "Ansible playbook" in demo
    assert "function packerReferenceFromCommand" in demo
    assert "Packer template path" in demo
    assert "Audit GitHub URL" in demo
    assert "Copy Demo Link" in demo
    assert "Public GitHub URL audits are bounded to 80 prioritized text-like files" in demo
    assert "demo.html?repo=owner/repo" in demo
    assert "Share `demo.html?repo=owner/repo`" in demo
    assert "function formatGitHubFetchStatus" in demo
    assert "function buildGitHubDemoUrl" in demo
    assert 'url.searchParams.set("audience", options.audience)' in demo
    assert "function loadGitHubUrlFromPageParams" in demo
    assert 'params.get("audience")' in demo
    assert "targetFitAudienceSelect.value = requestedAudience" in demo
    assert "buildGitHubDemoUrl(githubUrlInput.value, { audience })" in demo
    assert "Demo link copied for ${audience}" in demo
    assert "add &audit=1 only if you want the browser audit to start automatically" in demo
    assert "run the CLI full-repo scan for complete coverage" in demo
    assert "No upload, API key, or hosted backend was used" in demo
    assert "LC003" in demo
    assert "LC005" in demo
    assert "LC008" in demo
    assert "LC012" in demo
    assert "LC013" in demo
    assert "LC014" in demo
    assert "LC015" in demo
    assert "LC016" in demo
    assert "LC017" in demo
    assert "LC018" in demo
    assert "LC019" in demo
    assert "LC020" in demo
    assert "LC021" in demo
    assert "LC022" in demo
    assert "LC023" in demo
    assert "LC024" in demo
    assert "LC025" in demo
    assert "LC026" in demo
    assert "LC027" in demo
    assert "LC028" in demo
    assert "LC029" in demo
    assert "LC030" in demo
    assert "LC031" in demo
    assert "LC032" in demo
    assert "LC033" in demo
    assert "LC034" in demo
    assert "LC035" in demo
    assert "LC036" in demo
    assert "LC037" in demo
    assert "LC038" in demo
    assert "LC039" in demo
    assert "LC040" in demo
    assert "LC041" in demo
    assert "LC042" in demo
    assert "LC043" in demo
    assert "LC044" in demo
    assert "LC045" in demo
    assert "LC046" in demo
    assert "LC047" in demo
    assert "LC048" in demo
    assert "LC049" in demo
    assert "LC050" in demo
    assert "LC051" in demo
    assert "LC052" in demo
    assert "LC053" in demo
    assert "LC054" in demo
    assert "LC055" in demo
    assert "LC056" in demo
    assert "LC057" in demo
    assert "LC058" in demo
    assert "LC059" in demo
    assert "LC060" in demo
    assert "LC061" in demo
    assert "LC062" in demo
    assert "LC063" in demo
    assert "LC064" in demo
    assert "LC065" in demo
    assert "function findHardcodedSecretValues" in demo
    assert "function markdownLocalLinkFindings" in demo
    assert "Markdown link references a missing local file" in demo
    assert "function findReuseMetadataGaps" in demo
    assert "Missing reuse license metadata" in demo
    assert "Missing citation metadata" in demo
    assert "Hardcoded secret-looking value" in demo
    assert "function currentTimeUsageFindings" in demo
    assert "Current time used in workflow logic" in demo
    assert "function setDerivedOrderFindings" in demo
    assert "Set-derived order is unstable" in demo
    assert "function pythonHashUsageFindings" in demo
    assert "Python hash() is not stable across runs" in demo
    assert "function pytorchDeterministicBackendIssues" in demo
    assert "PyTorch deterministic backend is disabled" in demo
    assert "/content/drive" in demo
    assert "/kaggle/" in demo
    assert "function hasPythonRuntimeSpec" in demo
    assert "function notebookMetadataIssue" in demo
    assert "function notebookPythonSourceForAnalysis" in demo
    assert '"display","get_ipython"' in demo
    assert "function hasReadmeRunInstructions" in demo
    assert "function hasReadmeDependencySetupInstructions" in demo
    assert "function mutableRemoteInputIssues" in demo
    assert "function remoteDownloadTimeoutIssues" in demo
    assert "function remoteArtifactChecksumIssues" in demo
    assert "function huggingFaceRevisionIssues" in demo
    assert "requests.get" in demo
    assert "urlretrieve" in demo
    assert "wget" in demo
    assert "curl" in demo
    assert "function findDataVersioningRestoreGaps" in demo
    assert "function repoHasPythonModule" in demo
    assert "function findMakefile" in demo
    assert "function makefileTargets" in demo
    assert "function packageJsonScripts" in demo
    assert "function pyprojectScripts" in demo
    assert "function hatchScripts" in demo
    assert "function pdmScripts" in demo
    assert "function pixiTasks" in demo
    assert "function taskipyTasks" in demo
    assert "function taskfileTasks" in demo
    assert "function invokeTasks" in demo
    assert "function toxEnvs" in demo
    assert "function rakeTasks" in demo
    assert "function snakemakeTargets" in demo
    assert "function nextflowProfiles" in demo
    assert "function nextflowNames" in demo
    assert "function cromwellReferenceFromCommand" in demo
    assert "function cwlReferenceFromCommand" in demo
    assert "function papermillReferenceFromCommand" in demo
    assert "function dvcReferenceFromCommand" in demo
    assert "function dvcStageNames" in demo
    assert "DVC target" in demo
    assert "function quartoReferenceFromCommand" in demo
    assert "Quarto render target" in demo
    assert "function jupytextReferenceFromCommand" in demo
    assert "Jupytext sync target" in demo
    assert "function kedroReferenceFromCommand" in demo
    assert "Kedro pipeline" in demo
    assert "function prefectReferenceFromCommand" in demo
    assert "Prefect flow" in demo
    assert "function mlflowReferenceFromCommand" in demo
    assert "MLflow entry point" in demo
    assert "function dbtReferenceFromCommand" in demo
    assert "function dbtModelNames" in demo
    assert "dbt selector" in demo
    assert "function gxCheckpointReferenceFromCommand" in demo
    assert "function gxCheckpointNames" in demo
    assert "Great Expectations checkpoint" in demo
    assert "function dagsterReferenceFromCommand" in demo
    assert "function dagsterNames" in demo
    assert "Dagster job" in demo
    assert "function ploomberReferenceFromCommand" in demo
    assert "function ploomberTaskNames" in demo
    assert "Ploomber task" in demo
    assert "function luigiReferenceFromCommand" in demo
    assert "function luigiTaskNames" in demo
    assert "Luigi task" in demo
    assert "function airflowReferenceFromCommand" in demo
    assert "function airflowDagTaskNames" in demo
    assert "Airflow DAG" in demo
    assert "Airflow task" in demo
    assert "function metaflowReferenceFromCommand" in demo
    assert "Metaflow step" in demo
    assert "function noxSessions" in demo
    assert "function justRecipes" in demo
    assert "function doitTasks" in demo
    assert "commonUvRunExternalCommands" in demo
    assert "Python module" in demo
    assert "uv run train-model" in demo
    assert "uv run python -m demo_lab.report" in demo
    assert "Hatch script" in demo
    assert "PDM script" in demo
    assert "pixi task" in demo
    assert "taskipy task" in demo
    assert "Taskfile task" in demo
    assert "Invoke task" in demo
    assert "tox environment" in demo
    assert "Rake task" in demo
    assert "Snakemake target" in demo
    assert "Nextflow profile" in demo
    assert "WDL workflow" in demo
    assert "CWL workflow" in demo
    assert "Papermill parameter" in demo
    assert "nox session" in demo
    assert "just recipe" in demo
    assert "doit task" in demo
    assert "npm run reproduce" in demo
    assert "pnpm run dashboard" in demo
    assert "yarn report" in demo
    assert "package.json script" in demo
    assert "pyproject script" in demo
    assert "function sklearnRandomStateIssues" in demo
    assert "function pandasRandomStateIssues" in demo
    assert "function pytorchRandomSplitIssues" in demo
    assert "function pytorchDataLoaderGeneratorIssues" in demo
    assert "function pytorchDataLoaderWorkerInitIssues" in demo
    assert "function tensorflowRandomSeedIssues" in demo
    assert "function xgboostRandomStateIssues" in demo
    assert "function optunaSamplerSeedIssues" in demo
    assert "function jaxPrngKeyReuseIssues" in demo
    assert "function polarsSeedIssues" in demo
    assert "function numpyDefaultRngIssues" in demo
    assert "function missingOutputDirectoryFindings" in demo
    assert "function missingGlobbedInputFindings" in demo
    assert "function timestampedOutputFindings" in demo
    assert "function unsortedFileDiscoveryFindings" in demo
    assert "function inlineUnpinnedInstallIssues" in demo
    assert "function inlineSystemPackageInstallIssues" in demo
    assert "function startsShellCellMagic" in demo
    assert "function inlineCommandMissingPathFindings" in demo
    assert "function vcsDependenciesFromText" in demo
    assert "function inlineVcsDependencyIssues" in demo
    assert "function findMissingRequirementIncludes" in demo
    assert "function environmentPipEntries" in demo
    assert "function environmentPipRequirementIncludes" in demo
    assert "function requirementSeedPaths" in demo
    assert "function iterRequirementFiles" in demo
    assert "function findUnpinnedRequirementGraph" in demo
    assert "function vcsDependenciesFromRequirements" in demo
    assert "function findMissingLocalDependencyPaths" in demo
    assert "function gitignoreEntries" in demo
    assert "function gitignoredInputFindings" in demo
    assert "function localDependencyReferencesFromRequirementLine" in demo
    assert "function findUndeclaredCommonImports" in demo
    assert "function missingLocalModuleImports" in demo
    assert "commonImportDependencies" in demo
    assert "httpx.get" in demo
    assert "function undocumentedEnvironmentVariables" in demo
    assert "function interactivePromptIssues" in demo
    assert "function workingDirectoryChangeIssues" in demo
    assert "function acceleratorIssues" in demo
    assert "function findWorkflowDrift" in demo
    assert "function findWorkflowVerificationGaps" in demo
    assert "function findCiPythonRuntimeConflicts" in demo
    assert "function findFloatingDockerBaseImages" in demo
    assert "function findDockerDependencyInstallGaps" in demo
    assert "function findFloatingGithubActionRefs" in demo
    assert "CI workflow command references a missing path" in demo
    assert "CI workflow lacks verification step" in demo
    assert "CI Python version conflicts with project runtime" in demo
    assert "Floating Docker base image tag" in demo
    assert "Dockerfile skips dependency manifest" in demo
    assert "Remote artifact lacks checksum" in demo
    assert "Floating GitHub Action reference" in demo
    assert "PyTorch random_split lacks generator" in demo
    assert "PyTorch DataLoader shuffle lacks generator" in demo
    assert "PyTorch DataLoader workers lack seed init" in demo
    assert "Optuna study lacks seeded sampler" in demo
    assert "JAX PRNG key is reused" in demo
    assert "Interactive prompt blocks unattended rerun" in demo
    assert "Working directory changes during rerun" in demo
    assert "Inline command references a missing script" in demo
    assert "Referenced input is ignored by git" in demo
    assert "Hugging Face artifact revision is unpinned" in demo
    assert "VCS dependency uses moving ref" in demo
    assert "TensorFlow randomness lacks set_seed" in demo
    assert "XGBoost estimator lacks random_state" in demo
    assert "optuna.create_study(direction='maximize')" in demo
    assert "jax.random.bernoulli(key, 0.5, (4,))" in demo
    assert "Polars sampling lacks seed" in demo
    assert "NumPy default_rng lacks seed" in demo
    assert "Output directory is not created" in demo
    assert "Globbed input path is missing" in demo
    assert "Timestamped output path is unstable" in demo
    assert "Unsorted file discovery order" in demo
    assert "Local dependency path is missing" in demo
    assert "Imported dependency is not declared" in demo
    assert "Local helper module import is missing" in demo
    assert "Accelerator requirement is undocumented" in demo
    assert "Remote download has no timeout" in demo
    assert "Environment variable is undocumented" in demo
    assert "Requirement include file is missing" in demo
    assert "Conda pip include" in demo
    assert "Notebook installs unpinned packages inline" in demo
    assert "System package install is inline" in demo
    assert "git+https://github.com/example/research-utils.git@main" in demo
    assert "!sudo apt-get install -y graphviz" in demo
    assert "%pip install pandas" in demo
    assert ".python-version" in demo
    assert "Dockerfile" in demo
    assert "python:latest" in demo
    assert "COPY . ." in demo
    assert "release_reference = pd.read_csv('https://example.com/releases/v1/reference.csv')" in demo
    assert "actions/setup-python@main" in demo
    assert "random_split(dataset, [80, 20])" in demo
    assert "DataLoader(train_ds, batch_size=32, shuffle=True, num_workers=4)" in demo
    assert "input('Run label: ')" in demo
    assert "os.chdir('notebooks')" in demo
    assert "%run scripts/missing_preprocess.py" in demo
    assert "demo-lab/.gitignore" in demo
    assert "demo-lab/data/train.csv" in demo
    assert "torch.device('cuda')" in demo
    assert "load_dataset('squad')" in demo
    assert "from helpers.cleaning import normalize" in demo
    assert "AutoModel.from_pretrained('bert-base-uncased')" in demo
    assert "tf.random.normal" in demo
    assert "xgb.XGBClassifier" in demo
    assert "pl.DataFrame" in demo
    assert "np.random.default_rng()" in demo
    assert "outputs/report.csv" in demo
    assert "Path('data/unshared').glob('*.csv')" in demo
    assert "glob('data/raw/*.csv')" in demo
    assert "datetime.now().strftime" in demo
    assert "make reproduce" in demo
    assert "Makefile" in demo
    assert "Add the Makefile target" in demo
    assert "data.dvc" in demo
    assert "dvc pull" in demo
    assert "git lfs pull" in demo


def test_landing_page_links_adoption_pack() -> None:
    landing = Path("site/index.html").read_text(encoding="utf-8")
    scorecard = Path("docs/sample-audits/broken-repo-scorecard.md").read_text(encoding="utf-8")
    target_fit = Path("docs/sample-audits/broken-repo-target-fit.md").read_text(encoding="utf-8")
    markdown = Path("docs/sample-audits/broken-repo-audit.md").read_text(encoding="utf-8")
    assert '<div class="score">39</div>' in landing
    assert "5 high-severity findings" in landing
    assert "7 medium-severity findings" in landing
    assert "14 total findings" in landing
    assert "Overall score: **39/100**" in scorecard
    assert "Findings: **14** (`5` high, `7` medium, `2` low)" in scorecard
    assert "## Review Boundary" in scorecard
    assert "does not prove scientific validity" in scorecard
    assert "Explain top finding: `labcheck explain LC001`" in scorecard
    assert "# labcheck Target Fit" in target_fit
    assert "Fit score: **9/10**" in target_fit
    assert "strong outreach candidate" in target_fit
    assert "## Review Boundary" in markdown
    assert "## Understand Finding Codes" in markdown
    assert "## Next Steps" in markdown
    assert "Scorecard summary: `labcheck scorecard examples/broken-repo`" in markdown
    assert "`labcheck explain LC001`" in markdown
    assert "labcheck init --policy" in landing
    assert "Request public repo audit" in landing
    assert "issues/new?template=audit_request.yml" in landing
    assert "docs/reproducibility.md" in landing
    assert "docs/lab-adoption-guide.md" in landing
    assert "scorecard-path: labcheck-scorecard.md" in landing
    assert "target-fit-path: labcheck-target-fit.md" in landing
    assert "issue-draft-path: labcheck-issue-draft.md" in landing
    assert "Seedless sklearn splits" in landing
    assert "LC016" in landing
    assert "Seedless pandas samples" in landing
    assert "LC017" in landing
    assert "DVC and Git LFS restore gaps" in landing
    assert "LC018" in landing
    assert "Gitignored input" in landing
    assert "LC053" in landing
    assert "Hardcoded secret" in landing
    assert "LC054" in landing
    assert "Clock-dependent logic" in landing
    assert "LC055" in landing
    assert "Set-derived order" in landing
    assert "LC056" in landing
    assert "Unstable hash split" in landing
    assert "LC057" in landing
    assert "Runtime conflict" in landing
    assert "LC019" in landing
    assert "Inline notebook installs" in landing
    assert "LC020" in landing
    assert "Inline OS package installs" in landing
    assert "LC048" in landing
    assert "Missing setup step" in landing
    assert "LC021" in landing
    assert "Mutable remote data URLs" in landing
    assert "reads or downloads" in landing
    assert "LC022" in landing
    assert "Remote downloads without timeouts" in landing
    assert "LC047" in landing
    assert "Remote artifacts without checksums" in landing
    assert "LC050" in landing
    assert "Unpinned Hugging Face artifacts" in landing
    assert "LC042" in landing
    assert "Moving VCS dependency refs" in landing
    assert "LC043" in landing
    assert "Conda <code>pip:</code> entry, or notebook install uses a VCS URL" in landing
    assert "Hosted-notebook path" in landing
    assert "LC006" in landing
    assert "/kaggle/input/" in landing
    assert "Broken requirements include" in landing
    assert "LC023" in landing
    assert "Conda <code>pip:</code> section includes another local dependency file" in landing
    assert "Undocumented env vars" in landing
    assert "LC024" in landing
    assert "CI command drift" in landing
    assert "LC025" in landing
    assert "CI verification gap" in landing
    assert "LC044" in landing
    assert "CI runtime mismatch" in landing
    assert "LC026" in landing
    assert "Missing local dependency" in landing
    assert "LC027" in landing
    assert "manifest or Conda <code>pip:</code> entry references an editable" in landing
    assert "Undeclared import" in landing
    assert "LC028" in landing
    assert "Missing local helper import" in landing
    assert "LC045" in landing
    assert "Undocumented accelerator requirement" in landing
    assert "LC046" in landing
    assert "Floating Docker base image" in landing
    assert "LC029" in landing
    assert "Dockerfile skips dependency manifest" in landing
    assert "LC049" in landing
    assert "Floating GitHub Action reference" in landing
    assert "LC030" in landing
    assert "PyTorch random_split" in landing
    assert "LC031" in landing
    assert "PyTorch DataLoader shuffle" in landing
    assert "LC040" in landing
    assert "PyTorch worker seed drift" in landing
    assert "LC059" in landing
    assert "PyTorch backend drift" in landing
    assert "LC058" in landing
    assert "Interactive rerun prompts" in landing
    assert "LC041" in landing
    assert "Missing inline script" in landing
    assert "LC052" in landing
    assert "Working-directory mutation" in landing
    assert "LC051" in landing
    assert "TensorFlow randomness" in landing
    assert "LC032" in landing
    assert "XGBoost estimator" in landing
    assert "LC033" in landing
    assert "Optuna sampler drift" in landing
    assert "LC060" in landing
    assert "JAX PRNG key reuse" in landing
    assert "LC061" in landing
    assert "Dead docs link" in landing
    assert "LC062" in landing
    assert "Missing license metadata" in landing
    assert "LC063" in landing
    assert "Missing citation metadata" in landing
    assert "LC064" in landing
    assert "Compose dependency drift" in landing
    assert "LC065" in landing
    assert "Compose network drift" in landing
    assert "LC066" in landing
    assert "Compose healthcheck drift" in landing
    assert "LC067" in landing
    assert "Compose secret/config drift" in landing
    assert "LC068" in landing
    assert "Compose env_file drift" in landing
    assert "LC069" in landing
    assert "Compose extends drift" in landing
    assert "LC070" in landing
    assert "Compose include drift" in landing
    assert "LC071" in landing
    assert "Compose label_file drift" in landing
    assert "LC072" in landing
    assert "Compose watch path drift" in landing
    assert "LC073" in landing
    assert "Polars sampling" in landing
    assert "LC034" in landing
    assert "Seedless NumPy Generators" in landing
    assert "LC039" in landing
    assert "Missing output directories" in landing
    assert "LC035" in landing
    assert "Missing globbed inputs" in landing
    assert "LC036" in landing
    assert "Timestamped output paths" in landing
    assert "LC037" in landing
    assert "Unsorted file discovery" in landing
    assert "LC038" in landing
    assert "audience-specific target-fit card for professor/founder/maintainer outreach" in landing
    assert "downloadable scorecard/target-fit/issue-draft/outreach-note/Markdown/CSV/JSON results" in landing
    assert "bounded public GitHub repo files entirely in the browser" in landing
    assert "public GitHub URL box" in landing
    assert "prioritize README/manifests, CI, Docker/Make files, notebooks, and Python source" in landing
    assert "labcheck demo-link https://github.com/owner/repo" in landing
    assert "labcheck demo-repo" in landing
    assert "labcheck scorecard labcheck-demo-repo" in landing
    assert "privacy and safety model" in landing


def test_landing_page_promotes_audit_pack_for_outreach() -> None:
    landing = Path("site/index.html").read_text(encoding="utf-8")
    assert "labcheck target-fit" in landing
    assert "labcheck-target-fit.md" in landing
    assert "labcheck scorecard" in landing
    assert "labcheck-scorecard.md" in landing
    assert "labcheck-demo-link.txt" in landing
    assert "labcheck-demo-link.md" in landing
    assert "labcheck outreach" in landing
    assert "labcheck-outreach-note.md" in landing
    assert "labcheck issue" in landing
    assert "labcheck-issue-draft.md" in landing
    assert "bounded browser-demo link on public GitHub targets" in landing
    assert "respectful maintainer issue draft" in landing
    assert "labcheck pack --zip" in landing
    assert "MANIFEST.md" in landing
    assert "Prove cleanup progress" in landing
    assert "labcheck compare before-labcheck-report.json after-labcheck-report.json --output labcheck-compare.md" in landing
    assert "score deltas, severity deltas, resolved findings, and new findings" in landing
    assert "docs/faq.md" in landing
    assert "docs/first-audit.md" in landing
    assert "docs/reproducibility-patterns.md" in landing
    assert "docs/scoring-guide.md" in landing
    assert "docs/comparison.md" in landing
    assert "docs/demo-video-script.md" in landing
    assert "docs/roadmap.md" in landing
    assert "docs/good-first-issues.md" in landing
    assert "docs/issue-labels.md" in landing
    assert "docs/public-triage-board.md" in landing
    assert "docs/reply-derived-case-study-seed.md" in landing
    assert "docs/reply-to-case-study-checklist.md" in landing
    assert "docs/maintainer-reply-templates.md" in landing
    assert "docs/launch-kit.md" in landing
    assert "docs/launch-post-after-action.md" in landing
    assert "docs/launch-week-plan.md" in landing
    assert "docs/outreach-tracker-template.md" in landing
    assert "docs/install.md" in landing
    assert "docs/privacy-and-safety.md" in landing
    assert "broken-repo-scorecard.md" in landing
    assert "broken-repo-target-fit.md" in landing
    assert "broken-repo-outreach-note.md" in landing
    assert "broken-repo-issue-draft.md" in landing
    assert "broken-repo-labeled-issue.md" in landing
    assert "labcheck-audit" in landing
    assert "single archive" in landing
    assert "complete audit folder" in landing


def test_public_case_studies_match_checked_in_audit_snapshots() -> None:
    case_studies = Path("docs/case-studies.md").read_text(encoding="utf-8")
    landing = Path("site/index.html").read_text(encoding="utf-8")
    good_first = Path("docs/good-first-issues.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")
    examples = [
        ("ageron/handson-ml3", "docs/sample-audits/handson-ml3-audit.md"),
        ("jakevdp/PythonDataScienceHandbook", "docs/sample-audits/python-data-science-handbook-audit.md"),
    ]

    for repo, audit_path in examples:
        audit_text = Path(audit_path).read_text(encoding="utf-8")
        score, high, medium, low = _audit_snapshot(audit_path)
        docs_snapshot = f"score `{score}`, with `{high} high`, `{medium} medium`, and `{low} low` findings"
        landing_snapshot = f"score {score}; {high} high, {medium} medium, {low} low findings."
        assert repo in case_studies
        assert repo in landing
        assert docs_snapshot in case_studies
        assert landing_snapshot in landing
        assert "## Review Boundary" in audit_text
        assert "## Understand Finding Codes" in audit_text
        assert "## Next Steps" in audit_text
        assert "Sortable triage CSV" in audit_text
        assert f"labcheck scan https://github.com/{repo} --format markdown" in case_studies

    assert "What felt fair" in case_studies
    assert "What was noisy or needs human judgment" in case_studies
    assert "Tiny outreach angle" in case_studies
    assert "generated artifacts and hidden-state assumptions" in case_studies
    assert "data/recipeitems.json" in case_studies
    assert "Add a tiny public case study" not in good_first
    assert "Add a maintainer-facing false-positive example" not in launch_plan
    assert "Add CI ratchet examples for monorepos" not in launch_plan
    assert "Add reusable issue labels for labcheck findings" not in launch_plan
    assert "Add public triage board template" not in launch_plan
    assert "Add sample labeled audit issue bundle" not in launch_plan
    assert "Add first maintainer reply follow-up template" not in launch_plan
    assert "Add launch post after-action checklist" not in launch_plan
    assert "Add reply-to-case-study conversion checklist" not in launch_plan
    assert "Add first reply-derived case study" not in launch_plan
    assert "Replace reply-derived case-study seed with first real public reply" in launch_plan

def test_comparison_guide_positions_labcheck_without_overclaiming() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    faq = Path("docs/faq.md").read_text(encoding="utf-8")
    comparison = Path("docs/comparison.md").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")

    assert "[Comparison guide](docs/comparison.md)" in readme
    assert "[Reproducibility pattern gallery](docs/reproducibility-patterns.md)" in readme
    assert "[comparison guide](comparison.md)" in faq
    assert "[reproducibility pattern gallery](reproducibility-patterns.md)" in faq
    assert "[Comparison guide](comparison.md)" in launch_kit
    assert "[Reproducibility pattern gallery](reproducibility-patterns.md)" in launch_kit
    assert "a no-key, first-pass reproducibility and handoff audit" in comparison
    assert "Linters and formatters" in comparison
    assert "CI and notebook execution" in comparison
    assert "DVC, Git LFS, and data-versioning tools" in comparison
    assert "What labcheck Does Not Claim" in comparison
    assert "does not prove" in comparison
    assert "These workflows stack well" in comparison


def test_first_audit_guide_is_actionable_for_new_users() -> None:
    guide = Path("docs/first-audit.md").read_text(encoding="utf-8")

    assert "Path 1: No Install Demo" in guide
    assert "Path 2: Local Repo Audit" in guide
    assert "Path 3: Public GitHub Repo Audit" in guide
    assert "paste a public GitHub repository URL" in guide
    assert "demo.html?repo=owner/repo" in guide
    assert "demo.html?repo=owner/repo&audience=professor" in guide
    assert "labcheck demo-link https://github.com/owner/repo --audience professor --output labcheck-demo-link.txt" in guide
    assert "labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit --audience professor --output labcheck-demo-link.md" in guide
    assert "add `&audit=1` only when you intentionally want" in guide
    assert "browser GitHub path is intentionally bounded" in guide
    assert "prioritizes README/manifests" in guide
    assert "labcheck doctor /path/to/repo" in guide
    assert "labcheck pack /path/to/repo --output-dir labcheck-audit --zip" in guide
    assert "labcheck-audit/MANIFEST.md" in guide
    assert "labcheck demo-repo" in guide
    assert "labcheck scorecard labcheck-demo-repo" in guide
    assert "labcheck target-fit https://github.com/owner/repo --audience professor --output labcheck-target-fit.md" in guide
    assert "labcheck scorecard https://github.com/owner/repo --output labcheck-scorecard.md" in guide
    assert "labcheck outreach https://github.com/owner/repo --output labcheck-outreach-note.md" in guide
    assert "labcheck outreach https://github.com/owner/repo --audience professor --output labcheck-professor-note.md" in guide
    assert "labcheck outreach https://github.com/owner/repo --audience founder --output labcheck-founder-note.md" in guide
    assert "labcheck issue https://github.com/owner/repo --output labcheck-issue-draft.md" in guide
    assert "include a bounded browser-demo link automatically" in guide
    assert "--audience maintainer" in guide
    assert "labcheck compare before-labcheck-report.json after-labcheck-report.json --output labcheck-compare.md" in guide
    assert "before/after proof note" in guide
    assert "Only audit public repos unless you have explicit permission" in guide
    assert "it does not prove the research result" in guide
    assert "[Privacy and safety model](privacy-and-safety.md)" in guide


def test_scoring_guide_documents_score_limits_and_formula() -> None:
    guide = Path("docs/scoring-guide.md").read_text(encoding="utf-8")

    assert "not a claim" in guide
    assert "scientifically valid" in guide
    assert "High | 26 points" in guide
    assert "Medium | 14 points" in guide
    assert "Low | 6 points" in guide
    assert "35%" in guide
    assert "at most 72 points" in guide
    assert "overall = round(category_average * 0.70 + weakest_category * 0.30)" in guide


def test_docs_explain_targeted_suppressions() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    faq = Path("docs/faq.md").read_text(encoding="utf-8")
    action_guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    first_audit = Path("docs/first-audit.md").read_text(encoding="utf-8")

    for document in (readme, faq, action_guide, first_audit):
        assert "[[ignored_findings]]" in document
        assert 'check_id = "LC010"' in document
        assert 'path = "archive/old_experiment.py"' in document

    assert "When a finding is expected, say why in maintainer-facing language" in first_audit
    assert 'check_id = "LC002"' in first_audit
    assert 'path = "notebooks/tutorial.ipynb"' in first_audit
    assert "This `LC002` finding is expected for `notebooks/tutorial.ipynb`" in first_audit
    assert "rather than disabling hidden-state" in first_audit
    assert "checks globally" in first_audit


def test_github_action_guide_documents_monorepo_ratchets() -> None:
    guide = Path("docs/github-action.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")

    assert "## Monorepo Matrix Ratchet" in guide
    assert "avoid one giant root baseline owned by nobody" in guide
    assert "name: labcheck monorepo ratchet" in guide
    assert "fail-fast: false" in guide
    assert "target: notebooks" in guide
    assert "baseline: notebooks/.labcheck-baseline.json" in guide
    assert "target: services/ml" in guide
    assert "baseline: services/ml/.labcheck-baseline.json" in guide
    assert "config-path: ${{ matrix.config }}" in guide
    assert "baseline-path: ${{ matrix.baseline }}" in guide
    assert "min-score: ${{ matrix.min_score }}" in guide
    assert "labcheck-${{ matrix.name }}-scorecard.md" in guide
    assert "labcheck-${{ matrix.name }}-target-fit.md" in guide
    assert "labcheck baseline notebooks --config notebooks/.labcheck.toml" in guide
    assert "Leave unsupported or archived directories out of the matrix" in guide
    assert "Add CI ratchet examples for monorepos" not in launch_plan


def test_issue_label_guide_is_reusable_for_public_triage() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    labels = Path(".github/labels.yml").read_text(encoding="utf-8")
    guide = Path("docs/issue-labels.md").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")

    for label in (
        "severity/high",
        "severity/medium",
        "severity/low",
        "category/environment",
        "category/determinism",
        "category/artifacts",
        "category/portability",
        "category/onboarding",
        "finding/lc002",
        "finding/lc005",
        "triage/public-audit",
        "triage/false-positive",
        "triage/baseline-ratchet",
        "workflow/browser-demo",
        "workflow/github-action",
        "audience/professor",
        "audience/founder",
        "audience/maintainer",
    ):
        assert f"name: {label}" in labels
        assert label in guide

    assert "[Issue label guide](docs/issue-labels.md)" in readme
    assert "[issue-labels.md](issue-labels.md)" in launch_kit
    assert "[`.github/labels.yml`](https://github.com/ThomasAquinas14/labcheck/blob/main/.github/labels.yml)" in launch_kit
    assert "gh label create \"severity/high\"" in guide
    assert "one severity, one category, and one next-action label" in guide
    assert "Do not use labels to imply scientific validity" in guide
    assert "Add reusable issue labels for labcheck findings" not in launch_plan


def test_public_triage_board_template_guides_launch_followup() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    board = Path("docs/public-triage-board.md").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")
    landing = Path("site/index.html").read_text(encoding="utf-8")

    assert "[Public triage board template](docs/public-triage-board.md)" in readme
    assert "[public-triage-board.md](public-triage-board.md)" in launch_kit
    assert "[reply-to-case-study-checklist.md](reply-to-case-study-checklist.md)" in board
    assert "Open triage board template" in landing
    assert "# Public Triage Board Template" in board
    assert "labcheck public triage" in board
    assert "GitHub Issues are the source of truth" in board
    assert "| Inbox |" in board
    assert "| Needs Repro |" in board
    assert "| Case Study Candidate |" in board
    assert "| Finding ID | Text |" in board
    assert "is:issue is:open label:triage/public-audit" in board
    assert 'gh issue list --label "triage/public-audit" --state open' in board
    assert "Reduce LC002 noise for tutorial notebooks with shared setup cells" in board
    assert "Scope note to reuse" in board
    assert "without promising unlimited free consulting" in board
    assert "Add public triage board template" not in launch_plan


def test_sample_labeled_audit_issue_bundle_is_copyable() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    bundle = Path("docs/sample-audits/broken-repo-labeled-issue.md").read_text(encoding="utf-8")
    issue_draft = Path("docs/sample-audits/broken-repo-issue-draft.md").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")
    landing = Path("site/index.html").read_text(encoding="utf-8")

    assert "[Labeled issue bundle sample](docs/sample-audits/broken-repo-labeled-issue.md)" in readme
    assert "[Sample labeled issue bundle](sample-audits/broken-repo-labeled-issue.md)" in launch_kit
    assert "Labeled issue bundle" in landing
    assert "Open labeled issue bundle" in landing
    assert "# Labeled Audit Issue Bundle" in bundle
    assert "[maintainer reply templates](../maintainer-reply-templates.md)" in bundle
    assert "Reproducibility handoff gaps in `examples/broken-repo`" in bundle
    assert "severity/high" in bundle
    assert "category/determinism" in bundle
    assert "category/artifacts" in bundle
    assert "finding/lc001" in bundle
    assert "finding/lc002" in bundle
    assert "finding/lc005" in bundle
    assert "triage/public-audit" in bundle
    assert "gh issue create" in bundle
    assert "--body-file docs/sample-audits/broken-repo-issue-draft.md" in bundle
    assert "| Status | Ready To Fix |" in bundle
    assert "Put the issue in the [public triage board](../public-triage-board.md)" in bundle
    assert "Please treat this as a lightweight maintainer handoff signal" in issue_draft
    assert "Add sample labeled audit issue bundle" not in launch_plan


def test_maintainer_reply_templates_keep_followup_scoped() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    templates = Path("docs/maintainer-reply-templates.md").read_text(encoding="utf-8")
    board = Path("docs/public-triage-board.md").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")
    landing = Path("site/index.html").read_text(encoding="utf-8")

    assert "[Maintainer reply templates](docs/maintainer-reply-templates.md)" in readme
    assert "[Maintainer reply templates](maintainer-reply-templates.md)" in launch_kit
    assert "[maintainer-reply-templates.md](maintainer-reply-templates.md)" in board
    assert "Open reply templates" in landing
    assert "# Maintainer Reply Templates" in templates
    assert '## If They Say "Thanks, This Is Useful"' in templates
    assert "## If They Say The Finding Is Expected" in templates
    assert "## If They Ask For Reproduction Steps" in templates
    assert "## If They Invite A Pull Request" in templates
    assert "## If They Need Private Data Or Scientific Review" in templates
    assert "## If They Push Back" in templates
    assert "## If They Fix Something" in templates
    assert "## One Gentle No-Reply Follow-Up" in templates
    assert "Do not keep bumping public maintainers" in templates
    assert "Status: Waiting On Maintainer" in templates
    assert "labcheck compare before-labcheck-report.json after-labcheck-report.json" in templates
    assert "Add first maintainer reply follow-up template" not in launch_plan


def test_launch_post_after_action_checklist_turns_posts_into_evidence() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    checklist = Path("docs/launch-post-after-action.md").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")
    landing = Path("site/index.html").read_text(encoding="utf-8")

    assert "[Launch post after-action checklist](docs/launch-post-after-action.md)" in readme
    assert "[Launch post after-action checklist](launch-post-after-action.md)" in launch_kit
    assert "[launch-post-after-action.md](launch-post-after-action.md)" in launch_plan
    assert "Open after-action checklist" in landing
    assert "# Launch Post After-Action Checklist" in checklist
    assert "Capture The Baseline" in checklist
    assert "Triage Replies" in checklist
    assert "Convert Attention Into One Public Artifact" in checklist
    assert "Do not ask strangers to star the repo as the main call to action" in checklist
    assert "no hosted backend, no inference bill, no repo secrets" in checklist
    assert "Add launch post after-action checklist" not in launch_plan


def test_reply_to_case_study_checklist_keeps_public_proof_bounded() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    checklist = Path("docs/reply-to-case-study-checklist.md").read_text(encoding="utf-8")
    case_studies = Path("docs/case-studies.md").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")
    after_action = Path("docs/launch-post-after-action.md").read_text(encoding="utf-8")
    landing = Path("site/index.html").read_text(encoding="utf-8")

    assert "[Reply to case study checklist](docs/reply-to-case-study-checklist.md)" in readme
    assert "[Reply to case study checklist](reply-to-case-study-checklist.md)" in launch_kit
    assert "[reply-to-case-study-checklist.md](reply-to-case-study-checklist.md)" in case_studies
    assert "[reply-to-case-study-checklist.md](reply-to-case-study-checklist.md)" in launch_plan
    assert "[reply-to-case-study-checklist.md](reply-to-case-study-checklist.md)" in after_action
    assert "Open case-study checklist" in landing
    assert "# Reply To Case Study Checklist" in checklist
    assert "Only convert a reply into a case study when all of these are true" in checklist
    assert "Do not publish claims that are not visible in the report" in checklist
    assert "What was noisy or needs human judgment" in checklist
    assert "If anything feels unfairly represented, I am happy to revise or remove it." in checklist
    assert "Add reply-to-case-study conversion checklist" not in launch_plan


def test_reply_derived_case_study_seed_is_honest_and_actionable() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    seed = Path("docs/reply-derived-case-study-seed.md").read_text(encoding="utf-8")
    case_studies = Path("docs/case-studies.md").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")
    checklist = Path("docs/reply-to-case-study-checklist.md").read_text(encoding="utf-8")
    landing = Path("site/index.html").read_text(encoding="utf-8")

    assert "[Reply-derived case study seed](docs/reply-derived-case-study-seed.md)" in readme
    assert "[Reply-derived case study seed](reply-derived-case-study-seed.md)" in launch_kit
    assert "[reply-derived-case-study-seed.md](reply-derived-case-study-seed.md)" in case_studies
    assert "[reply-derived-case-study-seed.md](reply-derived-case-study-seed.md)" in checklist
    assert "Open case-study seed" in landing
    assert "# Reply-Derived Case Study Seed" in seed
    assert "not a real external reply yet" in seed
    assert "Do not pretend this seed is real external validation" in seed
    assert "Generated artifacts need an explicit contract" in seed
    assert "Replace reply-derived case-study seed with first real public reply" in launch_plan


def test_privacy_and_safety_model_is_public_and_specific() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    safety = Path("docs/privacy-and-safety.md").read_text(encoding="utf-8")

    assert "[Privacy and Safety Model](docs/privacy-and-safety.md)" in readme
    assert "No API keys are required" in safety
    assert "The browser demo does not send selected local files" in safety
    assert "contents: read" in safety
    assert "does not need repository secrets" in safety
    assert "GitHub's unauthenticated public API directly from the visitor's browser" in safety
    assert "does not execute target project code by default" in safety
    assert "Do not paste, upload, or scan private code unless you have permission" in safety
    assert "Avoid adding a hosted clone queue" in safety
    assert "no-key by default" in safety


def test_install_guide_supports_low_friction_first_run() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    install = Path("docs/install.md").read_text(encoding="utf-8")
    landing = Path("site/index.html").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")

    assert "[install guide](docs/install.md)" in readme
    assert "pipx install git+https://github.com/ThomasAquinas14/labcheck.git" in install
    assert "labcheck demo-repo" in install
    assert "labcheck doctor labcheck-demo-repo" in install
    assert "labcheck scorecard labcheck-demo-repo" in install
    assert "labcheck target-fit https://github.com/owner/repo --audience professor --output labcheck-target-fit.md" in install
    assert "labcheck scorecard https://github.com/owner/repo --output labcheck-scorecard.md" in install
    assert "labcheck demo-link https://github.com/owner/repo --audience professor --output labcheck-demo-link.txt" in install
    assert "labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit --audience professor --output labcheck-demo-link.md" in install
    assert "audience-specific target-fit card" in install
    assert "Open install guide" in landing
    assert "pipx install git+https://github.com/ThomasAquinas14/labcheck.git" in landing
    assert "The generated fixture is intentionally broken" in landing
    assert "[Install guide](install.md)" in launch_kit
    assert "labcheck demo-repo" in launch_kit


def test_public_pages_have_share_metadata() -> None:
    landing = Path("site/index.html").read_text(encoding="utf-8")
    demo = Path("site/demo.html").read_text(encoding="utf-8")
    sitemap = Path("site/sitemap.xml").read_text(encoding="utf-8")
    llms = Path("site/llms.txt").read_text(encoding="utf-8")
    landing_schema = _json_ld_documents(landing)[0]
    demo_schema = _json_ld_documents(demo)[0]

    assert '<meta name="description"' in landing
    assert 'property="og:title"' in landing
    assert 'property="og:site_name" content="labcheck"' in landing
    assert 'property="og:url" content="https://thomasaquinas14.github.io/labcheck/"' in landing
    assert 'rel="sitemap" type="application/xml" href="sitemap.xml"' in landing
    assert 'rel="alternate" type="text/plain" href="llms.txt" title="llms.txt"' in landing
    assert 'property="og:image" content="https://thomasaquinas14.github.io/labcheck/docs/assets/scorecard-preview.svg"' in landing
    assert 'name="twitter:card" content="summary_large_image"' in landing
    assert 'name="twitter:image" content="https://thomasaquinas14.github.io/labcheck/docs/assets/scorecard-preview.svg"' in landing
    assert '<link rel="canonical" href="https://thomasaquinas14.github.io/labcheck/">' in landing
    assert 'name="theme-color"' in landing
    assert "No-key reproducibility audits" in landing
    assert landing_schema["@context"] == "https://schema.org"
    assert landing_schema["@type"] == "SoftwareApplication"
    assert landing_schema["name"] == "labcheck"
    assert landing_schema["codeRepository"] == "https://github.com/ThomasAquinas14/labcheck"
    assert landing_schema["isAccessibleForFree"] is True
    assert landing_schema["offers"]["price"] == "0"
    assert "no API key required" in landing_schema["softwareRequirements"]
    assert '<meta name="description"' in demo
    assert 'property="og:title"' in demo
    assert 'property="og:url" content="https://thomasaquinas14.github.io/labcheck/demo.html"' in demo
    assert 'rel="sitemap" type="application/xml" href="sitemap.xml"' in demo
    assert 'rel="alternate" type="text/plain" href="llms.txt" title="llms.txt"' in demo
    assert 'name="twitter:card" content="summary_large_image"' in demo
    assert '<link rel="canonical" href="https://thomasaquinas14.github.io/labcheck/demo.html">' in demo
    assert "bounded public GitHub repos" in demo
    assert demo_schema["@context"] == "https://schema.org"
    assert demo_schema["@type"] == "WebApplication"
    assert demo_schema["name"] == "labcheck browser demo"
    assert demo_schema["url"] == "https://thomasaquinas14.github.io/labcheck/demo.html"
    assert demo_schema["isAccessibleForFree"] is True
    assert demo_schema["offers"]["price"] == "0"
    assert "no-API-key browser demo" in demo_schema["description"]
    assert "docs/sample-audits/broken-repo-target-fit.md" in sitemap
    assert "Sample target-fit card:" in llms
    assert "docs/sample-audits/broken-repo-target-fit.md" in llms


def test_public_deploy_docs_include_live_url_smoke_check() -> None:
    publish_guide = Path("docs/github-publish-guide.md").read_text(encoding="utf-8")
    deploy_guide = Path("docs/public-deploy-guide.md").read_text(encoding="utf-8")
    launch_kit = Path("docs/launch-kit.md").read_text(encoding="utf-8")
    release_checklist = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    command = "python scripts/check_public_urls.py https://thomasaquinas14.github.io/labcheck/"
    assert command in publish_guide
    assert command in deploy_guide
    assert command in launch_kit
    assert command in release_checklist
    assert "live landing page, browser demo, README, sample audit" in deploy_guide
    assert "after deployment, the public URL smoke checker" in release_checklist


def test_outreach_playbook_mentions_prefilled_demo_links() -> None:
    playbook = Path("docs/outreach-playbook.md").read_text(encoding="utf-8")
    landing = Path("site/index.html").read_text(encoding="utf-8")

    assert "demo.html?repo=owner/repo" in playbook
    assert "demo.html?repo=owner/repo&audience=professor" in playbook
    assert "demo.html?repo=owner/repo&audience=founder" in playbook
    assert "Prefilled demo pattern" in playbook
    assert "labcheck demo-link https://github.com/owner/repo" in playbook
    assert "labcheck demo-link https://github.com/owner/repo --audience professor" in playbook
    assert "labcheck demo-link https://github.com/owner/repo --audience founder" in playbook
    assert "labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit" in playbook
    assert "labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit --audience professor" in playbook
    assert "labcheck target-fit https://github.com/owner/repo --audience professor --output labcheck-target-fit.md" in playbook
    assert "labcheck outreach https://github.com/owner/repo --audience professor --output labcheck-professor-note.md" in playbook
    assert "labcheck outreach https://github.com/owner/repo --audience founder --output labcheck-founder-note.md" in playbook
    assert "labcheck issue https://github.com/owner/repo --output labcheck-issue-draft.md" in playbook
    assert "maintainer-friendly issue draft" in playbook
    assert "include a bounded browser-demo link automatically" in playbook
    assert "--audience maintainer" in playbook
    assert "shareable prefilled links" in landing
    assert "<code>demo.html?repo=owner/repo</code>" in landing
    assert "<code>demo.html?repo=owner/repo&amp;audience=professor</code>" in landing
    assert "<code>--audience professor</code>" in landing
    assert "<code>--format markdown --auto-audit</code>" in landing
    assert "<code>labcheck target-fit</code>" in landing
    assert "<code>labcheck outreach --audience professor</code>" in landing
    assert "labcheck outreach https://github.com/owner/repo --audience founder --output labcheck-founder-note.md" in landing


def test_demo_video_script_is_launch_ready() -> None:
    script = Path("docs/demo-video-script.md").read_text(encoding="utf-8")
    assert "75-Second Script" in script
    assert "30-Second Short" in script
    assert "Three-Minute Walkthrough" in script
    assert "No API keys" in script
    assert "No backend bill" in script
    assert "browser demo" in script
    assert "labcheck scorecard examples/broken-repo" in script
    assert "labcheck target-fit examples/broken-repo --audience founder" in script
    assert "labcheck issue examples/broken-repo --output labcheck-issue-draft.md" in script
    assert "target-fit card" in script
    assert "issue draft" in script
    assert "outreach note" in script


def test_readme_badges_reinforce_launch_positioning() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "python-3.11%2B" in readme
    assert "no_API_keys-required" in readme
    assert "local--first-reproducibility" in readme
    assert "license-MIT" in readme


def test_readme_shows_check_explain_example() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    good_first = Path("docs/good-first-issues.md").read_text(encoding="utf-8")
    launch_plan = Path("docs/launch-week-plan.md").read_text(encoding="utf-8")

    assert "Example `labcheck explain LC005` output:" in readme
    assert "LC005 - Referenced input artifact missing from repo" in readme
    assert "Default severity: high" in readme
    assert "Category: artifacts" in readme
    assert "Suggested fix: Commit the artifact, document how to obtain it, or define the input contract explicitly." in readme
    assert "This keeps finding codes safe to paste into issues, PR comments, outreach notes, or lab handoff checklists" in readme
    assert "Add a check explanation example to the README" not in good_first
    assert "Add a maintainer-facing false-positive example" not in launch_plan
    assert "Add CI ratchet examples for monorepos" not in launch_plan
    assert "Add reusable issue labels for labcheck findings" not in launch_plan
    assert "Add public triage board template" not in launch_plan
    assert "Add sample labeled audit issue bundle" not in launch_plan
    assert "Add first maintainer reply follow-up template" not in launch_plan


def test_browser_demo_escapes_user_controlled_html() -> None:
    demo = Path("site/demo.html").read_text(encoding="utf-8")
    assert "function escapeHtml" in demo
    assert "escapeHtml(node.label)" in demo
    assert "escapeHtml(risk.file)" in demo
    assert "escapeHtml(risk.evidence)" in demo
    assert "escapeHtml(finding.file)" in demo
    assert "escapeHtml(finding.evidence)" in demo
