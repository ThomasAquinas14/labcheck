from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import textwrap

import pytest


def _run_node(script: str) -> subprocess.CompletedProcess[str]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node is not installed")
    return subprocess.run(
        [node, "-e", script],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )


def _browser_harness(assertions: str) -> str:
    return textwrap.dedent(
        f"""
        const fs = require("fs");
        const vm = require("vm");
        const assert = require("assert");
        const {{ TextDecoder }} = require("util");

        const html = fs.readFileSync("site/demo.html", "utf8");
        const script = [...html.matchAll(/<script>([\\s\\S]*?)<\\/script>/g)].map(match => match[1]).join("\\n");

        function makeElement(id) {{
          return {{
            id,
            value: "",
            textContent: "",
            innerHTML: "",
            disabled: false,
            style: {{}},
            classList: {{ add() {{}}, remove() {{}} }},
            addEventListener() {{}},
            setAttribute() {{}},
            appendChild() {{}},
            removeChild() {{}},
            select() {{}},
            closest() {{ return false; }},
          }};
        }}

        const elements = new Map();
        const document = {{
          getElementById(id) {{
            if (!elements.has(id)) elements.set(id, makeElement(id));
            return elements.get(id);
          }},
          createElement(tag) {{ return makeElement(tag); }},
          body: makeElement("body"),
          execCommand() {{ return true; }},
        }};

        const URLCtor = URL;
        URLCtor.createObjectURL = () => "blob:mock";
        URLCtor.revokeObjectURL = () => {{}};

        const context = {{
          console,
          document,
          navigator: {{}},
          window: {{ isSecureContext: false, location: {{ href: "https://thomasaquinas14.github.io/labcheck/demo.html?old=1#section" }} }},
          URL: URLCtor,
          Blob,
          TextDecoder,
          Uint8Array,
          atob(value) {{ return Buffer.from(String(value), "base64").toString("binary"); }},
          alert(message) {{ throw new Error(String(message)); }},
        }};

        vm.createContext(context);
        vm.runInContext(script, context);

        (async () => {{
        {textwrap.indent(assertions, "  ")}
        }})().catch(error => {{
          console.error(error && error.stack ? error.stack : error);
          process.exit(1);
        }});
        """
    )


