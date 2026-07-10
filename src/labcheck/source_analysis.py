from __future__ import annotations

from dataclasses import dataclass
import ast
import builtins
from pathlib import Path
import re
import shlex

from .models import NotebookDocument

READ_PATTERNS = [
    re.compile(r"pd\.read_(?:csv|parquet|json|excel)\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"(?<![\w.])open\(\s*['\"]([^'\"]+)['\"]\s*(?:,\s*['\"]r[bt]?['\"]\s*)?\)"),
    re.compile(r"np\.load\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"torch\.load\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"(?:requests|httpx)\.(?:get|stream)\(\s*['\"](https?://[^'\"]+)['\"]"),
    re.compile(r"urllib\.request\.(?:urlopen|urlretrieve)\(\s*['\"](https?://[^'\"]+)['\"]"),
    re.compile(r"(?:wget|gdown)\.download\(\s*['\"](https?://[^'\"]+)['\"]"),
    re.compile(r"(?m)^\s*[!%]?\s*(?:wget|curl)\s+[^\n]*?(https?://[^\s'\"\\)]+)"),
]

WRITE_PATTERNS = [
    re.compile(r"to_(?:csv|parquet|json|excel|feather|pickle)\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"savefig\(\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"(?<![\w.])open\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"](?:w|wb|wt|a|ab|at|x|xb|xt)['\"]"),
    re.compile(r"torch\.save\([^,]+,\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"(?:joblib|pickle)\.dump\([^,]+,\s*['\"]([^'\"]+)['\"]"),
    re.compile(r"np\.savez?(?:_compressed)?\(\s*['\"]([^'\"]+)['\"]"),
]

RANDOM_USAGE_PATTERNS = [
    re.compile(r"\brandom\."),
    re.compile(r"\bnp\.random\."),
    re.compile(r"\bnumpy\.random\."),
    re.compile(r"\btorch\.(?:rand|randn|randint|bernoulli|multinomial)\b"),
    re.compile(
        r"\bjax\.random\.(?:bernoulli|beta|categorical|choice|exponential|gamma|gumbel|laplace|"
        r"logistic|multivariate_normal|normal|permutation|poisson|randint|truncated_normal|uniform)\b"
    ),
]

SEED_PATTERNS = [
    re.compile(r"\brandom\.seed\("),
    re.compile(r"\bnp\.random\.seed\("),
    re.compile(r"\bnumpy\.random\.seed\("),
    re.compile(r"\btorch\.manual_seed\("),
    re.compile(r"\bjax\.random\.PRNGKey\("),
]

RANDOM_USAGE_CALL_PREFIXES = (
    "random.",
    "np.random.",
    "numpy.random.",
)

TORCH_RANDOM_CALLS = {
    "torch.bernoulli",
    "torch.multinomial",
    "torch.rand",
    "torch.randn",
    "torch.randint",
}

JAX_RANDOM_CALLS = {
    "jax.random.bernoulli",
    "jax.random.beta",
    "jax.random.categorical",
    "jax.random.choice",
    "jax.random.exponential",
    "jax.random.gamma",
    "jax.random.gumbel",
    "jax.random.laplace",
    "jax.random.logistic",
    "jax.random.multivariate_normal",
    "jax.random.normal",
    "jax.random.permutation",
    "jax.random.poisson",
    "jax.random.randint",
    "jax.random.truncated_normal",
    "jax.random.uniform",
}

SEED_CALL_NAMES = {
    "random.seed",
    "np.random.seed",
    "numpy.random.seed",
    "torch.manual_seed",
    "jax.random.PRNGKey",
}

NOTEBOOK_IMPLICIT_NAMES = {
    "display",
    "get_ipython",
}

IPYTHON_MAGIC_ASSIGNMENT_PATTERN = re.compile(
    r"^(\s*[A-Za-z_][A-Za-z0-9_]*(?:\s*,\s*[A-Za-z_][A-Za-z0-9_]*)*)\s*=\s*[!%].*$"
)

README_COMMAND_PATTERNS = [
    re.compile(r"(?:uv\s+run\s+)?dbt\s+(?:run|test|build|ls|list)\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?(?:great_expectations|gx)\s+checkpoint\s+run\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?ploomber\s+(?:task\s+[^\n`]+|build\s+[^\n`]*--partially[^\n`]*)"),
    re.compile(r"(?:uv\s+run\s+)?luigi\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?meltano\s+(?:[^\n`]*\s)?run\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?(?:flyte|pyflyte)\s+[^\n`]*\brun\b[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?argo\s+submit\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?tkn\s+(?:pipeline|task)\s+start\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?ray\s+job\s+submit\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?dagger\s+[^\n`]*\bcall\b[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?bazel\s+[^\n`]*\b(?:build|test|run)\b[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?(?:\./)?pants\s+[^\n`]*\b(?:check|fmt|lint|package|run|test)\b[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?nix\s+(?:flake\s+check(?:\s+[^\n`]*)?|(?:build|run)\s+[^\n`]+)"),
    re.compile(r"(?:uv\s+run\s+)?docker\s+(?:buildx\s+build|image\s+build|build)\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?(?:docker\s+compose|docker-compose)\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?helm\s+(?:install|template|upgrade|lint|package)\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?(?:kustomize\s+build|kubectl\s+(?:apply|delete|diff|kustomize))\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?terraform\s+[^\n`]*-chdir(?:=|\s+)[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?pulumi\s+[^\n`]*(?:--cwd(?:=|\s+)|-C(?:=|\s*)\S)[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?ansible-playbook\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?packer\s+(?:build|fmt|init|inspect|validate)\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?dg\s+launch\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?dagster\s+job\s+(?:execute|launch|backfill|print|scaffold_config)\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?dagster\s+asset\s+materialize\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?airflow\s+(?:dags\s+test|tasks\s+(?:test|run))\s+[^\n`]+"),
    re.compile(r"uv\s+run\s+task\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(r"uv\s+run\s+([A-Za-z][A-Za-z0-9_.-]*)\b"),
    re.compile(r"uv\s+run\s+python(?:3)?\s+-m\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)\b"),
    re.compile(r"uv\s+run\s+python(?:3)?\s+[^\s`]+\.py\s+resume\s+[^\n`]+"),
    re.compile(r"uv\s+run\s+python(?:3)?\s+([^\s`]+\.py)\b"),
    re.compile(r"hatch\s+run\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(r"pdm\s+run\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(r"pixi\s+run\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(r"nox\s+(?:-s|--session)\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(r"tox(?:\s+run)?\s+(?:-e|--environment)\s+([A-Za-z0-9_.:-]+(?:\s*,\s*[A-Za-z0-9_.:-]+)*)\b"),
    re.compile(r"(?<!run\s)(?<!ploomber\s)(?<!tkn\s)(?<![-\w])task\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(r"just\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(r"doit\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(r"(?:invoke|inv)\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(r"(?:bundle\s+exec\s+)?(?:bin/)?rake\s+([A-Za-z0-9_.:-]+)\b"),
    re.compile(
        r"snakemake"
        r"(?:\s+(?:--snakefile|-s|--cores|-j|--jobs)\s+\S+|\s+(?:--use-conda|--rerun-incomplete|--dry-run|-n))*"
        r"\s+([A-Za-z0-9_./:][A-Za-z0-9_./:-]*)\b"
    ),
    re.compile(r"nextflow\s+run\s+[^\n`]+"),
    re.compile(r"(?:java(?:\s+-D\S+)*\s+-jar\s+\S+\s+|cromwell\s+)run\s+[^\n`]+"),
    re.compile(r"(?:cwltool|cwl-runner)\s+[^\n`]+"),
    re.compile(r"papermill\s+[^\n`]+"),
    re.compile(r"dvc\s+(?:repro|pull)\s+[^\n`]+"),
    re.compile(r"quarto\s+render(?:\s+[^\n`]+)?"),
    re.compile(r"jupytext\s+[^\n`]*--sync[^\n`]*"),
    re.compile(r"kedro\s+run[^\n`]*"),
    re.compile(r"(?:uv\s+run\s+)?prefect\s+deployment\s+run\s+[^\n`]+"),
    re.compile(r"(?:uv\s+run\s+)?mlflow\s+run\s+[^\n`]+"),
    re.compile(r"python(?:3)?\s+[^\s`]+\.py\s+resume\s+[^\n`]+"),
    re.compile(r"python(?:3)?\s+-m\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+)\b"),
    re.compile(r"python(?:3)?\s+([^\s`]+\.py)\b"),
    re.compile(r"jupyter\s+notebook\s+([^\s`]+\.ipynb)\b"),
    re.compile(r"bash\s+([^\s`]+\.sh)\b"),
    re.compile(r"(?<![\w-])make(?:\s+([A-Za-z0-9_./-]+))?\b"),
    re.compile(r"(npm|pnpm)\s+run\s+([A-Za-z0-9_./:-]+)\b"),
    re.compile(
        r"(yarn)(?:\s+run)?\s+"
        r"(?!add\b|cache\b|config\b|dlx\b|exec\b|import\b|init\b|install\b|remove\b|set\b|upgrade\b)"
        r"([A-Za-z0-9_./:-]+)\b"
    ),
]
README_COMMAND_START_PATTERN = re.compile(
    r"^(?:"
    r"uv\s+run\s+task\s+[A-Za-z0-9_.:-]+\b|"
    r"uv\s+run\s+[A-Za-z][A-Za-z0-9_.-]*\b|"
    r"uv\s+run\s+python(?:3)?\s+-m\s+[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b|"
    r"uv\s+run\s+python(?:3)?\s+[^\s`]+\.py\b|"
    r"hatch\s+run\s+[A-Za-z0-9_.:-]+\b|"
    r"pdm\s+run\s+[A-Za-z0-9_.:-]+\b|"
    r"pixi\s+run\s+[A-Za-z0-9_.:-]+\b|"
    r"nox\s+(?:-s|--session)\s+[A-Za-z0-9_.:-]+\b|"
    r"tox(?:\s+run)?\s+(?:-e|--environment)\s+[A-Za-z0-9_.:-]+(?:\s*,\s*[A-Za-z0-9_.:-]+)*\b|"
    r"(?<![-\w])task\s+[A-Za-z0-9_.:-]+\b|"
    r"just\s+[A-Za-z0-9_.:-]+\b|"
    r"doit\s+[A-Za-z0-9_.:-]+\b|"
    r"(?:invoke|inv)\s+[A-Za-z0-9_.:-]+\b|"
    r"(?:bundle\s+exec\s+)?(?:bin/)?rake\s+[A-Za-z0-9_.:-]+\b|"
    r"snakemake(?:\s+(?:--snakefile|-s|--cores|-j|--jobs)\s+\S+|\s+(?:--use-conda|--rerun-incomplete|--dry-run|-n))*\s+[A-Za-z0-9_./:][A-Za-z0-9_./:-]*\b|"
    r"nextflow\s+run\s+[^\s`]+\b|"
    r"(?:java(?:\s+-D\S+)*\s+-jar\s+\S+\s+|cromwell\s+)run\s+[^\s`]+\b|"
    r"(?:cwltool|cwl-runner)\s+[^\s`]+\b|"
    r"papermill\s+[^\s`]+\.ipynb\b|"
    r"dvc\s+(?:repro|pull)\s+[^\s`]+\b|"
    r"quarto\s+render(?:\s+[^\s`]+)?\b|"
    r"jupytext\s+[^\n`]*--sync\b|"
    r"kedro\s+run\b|"
    r"(?:uv\s+run\s+)?prefect\s+deployment\s+run\b|"
    r"(?:uv\s+run\s+)?mlflow\s+run\b|"
    r"(?:uv\s+run\s+)?dbt\s+(?:run|test|build|ls|list)\b|"
    r"(?:uv\s+run\s+)?(?:great_expectations|gx)\s+checkpoint\s+run\b|"
    r"(?:uv\s+run\s+)?ploomber\s+(?:task|build)\b|"
    r"(?:uv\s+run\s+)?luigi\b|"
    r"(?:uv\s+run\s+)?meltano\s+(?:[^\n`]*\s)?run\b|"
    r"(?:uv\s+run\s+)?(?:flyte|pyflyte)\s+[^\n`]*\brun\b|"
    r"(?:uv\s+run\s+)?argo\s+submit\b|"
    r"(?:uv\s+run\s+)?tkn\s+(?:pipeline|task)\s+start\b|"
    r"(?:uv\s+run\s+)?ray\s+job\s+submit\b|"
    r"(?:uv\s+run\s+)?dagger\s+[^\n`]*\bcall\b|"
    r"(?:uv\s+run\s+)?bazel\s+[^\n`]*\b(?:build|test|run)\b|"
    r"(?:uv\s+run\s+)?(?:\./)?pants\s+[^\n`]*\b(?:check|fmt|lint|package|run|test)\b|"
    r"(?:uv\s+run\s+)?nix\s+(?:flake\s+check|build|run)\b|"
    r"(?:uv\s+run\s+)?docker\s+(?:buildx\s+build|image\s+build|build)\b|"
    r"(?:uv\s+run\s+)?(?:docker\s+compose|docker-compose)\b|"
    r"(?:uv\s+run\s+)?helm\s+(?:install|template|upgrade|lint|package)\b|"
    r"(?:uv\s+run\s+)?kustomize\s+build\b|"
    r"(?:uv\s+run\s+)?kubectl\s+(?:apply|delete|diff)\b[^\n`]*(?:-k|--kustomize)\b|"
    r"(?:uv\s+run\s+)?kubectl\s+(?:apply|delete|diff)\b[^\n`]*(?:-f|--filename)\b|"
    r"(?:uv\s+run\s+)?kubectl\s+kustomize\b|"
    r"(?:uv\s+run\s+)?terraform\s+[^\n`]*-chdir(?:=|\s+)\S+\b|"
    r"(?:uv\s+run\s+)?pulumi\s+[^\n`]*(?:--cwd(?:=|\s+)|-C(?:=|\s*)\S)\S*|"
    r"(?:uv\s+run\s+)?ansible-playbook\b|"
    r"(?:uv\s+run\s+)?packer\s+(?:build|fmt|init|inspect|validate)\b|"
    r"(?:uv\s+run\s+)?dg\s+launch\b|"
    r"(?:uv\s+run\s+)?dagster\s+job\s+(?:execute|launch|backfill|print|scaffold_config)\b|"
    r"(?:uv\s+run\s+)?dagster\s+asset\s+materialize\b|"
    r"(?:uv\s+run\s+)?airflow\s+(?:dags\s+test|tasks\s+(?:test|run))\b|"
    r"(?:uv\s+run\s+)?python(?:3)?\s+[^\s`]+\.py\s+resume\b|"
    r"python(?:3)?\s+-m\s+[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b|"
    r"python(?:3)?\s+[^\s`]+\.py\b|"
    r"jupyter\s+notebook\s+[^\s`]+\.ipynb\b|"
    r"bash\s+[^\s`]+\.sh\b|"
    r"make(?:\s+[A-Za-z0-9_./-]+)?\b|"
    r"(?:npm|pnpm)\s+run\s+[A-Za-z0-9_./:-]+\b|"
    r"yarn(?:\s+run)?\s+"
    r"(?!add\b|cache\b|config\b|dlx\b|exec\b|import\b|init\b|install\b|remove\b|set\b|upgrade\b)"
    r"[A-Za-z0-9_./:-]+\b"
    r")"
)
README_RUN_INSTRUCTION_PATTERN = re.compile(
    r"^(?:"
    r"python(?:3)?\s+(?:-m\s+[\w.]+|[^\s`]+\.py)\b|"
    r"jupyter\s+(?:notebook|lab)(?:\s+[^\s`]+\.ipynb\b)?|"
    r"pip\s+install\b|"
    r"python(?:3)?\s+-m\s+pip\s+install\b|"
    r"conda\s+env\s+create\b|"
    r"poetry\s+(?:install|run)\b|"
    r"uv\s+(?:sync|run)\b|"
    r"hatch\s+(?:env\s+create|run)\b|"
    r"pdm\s+(?:install|sync|run)\b|"
    r"pixi\s+(?:install|run)\b|"
    r"nox(?:\s+(?:-s|--session)\s+[A-Za-z0-9_.:-]+)?\b|"
    r"tox(?:\s+(?:run\s+)?(?:-e|--environment)\s+[A-Za-z0-9_.:-]+(?:\s*,\s*[A-Za-z0-9_.:-]+)*)?\b|"
    r"(?<![-\w])task\s+[A-Za-z0-9_.:-]+\b|"
    r"just\s+[A-Za-z0-9_.:-]+\b|"
    r"doit\s+[A-Za-z0-9_.:-]+\b|"
    r"(?:invoke|inv)\s+[A-Za-z0-9_.:-]+\b|"
    r"(?:bundle\s+exec\s+)?(?:bin/)?rake(?:\s+[A-Za-z0-9_.:-]+)?\b|"
    r"nextflow\s+run\b|"
    r"(?:java(?:\s+-D\S+)*\s+-jar\s+\S+\s+|cromwell\s+)run\b|"
    r"(?:cwltool|cwl-runner)\b|"
    r"papermill\b|"
    r"(?:npm|pnpm)\s+(?:install|ci|run\s+[A-Za-z0-9_./:-]+)\b|"
    r"yarn(?:\s+(?:install|run\s+[A-Za-z0-9_./:-]+|"
    r"(?!add\b|cache\b|config\b|dlx\b|exec\b|import\b|init\b|install\b|remove\b|set\b|upgrade\b)"
    r"[A-Za-z0-9_./:-]+))?\b|"
    r"make(?:\s+[A-Za-z0-9_./-]+)?\b|"
    r"bash\s+[^\s`]+\.sh\b|"
    r"pytest\b|"
    r"snakemake\b|"
    r"dvc\s+(?:repro|pull)\b"
    r"|quarto\s+render\b"
    r"|jupytext\s+[^\n`]*--sync\b"
    r"|kedro\s+run\b"
    r"|(?:uv\s+run\s+)?prefect\s+deployment\s+run\b"
    r"|(?:uv\s+run\s+)?mlflow\s+run\b"
    r"|(?:uv\s+run\s+)?dbt\s+(?:run|test|build|ls|list)\b"
    r"|(?:uv\s+run\s+)?(?:great_expectations|gx)\s+checkpoint\s+run\b"
    r"|(?:uv\s+run\s+)?ploomber\s+(?:task|build)\b"
    r"|(?:uv\s+run\s+)?luigi\b"
    r"|(?:uv\s+run\s+)?meltano\b"
    r"|(?:uv\s+run\s+)?(?:flyte|pyflyte)\b"
    r"|(?:uv\s+run\s+)?argo\s+submit\b"
    r"|(?:uv\s+run\s+)?tkn\s+(?:pipeline|task)\s+start\b"
    r"|(?:uv\s+run\s+)?ray\s+job\s+submit\b"
    r"|(?:uv\s+run\s+)?dagger\s+[^\n`]*\bcall\b"
    r"|(?:uv\s+run\s+)?bazel\s+[^\n`]*\b(?:build|test|run)\b"
    r"|(?:uv\s+run\s+)?(?:\./)?pants\s+[^\n`]*\b(?:check|fmt|lint|package|run|test)\b"
    r"|(?:uv\s+run\s+)?nix\s+(?:flake\s+check|build|run)\b"
    r"|(?:uv\s+run\s+)?docker\s+(?:buildx\s+build|image\s+build|build)\b"
    r"|(?:uv\s+run\s+)?(?:docker\s+compose|docker-compose)\b"
    r"|(?:uv\s+run\s+)?helm\s+(?:install|template|upgrade|lint|package)\b"
    r"|(?:uv\s+run\s+)?kustomize\s+build\b"
    r"|(?:uv\s+run\s+)?kubectl\s+(?:apply|delete|diff)\b[^\n`]*(?:-k|--kustomize)\b"
    r"|(?:uv\s+run\s+)?kubectl\s+(?:apply|delete|diff)\b[^\n`]*(?:-f|--filename)\b"
    r"|(?:uv\s+run\s+)?kubectl\s+kustomize\b"
    r"|(?:uv\s+run\s+)?terraform\s+[^\n`]*-chdir(?:=|\s+)\S+\b"
    r"|(?:uv\s+run\s+)?pulumi\s+[^\n`]*(?:--cwd(?:=|\s+)|-C(?:=|\s*)\S)\S*"
    r"|(?:uv\s+run\s+)?ansible-playbook\b"
    r"|(?:uv\s+run\s+)?packer\s+(?:build|fmt|init|inspect|validate)\b"
    r"|(?:uv\s+run\s+)?dg\s+launch\b"
    r"|(?:uv\s+run\s+)?dagster\s+job\s+(?:execute|launch|backfill|print|scaffold_config)\b"
    r"|(?:uv\s+run\s+)?dagster\s+asset\s+materialize\b"
    r"|(?:uv\s+run\s+)?airflow\s+(?:dags\s+test|tasks\s+(?:test|run))\b"
    r"|(?:uv\s+run\s+)?python(?:3)?\s+[^\s`]+\.py\s+resume\b"
    r")"
)
README_DEPENDENCY_SETUP_PATTERN = re.compile(
    r"(?:^|\b)(?:"
    r"pip\s+install\b|"
    r"python(?:3)?\s+-m\s+pip\s+install\b|"
    r"uv\s+(?:sync|pip\s+(?:install|sync))\b|"
    r"poetry\s+install\b|"
    r"pipenv\s+install\b|"
    r"conda\s+(?:env\s+create|install)\b|"
    r"mamba\s+(?:env\s+create|install)\b|"
    r"micromamba\s+(?:env\s+create|install)\b|"
    r"make\s+(?:setup|install|env|environment|deps|dependencies)\b"
    r")"
)

COMMON_UV_RUN_EXTERNAL_COMMANDS = {
    "airflow",
    "ansible-playbook",
    "argo",
    "black",
    "bazel",
    "coverage",
    "dbt",
    "dagster",
    "dg",
    "dagger",
    "docker",
    "docker-compose",
    "flyte",
    "great_expectations",
    "gx",
    "helm",
    "ipython",
    "jupyter",
    "kubectl",
    "kustomize",
    "luigi",
    "meltano",
    "mlflow",
    "mypy",
    "nix",
    "packer",
    "pants",
    "pip",
    "pip3",
    "ploomber",
    "pre-commit",
    "prefect",
    "pyright",
    "pytest",
    "pyflyte",
    "pulumi",
    "python",
    "python3",
    "ray",
    "ruff",
    "task",
    "terraform",
    "tkn",
    "tox",
}

COMMON_DOIT_COMMANDS = {
    "clean",
    "dumpdb",
    "forget",
    "help",
    "ignore",
    "info",
    "list",
    "reset-dep",
    "strace",
    "tabcompletion",
}

NEXTFLOW_VALUE_OPTIONS = {
    "-C",
    "-c",
    "-config",
    "-entry",
    "-profile",
    "-with-dag",
    "-with-report",
    "-with-timeline",
    "-with-trace",
}
NEXTFLOW_REMOTE_PIPELINE_PATTERN = re.compile(r"^(?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+|https?://|git@)")
CROMWELL_INPUT_OPTIONS = {"-i", "--inputs"}
CROMWELL_WORKFLOW_ROOT_OPTIONS = {"--workflow-root"}
CROMWELL_VALUE_OPTIONS = {
    "--backend",
    "--call-caching",
    "--dependencies",
    "--labels",
    "--metadata-output",
    "--options",
    "--type",
    "--type-version",
    "--workflow-root",
    "-i",
    "--inputs",
}
CWL_VALUE_OPTIONS = {
    "--cachedir",
    "--beta-dependency-resolvers-configuration",
    "--cidfile-dir",
    "--cidfile-prefix",
    "--compute-checksum",
    "--default-container",
    "--destBucket",
    "--enable-ext",
    "--eval-timeout",
    "--leave-tmpdir",
    "--make-template",
    "--mpi-config-file",
    "--outdir",
    "--preserve-environment",
    "--provenance",
    "--relax-path-checks",
    "--rm-container",
    "--singularity",
    "--tmp-outdir-prefix",
    "--tmpdir-prefix",
    "--user-space-docker-cmd",
}
PAPERMILL_VALUE_OPTIONS = {
    "--cwd",
    "--engine",
    "--execution-timeout",
    "--kernel",
    "--language",
    "--parameters_base64",
    "--parameters_raw",
    "--parameters_yaml",
    "--start-timeout",
    "--stdout-file",
    "--stderr-file",
    "-b",
    "-y",
}
PAPERMILL_PARAMETER_FILE_OPTIONS = {"-f", "--parameters_file"}
PAPERMILL_TWO_VALUE_OPTIONS = {"-p", "-r"}
DVC_VALUE_OPTIONS = {
    "-j",
    "-r",
    "--jobs",
    "--remote",
    "--rev",
}
QUARTO_VALUE_OPTIONS = {
    "-M",
    "-P",
    "--cache",
    "--execute-dir",
    "--execute-param",
    "--execute-param-file",
    "--metadata",
    "--metadata-file",
    "--output",
    "--output-dir",
    "--profile",
    "--project",
    "--resource-path",
    "--to",
}
JUPYTEXT_VALUE_OPTIONS = {
    "--cell-metadata-filter",
    "--check",
    "--from",
    "--notebook-metadata-filter",
    "--opt",
    "--output",
    "--pipe",
    "--pipe-fmt",
    "--preserve-cell-metadata",
    "--set-formats",
    "--set-kernel",
    "--to",
    "--update-metadata",
}
JUPYTEXT_TARGET_SUFFIXES = {
    ".ipynb",
    ".jl",
    ".md",
    ".myst",
    ".py",
    ".qmd",
    ".r",
    ".rmd",
    ".sh",
}
KEDRO_PIPELINE_OPTIONS = {
    "-p",
    "--pipeline",
    "--pipelines",
}
PREFECT_DEPLOYMENT_VALUE_OPTIONS = {
    "--flow-run-name",
    "--id",
    "--job-variable",
    "--param",
    "--params",
    "--start-at",
    "--start-in",
    "--tag",
    "--watch-interval",
    "--watch-timeout",
    "-jv",
    "-p",
}
MLFLOW_RUN_ENTRY_OPTIONS = {
    "-e",
    "--entry-point",
}
MLFLOW_RUN_VALUE_OPTIONS = {
    "--backend",
    "--backend-config",
    "--env-manager",
    "--experiment-id",
    "--experiment-name",
    "--run-name",
    "--storage-dir",
    "--version",
    "-A",
    "-P",
    "-v",
}
DBT_SELECTOR_OPTIONS = {
    "--models",
    "--select",
    "-m",
    "-s",
}
DBT_NAMED_SELECTOR_OPTIONS = {
    "--selector",
}
DBT_VALUE_OPTIONS = {
    "--defer-state",
    "--exclude",
    "--indirect-selection",
    "--log-path",
    "--profiles-dir",
    "--project-dir",
    "--resource-type",
    "--state",
    "--target",
    "--target-path",
    "--threads",
    "--vars",
    "-t",
    "-x",
}
GX_CHECKPOINT_NAME_OPTIONS = {
    "--checkpoint-name",
    "--name",
}
GX_CHECKPOINT_VALUE_OPTIONS = {
    "--batch-request",
    "--context-root-dir",
    "--directory",
    "--expectation-suite-name",
    "--run-name",
    "--site-name",
    "--validation-operator-name",
}
PLOOMBER_PARTIAL_OPTIONS = {
    "--partially",
}
PLOOMBER_VALUE_OPTIONS = {
    "--entry-point",
    "--executor",
    "--log",
    "--log-file",
    "--serializer",
    "--unserializer",
    "-e",
}
LUIGI_VALUE_OPTIONS = {
    "--config",
    "--log-level",
    "--logging-conf-file",
    "--lock-pid-dir",
    "--module",
    "--parallel-scheduling-processes",
    "--pidlock",
    "--scheduler-host",
    "--scheduler-port",
    "--scheduler-url",
    "--workers",
}
MELTANO_GLOBAL_VALUE_OPTIONS = {
    "--database-uri",
    "--environment",
    "--log-level",
    "--project-root",
    "-e",
}
MELTANO_RUN_VALUE_OPTIONS = {
    "--environment",
    "--log-level",
    "--run-id",
    "--state-id-suffix",
    "--state-strategy",
    "--timeout",
    "-e",
}
FLYTE_RUN_VALUE_OPTIONS = {
    "--cluster-pool",
    "--config",
    "--copy-style",
    "--domain",
    "--env",
    "--image",
    "--input-file",
    "--name",
    "--project",
    "--raw-data-path",
    "--service-account",
    "--version",
    "-c",
    "-d",
    "-e",
    "-i",
    "-p",
}
ARGO_SUBMIT_ENTRYPOINT_OPTIONS = {
    "--entrypoint",
}
ARGO_SUBMIT_FROM_OPTIONS = {
    "--from",
}
ARGO_SUBMIT_VALUE_OPTIONS = {
    "--argo-server",
    "--as",
    "--as-group",
    "--as-uid",
    "--certificate-authority",
    "--client-certificate",
    "--client-key",
    "--cluster",
    "--context",
    "--generate-name",
    "--gloglevel",
    "--header",
    "--instanceid",
    "--kubeconfig",
    "--labels",
    "--log-format",
    "--loglevel",
    "--name",
    "--namespace",
    "--node-field-selector",
    "--output",
    "--parameter",
    "--parameter-file",
    "--password",
    "--priority",
    "--proxy-url",
    "--request-timeout",
    "--scheduled-time",
    "--server",
    "--serviceaccount",
    "--status",
    "--tls-server-name",
    "--token",
    "--user",
    "--username",
    "-f",
    "-H",
    "-l",
    "-n",
    "-o",
    "-p",
    "-s",
}
TEKTON_FILENAME_OPTIONS = {
    "--filename",
    "-f",
}
TEKTON_REMOTE_OPTIONS = {
    "--image",
    "-i",
}
TEKTON_START_VALUE_OPTIONS = {
    "--context",
    "--dry-run",
    "--kubeconfig",
    "--label",
    "--labels",
    "--last",
    "--namespace",
    "--output",
    "--param",
    "--pipeline-timeout",
    "--pod-template",
    "--prefix-name",
    "--remote-bearer",
    "--remote-password",
    "--remote-username",
    "--serviceaccount",
    "--showlog",
    "--task-serviceaccount",
    "--tasks-timeout",
    "--timeout",
    "--use-param-defaults",
    "--use-pipelinerun",
    "--use-taskrun",
    "--workspace",
    "-c",
    "-k",
    "-l",
    "-n",
    "-o",
    "-p",
    "-s",
    "-w",
}
DAGGER_MODULE_OPTIONS = {
    "--mod",
    "-m",
}
DAGGER_NO_MODULE_OPTIONS = {
    "--no-mod",
    "-M",
}
DAGGER_VALUE_OPTIONS = {
    "--allow-llm",
    "--cache-from",
    "--config",
    "--interactive-command",
    "--lock",
    "--model",
    "--output",
    "--progress",
    "--workdir",
    "-c",
    "-o",
    "-w",
}
BAZEL_COMMANDS = {
    "build",
    "run",
    "test",
}
BAZEL_VALUE_OPTIONS = {
    "--action_env",
    "--bazelrc",
    "--compilation_mode",
    "--config",
    "--cpu",
    "--define",
    "--extra_toolchains",
    "--features",
    "--host_platform",
    "--java_language_version",
    "--output_base",
    "--output_user_root",
    "--platforms",
    "--repo_env",
    "--spawn_strategy",
    "--strategy",
    "--test_filter",
    "--test_output",
    "--test_tag_filters",
    "--tool_java_language_version",
    "--toolchain_resolution_debug",
    "-c",
}
PANTS_GOALS = {
    "check",
    "fmt",
    "lint",
    "package",
    "run",
    "test",
}
PANTS_VALUE_OPTIONS = {
    "--backend-packages",
    "--changed-dependents",
    "--changed-since",
    "--config",
    "--filter-address-regex",
    "--from",
    "--lint-only",
    "--named-caches-dir",
    "--pants-bin-name",
    "--pants-config-files",
    "--pants-distdir",
    "--pants-subprocessdir",
    "--pants-workdir",
    "--py-executable-search-paths",
    "--pythonpath",
    "--tag",
    "--to",
    "-c",
}
NIX_VALUE_OPTIONS = {
    "--eval-store",
    "--expr",
    "--file",
    "--inputs-from",
    "--log-format",
    "--out-link",
    "--output-lock-file",
    "--profile",
    "--reference-lock-file",
    "--store",
    "--system",
    "--update-input",
    "-f",
    "-I",
    "-j",
    "-o",
}
NIX_TWO_VALUE_OPTIONS = {
    "--arg",
    "--argstr",
    "--option",
    "--override-input",
}
DOCKER_COMPOSE_SERVICE_COMMANDS = {
    "build",
    "create",
    "exec",
    "kill",
    "logs",
    "ps",
    "pull",
    "restart",
    "rm",
    "run",
    "start",
    "stop",
    "up",
}
DOCKER_COMPOSE_GLOBAL_VALUE_OPTIONS = {
    "--ansi",
    "--env-file",
    "--file",
    "--parallel",
    "--profile",
    "--progress",
    "--project-directory",
    "--project-name",
    "-f",
    "-p",
}
DOCKER_COMPOSE_COMMAND_VALUE_OPTIONS = {
    "--attach",
    "--build-arg",
    "--env",
    "--entrypoint",
    "--exit-code-from",
    "--format",
    "--index",
    "--label",
    "--memory",
    "--name",
    "--pull",
    "--scale",
    "--since",
    "--ssh",
    "--tail",
    "--timeout",
    "--until",
    "--user",
    "--workdir",
    "-e",
    "-t",
    "-u",
    "-w",
}
DOCKER_BUILD_VALUE_OPTIONS = {
    "--add-host",
    "--allow",
    "--annotation",
    "--attest",
    "--build-arg",
    "--build-context",
    "--cache-from",
    "--cache-to",
    "--cgroup-parent",
    "--file",
    "--iidfile",
    "--label",
    "--network",
    "--output",
    "--platform",
    "--progress",
    "--secret",
    "--ssh",
    "--tag",
    "--target",
    "--ulimit",
    "-f",
    "-o",
    "-t",
}
HELM_CHART_COMMANDS = {
    "install",
    "lint",
    "package",
    "template",
    "upgrade",
}
HELM_VALUE_OPTIONS = {
    "--api-versions",
    "--ca-file",
    "--cert-file",
    "--description",
    "--dry-run",
    "--key-file",
    "--keyring",
    "--kube-version",
    "--name-template",
    "--namespace",
    "--output-dir",
    "--password",
    "--post-renderer",
    "--post-renderer-args",
    "--repo",
    "--set",
    "--set-file",
    "--set-json",
    "--set-literal",
    "--set-string",
    "--show-only",
    "--timeout",
    "--username",
    "--values",
    "--version",
    "-a",
    "-f",
    "-n",
}
KUSTOMIZE_APPLY_COMMANDS = {
    "apply",
    "delete",
    "diff",
}
KUBECTL_MANIFEST_COMMANDS = {
    "apply",
    "delete",
    "diff",
}
KUBECTL_FILENAME_OPTIONS = {
    "--filename",
    "-f",
}
KUSTOMIZE_VALUE_OPTIONS = {
    "--as",
    "--as-group",
    "--cache-dir",
    "--certificate-authority",
    "--client-certificate",
    "--client-key",
    "--cluster",
    "--context",
    "--field-manager",
    "--filename",
    "--helm-command",
    "--kubeconfig",
    "--load-restrictor",
    "--mount",
    "--namespace",
    "--output",
    "--prune-allowlist",
    "--request-timeout",
    "--selector",
    "--server",
    "--token",
    "--user",
    "-f",
    "-l",
    "-n",
    "-o",
}
TERRAFORM_COMMANDS = {
    "apply",
    "destroy",
    "fmt",
    "init",
    "plan",
    "test",
    "validate",
}
PULUMI_PROJECT_COMMANDS = {
    "config",
    "destroy",
    "import",
    "install",
    "preview",
    "refresh",
    "stack",
    "up",
    "watch",
}
PULUMI_VALUE_OPTIONS = {
    "--color",
    "--config",
    "--config-file",
    "--cwd",
    "--exec-agent",
    "--message",
    "--profiling",
    "--secrets-provider",
    "--stack",
    "--tracing",
    "-C",
    "-m",
    "-s",
}
ANSIBLE_INVENTORY_OPTIONS = {
    "--inventory",
    "--inventory-file",
    "-i",
}
ANSIBLE_VALUE_OPTIONS = {
    "--become-method",
    "--become-user",
    "--connection",
    "--extra-vars",
    "--forks",
    "--inventory",
    "--inventory-file",
    "--key-file",
    "--limit",
    "--module-path",
    "--private-key",
    "--scp-extra-args",
    "--sftp-extra-args",
    "--skip-tags",
    "--ssh-common-args",
    "--ssh-extra-args",
    "--start-at-task",
    "--tags",
    "--timeout",
    "--user",
    "--vault-id",
    "--vault-password-file",
    "-c",
    "-e",
    "-f",
    "-i",
    "-l",
    "-M",
    "-t",
    "-T",
    "-u",
}
PACKER_TEMPLATE_COMMANDS = {
    "build",
    "fmt",
    "init",
    "inspect",
    "validate",
}
PACKER_VALUE_OPTIONS = {
    "--except",
    "--only",
    "--parallel-builds",
    "--var",
    "--var-file",
    "-except",
    "-only",
    "-parallel-builds",
    "-var",
    "-var-file",
}
DAGSTER_JOB_OPTIONS = {
    "--job",
    "--jobs",
    "-j",
}
DAGSTER_ASSET_OPTIONS = {
    "--asset",
    "--assets",
    "--select",
}
DAGSTER_VALUE_OPTIONS = {
    "--attribute",
    "--autoload-defs-module-name",
    "--config",
    "--config-json",
    "--grpc-host",
    "--grpc-port",
    "--grpc-socket",
    "--instance-ref",
    "--location-name",
    "--log-level",
    "--module-name",
    "--package-name",
    "--partition",
    "--partition-range",
    "--python-file",
    "--repository",
    "--target-path",
    "--workspace",
    "--working-directory",
    "-a",
    "-c",
    "-d",
    "-f",
    "-m",
    "-r",
    "-w",
}
AIRFLOW_DAGS_TEST_VALUE_OPTIONS = {
    "--bundle-name",
    "--conf",
    "--dagfile-path",
    "--mark-success-pattern",
    "--save-dagrun",
    "--subdir",
    "-B",
    "-c",
    "-f",
    "-S",
}
AIRFLOW_TASKS_VALUE_OPTIONS = {
    "--bundle-name",
    "--cfg-path",
    "--env-vars",
    "--executor",
    "--error-file",
    "--map-index",
    "--pool",
    "--task-params",
    "--subdir",
    "--pickle",
    "-B",
    "-p",
    "-S",
    "-t",
}
METAFLOW_RESUME_VALUE_OPTIONS = {
    "--decospec",
    "--max-num-splits",
    "--max-workers",
    "--namespace",
    "--origin-run-id",
    "--run-id",
    "--tag",
    "--with",
}

STRING_ASSIGNMENT_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE)
READ_VARIABLE_PATTERNS = [
    re.compile(r"pd\.read_(?:csv|parquet|json|excel)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"(?<![\w.])open\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*(?:,\s*['\"]r[bt]?['\"]\s*)?\)"),
    re.compile(r"np\.load\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"torch\.load\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
]

WRITE_VARIABLE_PATTERNS = [
    re.compile(r"to_(?:csv|parquet|json|excel|feather|pickle)\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"savefig\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"(?<![\w.])open\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,\s*['\"](?:w|wb|wt|a|ab|at|x|xb|xt)['\"]"),
    re.compile(r"torch\.save\([^,]+,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"(?:joblib|pickle)\.dump\([^,]+,\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)"),
    re.compile(r"np\.savez?(?:_compressed)?\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*,"),
]


@dataclass(slots=True)
class SourceArtifact:
    path: Path
    kind: str
    content: str
    reads: list[str]
    writes: list[str]
    uses_randomness: bool
    seeds_randomness: bool


@dataclass(slots=True)
class ReadmeReference:
    command: str
    referenced_path: str
    make_target: str = ""
    module_name: str = ""
    package_manager: str = ""
    package_script: str = ""
    project_script: str = ""
    nextflow_pipeline: str = ""
    nextflow_profiles: tuple[str, ...] = ()
    nextflow_entry: str = ""
    wdl_workflow: str = ""
    wdl_inputs: tuple[str, ...] = ()
    wdl_workflow_root: str = ""
    cwl_workflow: str = ""
    cwl_job: str = ""
    papermill_input: str = ""
    papermill_parameter_files: tuple[str, ...] = ()
    dvc_command: str = ""
    dvc_targets: tuple[str, ...] = ()
    quarto_target: str = ""
    jupytext_targets: tuple[str, ...] = ()
    kedro_pipelines: tuple[str, ...] = ()
    prefect_flow: str = ""
    prefect_deployment: str = ""
    mlflow_project: str = ""
    mlflow_entry_point: str = ""
    dbt_selectors: tuple[str, ...] = ()
    gx_checkpoint: str = ""
    ploomber_tasks: tuple[str, ...] = ()
    luigi_module: str = ""
    luigi_task: str = ""
    meltano_jobs: tuple[str, ...] = ()
    flyte_script: str = ""
    flyte_target: str = ""
    argo_workflow: str = ""
    argo_entrypoint: str = ""
    tekton_kind: str = ""
    tekton_name: str = ""
    tekton_file: str = ""
    ray_script: str = ""
    ray_module: str = ""
    dagger_module: str = ""
    dagger_function: str = ""
    bazel_command: str = ""
    bazel_targets: tuple[str, ...] = ()
    pants_goal: str = ""
    pants_specs: tuple[str, ...] = ()
    nix_command: str = ""
    nix_installables: tuple[str, ...] = ()
    docker_compose_command: str = ""
    docker_compose_files: tuple[str, ...] = ()
    docker_compose_env_files: tuple[str, ...] = ()
    docker_compose_project_dirs: tuple[str, ...] = ()
    docker_compose_profiles: tuple[str, ...] = ()
    docker_compose_services: tuple[str, ...] = ()
    docker_build_file: str = ""
    docker_build_target: str = ""
    helm_command: str = ""
    helm_chart_paths: tuple[str, ...] = ()
    kustomize_command: str = ""
    kustomize_paths: tuple[str, ...] = ()
    kubernetes_command: str = ""
    kubernetes_manifest_paths: tuple[str, ...] = ()
    terraform_command: str = ""
    terraform_working_dirs: tuple[str, ...] = ()
    pulumi_command: str = ""
    pulumi_project_dirs: tuple[str, ...] = ()
    ansible_playbooks: tuple[str, ...] = ()
    ansible_inventories: tuple[str, ...] = ()
    packer_command: str = ""
    packer_templates: tuple[str, ...] = ()
    dagster_jobs: tuple[str, ...] = ()
    dagster_assets: tuple[str, ...] = ()
    airflow_dag_id: str = ""
    airflow_task_id: str = ""
    metaflow_script: str = ""
    metaflow_step: str = ""


@dataclass(slots=True)
class HiddenStateIssue:
    cell_index: int
    names: list[str]


def _normalize_source(text: str) -> str:
    return text.replace("\\\r\n", "").replace("\\\n", "")


def extract_paths(text: str, patterns: list[re.Pattern[str]]) -> list[str]:
    normalized = _normalize_source(text)
    matches: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(normalized):
            matches.append(match.group(1))
    return matches


def _extract_string_assignments(text: str) -> dict[str, str]:
    normalized = _normalize_source(text)
    return {match.group(1): match.group(2) for match in STRING_ASSIGNMENT_PATTERN.finditer(normalized)}


def _extract_variable_paths(text: str, patterns: list[re.Pattern[str]], assignments: dict[str, str]) -> list[str]:
    normalized = _normalize_source(text)
    matches: list[str] = []
    for pattern in patterns:
        for match in pattern.finditer(normalized):
            variable_name = match.group(1)
            if variable_name in assignments:
                matches.append(assignments[variable_name])
    return matches


def analyze_notebook(notebook: NotebookDocument) -> SourceArtifact:
    content = "\n\n".join(notebook.sources)
    assignments = _extract_string_assignments(content)
    return SourceArtifact(
        path=notebook.path,
        kind="notebook",
        content=content,
        reads=extract_paths(content, READ_PATTERNS) + _extract_variable_paths(content, READ_VARIABLE_PATTERNS, assignments),
        writes=extract_paths(content, WRITE_PATTERNS) + _extract_variable_paths(content, WRITE_VARIABLE_PATTERNS, assignments),
        uses_randomness=any(pattern.search(content) for pattern in RANDOM_USAGE_PATTERNS),
        seeds_randomness=any(pattern.search(content) for pattern in SEED_PATTERNS),
    )


def analyze_python_file(path: Path) -> SourceArtifact:
    content = path.read_text(encoding="utf-8")
    assignments = _extract_string_assignments(content)
    uses_randomness, seeds_randomness = _python_randomness_flags(content)
    return SourceArtifact(
        path=path,
        kind="python",
        content=content,
        reads=extract_paths(content, READ_PATTERNS) + _extract_variable_paths(content, READ_VARIABLE_PATTERNS, assignments),
        writes=extract_paths(content, WRITE_PATTERNS) + _extract_variable_paths(content, WRITE_VARIABLE_PATTERNS, assignments),
        uses_randomness=uses_randomness,
        seeds_randomness=seeds_randomness,
    )


def _python_randomness_flags(content: str) -> tuple[bool, bool]:
    """Detect actual randomness calls in Python code while ignoring comments and strings."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return (
            any(pattern.search(content) for pattern in RANDOM_USAGE_PATTERNS),
            any(pattern.search(content) for pattern in SEED_PATTERNS),
        )

    uses_randomness = False
    seeds_randomness = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        call_name = _call_name(node.func)
        if call_name in SEED_CALL_NAMES:
            seeds_randomness = True
        if call_name in TORCH_RANDOM_CALLS or call_name in JAX_RANDOM_CALLS or any(
            call_name.startswith(prefix) for prefix in RANDOM_USAGE_CALL_PREFIXES
        ):
            uses_randomness = True
    return uses_randomness, seeds_randomness


def _call_name(node: ast.AST) -> str:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _nextflow_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) < 3 or tokens[:2] != ["nextflow", "run"]:
        return None

    pipeline = ""
    profiles: list[str] = []
    entry = ""
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token in NEXTFLOW_VALUE_OPTIONS:
            value = tokens[index + 1] if index + 1 < len(tokens) else ""
            if token == "-profile":
                profiles.extend(profile.strip() for profile in value.split(",") if profile.strip())
            elif token == "-entry":
                entry = value
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in NEXTFLOW_VALUE_OPTIONS):
            option, value = token.split("=", 1)
            if option == "-profile":
                profiles.extend(profile.strip() for profile in value.split(",") if profile.strip())
            elif option == "-entry":
                entry = value
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if not pipeline:
            pipeline = token
        index += 1

    if not pipeline or NEXTFLOW_REMOTE_PIPELINE_PATTERN.match(pipeline):
        return None

    return ReadmeReference(
        command=command,
        referenced_path=pipeline,
        package_manager="nextflow",
        nextflow_pipeline=pipeline,
        nextflow_profiles=tuple(profiles),
        nextflow_entry=entry,
    )


def _cromwell_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None

    args: list[str]
    if len(tokens) >= 3 and tokens[0] == "cromwell" and tokens[1] == "run":
        args = tokens[2:]
    elif tokens and tokens[0] == "java" and "-jar" in tokens:
        jar_index = tokens.index("-jar")
        run_index = jar_index + 2
        if run_index >= len(tokens) or tokens[run_index] != "run":
            return None
        args = tokens[run_index + 1 :]
    else:
        return None

    workflow = ""
    inputs: list[str] = []
    workflow_root = ""
    index = 0
    while index < len(args):
        token = args[index]
        if token in CROMWELL_VALUE_OPTIONS:
            value = args[index + 1] if index + 1 < len(args) else ""
            if token in CROMWELL_INPUT_OPTIONS and value:
                inputs.append(value)
            elif token in CROMWELL_WORKFLOW_ROOT_OPTIONS:
                workflow_root = value
            index += 2
            continue
        option_with_value = next(
            (option for option in CROMWELL_VALUE_OPTIONS if token.startswith(f"{option}=")),
            "",
        )
        if option_with_value:
            value = token.split("=", 1)[1]
            if option_with_value in CROMWELL_INPUT_OPTIONS and value:
                inputs.append(value)
            elif option_with_value in CROMWELL_WORKFLOW_ROOT_OPTIONS:
                workflow_root = value
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if not workflow:
            workflow = token
        index += 1

    if not workflow or workflow.startswith(("http://", "https://", "gs://", "s3://")):
        return None

    return ReadmeReference(
        command=command,
        referenced_path=workflow,
        package_manager="cromwell",
        wdl_workflow=workflow,
        wdl_inputs=tuple(inputs),
        wdl_workflow_root=workflow_root,
    )


def _cwl_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens or tokens[0] not in {"cwltool", "cwl-runner"}:
        return None

    positional: list[str] = []
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in CWL_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in CWL_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        positional.append(token)
        index += 1

    if not positional:
        return None
    workflow = positional[0]
    if workflow.startswith(("http://", "https://", "gs://", "s3://")):
        return None
    job = positional[1] if len(positional) > 1 else ""

    return ReadmeReference(
        command=command,
        referenced_path=workflow,
        package_manager="cwl",
        cwl_workflow=workflow,
        cwl_job=job,
    )


def _is_remote_path(reference: str) -> bool:
    return reference.startswith(("http://", "https://", "gs://", "s3://", "az://"))


def _papermill_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens or tokens[0] != "papermill":
        return None

    positional: list[str] = []
    parameter_files: list[str] = []
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in PAPERMILL_PARAMETER_FILE_OPTIONS:
            value = tokens[index + 1] if index + 1 < len(tokens) else ""
            if value:
                parameter_files.append(value)
            index += 2
            continue
        parameter_option = next(
            (option for option in PAPERMILL_PARAMETER_FILE_OPTIONS if token.startswith(f"{option}=")),
            "",
        )
        if parameter_option:
            value = token.split("=", 1)[1]
            if value:
                parameter_files.append(value)
            index += 1
            continue
        if token in PAPERMILL_TWO_VALUE_OPTIONS:
            index += 3
            continue
        if token in PAPERMILL_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in PAPERMILL_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        positional.append(token)
        index += 1

    input_notebook = positional[0] if positional else ""
    local_input = input_notebook if input_notebook and not _is_remote_path(input_notebook) else ""
    local_parameter_files = tuple(path for path in parameter_files if not _is_remote_path(path))
    if not local_input and not local_parameter_files:
        return None

    return ReadmeReference(
        command=command,
        referenced_path=local_input or (local_parameter_files[0] if local_parameter_files else ""),
        package_manager="papermill",
        papermill_input=local_input,
        papermill_parameter_files=local_parameter_files,
    )


def _is_dynamic_dvc_target(target: str) -> bool:
    return any(marker in target for marker in ("*", "?", "[", "]", "{", "}", "$"))


def _dvc_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) < 2 or tokens[0] != "dvc" or tokens[1] not in {"repro", "pull"}:
        return None

    targets: list[str] = []
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token in DVC_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in DVC_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if not _is_remote_path(token) and not token.startswith(("$", "${", "~", "<")) and not _is_dynamic_dvc_target(token):
            targets.append(token)
        index += 1

    if not targets:
        return None

    return ReadmeReference(
        command=command,
        referenced_path=targets[0],
        package_manager="dvc",
        dvc_command=tokens[1],
        dvc_targets=tuple(targets),
    )


def _quarto_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) < 2 or tokens[:2] != ["quarto", "render"]:
        return None

    target = ""
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token in QUARTO_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in QUARTO_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        target = token
        break

    if (
        not target
        or target == "-"
        or _is_remote_path(target)
        or target.startswith(("$", "${", "~", "<"))
        or _is_dynamic_dvc_target(target)
    ):
        return None

    return ReadmeReference(
        command=command,
        referenced_path=target,
        package_manager="quarto",
        quarto_target=target,
    )


def _is_jupytext_target(target: str) -> bool:
    suffix = Path(target.replace("\\", "/")).suffix.lower()
    return suffix in JUPYTEXT_TARGET_SUFFIXES


def _jupytext_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if not tokens or tokens[0] != "jupytext" or "--sync" not in tokens:
        return None

    targets: list[str] = []
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token in JUPYTEXT_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in JUPYTEXT_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if (
            not _is_remote_path(token)
            and not token.startswith(("$", "${", "~", "<"))
            and not _is_dynamic_dvc_target(token)
            and _is_jupytext_target(token)
        ):
            targets.append(token)
        index += 1

    if not targets:
        return None

    return ReadmeReference(
        command=command,
        referenced_path=targets[0],
        package_manager="jupytext",
        jupytext_targets=tuple(targets),
    )


def _split_kedro_pipeline_names(value: str) -> list[str]:
    names = [name.strip() for name in value.split(",")]
    return [
        name
        for name in names
        if name and name != "__default__" and re.fullmatch(r"[A-Za-z0-9_.:-]+", name)
    ]


def _kedro_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) < 2 or tokens[:2] != ["kedro", "run"]:
        return None

    pipelines: list[str] = []
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token in KEDRO_PIPELINE_OPTIONS:
            value = tokens[index + 1] if index + 1 < len(tokens) else ""
            pipelines.extend(_split_kedro_pipeline_names(value))
            index += 2
            continue
        option_with_value = next(
            (option for option in KEDRO_PIPELINE_OPTIONS if token.startswith(f"{option}=")),
            "",
        )
        if option_with_value:
            pipelines.extend(_split_kedro_pipeline_names(token.split("=", 1)[1]))
            index += 1
            continue
        if token.startswith("-p") and not token.startswith("--") and len(token) > 2:
            pipelines.extend(_split_kedro_pipeline_names(token[2:]))
            index += 1
            continue
        index += 1

    if not pipelines:
        return None

    return ReadmeReference(
        command=command,
        referenced_path="pipeline_registry.py",
        package_manager="kedro",
        kedro_pipelines=tuple(dict.fromkeys(pipelines)),
    )


def _prefect_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 4 or tokens[:3] != ["prefect", "deployment", "run"]:
        return None

    deployment_ref = ""
    index = 3
    while index < len(tokens):
        token = tokens[index]
        if token in PREFECT_DEPLOYMENT_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in PREFECT_DEPLOYMENT_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        deployment_ref = token
        break

    if not deployment_ref or "/" not in deployment_ref:
        return None
    flow_name, deployment_name = deployment_ref.split("/", 1)
    if (
        not flow_name
        or not deployment_name
        or _is_remote_path(deployment_ref)
        or deployment_ref.startswith(("$", "${", "~", "<"))
        or _is_dynamic_dvc_target(deployment_ref)
    ):
        return None

    return ReadmeReference(
        command=command,
        referenced_path=deployment_ref,
        package_manager="prefect",
        prefect_flow=flow_name,
        prefect_deployment=deployment_name,
    )


def _is_local_project_reference(reference: str) -> bool:
    return bool(reference) and not (
        _is_remote_path(reference)
        or reference.startswith(("git@", "runs:/", "models:/", "$", "${", "~", "<"))
        or _is_dynamic_dvc_target(reference)
    )


def _mlflow_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[:2] != ["mlflow", "run"]:
        return None

    project = ""
    entry_point = ""
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token in MLFLOW_RUN_ENTRY_OPTIONS:
            entry_point = tokens[index + 1] if index + 1 < len(tokens) else ""
            index += 2
            continue
        entry_option = next(
            (option for option in MLFLOW_RUN_ENTRY_OPTIONS if token.startswith(f"{option}=")),
            "",
        )
        if entry_option:
            entry_point = token.split("=", 1)[1]
            index += 1
            continue
        if token in MLFLOW_RUN_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in MLFLOW_RUN_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if not project:
            project = token
        index += 1

    if not entry_point or not _is_local_project_reference(project) or not _is_local_project_reference(entry_point):
        return None

    return ReadmeReference(
        command=command,
        referenced_path=project,
        package_manager="mlflow",
        mlflow_project=project,
        mlflow_entry_point=entry_point,
    )


def _is_local_dbt_selector(selector: str) -> bool:
    value = selector.strip()
    if not value:
        return False
    normalized = value.lstrip("@+").rstrip("+")
    if not normalized:
        return False
    if normalized.startswith(("$", "${", "~", "<")) or _is_remote_path(normalized) or _is_dynamic_dvc_target(normalized):
        return False
    if ":" in normalized:
        method, target = normalized.split(":", 1)
        return method in {"file", "path", "selector"} and bool(target) and not _is_dynamic_dvc_target(target)
    return bool(re.fullmatch(r"[A-Za-z0-9_./:-]+", normalized))


def _split_dbt_selector_values(value: str) -> list[str]:
    selectors: list[str] = []
    for comma_part in value.split(","):
        selector = comma_part.strip()
        if selector and _is_local_dbt_selector(selector):
            selectors.append(selector)
    return selectors


def _dbt_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "dbt" or tokens[1] not in {"run", "test", "build", "ls", "list"}:
        return None

    selectors: list[str] = []
    index = 2
    while index < len(tokens):
        token = tokens[index]
        selector_option = next((option for option in DBT_SELECTOR_OPTIONS if token.startswith(f"{option}=")), "")
        if selector_option:
            selectors.extend(_split_dbt_selector_values(token.split("=", 1)[1]))
            index += 1
            continue
        named_selector_option = next(
            (option for option in DBT_NAMED_SELECTOR_OPTIONS if token.startswith(f"{option}=")),
            "",
        )
        if named_selector_option:
            value = token.split("=", 1)[1]
            selectors.extend(_split_dbt_selector_values(f"selector:{value}"))
            index += 1
            continue
        if token in DBT_SELECTOR_OPTIONS:
            index += 1
            while index < len(tokens) and not tokens[index].startswith("-"):
                selectors.extend(_split_dbt_selector_values(tokens[index]))
                index += 1
            continue
        if token in DBT_NAMED_SELECTOR_OPTIONS:
            value = tokens[index + 1] if index + 1 < len(tokens) else ""
            selectors.extend(_split_dbt_selector_values(f"selector:{value}"))
            index += 2
            continue
        if token in DBT_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in DBT_VALUE_OPTIONS):
            index += 1
            continue
        index += 1

    if not selectors:
        return None

    return ReadmeReference(
        command=command,
        referenced_path="models",
        package_manager="dbt",
        dbt_selectors=tuple(dict.fromkeys(selectors)),
    )


def _is_local_gx_checkpoint(value: str) -> bool:
    return bool(value) and not (
        value.startswith(("$", "${", "~", "<"))
        or _is_remote_path(value)
        or _is_dynamic_dvc_target(value)
        or not re.fullmatch(r"[A-Za-z0-9_.:-]+", value)
    )


def _gx_checkpoint_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 4 or tokens[0] not in {"great_expectations", "gx"} or tokens[1:3] != ["checkpoint", "run"]:
        return None

    checkpoint = ""
    index = 3
    while index < len(tokens):
        token = tokens[index]
        checkpoint_option = next((option for option in GX_CHECKPOINT_NAME_OPTIONS if token.startswith(f"{option}=")), "")
        if checkpoint_option:
            checkpoint = token.split("=", 1)[1]
            break
        if token in GX_CHECKPOINT_NAME_OPTIONS:
            checkpoint = tokens[index + 1] if index + 1 < len(tokens) else ""
            break
        if token in GX_CHECKPOINT_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in GX_CHECKPOINT_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        checkpoint = token
        break

    if not _is_local_gx_checkpoint(checkpoint):
        return None

    return ReadmeReference(
        command=command,
        referenced_path="great_expectations/checkpoints",
        package_manager="great_expectations",
        gx_checkpoint=checkpoint,
    )


def _is_local_ploomber_task(value: str) -> bool:
    task = value.strip().strip("'\"")
    return bool(task) and not (
        task.startswith(("$", "${", "~", "<"))
        or _is_remote_path(task)
        or _is_dynamic_dvc_target(task)
        or not re.fullmatch(r"[A-Za-z0-9_.:-]+", task)
    )


def _split_ploomber_tasks(value: str) -> list[str]:
    tasks: list[str] = []
    for comma_part in value.split(","):
        task = comma_part.strip()
        if _is_local_ploomber_task(task):
            tasks.append(task)
    return tasks


def _ploomber_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "ploomber" or tokens[1] not in {"build", "task"}:
        return None

    tasks: list[str] = []
    if tokens[1] == "task":
        index = 2
        while index < len(tokens):
            token = tokens[index]
            if token in PLOOMBER_VALUE_OPTIONS:
                index += 2
                continue
            if any(token.startswith(f"{option}=") for option in PLOOMBER_VALUE_OPTIONS):
                index += 1
                continue
            if token.startswith("-"):
                index += 1
                continue
            tasks.extend(_split_ploomber_tasks(token))
            break
    else:
        index = 2
        while index < len(tokens):
            token = tokens[index]
            partial_option = next((option for option in PLOOMBER_PARTIAL_OPTIONS if token.startswith(f"{option}=")), "")
            if partial_option:
                tasks.extend(_split_ploomber_tasks(token.split("=", 1)[1]))
                index += 1
                continue
            if token in PLOOMBER_PARTIAL_OPTIONS:
                index += 1
                while index < len(tokens) and not tokens[index].startswith("-"):
                    tasks.extend(_split_ploomber_tasks(tokens[index]))
                    index += 1
                continue
            if token in PLOOMBER_VALUE_OPTIONS:
                index += 2
                continue
            if any(token.startswith(f"{option}=") for option in PLOOMBER_VALUE_OPTIONS):
                index += 1
                continue
            index += 1

    if not tasks:
        return None

    return ReadmeReference(
        command=command,
        referenced_path="pipeline.yaml",
        package_manager="ploomber",
        ploomber_tasks=tuple(dict.fromkeys(tasks)),
    )


def _is_local_luigi_task(value: str) -> bool:
    task = value.strip().strip("'\"")
    return bool(task) and not (
        task.startswith(("$", "${", "~", "<"))
        or _is_remote_path(task)
        or _is_dynamic_dvc_target(task)
        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:-]*", task)
    )


def _luigi_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 2 or tokens[0] != "luigi":
        return None

    module = ""
    task = ""
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--module":
            module = tokens[index + 1] if index + 1 < len(tokens) else ""
            index += 2
            continue
        if token.startswith("--module="):
            module = token.split("=", 1)[1]
            index += 1
            continue
        if token in LUIGI_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in LUIGI_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        task = token
        break

    if not _is_local_luigi_task(task):
        return None
    if module and not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", module):
        return None

    return ReadmeReference(
        command=command,
        referenced_path=f"{module.replace('.', '/')}.py" if module else "",
        package_manager="luigi",
        luigi_module=module,
        luigi_task=task,
    )


def _is_local_meltano_job(value: str) -> bool:
    job = value.strip().strip("'\"")
    return bool(job) and not (
        job.startswith(("$", "${", "~", "<"))
        or _is_remote_path(job)
        or _is_dynamic_dvc_target(job)
        or ":" in job
        or "/" in job
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", job)
    )


def _skip_meltano_value_option(tokens: list[str], index: int, value_options: set[str]) -> int:
    token = tokens[index]
    if token in value_options:
        return index + 2
    if any(token.startswith(f"{option}=") for option in value_options):
        return index + 1
    return index


def _meltano_run_reference_from_tokens(command: str, tokens: list[str], run_index: int) -> ReadmeReference | None:
    positional: list[str] = []
    index = run_index + 1
    while index < len(tokens):
        skipped_index = _skip_meltano_value_option(tokens, index, MELTANO_RUN_VALUE_OPTIONS)
        if skipped_index != index:
            index = skipped_index
            continue

        token = tokens[index]
        if token.startswith("-"):
            index += 1
            continue
        positional.append(token)
        index += 1

    # Multi-step Meltano commands usually name plugins, not a single job target.
    if len(positional) != 1:
        return None
    job = positional[0]
    if not _is_local_meltano_job(job):
        return None

    return ReadmeReference(
        command=command,
        referenced_path="meltano.yml",
        package_manager="meltano",
        meltano_jobs=(job,),
    )


def _meltano_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "meltano":
        return None

    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "run":
            return _meltano_run_reference_from_tokens(command, tokens, index)

        skipped_index = _skip_meltano_value_option(tokens, index, MELTANO_GLOBAL_VALUE_OPTIONS)
        if skipped_index != index:
            index = skipped_index
            continue
        if token.startswith("-"):
            index += 1
            continue
        return None

    return None


def _is_local_flyte_script(value: str) -> bool:
    script = value.strip().strip("'\"").replace("\\", "/")
    return bool(script) and not (
        script.startswith(("$", "${", "~", "/", "<"))
        or _is_remote_path(script)
        or _is_dynamic_dvc_target(script)
        or ".." in Path(script).parts
        or not script.endswith(".py")
    )


def _is_local_flyte_target(value: str) -> bool:
    target = value.strip().strip("'\"")
    return bool(target) and not (
        target.startswith(("$", "${", "~", "<"))
        or _is_remote_path(target)
        or _is_dynamic_dvc_target(target)
        or "/" in target
        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", target)
    )


def _flyte_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 4 or tokens[0] not in {"flyte", "pyflyte"}:
        return None

    try:
        run_index = tokens.index("run")
    except ValueError:
        return None

    positionals: list[str] = []
    index = run_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token in FLYTE_RUN_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in FLYTE_RUN_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        positionals.append(token)
        if len(positionals) >= 2:
            break
        index += 1

    if len(positionals) < 2:
        return None
    script, target = positionals[0], positionals[1]
    if script in {"deployed-task", "python-script"}:
        return None
    if not _is_local_flyte_script(script) or not _is_local_flyte_target(target):
        return None

    return ReadmeReference(
        command=command,
        referenced_path=script,
        package_manager="flyte",
        flyte_script=script,
        flyte_target=target,
    )


def _is_local_argo_workflow_file(value: str) -> bool:
    workflow = value.strip().strip("'\"").replace("\\", "/")
    return bool(workflow) and not (
        workflow.startswith(("$", "${", "~", "/", "<", "-"))
        or _is_remote_path(workflow)
        or _is_dynamic_dvc_target(workflow)
        or ".." in Path(workflow).parts
        or Path(workflow).suffix.lower() not in {".yml", ".yaml", ".json"}
    )


def _is_local_argo_entrypoint(value: str) -> bool:
    entrypoint = value.strip().strip("'\"")
    return bool(entrypoint) and not (
        entrypoint.startswith(("$", "${", "~", "<"))
        or _is_remote_path(entrypoint)
        or _is_dynamic_dvc_target(entrypoint)
        or not re.fullmatch(r"[A-Za-z0-9_.:-]+", entrypoint)
    )


def _argo_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[:2] != ["argo", "submit"]:
        return None

    workflow = ""
    entrypoint = ""
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token in ARGO_SUBMIT_FROM_OPTIONS or any(token.startswith(f"{option}=") for option in ARGO_SUBMIT_FROM_OPTIONS):
            return None
        if token in ARGO_SUBMIT_ENTRYPOINT_OPTIONS:
            entrypoint = tokens[index + 1] if index + 1 < len(tokens) else ""
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in ARGO_SUBMIT_ENTRYPOINT_OPTIONS):
            entrypoint = token.split("=", 1)[1]
            index += 1
            continue
        if token in ARGO_SUBMIT_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in ARGO_SUBMIT_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if not workflow and _is_local_argo_workflow_file(token):
            workflow = token.replace("\\", "/")
        index += 1

    if not workflow:
        return None
    if entrypoint and not _is_local_argo_entrypoint(entrypoint):
        return None

    return ReadmeReference(
        command=command,
        referenced_path=workflow,
        package_manager="argo",
        argo_workflow=workflow,
        argo_entrypoint=entrypoint,
    )


def _is_local_tekton_file(value: str) -> bool:
    tekton_file = value.strip().strip("'\"").replace("\\", "/")
    return bool(tekton_file) and not (
        tekton_file.startswith(("$", "${", "~", "/", "<", "-"))
        or _is_remote_path(tekton_file)
        or _is_dynamic_dvc_target(tekton_file)
        or ".." in Path(tekton_file).parts
        or Path(tekton_file).suffix.lower() not in {".yml", ".yaml", ".json"}
    )


def _is_local_tekton_name(value: str) -> bool:
    name = value.strip().strip("'\"")
    return bool(name) and not (
        name.startswith(("$", "${", "~", "<", "-"))
        or _is_remote_path(name)
        or _is_dynamic_dvc_target(name)
        or "=" in name
        or "/" in name
        or not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
    )


def _tekton_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 4 or tokens[0] != "tkn" or tokens[1] not in {"pipeline", "task"} or tokens[2] != "start":
        return None

    kind = tokens[1]
    name = ""
    filename = ""
    index = 3
    while index < len(tokens):
        token = tokens[index]
        if token in TEKTON_REMOTE_OPTIONS or any(token.startswith(f"{option}=") for option in TEKTON_REMOTE_OPTIONS):
            return None
        if token in TEKTON_FILENAME_OPTIONS:
            value = tokens[index + 1] if index + 1 < len(tokens) else ""
            if _is_local_tekton_file(value):
                filename = value.replace("\\", "/")
            else:
                return None
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in TEKTON_FILENAME_OPTIONS):
            value = token.split("=", 1)[1]
            if _is_local_tekton_file(value):
                filename = value.replace("\\", "/")
            else:
                return None
            index += 1
            continue
        if token in TEKTON_START_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in TEKTON_START_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        if not name and _is_local_tekton_name(token):
            name = token
        index += 1

    if not filename and not name:
        return None

    return ReadmeReference(
        command=command,
        referenced_path=filename,
        package_manager="tekton",
        tekton_kind=kind,
        tekton_name=name,
        tekton_file=filename,
    )


def _is_local_ray_script(value: str) -> bool:
    script = value.strip().strip("'\"").replace("\\", "/")
    return bool(script) and not (
        script.startswith(("$", "${", "~", "/", "<", "-"))
        or Path(script).drive
        or _is_remote_path(script)
        or _is_dynamic_dvc_target(script)
        or ".." in Path(script).parts
        or Path(script).suffix.lower() != ".py"
    )


def _is_local_ray_module(value: str) -> bool:
    module = value.strip().strip("'\"")
    return bool(module) and not (
        module.startswith(("$", "${", "~", "<", "-"))
        or _is_remote_path(module)
        or _is_dynamic_dvc_target(module)
        or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+", module)
    )


def _ray_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 5 or tokens[:3] != ["ray", "job", "submit"]:
        return None

    try:
        separator_index = tokens.index("--")
    except ValueError:
        return None
    entrypoint = tokens[separator_index + 1 :]
    if len(entrypoint) >= 2 and entrypoint[:2] == ["uv", "run"]:
        entrypoint = entrypoint[2:]
    if len(entrypoint) < 2 or entrypoint[0] not in {"python", "python3"}:
        return None

    if entrypoint[1] == "-m":
        if len(entrypoint) < 3 or not _is_local_ray_module(entrypoint[2]):
            return None
        return ReadmeReference(
            command=command,
            referenced_path="",
            package_manager="ray",
            ray_module=entrypoint[2],
        )

    if not _is_local_ray_script(entrypoint[1]):
        return None
    script = entrypoint[1].replace("\\", "/")
    return ReadmeReference(
        command=command,
        referenced_path=script,
        package_manager="ray",
        ray_script=script,
    )


def _is_remote_dagger_module(value: str) -> bool:
    module = value.strip().strip("'\"")
    return (
        _is_remote_path(module)
        or module.startswith(("github.com/", "gitlab.com/", "bitbucket.org/"))
        or module.startswith(("git@", "ssh://"))
        or "@" in module
    )


def _is_local_dagger_module(value: str) -> bool:
    module = value.strip().strip("'\"").replace("\\", "/")
    return bool(module) and not (
        module.startswith(("$", "${", "~", "/", "<", "-"))
        or Path(module).drive
        or _is_remote_dagger_module(module)
        or _is_dynamic_dvc_target(module)
        or ".." in Path(module).parts
    )


def _is_local_dagger_function(value: str) -> bool:
    function = value.strip().strip("'\"")
    return bool(function) and not (
        function.startswith(("$", "${", "~", "<", "-"))
        or _is_remote_path(function)
        or _is_dynamic_dvc_target(function)
        or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:-]*", function)
    )


def _dagger_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "dagger":
        return None

    module = ""
    call_index = -1
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "call":
            call_index = index
            break
        if token in DAGGER_NO_MODULE_OPTIONS or any(token.startswith(f"{option}=") for option in DAGGER_NO_MODULE_OPTIONS):
            return None
        if token in DAGGER_MODULE_OPTIONS:
            module = tokens[index + 1] if index + 1 < len(tokens) else ""
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in DAGGER_MODULE_OPTIONS):
            module = token.split("=", 1)[1]
            index += 1
            continue
        if token in DAGGER_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in DAGGER_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        return None

    if call_index < 0:
        return None
    if module:
        if not _is_local_dagger_module(module):
            return None
        module = module.replace("\\", "/").removeprefix("./").rstrip("/")

    function = ""
    index = call_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token in DAGGER_NO_MODULE_OPTIONS or any(token.startswith(f"{option}=") for option in DAGGER_NO_MODULE_OPTIONS):
            return None
        if token in DAGGER_MODULE_OPTIONS:
            module = tokens[index + 1] if index + 1 < len(tokens) else ""
            if not _is_local_dagger_module(module):
                return None
            module = module.replace("\\", "/").removeprefix("./").rstrip("/")
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in DAGGER_MODULE_OPTIONS):
            module = token.split("=", 1)[1]
            if not _is_local_dagger_module(module):
                return None
            module = module.replace("\\", "/").removeprefix("./").rstrip("/")
            index += 1
            continue
        if token in DAGGER_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in DAGGER_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        function = token
        break

    if not _is_local_dagger_function(function):
        return None
    referenced_path = f"{module}/dagger.json" if module else "dagger.json"
    return ReadmeReference(
        command=command,
        referenced_path=referenced_path,
        package_manager="dagger",
        dagger_module=module,
        dagger_function=function,
    )


def _is_local_bazel_target(value: str) -> bool:
    target = value.strip().strip("'\"")
    if not target or target.startswith(("$", "${", "~", "<", "-", "@")):
        return False
    if _is_remote_path(target) or _is_dynamic_dvc_target(target.replace("...", "")):
        return False
    if target.startswith("//"):
        package_part = target[2:].split(":", 1)[0]
        if ".." in Path(package_part).parts:
            return False
        return bool(re.fullmatch(r"//[A-Za-z0-9_./+-]*(?::[A-Za-z0-9_./+*=:-]+)?(?:\.\.\.)?", target))
    if target.startswith(":"):
        return bool(re.fullmatch(r":[A-Za-z0-9_./+*=:-]+", target))
    return False


def _bazel_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "bazel":
        return None

    command_index = -1
    bazel_command = ""
    for index, token in enumerate(tokens[1:], start=1):
        if token in BAZEL_COMMANDS:
            command_index = index
            bazel_command = token
            break
    if command_index < 0:
        return None

    targets: list[str] = []
    index = command_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token.startswith("--") or token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in BAZEL_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        if _is_local_bazel_target(token):
            targets.append(token)
        index += 1

    if not targets:
        return None
    return ReadmeReference(
        command=command,
        referenced_path="BUILD",
        package_manager="bazel",
        bazel_command=bazel_command,
        bazel_targets=tuple(dict.fromkeys(targets)),
    )


def _is_local_pants_spec(value: str) -> bool:
    spec = value.strip().strip("'\"")
    if not spec or spec.startswith(("$", "${", "~", "<", "-", "@")):
        return False
    if _is_remote_path(spec) or _is_dynamic_dvc_target(spec.replace("::", "").replace("#", "")):
        return False
    normalized = spec.removeprefix("//")
    path_part = normalized.split(":", 1)[0].split("#", 1)[0]
    if ".." in Path(path_part).parts:
        return False
    return bool(re.fullmatch(r"(?://)?[A-Za-z0-9_./+-]*(?::[A-Za-z0-9_./+*=,@-]*)?(?:::)?(?:#[A-Za-z0-9_.+-]+)?", spec))


def _pants_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] not in {"pants", "./pants"}:
        return None

    goal_index = -1
    goal = ""
    for index, token in enumerate(tokens[1:], start=1):
        if token in PANTS_GOALS:
            goal_index = index
            goal = token
            break
    if goal_index < 0:
        return None

    specs: list[str] = []
    index = goal_index + 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token.startswith("--") or token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in PANTS_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        if _is_local_pants_spec(token):
            specs.append(token)
        index += 1

    if not specs:
        return None
    return ReadmeReference(
        command=command,
        referenced_path="pants.toml",
        package_manager="pants",
        pants_goal=goal,
        pants_specs=tuple(dict.fromkeys(specs)),
    )


def _is_local_nix_installable(value: str) -> bool:
    installable = value.strip().strip("'\"")
    if not installable or installable.startswith(("$", "${", "~", "<", "-")):
        return False
    if _is_remote_path(installable) or _is_dynamic_dvc_target(installable.replace("#", "")):
        return False
    flake_ref = installable.removeprefix("path:")
    path_part, separator, attr = flake_ref.partition("#")
    if not path_part:
        path_part = "."
    if path_part in {".", "./"}:
        path_part = "."
    elif path_part.startswith("./"):
        path_part = path_part[2:].rstrip("/") or "."
    else:
        return False
    if ".." in Path(path_part).parts:
        return False
    if separator and attr and not re.fullmatch(r"[A-Za-z0-9_.+-]+", attr):
        return False
    return True


def _nix_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 2 or tokens[0] != "nix":
        return None

    if len(tokens) >= 3 and tokens[1:3] == ["flake", "check"]:
        nix_command = "flake check"
        start_index = 3
    elif tokens[1] in {"build", "run"}:
        nix_command = tokens[1]
        start_index = 2
    else:
        return None

    installables: list[str] = []
    saw_operand = False
    index = start_index
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token in NIX_TWO_VALUE_OPTIONS:
            index += 3
            continue
        if token.startswith("--") or token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in NIX_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        saw_operand = True
        if _is_local_nix_installable(token):
            installables.append(token)
        index += 1

    if nix_command == "flake check" and not installables and not saw_operand:
        installables.append(".")

    if not installables:
        return None
    return ReadmeReference(
        command=command,
        referenced_path="flake.nix",
        package_manager="nix",
        nix_command=nix_command,
        nix_installables=tuple(dict.fromkeys(installables)),
    )


def _is_local_docker_compose_file(value: str) -> bool:
    compose_file = value.strip().strip("'\"")
    if not compose_file or compose_file.startswith(("$", "${", "~", "<", "-")):
        return False
    if _is_remote_path(compose_file) or _is_dynamic_dvc_target(compose_file):
        return False
    if Path(compose_file).is_absolute() or ".." in Path(compose_file).parts:
        return False
    return Path(compose_file).suffix.lower() in {".yml", ".yaml"}


def _is_local_docker_compose_env_file(value: str) -> bool:
    env_file = value.strip().strip("'\"")
    if not env_file or env_file.startswith(("$", "${", "~", "<", "-")):
        return False
    if (
        _is_remote_path(env_file)
        or "://" in env_file
        or env_file.startswith(("git@", "github.com/", "gitlab.com/"))
        or _is_dynamic_dvc_target(env_file)
    ):
        return False
    normalized = env_file.replace("\\", "/").rstrip("/")
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        return False
    return bool(normalized)


def _is_local_docker_compose_project_dir(value: str) -> bool:
    project_dir = value.strip().strip("'\"")
    if not project_dir or project_dir.startswith(("$", "${", "~", "<", "-")):
        return False
    if (
        _is_remote_path(project_dir)
        or "://" in project_dir
        or project_dir.startswith(("git@", "github.com/", "gitlab.com/"))
        or _is_dynamic_dvc_target(project_dir)
    ):
        return False
    normalized = project_dir.replace("\\", "/").rstrip("/") or "."
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        return False
    return bool(normalized)


def _is_local_docker_compose_profile(value: str) -> bool:
    profile = value.strip().strip("'\"")
    return bool(profile) and not (
        profile.startswith(("$", "${", "~", "<", "-", "/"))
        or _is_remote_path(profile)
        or _is_dynamic_dvc_target(profile)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", profile)
    )


def _split_docker_compose_profiles(value: str) -> list[str]:
    return [profile.strip() for profile in value.split(",") if _is_local_docker_compose_profile(profile)]


def _is_local_docker_compose_service(value: str) -> bool:
    service = value.strip().strip("'\"")
    return bool(service) and not (
        service.startswith(("$", "${", "~", "<", "-", "/"))
        or _is_remote_path(service)
        or _is_dynamic_dvc_target(service)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", service)
    )


def _docker_compose_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 2:
        return None

    if tokens[0] == "docker-compose":
        index = 1
    elif len(tokens) >= 2 and tokens[:2] == ["docker", "compose"]:
        index = 2
    else:
        return None

    compose_files: list[str] = []
    env_files: list[str] = []
    project_dirs: list[str] = []
    profiles: list[str] = []
    external_compose_file = False
    external_project_dir = False
    command_name = ""
    while index < len(tokens):
        token = tokens[index]
        if token in DOCKER_COMPOSE_SERVICE_COMMANDS:
            command_name = token
            index += 1
            break
        if token in {"-f", "--file"} and index + 1 < len(tokens):
            compose_file = tokens[index + 1]
            if _is_local_docker_compose_file(compose_file):
                compose_files.append(compose_file)
            else:
                external_compose_file = True
            index += 2
            continue
        if token.startswith("--file="):
            compose_file = token.split("=", 1)[1]
            if _is_local_docker_compose_file(compose_file):
                compose_files.append(compose_file)
            else:
                external_compose_file = True
            index += 1
            continue
        if token.startswith("-f") and len(token) > 2:
            compose_file = token[2:]
            if _is_local_docker_compose_file(compose_file):
                compose_files.append(compose_file)
            else:
                external_compose_file = True
            index += 1
            continue
        if token == "--env-file" and index + 1 < len(tokens):
            env_file = tokens[index + 1]
            if _is_local_docker_compose_env_file(env_file):
                env_files.append(env_file)
            index += 2
            continue
        if token.startswith("--env-file="):
            env_file = token.split("=", 1)[1]
            if _is_local_docker_compose_env_file(env_file):
                env_files.append(env_file)
            index += 1
            continue
        if token == "--project-directory" and index + 1 < len(tokens):
            project_dir = tokens[index + 1]
            if _is_local_docker_compose_project_dir(project_dir):
                project_dirs.append(project_dir)
            else:
                external_project_dir = True
            index += 2
            continue
        if token.startswith("--project-directory="):
            project_dir = token.split("=", 1)[1]
            if _is_local_docker_compose_project_dir(project_dir):
                project_dirs.append(project_dir)
            else:
                external_project_dir = True
            index += 1
            continue
        if token == "--profile" and index + 1 < len(tokens):
            profiles.extend(_split_docker_compose_profiles(tokens[index + 1]))
            index += 2
            continue
        if token.startswith("--profile="):
            profiles.extend(_split_docker_compose_profiles(token.split("=", 1)[1]))
            index += 1
            continue
        if token.startswith("--") or token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in DOCKER_COMPOSE_GLOBAL_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        return None

    if external_compose_file or external_project_dir or not command_name:
        return None

    services: list[str] = []
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token.startswith("--") or token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in DOCKER_COMPOSE_COMMAND_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        if _is_local_docker_compose_service(token):
            services.append(token)
            if command_name in {"run", "exec"}:
                break
        index += 1

    if not services and not env_files and not project_dirs and not profiles:
        return None

    return ReadmeReference(
        command=command,
        referenced_path=compose_files[0] if compose_files else (project_dirs[0] if project_dirs else "compose.yaml"),
        package_manager="docker_compose",
        docker_compose_command=command_name,
        docker_compose_files=tuple(dict.fromkeys(compose_files)),
        docker_compose_env_files=tuple(dict.fromkeys(env_files)),
        docker_compose_project_dirs=tuple(dict.fromkeys(project_dirs)),
        docker_compose_profiles=tuple(dict.fromkeys(profiles)),
        docker_compose_services=tuple(dict.fromkeys(services)),
    )


def _is_local_dockerfile_path(value: str) -> bool:
    dockerfile = value.strip().strip("'\"")
    if not dockerfile or dockerfile.startswith(("$", "${", "~", "<", "-")):
        return False
    if _is_remote_path(dockerfile) or _is_dynamic_dvc_target(dockerfile):
        return False
    if Path(dockerfile).is_absolute() or ".." in Path(dockerfile).parts:
        return False
    return True


def _is_local_docker_build_target(value: str) -> bool:
    target = value.strip().strip("'\"")
    return bool(target) and not (
        target.startswith(("$", "${", "~", "<", "-", "/"))
        or _is_remote_path(target)
        or _is_dynamic_dvc_target(target)
        or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", target)
    )


def _docker_build_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "docker":
        return None

    if len(tokens) >= 3 and tokens[1:3] in (["buildx", "build"], ["image", "build"]):
        index = 3
    elif tokens[1] == "build":
        index = 2
    else:
        return None

    dockerfile = "Dockerfile"
    target = ""
    external_dockerfile = False
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token in {"-f", "--file"} and index + 1 < len(tokens):
            candidate = tokens[index + 1]
            if _is_local_dockerfile_path(candidate):
                dockerfile = candidate
            else:
                external_dockerfile = True
            index += 2
            continue
        if token.startswith("--file="):
            candidate = token.split("=", 1)[1]
            if _is_local_dockerfile_path(candidate):
                dockerfile = candidate
            else:
                external_dockerfile = True
            index += 1
            continue
        if token.startswith("-f") and len(token) > 2:
            candidate = token[2:]
            if _is_local_dockerfile_path(candidate):
                dockerfile = candidate
            else:
                external_dockerfile = True
            index += 1
            continue
        if token == "--target" and index + 1 < len(tokens):
            candidate = tokens[index + 1]
            if _is_local_docker_build_target(candidate):
                target = candidate
            index += 2
            continue
        if token.startswith("--target="):
            candidate = token.split("=", 1)[1]
            if _is_local_docker_build_target(candidate):
                target = candidate
            index += 1
            continue
        if token.startswith("--") or token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in DOCKER_BUILD_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        index += 1

    if external_dockerfile or not target:
        return None
    return ReadmeReference(
        command=command,
        referenced_path=dockerfile,
        package_manager="docker_build",
        docker_build_file=dockerfile,
        docker_build_target=target,
    )


def _is_local_helm_chart_path(value: str) -> bool:
    chart = value.strip().strip("'\"")
    if not chart or chart.startswith(("$", "${", "~", "<", "-")):
        return False
    if _is_remote_path(chart) or chart.startswith("oci://") or _is_dynamic_dvc_target(chart):
        return False
    normalized = chart.replace("\\", "/").rstrip("/")
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        return False
    if normalized.endswith((".tgz", ".tar.gz")):
        return False
    if normalized in {".", "./"} or normalized.startswith("./"):
        return True
    first_part = normalized.split("/", 1)[0]
    return "/" in normalized and first_part in {
        "chart",
        "charts",
        "deploy",
        "deployment",
        "deployments",
        "helm",
        "infra",
        "infrastructure",
        "k8s",
        "kubernetes",
        "ops",
    }


def _helm_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "helm" or tokens[1] not in HELM_CHART_COMMANDS:
        return None

    helm_command = tokens[1]
    positionals: list[str] = []
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token.startswith("--") or token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if token.startswith("-f") and len(token) > 2:
                index += 1
                continue
            if "=" not in token and option_name in HELM_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        positionals.append(token)
        index += 1

    chart_candidates: list[str] = []
    if helm_command in {"install", "template", "upgrade"}:
        if len(positionals) >= 2:
            chart_candidates.append(positionals[1])
        elif positionals:
            chart_candidates.append(positionals[0])
    else:
        chart_candidates.extend(positionals)

    chart_paths = [chart for chart in chart_candidates if _is_local_helm_chart_path(chart)]
    if not chart_paths:
        return None
    return ReadmeReference(
        command=command,
        referenced_path=chart_paths[0],
        package_manager="helm",
        helm_command=helm_command,
        helm_chart_paths=tuple(dict.fromkeys(chart_paths)),
    )


def _is_local_kustomize_path(value: str) -> bool:
    kustomize_path = value.strip().strip("'\"")
    if not kustomize_path or kustomize_path.startswith(("$", "${", "~", "<", "-")):
        return False
    if (
        _is_remote_path(kustomize_path)
        or kustomize_path.startswith(("git@", "github.com/", "gitlab.com/"))
        or _is_dynamic_dvc_target(kustomize_path)
    ):
        return False
    normalized = kustomize_path.replace("\\", "/").rstrip("/")
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        return False
    if normalized in {".", "./"} or normalized.startswith("./"):
        return True
    first_part = normalized.split("/", 1)[0]
    return "/" in normalized and first_part in {
        "base",
        "bases",
        "config",
        "configs",
        "deploy",
        "deployment",
        "deployments",
        "infra",
        "infrastructure",
        "k8s",
        "kubernetes",
        "manifests",
        "ops",
        "overlay",
        "overlays",
    }


def _first_kustomize_positional(tokens: list[str], start_index: int) -> str:
    index = start_index
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token.startswith("--") or token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in KUSTOMIZE_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        return token
    return ""


def _kustomize_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 2:
        return None

    kustomize_command = ""
    kustomize_paths: list[str] = []
    if len(tokens) >= 2 and tokens[:2] == ["kustomize", "build"]:
        kustomize_command = "build"
        candidate = _first_kustomize_positional(tokens, 2)
        if candidate:
            kustomize_paths.append(candidate)
    elif len(tokens) >= 2 and tokens[:2] == ["kubectl", "kustomize"]:
        kustomize_command = "kubectl kustomize"
        candidate = _first_kustomize_positional(tokens, 2)
        if candidate:
            kustomize_paths.append(candidate)
    elif len(tokens) >= 2 and tokens[0] == "kubectl" and tokens[1] in KUSTOMIZE_APPLY_COMMANDS:
        kustomize_command = f"kubectl {tokens[1]}"
        index = 2
        while index < len(tokens):
            token = tokens[index]
            if token == "--":
                break
            if token in {"-k", "--kustomize"} and index + 1 < len(tokens):
                kustomize_paths.append(tokens[index + 1])
                index += 2
                continue
            if token.startswith("--kustomize="):
                kustomize_paths.append(token.split("=", 1)[1])
                index += 1
                continue
            if token.startswith("-k="):
                kustomize_paths.append(token.split("=", 1)[1])
                index += 1
                continue
            option_name = token.split("=", 1)[0]
            if token.startswith("--") or token.startswith("-"):
                if "=" not in token and option_name in KUSTOMIZE_VALUE_OPTIONS:
                    index += 2
                    continue
                index += 1
                continue
            index += 1

    local_paths = [path for path in kustomize_paths if _is_local_kustomize_path(path)]
    if not local_paths:
        return None
    return ReadmeReference(
        command=command,
        referenced_path=local_paths[0],
        package_manager="kustomize",
        kustomize_command=kustomize_command,
        kustomize_paths=tuple(dict.fromkeys(local_paths)),
    )


def _is_local_kubernetes_manifest_path(value: str) -> bool:
    manifest_path = value.strip().strip("'\"")
    if not manifest_path or manifest_path.startswith(("$", "${", "~", "<", "-")):
        return False
    if (
        _is_remote_path(manifest_path)
        or "://" in manifest_path
        or manifest_path.startswith(("git@", "github.com/", "gitlab.com/"))
        or _is_dynamic_dvc_target(manifest_path)
    ):
        return False
    raw_normalized = manifest_path.replace("\\", "/")
    had_trailing_slash = raw_normalized.endswith("/")
    normalized = raw_normalized.rstrip("/") or "."
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        return False
    if normalized in {".", "./"} or normalized.startswith("./"):
        return True
    if normalized.endswith((".yaml", ".yml", ".json")):
        return True
    first_part = normalized.split("/", 1)[0]
    return had_trailing_slash or first_part in {
        "config",
        "configs",
        "deploy",
        "deployment",
        "deployments",
        "infra",
        "infrastructure",
        "k8s",
        "kubernetes",
        "manifest",
        "manifests",
        "ops",
    }


def _split_kubernetes_manifest_values(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _kubernetes_manifest_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "kubectl" or tokens[1] not in KUBECTL_MANIFEST_COMMANDS:
        return None

    manifests: list[str] = []
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token in KUBECTL_FILENAME_OPTIONS and index + 1 < len(tokens):
            manifests.extend(_split_kubernetes_manifest_values(tokens[index + 1]))
            index += 2
            continue
        if token.startswith("--filename=") or token.startswith("-f="):
            manifests.extend(_split_kubernetes_manifest_values(token.split("=", 1)[1]))
            index += 1
            continue
        if token.startswith("-f") and not token.startswith("--") and len(token) > 2:
            manifests.extend(_split_kubernetes_manifest_values(token[2:]))
            index += 1
            continue
        if token in {"-k", "--kustomize"} and index + 1 < len(tokens):
            index += 2
            continue
        if token.startswith("--kustomize=") or token.startswith("-k="):
            index += 1
            continue
        if token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in KUSTOMIZE_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        index += 1

    local_paths = [path for path in manifests if _is_local_kubernetes_manifest_path(path)]
    if not local_paths:
        return None
    return ReadmeReference(
        command=command,
        referenced_path=local_paths[0],
        package_manager="kubernetes",
        kubernetes_command=f"kubectl {tokens[1]}",
        kubernetes_manifest_paths=tuple(dict.fromkeys(local_paths)),
    )


def _is_local_terraform_working_dir(value: str) -> bool:
    terraform_dir = value.strip().strip("'\"")
    if not terraform_dir or terraform_dir.startswith(("$", "${", "~", "<", "-")):
        return False
    if (
        _is_remote_path(terraform_dir)
        or "://" in terraform_dir
        or terraform_dir.startswith(("git::", "git@", "github.com/", "gitlab.com/"))
        or _is_dynamic_dvc_target(terraform_dir)
    ):
        return False
    normalized = terraform_dir.replace("\\", "/").rstrip("/") or "."
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        return False
    return bool(normalized)


def _terraform_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "terraform":
        return None

    working_dir = ""
    terraform_command = ""
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token == "-chdir" and index + 1 < len(tokens):
            working_dir = tokens[index + 1]
            index += 2
            continue
        if token.startswith("-chdir="):
            working_dir = token.split("=", 1)[1]
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        terraform_command = token
        break

    if terraform_command not in TERRAFORM_COMMANDS:
        return None
    if not working_dir or not _is_local_terraform_working_dir(working_dir):
        return None
    return ReadmeReference(
        command=command,
        referenced_path=working_dir,
        package_manager="terraform",
        terraform_command=terraform_command,
        terraform_working_dirs=(working_dir,),
    )


def _is_local_pulumi_project_dir(value: str) -> bool:
    project_dir = value.strip().strip("'\"")
    if not project_dir or project_dir.startswith(("$", "${", "~", "<", "-")):
        return False
    if (
        _is_remote_path(project_dir)
        or "://" in project_dir
        or project_dir.startswith(("git::", "git@", "github.com/", "gitlab.com/"))
        or _is_dynamic_dvc_target(project_dir)
    ):
        return False
    normalized = project_dir.replace("\\", "/").rstrip("/") or "."
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        return False
    return bool(normalized)


def _pulumi_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "pulumi":
        return None

    project_dir = ""
    pulumi_command = ""
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token in {"--cwd", "-C"} and index + 1 < len(tokens):
            project_dir = tokens[index + 1]
            index += 2
            continue
        if token.startswith("--cwd=") or token.startswith("-C="):
            project_dir = token.split("=", 1)[1]
            index += 1
            continue
        if token.startswith("-C") and len(token) > 2:
            project_dir = token[2:]
            index += 1
            continue
        if token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in PULUMI_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        if not pulumi_command:
            pulumi_command = token
        index += 1

    if pulumi_command not in PULUMI_PROJECT_COMMANDS:
        return None
    if not project_dir or not _is_local_pulumi_project_dir(project_dir):
        return None
    return ReadmeReference(
        command=command,
        referenced_path=project_dir,
        package_manager="pulumi",
        pulumi_command=pulumi_command,
        pulumi_project_dirs=(project_dir,),
    )


def _is_local_ansible_path(value: str, *, playbook: bool) -> bool:
    ansible_path = value.strip().strip("'\"")
    if not ansible_path or ansible_path.startswith(("$", "${", "~", "<", "-")):
        return False
    if (
        _is_remote_path(ansible_path)
        or "://" in ansible_path
        or ansible_path.startswith(("git@", "github.com/", "gitlab.com/"))
        or _is_dynamic_dvc_target(ansible_path)
    ):
        return False
    if not playbook and "," in ansible_path:
        return False
    normalized = ansible_path.replace("\\", "/").rstrip("/")
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        return False
    if playbook:
        return normalized.endswith((".yml", ".yaml"))
    return bool(normalized)


def _ansible_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 2 or tokens[0] != "ansible-playbook":
        return None

    playbooks: list[str] = []
    inventories: list[str] = []
    index = 1
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token in ANSIBLE_INVENTORY_OPTIONS and index + 1 < len(tokens):
            inventory = tokens[index + 1]
            if _is_local_ansible_path(inventory, playbook=False):
                inventories.append(inventory)
            index += 2
            continue
        if token.startswith("--inventory=") or token.startswith("--inventory-file="):
            inventory = token.split("=", 1)[1]
            if _is_local_ansible_path(inventory, playbook=False):
                inventories.append(inventory)
            index += 1
            continue
        if token.startswith("-i") and len(token) > 2:
            inventory = token[2:]
            if _is_local_ansible_path(inventory, playbook=False):
                inventories.append(inventory)
            index += 1
            continue
        if token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in ANSIBLE_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        if _is_local_ansible_path(token, playbook=True):
            playbooks.append(token)
        index += 1

    if not playbooks and not inventories:
        return None
    return ReadmeReference(
        command=command,
        referenced_path=playbooks[0] if playbooks else inventories[0],
        package_manager="ansible",
        ansible_playbooks=tuple(dict.fromkeys(playbooks)),
        ansible_inventories=tuple(dict.fromkeys(inventories)),
    )


def _is_local_packer_template_path(value: str) -> bool:
    template_path = value.strip().strip("'\"")
    if not template_path or template_path.startswith(("$", "${", "~", "<", "-")):
        return False
    if (
        _is_remote_path(template_path)
        or "://" in template_path
        or template_path.startswith(("git@", "github.com/", "gitlab.com/"))
        or _is_dynamic_dvc_target(template_path)
    ):
        return False
    raw_normalized = template_path.replace("\\", "/")
    had_trailing_slash = raw_normalized.endswith("/")
    normalized = raw_normalized.rstrip("/") or "."
    if Path(normalized).is_absolute() or ".." in Path(normalized).parts:
        return False
    if normalized in {".", "./"} or normalized.startswith("./"):
        return True
    if normalized.endswith((".pkr.hcl", ".pkr.json")):
        return True
    return had_trailing_slash or "/" in normalized or normalized in {
        "build",
        "builds",
        "image",
        "images",
        "packer",
        "template",
        "templates",
    }


def _packer_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3 or tokens[0] != "packer" or tokens[1] not in PACKER_TEMPLATE_COMMANDS:
        return None

    packer_command = tokens[1]
    templates: list[str] = []
    index = 2
    while index < len(tokens):
        token = tokens[index]
        if token == "--":
            break
        if token.startswith("-"):
            option_name = token.split("=", 1)[0]
            if "=" not in token and option_name in PACKER_VALUE_OPTIONS:
                index += 2
                continue
            index += 1
            continue
        if _is_local_packer_template_path(token):
            templates.append(token)
        index += 1

    if not templates:
        return None
    return ReadmeReference(
        command=command,
        referenced_path=templates[0],
        package_manager="packer",
        packer_command=packer_command,
        packer_templates=tuple(dict.fromkeys(templates)),
    )


def _is_local_dagster_target(value: str) -> bool:
    target = value.strip().strip("'\"")
    return bool(target) and not (
        target.startswith(("$", "${", "~", "<"))
        or _is_remote_path(target)
        or _is_dynamic_dvc_target(target)
        or not re.fullmatch(r"[A-Za-z0-9_./:-]+", target)
    )


def _split_dagster_targets(value: str) -> list[str]:
    targets: list[str] = []
    for comma_part in value.split(","):
        target = comma_part.strip()
        if target and _is_local_dagster_target(target):
            targets.append(target)
    return targets


def _collect_dagster_option_values(tokens: list[str], index: int) -> tuple[list[str], int]:
    values: list[str] = []
    index += 1
    while index < len(tokens) and not tokens[index].startswith("-"):
        values.extend(_split_dagster_targets(tokens[index]))
        index += 1
    return values, index


def _dagster_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 3:
        return None

    start = 0
    if tokens[0:2] == ["dg", "launch"]:
        start = 2
    elif (
        len(tokens) >= 4
        and tokens[0:2] == ["dagster", "job"]
        and tokens[2] in {"execute", "launch", "backfill", "print", "scaffold_config"}
    ):
        start = 3
    elif len(tokens) >= 4 and tokens[0:3] == ["dagster", "asset", "materialize"]:
        start = 3
    else:
        return None

    jobs: list[str] = []
    assets: list[str] = []
    index = start
    while index < len(tokens):
        token = tokens[index]
        job_option = next((option for option in DAGSTER_JOB_OPTIONS if token.startswith(f"{option}=")), "")
        if job_option:
            jobs.extend(_split_dagster_targets(token.split("=", 1)[1]))
            index += 1
            continue
        asset_option = next((option for option in DAGSTER_ASSET_OPTIONS if token.startswith(f"{option}=")), "")
        if asset_option:
            assets.extend(_split_dagster_targets(token.split("=", 1)[1]))
            index += 1
            continue
        if token in DAGSTER_JOB_OPTIONS:
            values, index = _collect_dagster_option_values(tokens, index)
            jobs.extend(values)
            continue
        if token in DAGSTER_ASSET_OPTIONS:
            values, index = _collect_dagster_option_values(tokens, index)
            assets.extend(values)
            continue
        if token in DAGSTER_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in DAGSTER_VALUE_OPTIONS):
            index += 1
            continue
        index += 1

    if not jobs and not assets:
        return None

    return ReadmeReference(
        command=command,
        referenced_path="definitions.py",
        package_manager="dagster",
        dagster_jobs=tuple(dict.fromkeys(jobs)),
        dagster_assets=tuple(dict.fromkeys(assets)),
    )


def _is_local_airflow_id(value: str) -> bool:
    return bool(value) and not (
        value.startswith(("$", "${", "~", "<"))
        or _is_remote_path(value)
        or _is_dynamic_dvc_target(value)
        or not re.fullmatch(r"[A-Za-z0-9_.:-]+", value)
    )


def _airflow_positionals(tokens: list[str], start: int, value_options: set[str]) -> list[str]:
    positionals: list[str] = []
    index = start
    while index < len(tokens):
        token = tokens[index]
        if token in value_options:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in value_options):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        positionals.append(token)
        index += 1
    return positionals


def _airflow_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 4 or tokens[0] != "airflow":
        return None

    if tokens[1:3] == ["dags", "test"]:
        positionals = _airflow_positionals(tokens, 3, AIRFLOW_DAGS_TEST_VALUE_OPTIONS)
        dag_id = positionals[0] if positionals else ""
        if not _is_local_airflow_id(dag_id):
            return None
        return ReadmeReference(
            command=command,
            referenced_path="dags",
            package_manager="airflow",
            airflow_dag_id=dag_id,
        )

    if len(tokens) >= 5 and tokens[1] == "tasks" and tokens[2] in {"test", "run"}:
        positionals = _airflow_positionals(tokens, 3, AIRFLOW_TASKS_VALUE_OPTIONS)
        dag_id = positionals[0] if positionals else ""
        task_id = positionals[1] if len(positionals) > 1 else ""
        if not _is_local_airflow_id(dag_id) or not _is_local_airflow_id(task_id):
            return None
        return ReadmeReference(
            command=command,
            referenced_path="dags",
            package_manager="airflow",
            airflow_dag_id=dag_id,
            airflow_task_id=task_id,
        )

    return None


def _metaflow_reference_from_command(command: str) -> ReadmeReference | None:
    try:
        tokens = shlex.split(command)
    except ValueError:
        return None
    if len(tokens) >= 3 and tokens[:2] == ["uv", "run"]:
        tokens = tokens[2:]
    if len(tokens) < 4 or tokens[0] not in {"python", "python3"} or not tokens[1].endswith(".py"):
        return None
    if tokens[2] != "resume":
        return None

    step = ""
    index = 3
    while index < len(tokens):
        token = tokens[index]
        if token in METAFLOW_RESUME_VALUE_OPTIONS:
            index += 2
            continue
        if any(token.startswith(f"{option}=") for option in METAFLOW_RESUME_VALUE_OPTIONS):
            index += 1
            continue
        if token.startswith("-"):
            index += 1
            continue
        step = token
        break

    if not step or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", step):
        return None

    return ReadmeReference(
        command=command,
        referenced_path=tokens[1],
        package_manager="metaflow",
        metaflow_script=tokens[1],
        metaflow_step=step,
    )


def _notebook_python_source_for_ast(source: str) -> str:
    """Strip notebook-only shell/magic lines so normal Python cells can still be analyzed."""
    lines: list[str] = []
    for index, raw_line in enumerate(source.splitlines()):
        stripped = raw_line.lstrip()
        if index == 0 and stripped.startswith("%%"):
            continue
        if stripped.startswith(("%", "!", "?")):
            continue
        magic_assignment = IPYTHON_MAGIC_ASSIGNMENT_PATTERN.match(raw_line)
        if magic_assignment:
            lines.append(f"{magic_assignment.group(1)} = None")
            continue
        lines.append(raw_line)
    return "\n".join(lines)


def analyze_readme(path: Path) -> list[ReadmeReference]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    references: list[ReadmeReference] = []
    for line in _readme_command_candidate_lines(content):
        if re.match(r"(?:uv\s+run\s+)?ray\s+job\s+submit\b", line):
            for match in re.finditer(r"(?:uv\s+run\s+)?ray\s+job\s+submit\s+[^\n`]+", line):
                reference = _ray_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?dagger\b", line):
            for match in re.finditer(r"(?:uv\s+run\s+)?dagger\s+[^\n`]*\bcall\b[^\n`]+", line):
                reference = _dagger_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?bazel\b", line):
            for match in re.finditer(r"(?:uv\s+run\s+)?bazel\s+[^\n`]*\b(?:build|test|run)\b[^\n`]+", line):
                reference = _bazel_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?(?:\./)?pants\b", line):
            for match in re.finditer(
                r"(?:uv\s+run\s+)?(?:\./)?pants\s+[^\n`]*\b(?:check|fmt|lint|package|run|test)\b[^\n`]+",
                line,
            ):
                reference = _pants_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?nix\b", line):
            for match in re.finditer(
                r"(?:uv\s+run\s+)?nix\s+(?:flake\s+check(?:\s+[^\n`]*)?|(?:build|run)\s+[^\n`]+)",
                line,
            ):
                reference = _nix_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?docker\s+(?:buildx\s+build|image\s+build|build)\b", line):
            for match in re.finditer(
                r"(?:uv\s+run\s+)?docker\s+(?:buildx\s+build|image\s+build|build)\s+[^\n`]+",
                line,
            ):
                reference = _docker_build_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?(?:docker\s+compose|docker-compose)\b", line):
            for match in re.finditer(r"(?:uv\s+run\s+)?(?:docker\s+compose|docker-compose)\s+[^\n`]+", line):
                reference = _docker_compose_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?helm\s+(?:install|template|upgrade|lint|package)\b", line):
            for match in re.finditer(
                r"(?:uv\s+run\s+)?helm\s+(?:install|template|upgrade|lint|package)\s+[^\n`]+",
                line,
            ):
                reference = _helm_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?(?:kustomize\s+build|kubectl\s+(?:apply|delete|diff|kustomize))\b", line):
            for match in re.finditer(
                r"(?:uv\s+run\s+)?(?:kustomize\s+build|kubectl\s+(?:apply|delete|diff|kustomize))\s+[^\n`]+",
                line,
            ):
                reference = _kustomize_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
                reference = _kubernetes_manifest_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?terraform\b", line):
            for match in re.finditer(r"(?:uv\s+run\s+)?terraform\s+[^\n`]*-chdir(?:=|\s+)[^\n`]+", line):
                reference = _terraform_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?pulumi\b", line):
            for match in re.finditer(r"(?:uv\s+run\s+)?pulumi\s+[^\n`]*(?:--cwd(?:=|\s+)|-C(?:=|\s*)\S)[^\n`]+", line):
                reference = _pulumi_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?ansible-playbook\b", line):
            for match in re.finditer(r"(?:uv\s+run\s+)?ansible-playbook\s+[^\n`]+", line):
                reference = _ansible_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        if re.match(r"(?:uv\s+run\s+)?packer\s+(?:build|fmt|init|inspect|validate)\b", line):
            for match in re.finditer(r"(?:uv\s+run\s+)?packer\s+(?:build|fmt|init|inspect|validate)\s+[^\n`]+", line):
                reference = _packer_reference_from_command(match.group(0))
                if reference is not None:
                    references.append(reference)
            continue
        uv_python_line = re.match(r"uv\s+run\s+python(?:3)?\s+", line) is not None
        for pattern in README_COMMAND_PATTERNS:
            if uv_python_line and not pattern.pattern.startswith("uv"):
                continue
            for match in pattern.finditer(line):
                if match.group(0).startswith("make"):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="Makefile",
                            make_target=match.group(1) or "",
                        )
                    )
                    continue
                if match.group(0).startswith("pixi run "):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="pyproject.toml",
                            package_manager="pixi",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith(("task ", "uv run task ")):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="pyproject.toml",
                            package_manager="taskipy",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith("hatch run "):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="pyproject.toml",
                            package_manager="hatch",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith("pdm run "):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="pyproject.toml",
                            package_manager="pdm",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith("nox "):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="noxfile.py",
                            package_manager="nox",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith("tox"):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="tox.ini",
                            package_manager="tox",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith("just "):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="justfile",
                            package_manager="just",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith("doit "):
                    doit_task = match.group(1)
                    if doit_task not in COMMON_DOIT_COMMANDS:
                        references.append(
                            ReadmeReference(
                                command=match.group(0),
                                referenced_path="dodo.py",
                                package_manager="doit",
                                package_script=doit_task,
                            )
                        )
                    continue
                if match.group(0).startswith(("invoke ", "inv ")):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="tasks.py",
                            package_manager="invoke",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if re.match(r"(?:bundle\s+exec\s+)?(?:bin/)?rake\s+", match.group(0)):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="Rakefile",
                            package_manager="rake",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith("snakemake "):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="Snakefile",
                            package_manager="snakemake",
                            package_script=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith("nextflow run "):
                    reference = _nextflow_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("cromwell run ", "java ")):
                    reference = _cromwell_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("cwltool ", "cwl-runner ")):
                    reference = _cwl_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith("papermill "):
                    reference = _papermill_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("dvc repro ", "dvc pull ")):
                    reference = _dvc_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith("quarto render"):
                    reference = _quarto_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith("jupytext "):
                    reference = _jupytext_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith("kedro run"):
                    reference = _kedro_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("prefect deployment run", "uv run prefect deployment run")):
                    reference = _prefect_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("mlflow run", "uv run mlflow run")):
                    reference = _mlflow_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(
                    (
                        "dbt run",
                        "dbt test",
                        "dbt build",
                        "dbt ls",
                        "dbt list",
                        "uv run dbt run",
                        "uv run dbt test",
                        "uv run dbt build",
                        "uv run dbt ls",
                        "uv run dbt list",
                    )
                ):
                    reference = _dbt_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(
                    (
                        "great_expectations checkpoint run",
                        "gx checkpoint run",
                        "uv run great_expectations checkpoint run",
                        "uv run gx checkpoint run",
                    )
                ):
                    reference = _gx_checkpoint_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(
                    (
                        "ploomber task",
                        "ploomber build",
                        "uv run ploomber task",
                        "uv run ploomber build",
                    )
                ):
                    reference = _ploomber_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("luigi ", "uv run luigi ")):
                    reference = _luigi_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("meltano ", "uv run meltano ")):
                    reference = _meltano_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("flyte ", "pyflyte ", "uv run flyte ", "uv run pyflyte ")):
                    reference = _flyte_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("argo submit ", "uv run argo submit ")):
                    reference = _argo_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(
                    (
                        "tkn pipeline start",
                        "tkn task start",
                        "uv run tkn pipeline start",
                        "uv run tkn task start",
                    )
                ):
                    reference = _tekton_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("ray job submit ", "uv run ray job submit ")):
                    reference = _ray_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("dagger ", "uv run dagger ")):
                    reference = _dagger_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("bazel ", "uv run bazel ")):
                    reference = _bazel_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("pants ", "./pants ", "uv run pants ", "uv run ./pants ")):
                    reference = _pants_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("nix ", "uv run nix ")):
                    reference = _nix_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("docker build ", "docker buildx build ", "docker image build ", "uv run docker build ", "uv run docker buildx build ", "uv run docker image build ")):
                    reference = _docker_build_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("docker compose ", "docker-compose ", "uv run docker compose ", "uv run docker-compose ")):
                    reference = _docker_compose_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("helm ", "uv run helm ")):
                    reference = _helm_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(
                    (
                        "kustomize build",
                        "kubectl apply",
                        "kubectl delete",
                        "kubectl diff",
                        "kubectl kustomize",
                        "uv run kustomize build",
                        "uv run kubectl apply",
                        "uv run kubectl delete",
                        "uv run kubectl diff",
                        "uv run kubectl kustomize",
                    )
                ):
                    reference = _kustomize_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    reference = _kubernetes_manifest_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("terraform ", "uv run terraform ")):
                    reference = _terraform_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("pulumi ", "uv run pulumi ")):
                    reference = _pulumi_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("ansible-playbook ", "uv run ansible-playbook ")):
                    reference = _ansible_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("packer ", "uv run packer ")):
                    reference = _packer_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(
                    (
                        "dg launch",
                        "dagster job execute",
                        "dagster job launch",
                        "dagster job backfill",
                        "dagster job print",
                        "dagster job scaffold_config",
                        "dagster asset materialize",
                        "uv run dg launch",
                        "uv run dagster job execute",
                        "uv run dagster job launch",
                        "uv run dagster job backfill",
                        "uv run dagster job print",
                        "uv run dagster job scaffold_config",
                        "uv run dagster asset materialize",
                    )
                ):
                    reference = _dagster_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(
                    (
                        "airflow dags test",
                        "airflow tasks test",
                        "airflow tasks run",
                        "uv run airflow dags test",
                        "uv run airflow tasks test",
                        "uv run airflow tasks run",
                    )
                ):
                    reference = _airflow_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if re.match(r"(?:uv\s+run\s+)?python(?:3)?\s+[^\s`]+\.py\s+resume\b", match.group(0)):
                    reference = _metaflow_reference_from_command(match.group(0))
                    if reference is not None:
                        references.append(reference)
                    continue
                if match.group(0).startswith(("npm run ", "pnpm run ", "yarn ")):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="package.json",
                            package_manager=match.group(1),
                            package_script=match.group(2),
                        )
                    )
                    continue
                if " -m " in match.group(0):
                    references.append(
                        ReadmeReference(
                            command=match.group(0),
                            referenced_path="",
                            module_name=match.group(1),
                        )
                    )
                    continue
                if match.group(0).startswith("uv run ") and not match.group(0).startswith(
                    ("uv run python ", "uv run python3 ")
                ):
                    project_script = match.group(1)
                    if project_script not in COMMON_UV_RUN_EXTERNAL_COMMANDS:
                        references.append(
                            ReadmeReference(
                                command=match.group(0),
                                referenced_path="pyproject.toml",
                                package_manager="uv",
                                project_script=project_script,
                            )
                        )
                    continue
                references.append(
                    ReadmeReference(
                        command=match.group(0),
                        referenced_path=match.group(1),
                    )
                )
    return references


def readme_has_run_instructions(path: Path) -> bool:
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    return any(README_RUN_INSTRUCTION_PATTERN.match(line) for line in _readme_general_candidate_lines(content))


def readme_has_dependency_setup_instructions(path: Path) -> bool:
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8")
    return any(
        README_DEPENDENCY_SETUP_PATTERN.search(line)
        for line in _readme_general_candidate_lines(content, README_DEPENDENCY_SETUP_PATTERN)
    )


def _readme_command_candidate_lines(content: str) -> list[str]:
    lines: list[str] = []
    in_fence = False
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not stripped:
            continue

        candidate = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", stripped)
        candidate = re.sub(r"^(?:[$>]\s*)", "", candidate)
        if in_fence or README_COMMAND_START_PATTERN.match(candidate):
            lines.append(candidate)
    return lines


def _readme_general_candidate_lines(content: str, pattern: re.Pattern[str] = README_RUN_INSTRUCTION_PATTERN) -> list[str]:
    lines: list[str] = []
    in_fence = False
    for raw_line in content.splitlines():
        stripped = raw_line.strip()
        if stripped.startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not stripped:
            continue

        candidate = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+)", "", stripped)
        candidate = re.sub(r"^(?:[$>]\s*)", "", candidate)
        if in_fence or pattern.search(candidate):
            lines.append(candidate)
    return lines


def _assigned_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.alias):
            names.add(node.asname or node.name.split(".")[0])
    return names


def _loaded_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            names.add(node.id)
    return names


class _LoadCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()
        self._locals_stack: list[set[str]] = []

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load):
            if any(node.id in local_names for local_names in reversed(self._locals_stack)):
                return
            self.names.add(node.id)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        self._visit_arguments(node.args)
        if node.returns is not None:
            self.visit(node.returns)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        self._visit_arguments(node.args)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension([node.elt], node.generators)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension([node.key, node.value], node.generators)

    def _visit_arguments(self, node: ast.arguments) -> None:
        for default in node.defaults:
            self.visit(default)
        for default in node.kw_defaults:
            if default is not None:
                self.visit(default)
        for arg in [*node.posonlyargs, *node.args, *node.kwonlyargs]:
            if arg.annotation is not None:
                self.visit(arg.annotation)
        if node.vararg and node.vararg.annotation is not None:
            self.visit(node.vararg.annotation)
        if node.kwarg and node.kwarg.annotation is not None:
            self.visit(node.kwarg.annotation)

    def _visit_comprehension(self, value_nodes: list[ast.AST], generators: list[ast.comprehension]) -> None:
        local_names: set[str] = set()
        self._locals_stack.append(local_names)
        try:
            for generator in generators:
                self.visit(generator.iter)
                local_names.update(_names_assigned_in_target(generator.target))
                for condition in generator.ifs:
                    self.visit(condition)
            for value_node in value_nodes:
                self.visit(value_node)
        finally:
            self._locals_stack.pop()


def _loads_in_node(node: ast.AST) -> set[str]:
    collector = _LoadCollector()
    collector.visit(node)
    return collector.names


def _names_assigned_in_target(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
    return names


def _names_assigned_in_pattern(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.MatchAs) and child.name:
            names.add(child.name)
        elif isinstance(child, ast.MatchStar) and child.name:
            names.add(child.name)
    return names


def _analyze_statements(statements: list[ast.stmt], known_names: set[str]) -> tuple[set[str], set[str]]:
    current_known = set(known_names)
    missing: set[str] = set()

    for statement in statements:
        statement_missing, statement_assigned = _analyze_statement(statement, current_known)
        missing.update(name for name in statement_missing if name not in current_known)
        current_known.update(statement_assigned)

    return missing, current_known - known_names


def _analyze_statement(statement: ast.stmt, known_names: set[str]) -> tuple[set[str], set[str]]:
    if isinstance(statement, ast.Import):
        assigned = {alias.asname or alias.name.split(".")[0] for alias in statement.names}
        return set(), assigned

    if isinstance(statement, ast.ImportFrom):
        assigned = {alias.asname or alias.name for alias in statement.names}
        return set(), assigned

    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return _loads_in_node(statement), {statement.name}

    if isinstance(statement, ast.ClassDef):
        missing = set()
        for decorator in statement.decorator_list:
            missing.update(_loads_in_node(decorator))
        for base in statement.bases:
            missing.update(_loads_in_node(base))
        for keyword in statement.keywords:
            missing.update(_loads_in_node(keyword.value))
        class_missing, _ = _analyze_statements(statement.body, set(known_names))
        missing.update(class_missing)
        return missing, {statement.name}

    if isinstance(statement, ast.Assign):
        missing = _loads_in_node(statement.value)
        assigned = set()
        for target in statement.targets:
            assigned.update(_names_assigned_in_target(target))
        return missing, assigned

    if isinstance(statement, ast.AnnAssign):
        missing = _loads_in_node(statement.annotation)
        if statement.value is not None:
            missing.update(_loads_in_node(statement.value))
            return missing, _names_assigned_in_target(statement.target)
        return missing, set()

    if isinstance(statement, ast.AugAssign):
        missing = _loads_in_node(statement.target) | _loads_in_node(statement.value)
        return missing, _names_assigned_in_target(statement.target)

    if isinstance(statement, ast.For | ast.AsyncFor):
        missing = _loads_in_node(statement.iter)
        target_names = _names_assigned_in_target(statement.target)
        body_missing, body_assigned = _analyze_statements(statement.body, known_names | target_names)
        orelse_missing, orelse_assigned = _analyze_statements(statement.orelse, known_names | target_names)
        return missing | body_missing | orelse_missing, target_names | body_assigned | orelse_assigned

    if isinstance(statement, ast.While):
        missing = _loads_in_node(statement.test)
        body_missing, body_assigned = _analyze_statements(statement.body, set(known_names))
        orelse_missing, orelse_assigned = _analyze_statements(statement.orelse, set(known_names))
        return missing | body_missing | orelse_missing, body_assigned | orelse_assigned

    if isinstance(statement, ast.If):
        missing = _loads_in_node(statement.test)
        body_missing, body_assigned = _analyze_statements(statement.body, set(known_names))
        orelse_missing, orelse_assigned = _analyze_statements(statement.orelse, set(known_names))
        return missing | body_missing | orelse_missing, body_assigned | orelse_assigned

    if isinstance(statement, ast.With | ast.AsyncWith):
        missing = set()
        assigned = set()
        current_known = set(known_names)
        for item in statement.items:
            missing.update(_loads_in_node(item.context_expr))
            if item.optional_vars is not None:
                names = _names_assigned_in_target(item.optional_vars)
                assigned.update(names)
                current_known.update(names)
        body_missing, body_assigned = _analyze_statements(statement.body, current_known)
        return missing | body_missing, assigned | body_assigned

    if isinstance(statement, ast.Try):
        body_missing, body_assigned = _analyze_statements(statement.body, set(known_names))
        orelse_missing, orelse_assigned = _analyze_statements(statement.orelse, set(known_names))
        final_missing, final_assigned = _analyze_statements(statement.finalbody, set(known_names))
        missing = body_missing | orelse_missing | final_missing
        assigned = body_assigned | orelse_assigned | final_assigned
        for handler in statement.handlers:
            handler_known = set(known_names)
            if handler.type is not None:
                missing.update(_loads_in_node(handler.type))
            if handler.name:
                handler_known.add(handler.name)
                assigned.add(handler.name)
            handler_missing, handler_assigned = _analyze_statements(handler.body, handler_known)
            missing.update(handler_missing)
            assigned.update(handler_assigned)
        return missing, assigned

    if isinstance(statement, ast.Match):
        missing = _loads_in_node(statement.subject)
        assigned = set()
        for case in statement.cases:
            case_known = set(known_names)
            pattern_names = _names_assigned_in_pattern(case.pattern)
            case_known.update(pattern_names)
            assigned.update(pattern_names)
            if case.guard is not None:
                missing.update(_loads_in_node(case.guard))
            case_missing, case_assigned = _analyze_statements(case.body, case_known)
            missing.update(case_missing)
            assigned.update(case_assigned)
        return missing, assigned

    return _loads_in_node(statement), set()


def find_hidden_state_issues(notebook: NotebookDocument) -> list[HiddenStateIssue]:
    known_names = set(dir(builtins)) | NOTEBOOK_IMPLICIT_NAMES
    issues: list[HiddenStateIssue] = []

    for index, source in enumerate(notebook.sources, start=1):
        try:
            tree = ast.parse(_notebook_python_source_for_ast(source))
        except SyntaxError:
            continue

        missing, assigned = _analyze_statements(tree.body, known_names)
        missing = sorted(name for name in missing if name not in known_names)
        if missing:
            issues.append(HiddenStateIssue(cell_index=index, names=missing))
        known_names.update(assigned)
    return issues