def test_browser_demo_runtime_prioritizes_high_signal_github_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            assert.strictEqual(
              JSON.stringify(context.parseGitHubRepoUrl("https://github.com/owner/repo")),
              JSON.stringify({ owner: "owner", repo: "repo" }),
            );
            assert.strictEqual(
              JSON.stringify(context.parseGitHubRepoUrl("owner/repo")),
              JSON.stringify({ owner: "owner", repo: "repo" }),
            );
            assert.strictEqual(
              JSON.stringify(context.parseGitHubRepoUrl("github.com/owner/repo.git")),
              JSON.stringify({ owner: "owner", repo: "repo" }),
            );
            assert.strictEqual(context.parseGitHubRepoUrl("https://example.com/owner/repo"), null);
            assert.strictEqual(
              context.canonicalGitHubRepoUrl("owner/repo"),
              "https://github.com/owner/repo",
            );
            assert.strictEqual(
              context.buildGitHubDemoUrl("owner/repo"),
              "https://thomasaquinas14.github.io/labcheck/demo.html?repo=owner%2Frepo",
            );
            assert.strictEqual(
              context.buildGitHubDemoUrl("owner/repo", { autoAudit: true }),
              "https://thomasaquinas14.github.io/labcheck/demo.html?repo=owner%2Frepo&audit=1",
            );

            const ordered = context.sortGitHubBrowserCandidates([
              { path: "docs/background.md", size: 10 },
              { path: "src/train.py", size: 100 },
              { path: "notebooks/analysis.ipynb", size: 200 },
              { path: ".github/workflows/ci.yml", size: 20 },
              { path: "README.md", size: 1000 },
              { path: "requirements.txt", size: 80 },
            ]).map(item => item.path);

            assert.deepStrictEqual(Array.from(ordered), [
              "requirements.txt",
              "README.md",
              ".github/workflows/ci.yml",
              "notebooks/analysis.ipynb",
              "src/train.py",
              "docs/background.md",
            ]);

            assert.strictEqual(
              context.formatGitHubFetchStatus(1, 0),
              "Fetched 1 prioritized browser-auditable public file. For complete coverage, run the CLI full-repo scan.",
            );
            assert.strictEqual(
              context.formatGitHubFetchStatus(3, 2),
              "Fetched 3 prioritized browser-auditable public files. Skipped 2 extra matching files due to browser limits; run the CLI full-repo scan for complete coverage.",
            );
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_task_runner_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npixi run reproduce\\nnox -s tests\\nnox --session docs\\ntask train\\nuv run task report\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "pyproject.toml",
                text: [
                  "[project]",
                  'name = "demo-lab"',
                  'version = "0.1.0"',
                  "",
                  "[tool.pixi.tasks]",
                  'reproduce = "python scripts/reproduce.py"',
                  "",
                  "[tool.taskipy.tasks]",
                  'train = "python scripts/train.py"',
                  'report = "python scripts/report.py"',
                ].join("\\n"),
              },
              {
                path: "noxfile.py",
                text: [
                  "import nox",
                  "",
                  "@nox.session",
                  "def tests(session):",
                  "    session.run('pytest')",
                  "",
                  "@nox.session(name='docs')",
                  "def build_docs(session):",
                  "    session.run('python', 'docs.py')",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_task_runner_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npixi run reproduce\\nnox -s tests\\ntask train\\nuv run task report\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "pyproject.toml",
                text: [
                  "[project]",
                  'name = "demo-lab"',
                  'version = "0.1.0"',
                  "",
                  "[tool.pixi.tasks]",
                  'lint = "ruff check ."',
                  "",
                  "[tool.taskipy.tasks]",
                  'format = "ruff format ."',
                ].join("\\n"),
              },
              {
                path: "noxfile.py",
                text: [
                  "import nox",
                  "",
                  "@nox.session",
                  "def lint(session):",
                  "    session.run('ruff', 'check', '.')",
                ].join("\\n"),
              },
            ], "demo files");

            const findings = report.findings.filter(finding => finding.id === "LC008");
            const evidence = findings.map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("pixi task 'reproduce'"));
            assert.ok(evidence.includes("nox session 'tests'"));
            assert.ok(evidence.includes("taskipy task 'train'"));
            assert.ok(evidence.includes("taskipy task 'report'"));
            assert.strictEqual(findings.length, 4);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_invoke_and_taskfile_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ninvoke reproduce\\ninv report\\ntask build\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "tasks.py",
                text: [
                  "from invoke import task",
                  "",
                  "@task",
                  "def reproduce(c):",
                  "    c.run('python scripts/reproduce.py')",
                  "",
                  "@task(name='report')",
                  "def build_report(c):",
                  "    c.run('python scripts/report.py')",
                ].join("\\n"),
              },
              {
                path: "Taskfile.yml",
                text: [
                  "version: '3'",
                  "tasks:",
                  "  build:",
                  "    cmds:",
                  "      - python scripts/build.py",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_invoke_and_taskfile_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ninvoke reproduce\\ninv report\\ntask build\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "tasks.py",
                text: [
                  "from invoke import task",
                  "",
                  "@task",
                  "def lint(c):",
                  "    c.run('ruff check .')",
                ].join("\\n"),
              },
              {
                path: "Taskfile.yml",
                text: [
                  "version: '3'",
                  "tasks:",
                  "  lint:",
                  "    cmds:",
                  "      - ruff check .",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Invoke task 'reproduce'"));
            assert.ok(evidence.includes("Invoke task 'report'"));
            assert.ok(evidence.includes("Taskfile task 'build'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_tox_and_rake_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ntox -e py311,lint\\ntox run -e docs\\nrake reproduce\\nbundle exec rake data:build\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "tox.ini",
                text: [
                  "[tox]",
                  "envlist =",
                  "    py{310,311}",
                  "    lint",
                  "",
                  "[testenv:docs]",
                  "commands = python docs.py",
                ].join("\\n"),
              },
              {
                path: "Rakefile",
                text: [
                  "task :reproduce do",
                  "  sh 'python scripts/reproduce.py'",
                  "end",
                  "",
                  "namespace :data do",
                  "  task :build do",
                  "    sh 'python scripts/build_data.py'",
                  "  end",
                  "end",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_tox_and_rake_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ntox -e py311,docs\\nrake reproduce\\nbundle exec rake data:build\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "tox.ini",
                text: [
                  "[tox]",
                  "envlist = lint",
                ].join("\\n"),
              },
              {
                path: "Rakefile",
                text: [
                  "task :lint do",
                  "  sh 'ruby -c app.rb'",
                  "end",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("tox environment(s) docs, py311"));
            assert.ok(evidence.includes("Rake task 'reproduce'"));
            assert.ok(evidence.includes("Rake task 'data:build'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_snakemake_readme_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nsnakemake --cores 4 all\\nsnakemake --use-conda results/summary.csv\\nsnakemake plots/final.png\\nsnakemake -n\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              { path: "results/summary.csv", text: "metric,value\\n" },
              {
                path: "Snakefile",
                text: [
                  "rule all:",
                  "    input:",
                  "        'results/summary.csv'",
                  "",
                  "rule plot:",
                  "    output:",
                  "        'plots/final.png'",
                  "    shell:",
                  "        'python scripts/plot.py'",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_snakemake_readme_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nsnakemake --cores 4 report\\nsnakemake results/missing.csv\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "Snakefile",
                text: [
                  "rule all:",
                  "    input:",
                  "        'results/summary.csv'",
                  "",
                  "rule build:",
                  "    output:",
                  "        'results/summary.csv'",
                  "    shell:",
                  "        'python scripts/build.py'",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Snakemake target 'report'"));
            assert.ok(evidence.includes("Snakemake target 'results/missing.csv'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_nextflow_profiles_and_entries() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nnextflow run main.nf -profile docker,test -entry align_reads\\nnextflow run nf-core/rnaseq -profile test,docker\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "main.nf",
                text: [
                  "process ALIGN {",
                  "  script:",
                  "  'echo ok'",
                  "}",
                  "",
                  "workflow align_reads {",
                  "  ALIGN()",
                  "}",
                ].join("\\n"),
              },
              {
                path: "nextflow.config",
                text: [
                  "profiles {",
                  "  docker {",
                  "    docker.enabled = true",
                  "  }",
                  "  test {",
                  "    params.test = true",
                  "  }",
                  "}",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_nextflow_profiles_and_entries() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nnextflow run main.nf -profile docker,slurm -entry align_reads\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "main.nf", text: "workflow report { }\\n" },
              {
                path: "nextflow.config",
                text: [
                  "profiles {",
                  "  docker {",
                  "    docker.enabled = true",
                  "  }",
                  "}",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Nextflow profile(s) slurm"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_cromwell_workflow_inputs_and_root() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\njava -jar cromwell.jar run workflows/main.wdl --inputs inputs/demo.json --workflow-root workflows\\ncromwell run https://example.org/workflow.wdl --inputs inputs/remote.json\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "workflows/main.wdl", text: "workflow demo {}\\n" },
              { path: "inputs/demo.json", text: "{}\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_cromwell_workflow_inputs_and_root() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\njava -jar cromwell.jar run workflows/main.wdl --inputs inputs/demo.json --workflow-root imports\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "workflows/main.wdl", text: "workflow demo {}\\n" },
              { path: "inputs/demo.json", text: "{}\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Cromwell workflow root 'imports'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_cwl_workflow_and_job_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ncwltool --outdir results workflows/main.cwl inputs/demo.yml\\ncwl-runner https://example.org/workflow.cwl inputs/remote.yml\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "workflows/main.cwl", text: "cwlVersion: v1.2\\nclass: Workflow\\n" },
              { path: "inputs/demo.yml", text: "{}\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_cwl_workflow_and_job_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ncwltool workflows/main.cwl inputs/demo.yml\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "workflows/main.cwl", text: "cwlVersion: v1.2\\nclass: Workflow\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("CWL job file 'inputs/demo.yml'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_papermill_input_and_parameter_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "papermill --log-output notebooks/input.ipynb reports/output.ipynb -f params/demo.yaml\\npapermill s3://bucket/input.ipynb s3://bucket/output.ipynb\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "notebooks/input.ipynb", text: JSON.stringify({ cells: [], metadata: {}, nbformat: 4, nbformat_minor: 5 }) },
              { path: "params/demo.yaml", text: "alpha: 0.1\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_papermill_parameter_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "papermill notebooks/input.ipynb reports/output.ipynb -f params/demo.yaml\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "notebooks/input.ipynb", text: JSON.stringify({ cells: [], metadata: {}, nbformat: 4, nbformat_minor: 5 }) },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Papermill parameter file(s) params/demo.yaml"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_dvc_readme_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndvc repro train\\ndvc repro dvc.yaml:evaluate\\ndvc pull data/raw\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "dvc.yaml",
                text: [
                  "stages:",
                  "  train:",
                  "    cmd: python train.py",
                  "  evaluate:",
                  "    cmd: python evaluate.py",
                ].join("\\n"),
              },
              { path: "data/raw.dvc", text: "outs:\\n- md5: abc\\n  path: raw\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_dvc_readme_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndvc repro train\\ndvc pull data/raw\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "dvc.yaml",
                text: [
                  "stages:",
                  "  evaluate:",
                  "    cmd: python evaluate.py",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("DVC target(s) train"));
            assert.ok(evidence.includes("DVC target(s) data/raw"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_data_restore_wrappers() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nmake data\\nnpm run fetch-data\\nbash scripts/restore-data.sh\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "Makefile", text: "data:\\n\\tdvc pull data/raw\\n" },
              { path: "package.json", text: JSON.stringify({ scripts: { "fetch-data": "git-lfs pull" } }) },
              { path: "scripts/restore-data.sh", text: "python -m dvc checkout\\ngit lfs fetch\\n" },
              { path: "dvc.yaml", text: "stages: {}\\n" },
              { path: "data/raw.dvc", text: "outs:\\n- md5: abc\\n  path: raw\\n" },
              { path: ".gitattributes", text: "models/*.pt filter=lfs diff=lfs merge=lfs -text\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC018"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_unimplemented_data_restore_wrapper() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nmake data\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "Makefile", text: "train:\\n\\tpython train.py\\n" },
              { path: "data/raw.dvc", text: "outs:\\n- md5: abc\\n  path: raw\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC018").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("DVC metadata"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_quarto_render_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nquarto render paper.qmd --to html\\nquarto render notebooks/demo.ipynb\\nquarto render docs\\nquarto render\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "paper.qmd", text: "---\\ntitle: Demo\\n---\\n\\nReady.\\n" },
              { path: "notebooks/demo.ipynb", text: JSON.stringify({ cells: [], metadata: {}, nbformat: 4, nbformat_minor: 5 }) },
              { path: "docs/index.qmd", text: "---\\ntitle: Docs\\n---\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_quarto_render_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nquarto render paper.qmd --to html\\nquarto render docs\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Quarto render target 'paper.qmd'"));
            assert.ok(evidence.includes("Quarto render target 'docs'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_jupytext_sync_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\njupytext --sync notebooks/demo.ipynb\\njupytext --set-formats ipynb,py:percent --sync notebooks/pair.py\\njupytext --sync --pipe black notebooks/clean.ipynb\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "notebooks/demo.ipynb", text: JSON.stringify({ cells: [], metadata: {}, nbformat: 4, nbformat_minor: 5 }) },
              { path: "notebooks/clean.ipynb", text: JSON.stringify({ cells: [], metadata: {}, nbformat: 4, nbformat_minor: 5 }) },
              { path: "notebooks/pair.py", text: "# %%\\nprint('ready')\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_jupytext_sync_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\njupytext --sync notebooks/demo.ipynb\\njupytext --sync notebooks/pair.py\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Jupytext sync target(s) notebooks/demo.ipynb"));
            assert.ok(evidence.includes("Jupytext sync target(s) notebooks/pair.py"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_kedro_pipeline_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nkedro run --pipeline data_science\\nkedro run --pipelines=data_engineering,reporting\\nkedro run\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "kedro==0.19.9\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "src/demo_project/pipeline_registry.py",
                text: [
                  "def register_pipelines():",
                  "    return {",
                  "        '__default__': None,",
                  "        'data_science': None,",
                  "        'reporting': None,",
                  "    }",
                ].join("\\n"),
              },
              { path: "src/demo_project/pipelines/data_engineering/pipeline.py", text: "def create_pipeline(): pass\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_kedro_pipeline_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nkedro run --pipeline data_science\\nkedro run -p reporting\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "kedro==0.19.9\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "src/demo_project/pipeline_registry.py",
                text: [
                  "def register_pipelines():",
                  "    return {'data_engineering': None}",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Kedro pipeline(s) data_science"));
            assert.ok(evidence.includes("Kedro pipeline(s) reporting"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_prefect_flow_names() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nprefect deployment run train-flow/prod\\nuv run prefect deployment run data-flow/daily\\nprefect deployment run yaml_flow/nightly\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "prefect==3.1.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "flows.py",
                text: [
                  "from prefect import flow",
                  "",
                  "@flow(name='train-flow')",
                  "def train_model():",
                  "    pass",
                  "",
                  "@flow",
                  "def data_flow():",
                  "    pass",
                ].join("\\n"),
              },
              {
                path: "prefect.yaml",
                text: [
                  "deployments:",
                  "  - name: nightly",
                  "    entrypoint: flows.py:yaml_flow",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_prefect_flow_names() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nprefect deployment run train-flow/prod\\nuv run prefect deployment run data-flow/daily\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "prefect==3.1.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "flows.py",
                text: [
                  "from prefect import flow",
                  "",
                  "@flow(name='other-flow')",
                  "def other():",
                  "    pass",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Prefect flow 'train-flow'"));
            assert.ok(evidence.includes("Prefect flow 'data-flow'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_mlflow_entry_points() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nmlflow run . -e train\\nuv run mlflow run experiments/model --entry-point evaluate\\nmlflow run scripts -e train.py\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "mlflow==2.17.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "MLproject",
                text: [
                  "name: demo",
                  "entry_points:",
                  "  train:",
                  "    command: python train.py",
                ].join("\\n"),
              },
              {
                path: "experiments/model/MLproject",
                text: [
                  "entry_points:",
                  "  evaluate:",
                  "    command: python evaluate.py",
                ].join("\\n"),
              },
              { path: "scripts/train.py", text: "print('ready')\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_mlflow_entry_points() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nmlflow run . -e train\\nuv run mlflow run experiments/model --entry-point evaluate\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "mlflow==2.17.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "MLproject",
                text: [
                  "entry_points:",
                  "  score:",
                  "    command: python score.py",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("MLflow entry point 'train'"));
            assert.ok(evidence.includes("MLflow project 'experiments/model'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_dbt_selectors() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndbt run --select orders\\ndbt test -s path:models/marts/customers.sql\\nuv run dbt build --cache-selected-only --models staging.orders,staging.customers --target prod\\ndbt ls --selector nightly\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "dbt-core==1.8.8\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "dbt_project.yml", text: "name: demo_dbt\\n" },
              { path: "models/marts/orders.sql", text: "select 1 as order_id\\n" },
              { path: "models/marts/customers.sql", text: "select 1 as customer_id\\n" },
              { path: "selectors.yml", text: "selectors:\\n  - name: nightly\\n    definition:\\n      method: path\\n      value: models/marts\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_dbt_selectors() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndbt run --select missing_model\\ndbt test -s path:models/marts/missing.sql\\ndbt ls --selector stale\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "dbt-core==1.8.8\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "dbt_project.yml", text: "name: demo_dbt\\n" },
              { path: "models/marts/orders.sql", text: "select 1 as order_id\\n" },
              { path: "selectors.yml", text: "selectors:\\n  - name: nightly\\n    definition:\\n      method: path\\n      value: models/marts\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("dbt selector(s) missing_model"));
            assert.ok(evidence.includes("dbt selector(s) path:models/marts/missing.sql"));
            assert.ok(evidence.includes("dbt selector(s) selector:stale"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_great_expectations_checkpoints() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ngreat_expectations checkpoint run daily\\ngx checkpoint run --checkpoint-name weekly\\nuv run gx checkpoint run --context-root-dir gx nightly\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "great_expectations==0.18.21\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "great_expectations/checkpoints/daily.yml", text: "name: daily\\n" },
              { path: "great_expectations/checkpoints/weekly.yaml", text: "name: weekly_explicit\\n" },
              { path: "gx/checkpoints/nightly.json", text: "{\\"name\\": \\"nightly\\"}\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_great_expectations_checkpoints() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ngreat_expectations checkpoint run missing_checkpoint\\ngx checkpoint run stale\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "great_expectations==0.18.21\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "great_expectations/checkpoints/daily.yml", text: "name: daily\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Great Expectations checkpoint 'missing_checkpoint'"));
            assert.ok(evidence.includes("Great Expectations checkpoint 'stale'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_dagster_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndagster job execute -f definitions.py -j train_model\\ndg launch --job daily_assets --assets target/main/raw_customers,feature_table\\nuv run dagster asset materialize --select target/main/raw_customers\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "dagster==1.9.3\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "definitions.py",
                text: [
                  "from dagster import AssetOut, asset, define_asset_job, job, multi_asset",
                  "",
                  "@job(name='train_model')",
                  "def train_job():",
                  "    pass",
                  "",
                  "daily_assets = define_asset_job('daily_assets')",
                  "",
                  "@asset(key_prefix=['target', 'main'], name='raw_customers')",
                  "def raw_customers_asset():",
                  "    pass",
                  "",
                  "@asset",
                  "def feature_table():",
                  "    pass",
                  "",
                  "@multi_asset(outs={'summary_table': AssetOut()})",
                  "def summaries():",
                  "    pass",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_dagster_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndagster job execute -f definitions.py -j missing_job\\ndg launch --assets missing_asset\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "dagster==1.9.3\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "definitions.py",
                text: [
                  "from dagster import asset, job",
                  "",
                  "@job",
                  "def train_model():",
                  "    pass",
                  "",
                  "@asset",
                  "def raw_customers():",
                  "    pass",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Dagster job(s) missing_job"));
            assert.ok(evidence.includes("asset(s) missing_asset"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_ploomber_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nploomber task --status load_data\\nploomber build --partially train_model\\nuv run ploomber build --entry-point pipeline.yaml --partially imported_task\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "ploomber==0.23.1\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "pipeline.yaml",
                text: [
                  "import_tasks_from:",
                  "  - imported.yaml",
                  "tasks:",
                  "  - source: tasks/load_data.py",
                  "  - source: tasks/train.py",
                  "    name: train_model",
                ].join("\\n"),
              },
              {
                path: "imported.yaml",
                text: [
                  "tasks:",
                  "  - source: tasks/imported.py",
                  "    name: imported_task",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_ploomber_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nploomber task missing_task\\nploomber build --partially stale_task\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "ploomber==0.23.1\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "pipeline.yaml",
                text: [
                  "tasks:",
                  "  - source: tasks/load_data.py",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Ploomber task(s) missing_task"));
            assert.ok(evidence.includes("Ploomber task(s) stale_task"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_luigi_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nluigi --module workflows.tasks TrainModel --local-scheduler --date 2026-01-01\\nuv run luigi --module workflows.tasks experiments.NamespacedTask --scheduler-host localhost\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "luigi==3.5.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "workflows/tasks.py",
                text: [
                  "import luigi",
                  "",
                  "class TrainModel(luigi.Task):",
                  "    pass",
                  "",
                  "class NamespacedTask(luigi.WrapperTask):",
                  "    task_namespace = 'experiments'",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_luigi_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nluigi --module workflows.tasks MissingTask --local-scheduler\\nluigi --module workflows.missing TrainModel --local-scheduler\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "luigi==3.5.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "workflows/tasks.py",
                text: [
                  "import luigi",
                  "",
                  "class TrainModel(luigi.Task):",
                  "    pass",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Luigi task 'MissingTask'"));
            assert.ok(evidence.includes("in module 'workflows.missing'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_meltano_jobs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nmeltano run daily-load\\nuv run meltano --environment=prod run nightly-sync --dry-run\\nmeltano run tap-gitlab target-postgres\\nmeltano job start legacy-backfill\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "meltano==3.8.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "meltano.yml",
                text: [
                  "version: 1",
                  "jobs:",
                  "  - name: daily-load",
                  "    tasks:",
                  "      - tap-gitlab target-postgres",
                  "  - name: nightly-sync",
                  "    tasks:",
                  "      - tap-gitlab target-bigquery",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_meltano_jobs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nmeltano run stale-load\\nmeltano job start missing-backfill\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "meltano==3.8.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "meltano.yml",
                text: [
                  "version: 1",
                  "jobs:",
                  "  - name: daily-load",
                  "    tasks:",
                  "      - tap-gitlab target-postgres",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Meltano job(s) stale-load"));
            assert.ok(!evidence.includes("missing-backfill"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_flyte_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nflyte run --local workflows/train.py train_model --epochs 2\\nuv run pyflyte run --remote workflows/train.py scoring_workflow --name smoke\\npyflyte --config config.yaml run --remote workflows/train.py package_model --image ghcr.io/acme/flyte:latest\\nflyte run deployed-task project.domain.task\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "flytekit==1.13.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "workflows/train.py",
                text: [
                  "from flytekit import task, workflow",
                  "import flyte",
                  "",
                  "env = flyte.TaskEnvironment(name='modeling')",
                  "",
                  "@task",
                  "def train_model(epochs: int = 1) -> str:",
                  "    return 'model'",
                  "",
                  "@workflow",
                  "def scoring_workflow() -> str:",
                  "    return train_model()",
                  "",
                  "@env.task",
                  "async def package_model() -> str:",
                  "    return 'package'",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_flyte_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nflyte run workflows/train.py missing_workflow\\npyflyte run workflows/missing.py train_model\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "flytekit==1.13.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "workflows/train.py",
                text: [
                  "from flytekit import task",
                  "",
                  "@task",
                  "def train_model() -> str:",
                  "    return 'model'",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Flyte workflow/task 'missing_workflow'"));
            assert.ok(evidence.includes("Flyte script 'workflows/missing.py'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_argo_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nargo submit workflows/model.yaml --entrypoint train\\nuv run argo submit --entrypoint=score workflows/model.yaml -p split=test\\nargo submit workflows/default.yaml\\nargo submit --from workflowtemplate/cluster-template\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "workflows/model.yaml",
                text: [
                  "apiVersion: argoproj.io/v1alpha1",
                  "kind: Workflow",
                  "spec:",
                  "  entrypoint: main",
                  "  templates:",
                  "    - name: main",
                  "      steps:",
                  "        - - name: train",
                  "            template: train",
                  "    - name: train",
                  "      container:",
                  "        image: python:3.11",
                  "    - name: score",
                  "      container:",
                  "        image: python:3.11",
                ].join("\\n"),
              },
              {
                path: "workflows/default.yaml",
                text: [
                  "apiVersion: argoproj.io/v1alpha1",
                  "kind: WorkflowTemplate",
                  "spec:",
                  "  entrypoint: run-all",
                  "  templates:",
                  "    - name: run-all",
                  "      container:",
                  "        image: alpine:3.20",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_argo_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nargo submit workflows/model.yaml --entrypoint stale\\nargo submit workflows/missing.yaml --entrypoint train\\nargo submit workflows/no-templates.yaml --entrypoint train\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "workflows/model.yaml",
                text: [
                  "apiVersion: argoproj.io/v1alpha1",
                  "kind: Workflow",
                  "spec:",
                  "  entrypoint: train",
                  "  templates:",
                  "    - name: train",
                  "      container:",
                  "        image: python:3.11",
                ].join("\\n"),
              },
              {
                path: "workflows/no-templates.yaml",
                text: [
                  "apiVersion: argoproj.io/v1alpha1",
                  "kind: Workflow",
                  "spec:",
                  "  entrypoint: train",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Argo entrypoint 'stale'"));
            assert.ok(evidence.includes("Argo workflow file 'workflows/missing.yaml'"));
            assert.ok(evidence.includes("no local template names were found in 'workflows/no-templates.yaml'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_tekton_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ntkn pipeline start build-and-test\\nuv run tkn task start unit-test --param image=python:3.11\\ntkn pipeline start -f tekton/pipeline.yaml\\ntkn task start --filename=tekton/task.yaml unit-test\\ntkn task start --image ghcr.io/acme/remote-task:latest remote-task\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "tekton/pipeline.yaml",
                text: [
                  "apiVersion: tekton.dev/v1",
                  "kind: Pipeline",
                  "metadata:",
                  "  name: build-and-test",
                  "spec:",
                  "  tasks: []",
                ].join("\\n"),
              },
              {
                path: "tekton/task.yaml",
                text: [
                  "apiVersion: tekton.dev/v1",
                  "kind: Task",
                  "metadata:",
                  "  name: unit-test",
                  "spec:",
                  "  steps: []",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_tekton_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ntkn pipeline start stale-pipeline\\ntkn task start missing-task\\ntkn pipeline start -f tekton/missing.yaml\\ntkn task start --filename=tekton/task.yaml wrong-task\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "tekton/pipeline.yaml",
                text: [
                  "apiVersion: tekton.dev/v1",
                  "kind: Pipeline",
                  "metadata:",
                  "  name: build-and-test",
                  "spec:",
                  "  tasks: []",
                ].join("\\n"),
              },
              {
                path: "tekton/task.yaml",
                text: [
                  "apiVersion: tekton.dev/v1",
                  "kind: Task",
                  "metadata:",
                  "  name: unit-test",
                  "spec:",
                  "  steps: []",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Tekton pipeline 'stale-pipeline'"));
            assert.ok(evidence.includes("Tekton task 'missing-task'"));
            assert.ok(evidence.includes("Tekton manifest 'tekton/missing.yaml'"));
            assert.ok(evidence.includes("Tekton task 'wrong-task'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_ray_job_entrypoints() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nray job submit --address http://127.0.0.1:8265 -- python scripts/train.py --epochs 2\\nuv run ray job submit --working-dir . -- uv run python -m demo.jobs.train --smoke\\nray job submit -- bash scripts/train.sh\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "ray==2.40.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "scripts/train.py", text: "print('train')\\n" },
              { path: "demo/__init__.py", text: "" },
              { path: "demo/jobs/__init__.py", text: "" },
              { path: "demo/jobs/train.py", text: "print('module')\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_ray_job_entrypoints() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nray job submit -- python scripts/missing.py\\nray job submit -- python -m demo.jobs.missing\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "ray==2.40.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Ray job script 'scripts/missing.py'"));
            assert.ok(evidence.includes("Ray job module 'demo.jobs.missing'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_dagger_call_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndagger call train-model --source=.\\ndagger -m ./ci call build-image\\nuv run dagger --mod ./ci call lint --json\\ndagger -m github.com/dagger/hello-dagger call hello\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "dagger-io==0.13.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "dagger.json", text: "{\\"name\\": \\"demo\\", \\"sdk\\": \\"python\\", \\"source\\": \\".\\"}\\n" },
              {
                path: "src/demo/main.py",
                text: [
                  "from dagger import function, object_type",
                  "",
                  "@object_type",
                  "class Demo:",
                  "    @function",
                  "    async def train_model(self) -> str:",
                  "        return 'ok'",
                ].join("\\n"),
              },
              { path: "ci/dagger.json", text: "{\\"name\\": \\"ci\\", \\"sdk\\": \\"go\\", \\"source\\": \\".\\"}\\n" },
              {
                path: "ci/main.go",
                text: [
                  "package main",
                  "",
                  "type Ci struct{}",
                  "",
                  "func (m *Ci) BuildImage() string {",
                  "    return \\"image\\"",
                  "}",
                  "",
                  "func (m *Ci) Lint() string {",
                  "    return \\"lint\\"",
                  "}",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_dagger_call_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndagger call train-model\\ndagger -m ./ci call missing-function\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "dagger-io==0.13.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "ci/dagger.json", text: "{\\"name\\": \\"ci\\", \\"sdk\\": \\"go\\", \\"source\\": \\".\\"}\\n" },
              {
                path: "ci/main.go",
                text: [
                  "package main",
                  "",
                  "type Ci struct{}",
                  "",
                  "func (m *Ci) BuildImage() string {",
                  "    return \\"image\\"",
                  "}",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Dagger module '.'"));
            assert.ok(evidence.includes("Dagger function 'missing-function'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_bazel_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nbazel build //src:train //...\\nuv run bazel test --config=ci //tests:unit\\nbazel run --platforms //tools:linux //apps:serve -- --port 8000\\nbazel build @rules_python//python:defs.bzl\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "src/BUILD",
                text: [
                  "py_binary(",
                  "    name = \\"train\\",",
                  "    srcs = [\\"train.py\\"],",
                  ")",
                ].join("\\n"),
              },
              {
                path: "tests/BUILD.bazel",
                text: [
                  "py_test(",
                  "    name = \\"unit\\",",
                  "    srcs = [\\"test_unit.py\\"],",
                  ")",
                ].join("\\n"),
              },
              {
                path: "apps/BUILD",
                text: [
                  "py_binary(",
                  "    name = \\"serve\\",",
                  "    srcs = [\\"serve.py\\"],",
                  ")",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_bazel_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nbazel build //src:missing\\nbazel test //missing:unit\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "src/BUILD",
                text: [
                  "py_binary(",
                  "    name = \\"train\\",",
                  "    srcs = [\\"train.py\\"],",
                  ")",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Bazel target(s) //src:missing"));
            assert.ok(evidence.includes("//missing:unit"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_pants_specs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npants test src/python:: tests:unit\\n./pants run src/python/app.py -- --port 8000\\nuv run pants --changed-since=HEAD lint src/python:lib\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "pants.toml", text: "[GLOBAL]\\npants_version = \\"2.23.0\\"\\n" },
              { path: "requirements.txt", text: "pantsbuild.pants==2.23.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "src/python/BUILD",
                text: [
                  "python_sources(",
                  "    name = \\"lib\\",",
                  ")",
                  "pex_binary(",
                  "    name = \\"app\\",",
                  "    entry_point = \\"app.py\\",",
                  ")",
                ].join("\\n"),
              },
              { path: "src/python/app.py", text: "print('ready')\\n" },
              {
                path: "tests/BUILD",
                text: [
                  "python_tests(",
                  "    name = \\"unit\\",",
                  ")",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_pants_specs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npants test src/python:missing tests:unit\\npants run src/python/missing_app.py\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "pants.toml", text: "[GLOBAL]\\npants_version = \\"2.23.0\\"\\n" },
              { path: "requirements.txt", text: "pantsbuild.pants==2.23.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "src/python/BUILD",
                text: [
                  "python_sources(",
                  "    name = \\"lib\\",",
                  ")",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Pants target spec(s) src/python:missing, tests:unit"));
            assert.ok(evidence.includes("src/python/missing_app.py"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_nix_flake_outputs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nnix flake check\\nnix build .#labcheck .#dockerImage\\nnix run .#cli -- --help\\nuv run nix build path:./nix#tool\\nnix build nixpkgs#hello\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "flake.nix",
                text: [
                  "{",
                  "  outputs = { self, nixpkgs }: {",
                  "    packages.x86_64-linux.default = nixpkgs.legacyPackages.x86_64-linux.hello;",
                  "    packages.x86_64-linux.labcheck = nixpkgs.legacyPackages.x86_64-linux.hello;",
                  "    packages.x86_64-linux.dockerImage = nixpkgs.legacyPackages.x86_64-linux.hello;",
                  "    apps.x86_64-linux.cli = {",
                  "      type = \\"app\\";",
                  "      program = \\"${self.packages.x86_64-linux.labcheck}/bin/labcheck\\";",
                  "    };",
                  "    checks.x86_64-linux.unit = self.packages.x86_64-linux.labcheck;",
                  "  };",
                  "}",
                ].join("\\n"),
              },
              {
                path: "nix/flake.nix",
                text: [
                  "{",
                  "  outputs = { nixpkgs, ... }: {",
                  "    packages.x86_64-linux.tool = nixpkgs.legacyPackages.x86_64-linux.hello;",
                  "  };",
                  "}",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_nix_flake_outputs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nnix build .#missing\\nnix run .#missingApp\\nnix flake check ./nix\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "flake.nix",
                text: [
                  "{",
                  "  outputs = { nixpkgs, ... }: {",
                  "    packages.x86_64-linux.labcheck = nixpkgs.legacyPackages.x86_64-linux.hello;",
                  "    apps.x86_64-linux.cli = {",
                  "      type = \\"app\\";",
                  "      program = \\"${nixpkgs.legacyPackages.x86_64-linux.hello}/bin/hello\\";",
                  "    };",
                  "  };",
                  "}",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Nix flake output(s) .#missing"));
            assert.ok(evidence.includes(".#missingApp"));
            assert.ok(evidence.includes("./nix"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_services() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker compose up -d api worker\\ndocker compose -f compose.dev.yml run --rm api pytest -q\\ndocker compose --profile obs logs -f grafana\\ndocker-compose restart db\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11-slim",
                  "  worker:",
                  "    image: python:3.11-slim",
                  "  grafana:",
                  "    image: grafana/grafana:11.0.0",
                  "    profiles: [obs]",
                  "  db:",
                  "    image: postgres:16",
                  "volumes:",
                  "  db-data:",
                ].join("\\n"),
              },
              {
                path: "compose.dev.yml",
                text: [
                  "services:",
                  "  api:",
                  "    build: .",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_services() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker compose up api worker\\ndocker compose -f compose.dev.yml run api pytest\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11-slim",
                  "volumes:",
                  "  worker:",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose service(s) worker"));
            assert.ok(evidence.includes("Docker Compose file(s) compose.dev.yml"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_env_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker compose --env-file .env.demo up -d\\ndocker compose --env-file config/dev.env run api pytest -q\\ndocker-compose --env-file=.env.local restart db\\ndocker compose --env-file $COMPOSE_ENV up -d\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "  db:",
                  "    image: postgres:16",
                ].join("\\n"),
              },
              { path: ".env.demo", text: "DEBUG=1\\n" },
              { path: "config/dev.env", text: "APP_ENV=dev\\n" },
              { path: ".env.local", text: "APP_ENV=local\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_env_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker compose --env-file .env.demo up -d\\ndocker compose --env-file config/dev.env run api pytest -q\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                ].join("\\n"),
              },
              { path: "config/README.md", text: "env docs\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose env-file(s) .env.demo"));
            assert.ok(evidence.includes("Docker Compose env-file(s) config/dev.env"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_project_dirs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker compose --project-directory deploy up -d\\ndocker compose --project-directory ./ops run api pytest -q\\ndocker-compose --project-directory stacks/dev logs db\\ndocker compose --project-directory $COMPOSE_PROJECT_DIR up -d\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "deploy/compose.yaml",
                text: [
                  "services:",
                  "  web:",
                  "    image: nginx:1.27",
                ].join("\\n"),
              },
              {
                path: "ops/compose.yml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                ].join("\\n"),
              },
              {
                path: "stacks/dev/docker-compose.yml",
                text: [
                  "services:",
                  "  db:",
                  "    image: postgres:16",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_project_dirs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker compose --project-directory missing up -d\\ndocker compose --project-directory deploy run api pytest -q\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "deploy/README.md", text: "compose docs\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose project dir(s) missing"));
            assert.ok(evidence.includes("Docker Compose file(s) deploy/compose.yaml"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_profiles() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker compose --profile obs logs grafana\\ndocker compose --profile gpu run trainer pytest -q\\ndocker-compose --profile=debug --profile qa up worker\\ndocker compose --profile $COMPOSE_PROFILE up -d\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  grafana:",
                  "    image: grafana/grafana:11.0.0",
                  "    profiles: [obs]",
                  "  trainer:",
                  "    image: python:3.11",
                  "    profiles:",
                  "      - gpu",
                  "  worker:",
                  "    image: python:3.11",
                  "    profiles: [\\"debug\\", \\"qa\\"]",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_profiles() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker compose --profile obs logs grafana\\ndocker compose --profile gpu run trainer pytest -q\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  grafana:",
                  "    image: grafana/grafana:11.0.0",
                  "  trainer:",
                  "    image: python:3.11",
                  "    profiles: [cpu]",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose profile(s) obs"));
            assert.ok(evidence.includes("Docker Compose profile(s) gpu"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_volume_sources() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "data/.gitkeep", text: "" },
              { path: "config/settings.yml", text: "debug: true\\n" },
              { path: "logs/.gitkeep", text: "" },
              { path: "shared/.gitkeep", text: "" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    volumes:",
                  "      - ./data:/data",
                  "      - ./config:/config:ro",
                  "      - type: bind",
                  "        source: ./logs",
                  "        target: /logs",
                  "      - db-data:/var/lib/postgresql/data",
                  "      - /tmp/cache:/cache",
                  "      - ${HOST_DATA}:/host-data",
                  "volumes:",
                  "  db-data:",
                ].join("\\n"),
              },
              {
                path: "deploy/compose.yml",
                text: [
                  "services:",
                  "  worker:",
                  "    image: python:3.11",
                  "    volumes:",
                  "      - ../shared:/shared",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC005").map(finding => finding.evidence).join("\\n");
            assert.ok(!evidence.includes("Docker Compose bind source"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_volume_sources() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    volumes:",
                  "      - ./data:/data",
                  "      - ../secrets:/run/secrets",
                  "      - type: bind",
                  "        source: ./logs",
                  "        target: /logs",
                  "      - db-data:/var/lib/postgresql/data",
                  "      - /tmp/cache:/cache",
                  "volumes:",
                  "  db-data:",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC005").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose bind source(s)"));
            assert.ok(evidence.includes("./data"));
            assert.ok(evidence.includes("../secrets"));
            assert.ok(evidence.includes("./logs"));
            assert.ok(!evidence.includes("db-data"));
            assert.ok(!evidence.includes("/tmp/cache"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_build_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up --build.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "Dockerfile", text: "FROM python:3.11-slim\\n" },
              { path: "app/Dockerfile", text: "FROM python:3.11-slim\\n" },
              { path: "services/api/Dockerfile.prod", text: "FROM python:3.11-slim\\n" },
              { path: "services/inline/.gitkeep", text: "" },
              { path: "object/Dockerfile.custom", text: "FROM python:3.11-slim\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  root:",
                  "    build: .",
                  "  api:",
                  "    build: ./app",
                  "  worker:",
                  "    build:",
                  "      context: services/api",
                  "      dockerfile: Dockerfile.prod",
                  "  inline:",
                  "    build:",
                  "      context: services/inline",
                  "      dockerfile_inline: |",
                  "        FROM python:3.11-slim",
                  "  object:",
                  "    build: { context: ./object, dockerfile: Dockerfile.custom }",
                  "  remote:",
                  "    build: https://github.com/example/project.git",
                  "  db:",
                  "    image: postgres:16",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC005").map(finding => finding.evidence).join("\\n");
            assert.ok(!evidence.includes("Docker Compose build"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_build_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up --build.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "services/api/.gitkeep", text: "" },
              { path: "services/default/.gitkeep", text: "" },
              { path: "services/inline/.gitkeep", text: "" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    build: ./missing",
                  "  default:",
                  "    build: services/default",
                  "  worker:",
                  "    build:",
                  "      context: services/api",
                  "      dockerfile: Dockerfile.prod",
                  "  escape:",
                  "    build:",
                  "      context: ../outside",
                  "  inline:",
                  "    build:",
                  "      context: services/inline",
                  "      dockerfile_inline: |",
                  "        FROM python:3.11-slim",
                  "  remote:",
                  "    build: https://github.com/example/project.git",
                  "  db:",
                  "    image: postgres:16",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC005").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose build context(s)"));
            assert.ok(evidence.includes("./missing"));
            assert.ok(evidence.includes("../outside"));
            assert.ok(evidence.includes("Docker Compose Dockerfile(s)"));
            assert.ok(evidence.includes("services/default/Dockerfile"));
            assert.ok(evidence.includes("services/api/Dockerfile.prod"));
            assert.ok(!evidence.includes("services/inline/Dockerfile"));
            assert.ok(!evidence.includes("github.com/example/project"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_depends_on_services() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    depends_on:",
                  "      - db",
                  "      - redis",
                  "  worker:",
                  "    image: python:3.11",
                  "    depends_on: [api, db]",
                  "  dashboard:",
                  "    image: nginx:1.27",
                  "    depends_on:",
                  "      db:",
                  "        condition: service_healthy",
                  "      redis:",
                  "        condition: service_started",
                  "  db:",
                  "    image: postgres:16",
                  "  redis:",
                  "    image: redis:7",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC065").map(finding => finding.evidence).join("\\n");
            assert.equal(evidence, "");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_depends_on_services() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    depends_on:",
                  "      - db",
                  "      - missing-cache",
                  "  worker:",
                  "    image: python:3.11",
                  "    depends_on: [api, stale-db]",
                  "  dashboard:",
                  "    image: nginx:1.27",
                  "    depends_on:",
                  "      redis:",
                  "        condition: service_started",
                  "      missing-queue:",
                  "        condition: service_healthy",
                  "  db:",
                  "    image: postgres:16",
                  "  redis:",
                  "    image: redis:7",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC065").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose depends_on service(s)"));
            assert.ok(evidence.includes("missing-cache"));
            assert.ok(evidence.includes("missing-queue"));
            assert.ok(evidence.includes("stale-db"));
            assert.ok(!evidence.includes("condition"));
            assert.ok(!evidence.includes("service_started"));
            assert.strictEqual(context.findingCategory("LC065"), "onboarding");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_service_networks() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    networks:",
                  "      - backend",
                  "      - default",
                  "  worker:",
                  "    image: python:3.11",
                  "    networks: [backend, external-net]",
                  "  dashboard:",
                  "    image: nginx:1.27",
                  "    networks:",
                  "      frontend:",
                  "        aliases:",
                  "          - web",
                  "      backend:",
                  "        aliases:",
                  "          - api",
                  "networks:",
                  "  backend:",
                  "  frontend:",
                  "  external-net:",
                  "    external: true",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC066").map(finding => finding.evidence).join("\\n");
            assert.equal(evidence, "");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_service_networks() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    networks:",
                  "      - backend",
                  "      - stale-net",
                  "  worker:",
                  "    image: python:3.11",
                  "    networks: [backend, missing-inline]",
                  "  dashboard:",
                  "    image: nginx:1.27",
                  "    networks:",
                  "      frontend:",
                  "        aliases:",
                  "          - web",
                  "      missing-map:",
                  "        aliases:",
                  "          - dash",
                  "      default:",
                  "        aliases:",
                  "          - dashboard",
                  "networks:",
                  "  backend:",
                  "  frontend:",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC066").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose network(s)"));
            assert.ok(evidence.includes("missing-inline"));
            assert.ok(evidence.includes("missing-map"));
            assert.ok(evidence.includes("stale-net"));
            assert.ok(!evidence.includes("aliases"));
            assert.ok(!evidence.includes("default"));
            assert.strictEqual(context.findingCategory("LC066"), "onboarding");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_healthcheck_scripts() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "scripts/healthcheck.sh", text: "#!/usr/bin/env sh\\nexit 0\\n" },
              { path: "scripts/worker_health.py", text: "raise SystemExit(0)\\n" },
              { path: "scripts/check-api.py", text: "raise SystemExit(0)\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    healthcheck:",
                  "      test: [\\"CMD\\", \\"./scripts/healthcheck.sh\\"]",
                  "  worker:",
                  "    image: python:3.11",
                  "    healthcheck:",
                  "      test: [\\"CMD-SHELL\\", \\"python scripts/worker_health.py || exit 1\\"]",
                  "  dashboard:",
                  "    image: python:3.11",
                  "    healthcheck:",
                  "      test:",
                  "        - CMD",
                  "        - scripts/check-api.py",
                  "  db:",
                  "    image: postgres:16",
                  "    healthcheck:",
                  "      test: [\\"CMD\\", \\"pg_isready\\", \\"-U\\", \\"postgres\\"]",
                  "  cache:",
                  "    image: redis:7",
                  "    healthcheck:",
                  "      test: CMD-SHELL curl -f http://localhost:8080/health || exit 1",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC067").map(finding => finding.evidence).join("\\n");
            assert.equal(evidence, "");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_healthcheck_scripts() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "scripts/existing.sh", text: "#!/usr/bin/env sh\\nexit 0\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    healthcheck:",
                  "      test: [\\"CMD\\", \\"./scripts/missing.sh\\"]",
                  "  worker:",
                  "    image: python:3.11",
                  "    healthcheck:",
                  "      test: [\\"CMD-SHELL\\", \\"python scripts/missing_health.py || exit 1\\"]",
                  "  dashboard:",
                  "    image: python:3.11",
                  "    healthcheck:",
                  "      test:",
                  "        - CMD-SHELL",
                  "        - ./scripts/missing-list.sh --flag",
                  "  good:",
                  "    image: python:3.11",
                  "    healthcheck:",
                  "      test: [\\"CMD\\", \\"./scripts/existing.sh\\"]",
                  "  remote:",
                  "    image: python:3.11",
                  "    healthcheck:",
                  "      test: [\\"CMD-SHELL\\", \\"curl -f https://example.com/health || exit 1\\"]",
                  "  db:",
                  "    image: postgres:16",
                  "    healthcheck:",
                  "      test: [\\"CMD\\", \\"/usr/bin/pg_isready\\", \\"-U\\", \\"postgres\\"]",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC067").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose healthcheck script(s)"));
            assert.ok(evidence.includes("./scripts/missing.sh"));
            assert.ok(evidence.includes("scripts/missing_health.py"));
            assert.ok(evidence.includes("./scripts/missing-list.sh"));
            assert.ok(!evidence.includes("./scripts/existing.sh"));
            assert.ok(!evidence.includes("https://example.com"));
            assert.ok(!evidence.includes("/usr/bin/pg_isready"));
            assert.strictEqual(context.findingCategory("LC067"), "onboarding");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_secret_config_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "compose-secrets/db.txt", text: "placeholder\\n" },
              { path: "compose-secrets/api.txt", text: "placeholder\\n" },
              { path: "config/app.yml", text: "debug: false\\n" },
              { path: "config/root.yml", text: "debug: true\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "secrets:",
                  "  db_secret:",
                  "    file: ./compose-secrets/db.txt",
                  "  api_secret: { file: ./compose-secrets/api.txt }",
                  "  external_secret:",
                  "    external: true",
                  "configs:",
                  "  app_config:",
                  "    file: ./config/app.yml",
                  "  root_config: { file: config/root.yml }",
                  "  inline_config:",
                  "    content: |",
                  "      debug: true",
                  "  external_config:",
                  "    external: true",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC068").map(finding => finding.evidence).join("\\n");
            assert.equal(evidence, "");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_secret_config_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "compose-secrets/existing.txt", text: "placeholder\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "secrets:",
                  "  missing_secret:",
                  "    file: ./compose-secrets/missing.txt",
                  "  existing_secret:",
                  "    file: ./compose-secrets/existing.txt",
                  "  external_secret:",
                  "    file: ./compose-secrets/external-only.txt",
                  "    external: true",
                  "  remote_secret:",
                  "    file: https://example.com/secret.txt",
                  "configs:",
                  "  missing_config:",
                  "    file: ./config/missing.yml",
                  "  inline_config:",
                  "    content: |",
                  "      debug: true",
                  "  external_config:",
                  "    external: true",
                  "  image_config:",
                  "    file: /etc/app/config.yml",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC068").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose secret/config file(s)"));
            assert.ok(evidence.includes("./compose-secrets/missing.txt"));
            assert.ok(evidence.includes("./config/missing.yml"));
            assert.ok(!evidence.includes("./compose-secrets/existing.txt"));
            assert.ok(!evidence.includes("external-only.txt"));
            assert.ok(!evidence.includes("https://example.com"));
            assert.ok(!evidence.includes("/etc/app/config.yml"));
            assert.strictEqual(context.findingCategory("LC068"), "onboarding");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_service_env_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: ".env", text: "DEBUG=1\\n" },
              { path: "config/dev.env", text: "APP_ENV=dev\\n" },
              { path: "deploy/worker.env", text: "WORKER_COUNT=2\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    env_file: .env",
                  "  worker:",
                  "    image: python:3.11",
                  "    env_file:",
                  "      - config/dev.env",
                  "      - path: deploy/worker.env",
                  "        required: true",
                  "  dynamic:",
                  "    image: python:3.11",
                  "    env_file: ${COMPOSE_ENV_FILE}",
                  "  absolute:",
                  "    image: python:3.11",
                  "    env_file: /etc/app.env",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC069").map(finding => finding.evidence).join("\\n");
            assert.equal(evidence, "");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_service_env_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: ".env", text: "DEBUG=1\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    env_file: missing.env",
                  "  worker:",
                  "    image: python:3.11",
                  "    env_file:",
                  "      - config/missing.env",
                  "      - path: deploy/missing-worker.env",
                  "        required: false",
                  "      - .env",
                  "  dynamic:",
                  "    image: python:3.11",
                  "    env_file: $COMPOSE_ENV_FILE",
                  "  absolute:",
                  "    image: python:3.11",
                  "    env_file: /etc/app.env",
                  "  remote:",
                  "    image: python:3.11",
                  "    env_file: https://example.com/app.env",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC069").map(finding => finding.evidence).join("\\n");
            const missingItems = evidence.split("Docker Compose service env_file(s) ", 2)[1].split(" are referenced", 1)[0].split(", ");
            assert.ok(evidence.includes("Docker Compose service env_file(s)"));
            assert.ok(evidence.includes("missing.env"));
            assert.ok(evidence.includes("config/missing.env"));
            assert.ok(evidence.includes("deploy/missing-worker.env"));
            assert.ok(!missingItems.includes(".env"));
            assert.ok(!evidence.includes("$COMPOSE_ENV_FILE"));
            assert.ok(!evidence.includes("/etc/app.env"));
            assert.ok(!evidence.includes("https://example.com"));
            assert.strictEqual(context.findingCategory("LC069"), "onboarding");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_extends_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.base.yml",
                text: [
                  "services:",
                  "  base_worker:",
                  "    image: python:3.11",
                  "  base_web:",
                  "    image: nginx:1.27",
                ].join("\\n"),
              },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  base_api:",
                  "    image: python:3.11",
                  "  api:",
                  "    extends: base_api",
                  "  worker:",
                  "    extends:",
                  "      file: compose.base.yml",
                  "      service: base_worker",
                  "  web:",
                  "    extends: { file: compose.base.yml, service: base_web }",
                  "  dynamic:",
                  "    extends:",
                  "      file: ${BASE_COMPOSE_FILE}",
                  "      service: base_api",
                  "  remote:",
                  "    extends:",
                  "      file: https://example.com/compose.yml",
                  "      service: base_api",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC070").map(finding => finding.evidence).join("\\n");
            assert.equal(evidence, "");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_extends_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "compose.base.yml",
                text: [
                  "services:",
                  "  base_worker:",
                  "    image: python:3.11",
                ].join("\\n"),
              },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  base_api:",
                  "    image: python:3.11",
                  "  good:",
                  "    extends: base_api",
                  "  api:",
                  "    extends: missing_base",
                  "  worker:",
                  "    extends:",
                  "      file: missing-compose.yml",
                  "      service: base_worker",
                  "  web:",
                  "    extends: { file: compose.base.yml, service: missing_web }",
                  "  dynamic:",
                  "    extends:",
                  "      file: $BASE_COMPOSE_FILE",
                  "      service: missing_dynamic",
                  "  absolute:",
                  "    extends:",
                  "      file: /etc/compose.yml",
                  "      service: missing_absolute",
                  "  remote:",
                  "    extends:",
                  "      file: https://example.com/compose.yml",
                  "      service: missing_remote",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC070").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose extends file(s)"));
            assert.ok(evidence.includes("missing-compose.yml"));
            assert.ok(evidence.includes("Docker Compose extends service target(s)"));
            assert.ok(evidence.includes("api->missing_base"));
            assert.ok(evidence.includes("web->missing_web in compose.base.yml"));
            assert.ok(!evidence.includes("good->base_api"));
            assert.ok(!evidence.includes("$BASE_COMPOSE_FILE"));
            assert.ok(!evidence.includes("missing_dynamic"));
            assert.ok(!evidence.includes("/etc/compose.yml"));
            assert.ok(!evidence.includes("https://example.com"));
            assert.strictEqual(context.findingCategory("LC070"), "onboarding");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_include_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "compose/common.yml", text: "services:\\n  common:\\n    image: alpine:3.20\\n" },
              { path: "compose/worker.yml", text: "services:\\n  worker:\\n    image: python:3.11\\n" },
              { path: "db.yml", text: "services:\\n  db:\\n    image: postgres:16\\n" },
              { path: "cache.yml", text: "services:\\n  cache:\\n    image: redis:7\\n" },
              { path: "object.yml", text: "services:\\n  object:\\n    image: alpine:3.20\\n" },
              {
                path: "compose.yaml",
                text: [
                  "include:",
                  "  - compose/common.yml",
                  "  - path: compose/worker.yml",
                  "  - { path: db.yml }",
                  "  - path:",
                  "      - cache.yml",
                  "  - ${COMPOSE_INCLUDE_FILE}",
                  "  - https://example.com/compose.yml",
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                ].join("\\n"),
              },
              { path: "objects/compose.yaml", text: "include: { path: ../object.yml }\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC071").map(finding => finding.evidence).join("\\n");
            assert.equal(evidence, "");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_include_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "compose/common.yml", text: "services:\\n  common:\\n    image: alpine:3.20\\n" },
              {
                path: "compose.yaml",
                text: [
                  "include:",
                  "  - compose/common.yml",
                  "  - compose/missing.yml",
                  "  - path: compose/missing-worker.yml",
                  "  - { path: missing-db.yml }",
                  "  - path:",
                  "      - missing-cache.yml",
                  "  - $COMPOSE_INCLUDE_FILE",
                  "  - /etc/compose.yml",
                  "  - https://example.com/compose.yml",
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                ].join("\\n"),
              },
              { path: "objects/compose.yaml", text: "include: { path: ../missing-object.yml }\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC071").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose include file(s)"));
            assert.ok(evidence.includes("compose/missing.yml"));
            assert.ok(evidence.includes("compose/missing-worker.yml"));
            assert.ok(evidence.includes("missing-db.yml"));
            assert.ok(evidence.includes("missing-cache.yml"));
            assert.ok(evidence.includes("../missing-object.yml"));
            assert.ok(!evidence.includes("compose/common.yml"));
            assert.ok(!evidence.includes("$COMPOSE_INCLUDE_FILE"));
            assert.ok(!evidence.includes("/etc/compose.yml"));
            assert.ok(!evidence.includes("https://example.com"));
            assert.strictEqual(context.findingCategory("LC071"), "onboarding");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_service_label_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "labels/api.labels", text: "com.example.role=api\\n" },
              { path: "labels/worker.labels", text: "com.example.role=worker\\n" },
              { path: "labels/common.labels", text: "com.example.team=platform\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    label_file: labels/api.labels",
                  "  worker:",
                  "    image: python:3.11",
                  "    label_file:",
                  "      - labels/worker.labels",
                  "      - labels/common.labels",
                  "  inline:",
                  "    image: python:3.11",
                  "    label_file: [labels/api.labels, labels/common.labels]",
                  "  dynamic:",
                  "    image: python:3.11",
                  "    label_file: ${COMPOSE_LABEL_FILE}",
                  "  absolute:",
                  "    image: python:3.11",
                  "    label_file: /etc/docker/labels",
                  "  remote:",
                  "    image: python:3.11",
                  "    label_file: https://example.com/labels",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC072").map(finding => finding.evidence).join("\\n");
            assert.equal(evidence, "");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_service_label_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "labels/common.labels", text: "com.example.team=platform\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    label_file: labels/missing-api.labels",
                  "  worker:",
                  "    image: python:3.11",
                  "    label_file:",
                  "      - labels/missing-worker.labels",
                  "      - labels/common.labels",
                  "  inline:",
                  "    image: python:3.11",
                  "    label_file: [labels/missing-inline.labels, labels/common.labels]",
                  "  dynamic:",
                  "    image: python:3.11",
                  "    label_file: $COMPOSE_LABEL_FILE",
                  "  absolute:",
                  "    image: python:3.11",
                  "    label_file: /etc/docker/labels",
                  "  remote:",
                  "    image: python:3.11",
                  "    label_file: https://example.com/labels",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC072").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose service label_file(s)"));
            assert.ok(evidence.includes("labels/missing-api.labels"));
            assert.ok(evidence.includes("labels/missing-worker.labels"));
            assert.ok(evidence.includes("labels/missing-inline.labels"));
            assert.ok(!evidence.includes("labels/common.labels"));
            assert.ok(!evidence.includes("$COMPOSE_LABEL_FILE"));
            assert.ok(!evidence.includes("/etc/docker/labels"));
            assert.ok(!evidence.includes("https://example.com"));
            assert.strictEqual(context.findingCategory("LC072"), "onboarding");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_compose_develop_watch_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up --watch.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "src/app.py", text: "print('ready')\\n" },
              { path: "web/index.html", text: "<main>ready</main>\\n" },
              { path: "package.json", text: "{\\"scripts\\":{\\"dev\\":\\"vite\\"}}\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    develop:",
                  "      watch:",
                  "        - action: sync",
                  "          path: src",
                  "          target: /app/src",
                  "        - action: rebuild",
                  "          path: package.json",
                  "        - { action: sync, path: web, target: /app/web }",
                  "  dynamic:",
                  "    image: python:3.11",
                  "    develop:",
                  "      watch:",
                  "        - action: sync",
                  "          path: ${WATCH_PATH}",
                  "          target: /app/dynamic",
                  "  absolute:",
                  "    image: python:3.11",
                  "    develop:",
                  "      watch:",
                  "        - action: sync",
                  "          path: /tmp/project",
                  "          target: /tmp/project",
                  "  remote:",
                  "    image: python:3.11",
                  "    develop:",
                  "      watch:",
                  "        - action: sync",
                  "          path: https://example.com/src",
                  "          target: /app/remote",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC073").map(finding => finding.evidence).join("\\n");
            assert.equal(evidence, "");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_compose_develop_watch_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run with docker compose up --watch.\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "src/app.py", text: "print('ready')\\n" },
              { path: "package.json", text: "{\\"scripts\\":{\\"dev\\":\\"vite\\"}}\\n" },
              {
                path: "compose.yaml",
                text: [
                  "services:",
                  "  api:",
                  "    image: python:3.11",
                  "    develop:",
                  "      watch:",
                  "        - action: sync",
                  "          path: missing-src",
                  "          target: /app/src",
                  "        - action: rebuild",
                  "          path: config/missing.yml",
                  "        - { action: sync, path: missing-web, target: /app/web }",
                  "        - action: rebuild",
                  "          path: package.json",
                  "  dynamic:",
                  "    image: python:3.11",
                  "    develop:",
                  "      watch:",
                  "        - action: sync",
                  "          path: $WATCH_PATH",
                  "          target: /app/dynamic",
                  "  absolute:",
                  "    image: python:3.11",
                  "    develop:",
                  "      watch:",
                  "        - action: sync",
                  "          path: /tmp/project",
                  "          target: /tmp/project",
                  "  remote:",
                  "    image: python:3.11",
                  "    develop:",
                  "      watch:",
                  "        - action: sync",
                  "          path: https://example.com/src",
                  "          target: /app/remote",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC073").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker Compose develop watch path(s)"));
            assert.ok(evidence.includes("missing-src"));
            assert.ok(evidence.includes("config/missing.yml"));
            assert.ok(evidence.includes("missing-web"));
            assert.ok(!evidence.includes("package.json"));
            assert.ok(!evidence.includes("$WATCH_PATH"));
            assert.ok(!evidence.includes("/tmp/project"));
            assert.ok(!evidence.includes("https://example.com"));
            assert.strictEqual(context.findingCategory("LC073"), "onboarding");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_docker_build_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker build --target runtime -t demo .\\ndocker build -f docker/Dockerfile --target=prod .\\ndocker image build --file Dockerfile.worker --target worker .\\ndocker buildx build --platform linux/amd64 --target release .\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "Dockerfile",
                text: [
                  "FROM python:3.11-slim AS base",
                  "FROM base AS runtime",
                  "FROM base AS release",
                ].join("\\n"),
              },
              {
                path: "docker/Dockerfile",
                text: [
                  "FROM python:3.11-slim AS builder",
                  "FROM builder AS prod",
                ].join("\\n"),
              },
              {
                path: "Dockerfile.worker",
                text: "FROM python:3.11-slim AS worker\\n",
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_docker_build_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\ndocker build --target prod .\\ndocker build -f docker/Missingfile --target worker .\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "Dockerfile",
                text: [
                  "FROM python:3.11-slim AS base",
                  "FROM base AS runtime",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Docker build stage 'prod'"));
            assert.ok(evidence.includes("Dockerfile does not define it"));
            assert.ok(evidence.includes("Dockerfile 'docker/Missingfile'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_helm_chart_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nhelm template ./charts/api -f values/dev.yaml\\nhelm install api ./charts/api --namespace demo\\nhelm upgrade api charts/api --install\\nhelm lint charts/api charts/worker\\nuv run helm package ./charts/worker\\nhelm install nginx bitnami/nginx\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "charts/api/Chart.yaml", text: "apiVersion: v2\\nname: api\\nversion: 0.1.0\\n" },
              { path: "charts/worker/Chart.yaml", text: "apiVersion: v2\\nname: worker\\nversion: 0.1.0\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_helm_chart_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nhelm template ./charts/api\\nhelm lint charts/api charts/worker\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Helm chart path(s) ./charts/api"));
            assert.ok(evidence.includes("charts/api, charts/worker"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_kustomize_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nkustomize build overlays/dev\\nkustomize build --enable-helm ./overlays/prod\\nkubectl apply -k overlays/dev\\nkubectl diff --kustomize=overlays/prod\\nkubectl kustomize ./base\\nkubectl apply -f deployment.yaml\\nkubectl apply -k https://github.com/example/repo//overlays/dev\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "overlays/dev/kustomization.yaml", text: "resources: []\\n" },
              { path: "overlays/prod/kustomization.yml", text: "resources: []\\n" },
              { path: "base/Kustomization", text: "resources: []\\n" },
              { path: "deployment.yaml", text: "apiVersion: apps/v1\\nkind: Deployment\\nmetadata:\\n  name: demo\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_kustomize_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nkustomize build overlays/dev\\nkubectl apply -k overlays/missing\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "overlays/dev/README.md", text: "overlay docs\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Kustomize path(s) overlays/dev"));
            assert.ok(evidence.includes("Kustomize path(s) overlays/missing"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_kubernetes_manifest_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nkubectl apply -f manifests/app.yaml\\nkubectl diff --filename deploy/\\nuv run kubectl apply --filename=manifests/db.json\\nkubectl delete -f deploy/api.yaml -f deploy/job.yml\\nkubectl apply -f manifests/app.yaml,deploy/worker.yaml\\nkubectl apply -f https://example.com/app.yaml\\nkubectl apply -f $KUBERNETES_MANIFEST\\nkubectl apply -k overlays/dev\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "manifests/app.yaml", text: "apiVersion: v1\\nkind: Service\\nmetadata:\\n  name: app\\n" },
              { path: "manifests/db.json", text: "{\\"apiVersion\\":\\"v1\\",\\"kind\\":\\"ConfigMap\\",\\"metadata\\":{\\"name\\":\\"db\\"}}\\n" },
              { path: "deploy/api.yaml", text: "apiVersion: v1\\nkind: Service\\nmetadata:\\n  name: api\\n" },
              { path: "deploy/job.yml", text: "apiVersion: batch/v1\\nkind: Job\\nmetadata:\\n  name: job\\n" },
              { path: "deploy/worker.yaml", text: "apiVersion: apps/v1\\nkind: Deployment\\nmetadata:\\n  name: worker\\n" },
              { path: "overlays/dev/kustomization.yaml", text: "resources: []\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_kubernetes_manifest_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nkubectl apply -f manifests/app.yaml\\nkubectl diff --filename deploy/\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "deploy/README.md", text: "deployment docs\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Kubernetes manifest path(s) manifests/app.yaml"));
            assert.ok(evidence.includes("Kubernetes manifest path(s) deploy/"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_terraform_working_dirs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nterraform -chdir=infra plan\\nterraform -chdir deploy apply -auto-approve\\nterraform -chdir=infra fmt -check\\nuv run terraform -chdir=envs/dev validate\\nterraform -chdir=./stack/test test\\nterraform plan -out=tfplan\\nterraform -chdir=https://github.com/example/infra plan\\nterraform -chdir=$TF_DIR plan\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "infra/main.tf", text: "resource \\"null_resource\\" \\"demo\\" {}\\n" },
              { path: "deploy/main.tf.json", text: "{\\"resource\\":{}}\\n" },
              { path: "envs/dev/versions.tf", text: "terraform {}\\n" },
              { path: "stack/test/main.tf", text: "resource \\"null_resource\\" \\"test\\" {}\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_terraform_working_dirs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nterraform -chdir=infra plan\\nterraform -chdir=deploy/missing validate\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "infra/README.md", text: "infra docs\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Terraform working dir(s) infra"));
            assert.ok(evidence.includes("Terraform working dir(s) deploy/missing"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_pulumi_project_dirs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npulumi -C infra preview\\npulumi --cwd deploy up --yes\\npulumi preview --cwd=envs/dev --stack dev\\nuv run pulumi install -C ./stacks/prod\\npulumi -C./stacks/test refresh\\npulumi preview\\npulumi --cwd https://github.com/example/infra preview\\npulumi --cwd $PULUMI_DIR preview\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "infra/Pulumi.yaml", text: "name: infra\\nruntime: yaml\\n" },
              { path: "deploy/Pulumi.yml", text: "name: deploy\\nruntime: yaml\\n" },
              { path: "envs/dev/Pulumi.yaml", text: "name: dev\\nruntime: yaml\\n" },
              { path: "stacks/prod/Pulumi.yaml", text: "name: prod\\nruntime: yaml\\n" },
              { path: "stacks/test/Pulumi.yaml", text: "name: test\\nruntime: yaml\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_pulumi_project_dirs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npulumi -C infra preview\\npulumi --cwd deploy/missing up\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "infra/README.md", text: "infra docs\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Pulumi project dir(s) infra"));
            assert.ok(evidence.includes("Pulumi project dir(s) deploy/missing"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_ansible_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nansible-playbook playbooks/site.yml -i inventory.ini\\nansible-playbook -i inventories/dev playbooks/deploy.yaml --tags app\\nuv run ansible-playbook playbooks/check.yml --inventory=inventories/prod.yml\\nansible-playbook -iinventory/hosts.yml playbooks/site.yml\\nansible-playbook https://example.com/site.yml\\nansible-playbook playbooks/${PLAYBOOK}.yml -i localhost,\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "playbooks/site.yml", text: "- hosts: all\\n  tasks: []\\n" },
              { path: "playbooks/deploy.yaml", text: "- hosts: app\\n  tasks: []\\n" },
              { path: "playbooks/check.yml", text: "- hosts: all\\n  tasks: []\\n" },
              { path: "inventory.ini", text: "[all]\\nlocalhost\\n" },
              { path: "inventories/dev/hosts.ini", text: "[app]\\nlocalhost\\n" },
              { path: "inventories/prod.yml", text: "all:\\n  hosts:\\n    localhost:\\n" },
              { path: "inventory/hosts.yml", text: "all:\\n  hosts:\\n    localhost:\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_ansible_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nansible-playbook playbooks/site.yml -i inventory.ini\\nansible-playbook playbooks/missing.yml --inventory inventories/missing\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "inventory.ini", text: "[all]\\nlocalhost\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("playbook(s) playbooks/site.yml"));
            assert.ok(evidence.includes("playbook(s) playbooks/missing.yml"));
            assert.ok(evidence.includes("inventory path(s) inventories/missing"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_packer_template_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npacker init templates/web.pkr.hcl\\npacker validate -var-file vars/dev.pkrvars.hcl templates/\\nuv run packer build -only amazon-ebs.web images/web.pkr.hcl\\npacker fmt templates images/db.pkr.hcl\\npacker inspect ./templates/web.pkr.hcl\\npacker validate https://example.com/template.pkr.hcl\\npacker build $PACKER_TEMPLATE\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "templates/web.pkr.hcl", text: "source \\"null\\" \\"web\\" {}\\n" },
              { path: "images/web.pkr.hcl", text: "source \\"null\\" \\"web\\" {}\\n" },
              { path: "images/db.pkr.hcl", text: "source \\"null\\" \\"db\\" {}\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_packer_template_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npacker validate templates/\\npacker build images/missing.pkr.hcl\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "templates/README.md", text: "template docs\\n" },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Packer template path(s) templates/"));
            assert.ok(evidence.includes("Packer template path(s) images/missing.pkr.hcl"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_airflow_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nairflow dags test -B local demo_dag\\nairflow tasks test --task-params params.json demo_dag train 2026-01-01\\nuv run airflow tasks run --ship-dag decorated_dag evaluate 2026-01-01\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "apache-airflow==2.10.4\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "dags/demo.py",
                text: [
                  "from airflow import DAG",
                  "from airflow.decorators import dag, task",
                  "from airflow.operators.empty import EmptyOperator",
                  "",
                  "with DAG(dag_id='demo_dag'):",
                  "    train = EmptyOperator(task_id='train')",
                  "",
                  "@dag(dag_id='decorated_dag')",
                  "def decorated():",
                  "    @task(task_id='evaluate')",
                  "    def evaluate_task():",
                  "        return 'ready'",
                  "    evaluate_task()",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_airflow_targets() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nairflow dags test missing_dag\\nairflow tasks test demo_dag missing_task 2026-01-01\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "apache-airflow==2.10.4\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "dags/demo.py",
                text: [
                  "from airflow import DAG",
                  "from airflow.operators.empty import EmptyOperator",
                  "",
                  "with DAG(dag_id='demo_dag'):",
                  "    train = EmptyOperator(task_id='train')",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Airflow DAG 'missing_dag'"));
            assert.ok(evidence.includes("Airflow task 'missing_task'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_metaflow_resume_steps() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npython flow.py resume train_model\\nuv run python flow.py resume --origin-run-id 42 evaluate\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "metaflow==2.12.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "flow.py",
                text: [
                  "from metaflow import FlowSpec, step",
                  "",
                  "class DemoFlow(FlowSpec):",
                  "    @step",
                  "    def start(self):",
                  "        self.next(self.train_model)",
                  "",
                  "    @step",
                  "    def train_model(self):",
                  "        self.next(self.evaluate)",
                  "",
                  "    @step",
                  "    def evaluate(self):",
                  "        self.next(self.end)",
                  "",
                  "    @step",
                  "    def end(self):",
                  "        pass",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_metaflow_resume_steps() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npython flow.py resume train_model\\npython missing_flow.py resume evaluate\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "metaflow==2.12.0\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              {
                path: "flow.py",
                text: [
                  "from metaflow import FlowSpec, step",
                  "",
                  "class DemoFlow(FlowSpec):",
                  "    @step",
                  "    def start(self):",
                  "        self.next(self.end)",
                  "",
                  "    @step",
                  "    def end(self):",
                  "        pass",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Metaflow step 'train_model'"));
            assert.ok(evidence.includes("Metaflow script 'missing_flow.py'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_hatch_and_pdm_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nhatch env create\\nhatch run reproduce\\nhatch run docs:build\\npdm install\\npdm run report\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "pyproject.toml",
                text: [
                  "[project]",
                  'name = "demo-lab"',
                  'version = "0.1.0"',
                  "",
                  "[tool.hatch.envs.default.scripts]",
                  'reproduce = "python scripts/reproduce.py"',
                  "",
                  "[tool.pdm.scripts]",
                  'report = "python scripts/report.py"',
                ].join("\\n"),
              },
              {
                path: "hatch.toml",
                text: [
                  "[envs.docs.scripts]",
                  'build = "mkdocs build"',
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            assert.ok(!report.findings.some(finding => finding.id === "LC013"));
            assert.ok(!report.findings.some(finding => finding.id === "LC021"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_hatch_and_pdm_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\nhatch run reproduce\\nhatch run docs:build\\npdm run report\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "pyproject.toml",
                text: [
                  "[project]",
                  'name = "demo-lab"',
                  'version = "0.1.0"',
                  "",
                  "[tool.hatch.envs.default.scripts]",
                  'lint = "ruff check ."',
                  "",
                  "[tool.pdm.scripts]",
                  'format = "ruff format ."',
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("Hatch script 'reproduce'"));
            assert.ok(evidence.includes("Hatch script 'docs:build'"));
            assert.ok(evidence.includes("PDM script 'report'"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_just_and_doit_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\njust reproduce\\njust r\\ndoit report\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "justfile",
                text: [
                  "alias r := reproduce",
                  "",
                  "reproduce seed='7':",
                  "    python scripts/reproduce.py {{seed}}",
                ].join("\\n"),
              },
              {
                path: "dodo.py",
                text: [
                  "def task_report():",
                  "    return {'actions': ['python scripts/report.py']}",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC008"));
            assert.ok(!report.findings.some(finding => finding.id === "LC013"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_just_and_doit_readme_aliases() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\njust reproduce\\ndoit report\\ndoit list\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "analysis.py", text: "print('ready')\\n" },
              {
                path: "justfile",
                text: [
                  "lint:",
                  "    ruff check .",
                ].join("\\n"),
              },
              {
                path: "dodo.py",
                text: [
                  "def task_lint():",
                  "    return {'actions': ['ruff check .']}",
                ].join("\\n"),
              },
            ], "demo files");

            const evidence = report.findings.filter(finding => finding.id === "LC008").map(finding => finding.evidence).join("\\n");
            assert.ok(evidence.includes("just recipe 'reproduce'"));
            assert.ok(evidence.includes("doit task 'report'"));
            assert.ok(!evidence.includes("doit list"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_prefills_shared_github_url_without_autorun() -> None:
    result = _run_node(
        _browser_harness(
            """
            context.window.location.href = "https://thomasaquinas14.github.io/labcheck/demo.html?repo=owner/repo";
            context.loadGitHubUrlFromPageParams();

            const input = context.document.getElementById("github-url-input");
            const status = context.document.getElementById("github-status");

            assert.strictEqual(input.value, "https://github.com/owner/repo");
            assert.ok(status.textContent.includes("Loaded a shareable demo link for github.com/owner/repo"));
            assert.ok(status.textContent.includes("Press Audit GitHub URL"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_reports_actionable_github_fetch_errors() -> None:
    result = _run_node(
        _browser_harness(
            """
            function jsonResponse(payload) {
              return { ok: true, status: 200, json: async () => payload };
            }
            async function rejectionMessage(promise) {
              try {
                await promise;
              } catch (error) {
                return error.message;
              }
              throw new Error("expected rejection");
            }

            assert.strictEqual(
              await rejectionMessage(context.fetchPublicGitHubRepo("not a github url")),
              "Enter a public GitHub repository URL like https://github.com/owner/repo.",
            );

            context.fetch = async () => ({ ok: false, status: 403, json: async () => ({}) });
            assert.strictEqual(
              await rejectionMessage(context.fetchGitHubJson("https://api.github.com/rate-limited")),
              "GitHub rate limited this browser session. Try again later or use the CLI for the full audit.",
            );

            context.fetch = async () => ({ ok: false, status: 404, json: async () => ({}) });
            assert.strictEqual(
              await rejectionMessage(context.fetchGitHubJson("https://api.github.com/missing")),
              "Could not find that public GitHub repository or file.",
            );

            context.fetch = async (url) => {
              const raw = String(url);
              if (raw.endsWith("/repos/owner/repo")) {
                return jsonResponse({ default_branch: "main" });
              }
              if (raw.endsWith("/repos/owner/repo/git/trees/main?recursive=1")) {
                return jsonResponse({ truncated: true, tree: [] });
              }
              throw new Error(`unexpected URL ${raw}`);
            };
            assert.strictEqual(
              await rejectionMessage(context.fetchPublicGitHubRepo("https://github.com/owner/repo")),
              "GitHub returned a truncated tree for this large repo. Use the CLI for a full public-repo audit.",
            );
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_renders_browser_issue_draft() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = {
              label: "github.com/owner/repo",
              overall: 42,
              filesCount: 4,
              notebookCount: 1,
              pythonFiles: 2,
              severityCounts: { high: 1, medium: 1, low: 0 },
              scores: { environment: 60, determinism: 30, artifacts: 35, portability: 90, onboarding: 70 },
              findings: [
                {
                  id: "LC005",
                  title: "Referenced input artifact missing from repo",
                  severity: "high",
                  file: "notebooks/train.ipynb",
                  evidence: "Reads 'data/train.csv', but that path is not present.",
                  why: "A new user may not be able to run the workflow because required inputs are missing.",
                  fix: "Commit the artifact, document how to obtain it, or make the input contract explicit.",
                },
                {
                  id: "LC021",
                  title: "Dependency setup step is undocumented",
                  severity: "medium",
                  file: "README.md",
                  evidence: "requirements.txt exists, but no install command was found.",
                  why: "A README can show what to run and still fail handoff if dependencies are never installed.",
                  fix: "Add a setup command such as python -m pip install -r requirements.txt.",
                },
              ],
            };

            const draft = context.toIssueDraft(report);
            assert.ok(draft.includes("# labcheck Browser Issue Draft"));
            assert.ok(draft.includes("Suggested title: Reproducibility handoff gaps in `github.com/owner/repo`"));
            assert.ok(draft.includes("This is not a scientific-validity judgment"));
            assert.ok(draft.includes("browser demo does not execute project code"));
            assert.ok(draft.includes("`LC005` - Referenced input artifact missing from repo"));
            assert.ok(draft.includes("First evidence: `notebooks/train.ipynb`"));
            assert.ok(draft.includes("labcheck scan <repo> --format markdown"));
            assert.ok(draft.includes("No upload, API key, or hosted backend was used"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_renders_scorecard_review_boundary() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = {
              label: "github.com/owner/repo",
              overall: 42,
              filesCount: 4,
              notebookCount: 1,
              pythonFiles: 2,
              severityCounts: { high: 1, medium: 1, low: 0 },
              scores: { environment: 60, determinism: 30, artifacts: 35, portability: 90, onboarding: 70 },
              findings: [
                {
                  id: "LC005",
                  title: "Referenced input artifact missing from repo",
                  severity: "high",
                  file: "notebooks/train.ipynb",
                  evidence: "Reads 'data/train.csv', but that path is not present.",
                  why: "A new user may not be able to run the workflow because required inputs are missing.",
                  fix: "Commit the artifact, document how to obtain it, or make the input contract explicit.",
                },
              ],
            };

            const scorecard = context.toScorecard(report);
            assert.ok(scorecard.includes("# labcheck Browser Scorecard"));
            assert.ok(scorecard.includes("## Review Boundary"));
            assert.ok(scorecard.includes("static, no-key first-pass audit"));
            assert.ok(scorecard.includes("does not execute the project code by default"));
            assert.ok(scorecard.includes("does not prove scientific validity"));
            assert.ok(scorecard.includes("## Top Risks"));
            assert.ok(scorecard.includes("## Understand Finding Codes"));
            assert.ok(scorecard.includes("`LC005` Referenced input artifact missing from repo"));
            assert.ok(scorecard.includes("A new user may not be able to run the workflow"));
            assert.ok(scorecard.includes("Suggested fix: Commit the artifact"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_renders_markdown_finding_code_explanations() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = {
              label: "github.com/owner/repo",
              overall: 42,
              filesCount: 4,
              notebookCount: 1,
              pythonFiles: 2,
              graphEdges: [],
              severityCounts: { high: 1, medium: 1, low: 0 },
              scores: { environment: 60, determinism: 30, artifacts: 35, portability: 90, onboarding: 70 },
              findings: [
                {
                  id: "LC005",
                  title: "Referenced input artifact missing from repo",
                  severity: "high",
                  file: "notebooks/train.ipynb",
                  evidence: "Reads 'data/train.csv', but that path is not present.",
                  why: "A new user may not be able to run the workflow because required inputs are missing.",
                  fix: "Commit the artifact, document how to obtain it, or make the input contract explicit.",
                },
              ],
            };

            const markdown = context.toMarkdown(report);
            assert.ok(markdown.includes("# labcheck browser audit"));
            assert.ok(markdown.includes("## Review Boundary"));
            assert.ok(markdown.includes("does not upload source files to a hosted backend"));
            assert.ok(markdown.includes("## Top Risks"));
            assert.ok(markdown.includes("## Understand Finding Codes"));
            assert.ok(markdown.includes("## Next Steps"));
            assert.ok(markdown.includes("Download the CSV findings table"));
            assert.ok(markdown.includes("`LC005` Referenced input artifact missing from repo"));
            assert.ok(markdown.includes("A new user may not be able to run the workflow"));
            assert.ok(markdown.includes("Suggested fix: Commit the artifact"));
            assert.ok(markdown.includes("## Findings"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_renders_csv_findings_export() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = {
              label: "github.com/owner/repo",
              overall: 42,
              filesCount: 4,
              notebookCount: 1,
              pythonFiles: 2,
              graphEdges: [],
              severityCounts: { high: 1, medium: 1, low: 0 },
              scores: { environment: 60, determinism: 30, artifacts: 35, portability: 90, onboarding: 70 },
              findings: [
                {
                  id: "LC005",
                  title: "Referenced input artifact missing from repo",
                  severity: "high",
                  file: "notebooks/train.ipynb",
                  evidence: "Reads \\"data/train.csv\\",\\nthen fails.",
                  why: "A new user may not be able to run the workflow because required inputs are missing.",
                  fix: "Commit the artifact, document how to obtain it, or make the input contract explicit.",
                },
              ],
            };

            const csv = context.toCsv(report);
            assert.ok(csv.startsWith("target,overall_score,status,owner,suggested_owner,check_id,title,severity,category,file_path,evidence,why_it_matters,suggested_fix\\n"));
            assert.ok(csv.includes("github.com/owner/repo,42,,,data/artifact owner,LC005"));
            assert.ok(csv.includes(",high,artifacts,notebooks/train.ipynb,"));
            assert.ok(csv.includes("\\"Reads \\"\\"data/train.csv\\"\\",\\nthen fails.\\""));
            assert.ok(csv.endsWith("\\n"));
            assert.strictEqual(context.findingCategory("LC021"), "onboarding");
            assert.strictEqual(context.findingCategory("LC062"), "onboarding");
            assert.strictEqual(context.suggestedOwnerForCategory("onboarding"), "docs/CI owner");
            assert.strictEqual(context.findingCategory("LC999"), "unknown");
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_markdown_links_to_missing_local_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "README.md",
                text: [
                  "# Demo",
                  "",
                  "[Existing guide](docs/guide.md)",
                  "[Missing notebook](notebooks/missing.ipynb)",
                  "![Missing figure](figures/result.png)",
                  "[External](https://example.com)",
                  "[Anchor](#usage)",
                  "```markdown",
                  "[Example-only missing link](docs/example-only.md)",
                  "```",
                ].join("\\n"),
              },
              { path: "docs/guide.md", text: "[Back](../README.md)\\n[Missing policy](policy.md)\\n" },
            ], "demo files");

            const findings = report.findings.filter(finding => finding.id === "LC062");
            assert.strictEqual(findings.length, 3);
            assert.ok(findings.some(finding => finding.file === "README.md" && finding.evidence.includes("notebooks/missing.ipynb")));
            assert.ok(findings.some(finding => finding.file === "README.md" && finding.evidence.includes("figures/result.png")));
            assert.ok(findings.some(finding => finding.file === "docs/guide.md" && finding.evidence.includes("policy.md")));
            assert.ok(!findings.some(finding => finding.evidence.includes("example.com")));
            assert.ok(!findings.some(finding => finding.evidence.includes("example-only.md")));
            assert.ok(report.scores.onboarding < 100);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_missing_reuse_metadata() -> None:
    result = _run_node(
        _browser_harness(
            """
            const notebook = {
              cells: [{ cell_type: "code", execution_count: 1, metadata: {}, outputs: [], source: ["x = 1\\n"] }],
              metadata: { kernelspec: { name: "python3" }, language_info: { name: "python" } },
              nbformat: 4,
              nbformat_minor: 5,
            };
            const report = context.analyzeFileSet([
              { path: "README.md", text: "Run the notebook:\\n\\n```bash\\njupyter notebook analysis.ipynb\\n```\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "analysis.ipynb", text: JSON.stringify(notebook) },
            ], "demo files");

            const ids = report.findings.map(finding => finding.id);
            assert.ok(ids.includes("LC063"));
            assert.ok(ids.includes("LC064"));
            assert.strictEqual(context.findingCategory("LC063"), "onboarding");
            assert.strictEqual(context.findingCategory("LC064"), "onboarding");
            assert.ok(report.findings.some(finding => finding.id === "LC063" && finding.evidence.includes("LICENSE/COPYING")));
            assert.ok(report.findings.some(finding => finding.id === "LC064" && finding.evidence.includes("CITATION.cff")));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_reuse_metadata() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "README.md",
                text: [
                  "# Demo research repo",
                  "",
                  "Run the experiment:",
                  "",
                  "```bash",
                  "python analysis.py",
                  "```",
                  "",
                  "## Citation",
                  "",
                  "Please cite this repository if it helps your research.",
                ].join("\\n"),
              },
              { path: "analysis.py", text: "print('ready')\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "LICENSE", text: "MIT License\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC063"));
            assert.ok(!report.findings.some(finding => finding.id === "LC064"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_conda_pip_requirement_includes() -> None:
    result = _run_node(
        _browser_harness(
            """
            const files = [
              {
                path: "environment.yml",
                text: [
                  "name: demo",
                  "dependencies:",
                  "  - python=3.11",
                  "  - pip:",
                  "    - -r requirements/pip.txt",
                  "    - --constraint constraints.txt",
                  "    - -r https://example.com/requirements.txt",
                ].join("\\n"),
              },
              { path: "requirements/pip.txt", text: "pandas==2.2.2\\n-r nested.txt\\n" },
            ];
            const repoPaths = new Set(files.map(file => context.normalizeRepoPath(file.path)));
            const findings = context.findMissingRequirementIncludes(files, repoPaths);

            assert.strictEqual(findings.length, 2);
            assert.strictEqual(
              JSON.stringify(findings.map(finding => [finding.file, finding.id])),
              JSON.stringify([["environment.yml", "LC023"], ["requirements/pip.txt", "LC023"]]),
            );
            assert.ok(findings[0].evidence.includes("constraints.txt"));
            assert.ok(findings[0].why.includes("Conda pip include"));
            assert.ok(findings[1].evidence.includes("nested.txt"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_follows_conda_pip_requirement_graph() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "environment.yml",
                text: [
                  "dependencies:",
                  "  - python=3.11",
                  "  - pip:",
                  "    - -r deps/pip.txt",
                ].join("\\n"),
              },
              {
                path: "deps/pip.txt",
                text: [
                  "pandas",
                  "scikit-learn==1.5.0",
                  "-e ../missing-local-lib",
                  "git+https://github.com/example/research-utils.git@main#egg=research-utils",
                ].join("\\n"),
              },
              { path: "analysis.py", text: "import pandas as pd\\nfrom sklearn.model_selection import train_test_split\\n" },
            ], "demo files");

            const ids = report.findings.map(finding => finding.id);
            assert.ok(ids.includes("LC004"));
            assert.ok(ids.includes("LC027"));
            assert.ok(ids.includes("LC043"));
            assert.ok(!report.findings.some(finding => finding.id === "LC028" && finding.evidence.includes("scikit-learn")));
            assert.ok(report.findings.some(finding => finding.id === "LC004" && finding.file === "deps/pip.txt"));
            assert.ok(report.findings.some(finding => finding.id === "LC027" && finding.file === "deps/pip.txt"));
            assert.ok(report.findings.some(finding => finding.id === "LC043" && finding.file === "deps/pip.txt"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_direct_conda_pip_vcs_and_local_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "environment.yml",
                text: [
                  "dependencies:",
                  "  - python=3.11",
                  "  - pip:",
                  "    - git+https://github.com/example/research-utils.git@main#egg=research-utils",
                  "    - -e ../missing-local-lib",
                ].join("\\n"),
              },
              { path: "analysis.py", text: "print('ready')\\n" },
            ], "demo files");

            assert.ok(report.findings.some(finding => finding.id === "LC043" && finding.file === "environment.yml"));
            assert.ok(report.findings.some(finding => finding.id === "LC027" && finding.file === "environment.yml" && finding.evidence.includes("../missing-local-lib")));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_working_directory_changes() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npython -m pip install -r requirements.txt\\npython analysis.py\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              {
                path: "analysis.py",
                text: [
                  "import os as operating_system",
                  "from os import chdir as cd",
                  "operating_system.chdir('notebooks')",
                  "cd('../data')",
                ].join("\\n"),
              },
              {
                path: "notebooks/analysis.ipynb",
                text: JSON.stringify({
                  cells: [
                    { cell_type: "code", execution_count: 1, source: "%cd notebooks\\nprint('ready')\\n" },
                  ],
                  metadata: { kernelspec: { name: "python3" }, language_info: { name: "python" } },
                }),
              },
            ], "demo files");

            const cwdFindings = report.findings.filter(finding => finding.id === "LC051");
            assert.strictEqual(cwdFindings.length, 2);
            assert.ok(cwdFindings.some(finding => finding.file === "analysis.py" && finding.evidence.includes("operating_system.chdir")));
            assert.ok(cwdFindings.some(finding => finding.file === "analysis.py" && finding.evidence.includes("cd(...)")));
            assert.ok(cwdFindings.some(finding => finding.file === "notebooks/analysis.ipynb" && finding.evidence.includes("%cd notebooks")));
            assert.strictEqual(report.scores.portability, 60);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_inline_command_missing_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npython -m pip install -r requirements.txt\\npython analysis.py\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "LICENSE", text: "MIT\\n" },
              { path: "CITATION.cff", text: "cff-version: 1.2.0\\ntitle: Demo files\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              {
                path: "analysis.py",
                text: [
                  "import os",
                  "import subprocess",
                  "subprocess.run(['python', 'scripts/build_features.py'])",
                  "os.system('bash scripts/export.sh')",
                ].join("\\n"),
              },
              {
                path: "notebooks/analysis.ipynb",
                text: JSON.stringify({
                  cells: [
                    {
                      cell_type: "code",
                      execution_count: 1,
                      source: [
                        "%run scripts/preprocess.py",
                        "!python scripts/train.py --epochs 1",
                        "%%bash",
                        "python scripts/from_bash_cell.py",
                      ].join("\\n"),
                    },
                  ],
                  metadata: { kernelspec: { name: "python3" }, language_info: { name: "python" } },
                }),
              },
            ], "demo files");

            const commandFindings = report.findings.filter(finding => finding.id === "LC052");
            assert.strictEqual(commandFindings.length, 2);
            assert.ok(commandFindings.some(finding => finding.file === "analysis.py" && finding.evidence.includes("scripts/build_features.py")));
            assert.ok(commandFindings.some(finding => finding.file === "analysis.py" && finding.evidence.includes("scripts/export.sh")));
            assert.ok(commandFindings.some(finding => finding.file === "notebooks/analysis.ipynb" && finding.evidence.includes("scripts/preprocess.py")));
            assert.ok(commandFindings.some(finding => finding.file === "notebooks/analysis.ipynb" && finding.evidence.includes("scripts/train.py")));
            assert.ok(commandFindings.some(finding => finding.file === "notebooks/analysis.ipynb" && finding.evidence.includes("scripts/from_bash_cell.py")));
            assert.strictEqual(report.scores.onboarding, 64);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_existing_inline_command_paths() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npython analysis.py\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: "scripts/preprocess.py", text: "print('ready')\\n" },
              { path: "scripts/setup.sh", text: "echo ready\\n" },
              {
                path: "notebooks/analysis.ipynb",
                text: JSON.stringify({
                  cells: [
                    { cell_type: "code", execution_count: 1, source: "%run ../scripts/preprocess.py\\n!bash ../scripts/setup.sh\\n" },
                  ],
                  metadata: { kernelspec: { name: "python3" }, language_info: { name: "python" } },
                }),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC052"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_gitignored_input_artifacts() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npython -m pip install -r requirements.txt\\npython analysis.py\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: ".gitignore", text: "data/\\n" },
              { path: "data/train.csv", text: "value\\n1\\n" },
              { path: "data/raw/batch.csv", text: "value\\n1\\n" },
              {
                path: "analysis.py",
                text: [
                  "import pandas as pd",
                  "from pathlib import Path",
                  "df = pd.read_csv('data/train.csv')",
                  "files = list(Path('data/raw').glob('*.csv'))",
                ].join("\\n"),
              },
            ], "demo files");

            const ignoredFindings = report.findings.filter(finding => finding.id === "LC053");
            assert.strictEqual(ignoredFindings.length, 2);
            assert.ok(ignoredFindings.some(finding => finding.evidence.includes("data/train.csv")));
            assert.ok(ignoredFindings.some(finding => finding.evidence.includes("data/raw")));
            assert.ok(!report.findings.some(finding => finding.id === "LC005"));
            assert.strictEqual(report.scores.artifacts, 52);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_gitignore_unignored_exception() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npython -m pip install -r requirements.txt\\npython analysis.py\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: ".gitignore", text: "data/*\\n!data/fixture.csv\\n" },
              { path: "data/fixture.csv", text: "value\\n1\\n" },
              { path: "analysis.py", text: "import pandas as pd\\ndf = pd.read_csv('data/fixture.csv')\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC053"));
            assert.ok(!report.findings.some(finding => finding.id === "LC005"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_negated_file_below_ignored_parent() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: "README.md", text: "```bash\\npython -m pip install -r requirements.txt\\npython analysis.py\\n```\\n" },
              { path: ".python-version", text: "3.11\\n" },
              { path: "requirements.txt", text: "pandas==2.2.2\\n" },
              { path: ".gitignore", text: "data/\\n!data/fixture.csv\\n" },
              { path: "data/fixture.csv", text: "value\\n1\\n" },
              { path: "analysis.py", text: "import pandas as pd\\ndf = pd.read_csv('data/fixture.csv')\\n" },
            ], "demo files");

            const ignoredFindings = report.findings.filter(finding => finding.id === "LC053");
            assert.strictEqual(ignoredFindings.length, 1);
            assert.ok(ignoredFindings[0].evidence.includes("data/fixture.csv"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_hardcoded_secret_and_masks_value() -> None:
    result = _run_node(
        _browser_harness(
            """
            const secret = "sk-proj-" + "A".repeat(28);
            const report = context.analyzeFileSet([
              { path: ".env", text: `OPENAI_API_KEY=${secret}\\n` },
            ], "demo files");

            const secretFindings = report.findings.filter(finding => finding.id === "LC054");
            assert.strictEqual(secretFindings.length, 1);
            assert.ok(secretFindings[0].evidence.includes("OPENAI_API_KEY"));
            assert.ok(secretFindings[0].evidence.includes("sk-p...AAAA"));
            assert.ok(!secretFindings[0].evidence.includes(secret));
            assert.strictEqual(report.scores.onboarding, 82);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_ignores_secret_placeholders() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              { path: ".env.example", text: "OPENAI_API_KEY=your_api_key\\n" },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC054"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_private_key_marker() -> None:
    result = _run_node(
        _browser_harness(
            """
            const marker = "-----BEGIN " + "PRIVATE KEY-----";
            const report = context.analyzeFileSet([
              { path: "service-account.key", text: `${marker}\\nredacted\\n` },
            ], "demo files");

            const secretFindings = report.findings.filter(finding => finding.id === "LC054");
            assert.strictEqual(secretFindings.length, 1);
            assert.ok(secretFindings[0].evidence.includes("private key block"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_current_time_usage() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "analysis.py",
                text: [
                  "from datetime import date",
                  "cutoff = date.today()",
                  "recent = df[df['created_at'] >= cutoff]",
                ].join("\\n"),
              },
            ], "demo files");

            const timeFindings = report.findings.filter(finding => finding.id === "LC055");
            assert.strictEqual(timeFindings.length, 1);
            assert.ok(timeFindings[0].evidence.includes("date.today"));
            assert.strictEqual(report.scores.determinism, 72);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_ignores_current_time_logging_and_timestamped_outputs() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "analysis.py",
                text: [
                  "from datetime import datetime",
                  "print(datetime.now())",
                  "stamp = datetime.now().strftime('%Y%m%d')",
                  "df.to_csv(f'outputs/report_{stamp}.csv')",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(report.findings.some(finding => finding.id === "LC037"));
            assert.ok(!report.findings.some(finding => finding.id === "LC055"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_set_derived_order() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "analysis.py",
                text: [
                  "labels = list(set(raw_labels))",
                  "encoded = [label for label in set(raw_labels)]",
                ].join("\\n"),
              },
            ], "demo files");

            const setFindings = report.findings.filter(finding => finding.id === "LC056");
            assert.strictEqual(setFindings.length, 2);
            assert.ok(setFindings[0].evidence.includes("list(set(raw_labels))"));
            assert.strictEqual(report.scores.determinism, 44);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_sorted_set_order() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "analysis.py",
                text: [
                  "labels = sorted(set(raw_labels))",
                  "ordered = list(dict.fromkeys(raw_labels))",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC056"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_python_hash_usage() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "analysis.py",
                text: [
                  "bucket = hash(user_id) % 10",
                  "split = 'test' if bucket == 0 else 'train'",
                ].join("\\n"),
              },
            ], "demo files");

            const hashFindings = report.findings.filter(finding => finding.id === "LC057");
            assert.strictEqual(hashFindings.length, 1);
            assert.ok(hashFindings[0].evidence.includes("hash(user_id)"));
            assert.strictEqual(report.scores.determinism, 72);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_hashlib_and_dunder_hash() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "analysis.py",
                text: [
                  "import hashlib",
                  "stable = hashlib.sha256(user_id.encode()).hexdigest()",
                  "class Label:",
                  "    def __hash__(self):",
                  "        return hash((self.name, self.version))",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC057"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_pytorch_deterministic_backend() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "train.py",
                text: [
                  "import torch",
                  "torch.backends.cudnn.benchmark = True",
                  "torch.use_deterministic_algorithms(False)",
                ].join("\\n"),
              },
            ], "demo files");

            const backendFindings = report.findings.filter(finding => finding.id === "LC058");
            assert.strictEqual(backendFindings.length, 1);
            assert.ok(backendFindings[0].evidence.includes("torch.backends.cudnn.benchmark = True"));
            assert.ok(backendFindings[0].evidence.includes("torch.use_deterministic_algorithms(False)"));
            assert.strictEqual(report.scores.determinism, 72);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_pytorch_deterministic_backend_settings() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "train.py",
                text: [
                  "import torch",
                  "torch.backends.cudnn.benchmark = False",
                  "torch.backends.cudnn.deterministic = True",
                  "torch.use_deterministic_algorithms(True)",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC058"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_pytorch_worker_seed_gap() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "train.py",
                text: [
                  "from torch.utils.data import DataLoader",
                  "loader = DataLoader(dataset, batch_size=32, num_workers=4)",
                ].join("\\n"),
              },
            ], "demo files");

            const workerFindings = report.findings.filter(finding => finding.id === "LC059");
            assert.strictEqual(workerFindings.length, 1);
            assert.ok(workerFindings[0].evidence.includes("DataLoader(..., num_workers>0)"));
            assert.strictEqual(report.scores.determinism, 72);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_pytorch_worker_seed_hook() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "train.py",
                text: [
                  "from torch.utils.data import DataLoader",
                  "def seed_worker(worker_id):",
                  "    pass",
                  "loader = DataLoader(dataset, batch_size=32, num_workers=4, worker_init_fn=seed_worker)",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC059"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_optuna_sampler_seed_gap() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "tune.py",
                text: [
                  "import optuna",
                  "study = optuna.create_study(direction='maximize')",
                ].join("\\n"),
              },
            ], "demo files");

            const optunaFindings = report.findings.filter(finding => finding.id === "LC060");
            assert.strictEqual(optunaFindings.length, 1);
            assert.ok(optunaFindings[0].evidence.includes("create_study"));
            assert.strictEqual(report.scores.determinism, 72);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_seeded_optuna_sampler() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "tune.py",
                text: [
                  "import optuna",
                  "sampler = optuna.samplers.TPESampler(seed=42)",
                  "study = optuna.create_study(direction='maximize', sampler=sampler)",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC060"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_flags_jax_prng_key_reuse() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "train_jax.py",
                text: [
                  "import jax",
                  "key = jax.random.PRNGKey(0)",
                  "a = jax.random.normal(key, (4,))",
                  "b = jax.random.uniform(key, (4,))",
                ].join("\\n"),
              },
            ], "demo files");

            const jaxFindings = report.findings.filter(finding => finding.id === "LC061");
            assert.strictEqual(jaxFindings.length, 1);
            assert.ok(jaxFindings[0].evidence.includes("uniform"));
            assert.strictEqual(report.scores.determinism, 72);
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_accepts_split_jax_prng_keys() -> None:
    result = _run_node(
        _browser_harness(
            """
            const report = context.analyzeFileSet([
              {
                path: "train_jax.py",
                text: [
                  "from jax import random as jr",
                  "key = jr.PRNGKey(0)",
                  "key, subkey = jr.split(key)",
                  "a = jr.normal(subkey, (4,))",
                  "key, subkey = jr.split(key)",
                  "b = jr.uniform(subkey, (4,))",
                ].join("\\n"),
              },
            ], "demo files");

            assert.ok(!report.findings.some(finding => finding.id === "LC061"));
            """
        )
    )

    assert result.returncode == 0, result.stderr


def test_browser_demo_runtime_fetches_bounded_public_github_files() -> None:
    result = _run_node(
        _browser_harness(
            """
            function jsonResponse(payload) {
              return { ok: true, status: 200, json: async () => payload };
            }
            const blobs = new Map([
              ["blob-readme", "# Demo\\n"],
              ["blob-ci", "jobs:\\n  test:\\n    steps:\\n      - run: pytest\\n"],
              ["blob-notebook", JSON.stringify({ cells: [], metadata: {} })],
              ["blob-python", "print('ready')\\n"],
              ["blob-doc", "notes\\n"],
            ]);
            context.fetch = async (url) => {
              const raw = String(url);
              if (raw.endsWith("/repos/owner/repo")) {
                return jsonResponse({ default_branch: "main" });
              }
              if (raw.endsWith("/repos/owner/repo/git/trees/main?recursive=1")) {
                return jsonResponse({
                  truncated: false,
                  tree: [
                    { type: "blob", path: "docs/background.md", size: 10, url: "blob-doc" },
                    { type: "blob", path: "huge.ipynb", size: 900000, url: "blob-huge" },
                    { type: "blob", path: "src/train.py", size: 100, url: "blob-python" },
                    { type: "blob", path: "notebooks/analysis.ipynb", size: 200, url: "blob-notebook" },
                    { type: "blob", path: ".github/workflows/ci.yml", size: 20, url: "blob-ci" },
                    { type: "blob", path: "README.md", size: 1000, url: "blob-readme" },
                  ],
                });
              }
              if (blobs.has(raw)) {
                return jsonResponse({
                  encoding: "base64",
                  content: Buffer.from(blobs.get(raw), "utf8").toString("base64"),
                });
              }
              throw new Error(`unexpected URL ${raw}`);
            };

            const result = await context.fetchPublicGitHubRepo("https://github.com/owner/repo");
            assert.strictEqual(result.label, "github.com/owner/repo");
            assert.strictEqual(result.skipped, 1);
            assert.deepStrictEqual(
              Array.from(result.files.map(file => file.path)),
              ["README.md", ".github/workflows/ci.yml", "notebooks/analysis.ipynb", "src/train.py", "docs/background.md"],
            );
            assert.ok(result.files.every(file => file.textLike));
            assert.ok(result.files.find(file => file.path === "README.md").text.includes("# Demo"));
            """
        )
    )

    assert result.returncode == 0, result.stderr
