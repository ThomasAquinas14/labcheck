# Reproducibility Pattern Gallery

Use this page when you want to understand the kinds of repo hygiene problems `labcheck` is built to catch.

The examples are intentionally small. They are not meant to shame a project; they are meant to make common handoff failures visible before a student, reviewer, maintainer, or new engineer loses a day to "works on my machine."

---

## Hidden notebook state

Fragile pattern:

```python
predictions = model.predict(cleaned_features)
```

The cell looks fine, but the notebook never defines `model` or `cleaned_features` in an earlier saved cell. It may only work because the author's kernel still has old variables in memory.

Better pattern:

```python
from pathlib import Path
import joblib
import pandas as pd

features = pd.read_csv(Path("data") / "features.csv")
model = joblib.load(Path("models") / "baseline.joblib")
predictions = model.predict(features)
```

Related checks: `LC001`, `LC002`, `LC011`, `LC014`, `LC015`

---

## Missing input artifacts

Fragile pattern:

```python
train = pd.read_csv("data/train.csv")
```

If `data/train.csv` is not committed, documented, generated, or restored through a clear command, the next person cannot rerun the workflow.

Better pattern:

```text
data/train.csv is restored with:

python scripts/download_data.py --version 2026-01-15 --checksum sha256:...
```

Related checks: `LC005`, `LC018`, `LC022`, `LC036`, `LC050`, `LC053`

---

## Inputs that exist locally but are gitignored

Fragile pattern:

```gitignore
data/
```

```python
train = pd.read_csv("data/train.csv")
```

The file may exist on the author's machine, so the workflow passes locally, but a public clone will not receive anything under `data/`.

Better pattern:

```gitignore
data/*
!data/sample-train.csv
```

Commit a small fixture, document a restore command, or add a safe `.gitignore` exception for the exact file a quickstart needs.

Related checks: `LC053`

---

## Hardcoded credentials

Fragile pattern:

```python
OPENAI_API_KEY = "sk-proj-..."
github_token = "ghp_..."
```

The project may run for the author, but publishing committed credentials can expose paid APIs, private infrastructure, or lab data once the repo is shared.

Better pattern:

```python
import os

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
```

Document safe placeholders in `.env.example`, keep real `.env` files out of git, rotate any exposed secret, and remove it from history before sharing.

Related checks: `LC024`, `LC054`

---

## Unstable remote artifacts

Fragile pattern:

```python
df = pd.read_csv("https://example.com/latest/train.csv")
```

`latest`, branch-style URLs, and unchecked downloads can change or hang between reruns.

Better pattern:

```python
import hashlib
import requests

url = "https://example.com/releases/2026-01-15/train.csv"
response = requests.get(url, timeout=30)
response.raise_for_status()
digest = hashlib.sha256(response.content).hexdigest()
assert digest == "expected_sha256_here"
```

Related checks: `LC022`, `LC047`, `LC050`

---

## README drift

Fragile pattern:

```bash
python scripts/train.py
make reproduce
```

The README names commands, scripts, modules, Makefile targets, or package scripts that do not exist anymore.

Better pattern:

```bash
python -m lab_project.train --config configs/baseline.toml
python -m lab_project.report --input outputs/metrics.json
```

Then keep those commands under CI or a lightweight smoke workflow so they do not silently rot.

Related checks: `LC008`, `LC013`, `LC021`, `LC025`, `LC044`, `LC052`, `LC062`

---

## Dead documentation links

Fragile pattern:

```markdown
[Run the training notebook](notebooks/train.ipynb)
![Expected figure](figures/main-result.png)
```

Those links are helpful only if the linked notebook, image, data file, or policy page is actually present in the repo. Broken local links are especially painful in cold handoffs because a reviewer may never reach the evidence you meant to show them.

Better pattern:

```markdown
[Run the training notebook](notebooks/train.ipynb)
![Expected figure](figures/main-result.png)
```

Then keep those linked files committed, or replace the link with clear restore/download instructions when the artifact is intentionally external.

Related checks: `LC062`

---

## Missing reuse metadata

Fragile pattern:

```text
README.md
analysis.ipynb
requirements.txt
```

The repo may run, but a public reviewer still cannot tell whether reuse is allowed or how the project should be cited.

Better pattern:

```text
README.md
LICENSE
CITATION.cff
analysis.ipynb
requirements.txt
```

For software-heavy repos, add a top-level `LICENSE` and mention the license in `README.md` or `pyproject.toml`. For research, notebooks, datasets, or paper-adjacent repos, add `CITATION.cff`, `.zenodo.json`, `codemeta.json`, or a README citation section so credit is explicit.

Related checks: `LC063`, `LC064`

---

## Inline commands that call missing scripts

Fragile pattern:

```python
%run scripts/preprocess.py
!python scripts/train.py --epochs 1
```

```python
%%bash
python scripts/build_features.py
```

```python
subprocess.run(["python", "scripts/build_features.py"])
```

These commands can hide required setup or preprocessing behind a notebook cell. If the referenced script is not shared, a fresh rerun fails even when the notebook itself is present.

Better pattern:

```text
scripts/preprocess.py
scripts/train.py
```

Commit the scripts, or replace the inline call with a documented package entrypoint that exists in the repo.

Related checks: `LC052`

---

## Nondeterministic splits and sampling

Fragile pattern:

```python
train, test = train_test_split(df, test_size=0.2)
sample = df.sample(100)
```

The results may shift every run, making figures and metrics hard to compare.

Better pattern:

```python
SEED = 42
train, test = train_test_split(df, test_size=0.2, random_state=SEED)
sample = df.sample(100, random_state=SEED)
```

Related checks: `LC007`, `LC016`, `LC017`, `LC031`, `LC032`, `LC033`, `LC034`, `LC039`, `LC040`, `LC058`, `LC059`, `LC060`, `LC061`, `LC074`, `LC075`, `LC076`

---

## JAX PRNG key reuse

Fragile pattern:

```python
import jax

key = jax.random.PRNGKey(0)
weights = jax.random.normal(key, (4, 4))
dropout = jax.random.bernoulli(key, 0.5, (4,))
```

JAX PRNG keys are immutable. Reusing one key can repeat or correlate stochastic draws, so the code may look seeded while the random streams are not independent.

Better pattern:

```python
import jax

key = jax.random.PRNGKey(0)
key, weights_key = jax.random.split(key)
weights = jax.random.normal(weights_key, (4, 4))
key, dropout_key = jax.random.split(key)
dropout = jax.random.bernoulli(dropout_key, 0.5, (4,))
```

Split before each stochastic operation and treat each subkey as single-use.

Related checks: `LC061`

---

## Optuna sampler seeds

Fragile pattern:

```python
import optuna

study = optuna.create_study(direction="maximize")
```

Optuna's default sampler is stochastic. If a hyperparameter search is rerun without a seeded sampler, the trial sequence and selected best parameters can drift even when the model training loop itself is seeded.

Better pattern:

```python
import optuna

sampler = optuna.samplers.TPESampler(seed=42)
study = optuna.create_study(direction="maximize", sampler=sampler)
```

If you use `RandomSampler`, `CmaEsSampler`, `NSGAIISampler`, or another stochastic Optuna sampler, pass a documented seed there too.

Related checks: `LC060`

---

## Gradient boosting framework seeds

Fragile pattern:

```python
import lightgbm as lgb
from catboost import CatBoostClassifier

lgb_model = lgb.LGBMClassifier()
cat_model = CatBoostClassifier(iterations=200)
```

LightGBM and CatBoost can use stochastic training paths even when the surrounding notebook sets Python or NumPy seeds.

Better pattern:

```python
SEED = 42
lgb_model = lgb.LGBMClassifier(random_state=SEED)
cat_model = CatBoostClassifier(iterations=200, random_seed=SEED)
```

For `lgb.train(...)`, put the seed in the params dictionary so the training call carries its own reproducibility contract.

Related checks: `LC074`, `LC075`

---

## Keras shuffled data sources

Fragile pattern:

```python
import tensorflow as tf

train = tf.keras.utils.image_dataset_from_directory("images/train")
```

Directory datasets and generator flows shuffle by default. A global TensorFlow seed is useful, but a visible loader seed makes the input order contract local to the data source.

Better pattern:

```python
SEED = 42
train = tf.keras.utils.image_dataset_from_directory("images/train", seed=SEED)
```

If order is intentional, say so in code with `shuffle=False`.

Related checks: `LC076`

---

## PyTorch DataLoader worker seeds

Fragile pattern:

```python
from torch.utils.data import DataLoader

loader = DataLoader(dataset, batch_size=32, shuffle=True, num_workers=4)
```

The batch order may be seeded by a `generator`, but worker processes can still run transforms that use Python, NumPy, or library randomness. Without a visible worker seed hook, multi-worker reruns can drift in ways that are hard to reproduce.

Better pattern:

```python
import random
import numpy as np
import torch
from torch.utils.data import DataLoader

def seed_worker(worker_id):
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)

generator = torch.Generator().manual_seed(42)
loader = DataLoader(
    dataset,
    batch_size=32,
    shuffle=True,
    num_workers=4,
    worker_init_fn=seed_worker,
    generator=generator,
)
```

Related checks: `LC040`, `LC059`

---

## PyTorch backend nondeterminism

Fragile pattern:

```python
import torch

torch.manual_seed(42)
torch.backends.cudnn.benchmark = True
torch.use_deterministic_algorithms(False)
```

A visible seed is not always enough. CuDNN benchmark mode can select different kernels across shapes, hardware, and reruns, and explicitly disabled deterministic algorithms allow backend nondeterminism to leak into training.

Better pattern:

```python
import torch

torch.manual_seed(42)
torch.backends.cudnn.benchmark = False
torch.backends.cudnn.deterministic = True
torch.use_deterministic_algorithms(True)
```

Deterministic PyTorch settings can trade some speed for reproducibility. If a workflow intentionally disables them for performance, document that choice in the experiment notes so reviewers know the drift is expected.

Related checks: `LC031`, `LC040`, `LC058`, `LC059`

---

## Clock-dependent workflow logic

Fragile pattern:

```python
from datetime import date

cutoff = date.today()
recent = df[df["created_at"] >= cutoff]
```

The same repo can select different rows tomorrow, next month, or on a reviewer machine that runs in a different timezone.

Better pattern:

```python
from datetime import date

RUN_DATE = date.fromisoformat("2026-01-15")
recent = df[df["created_at"] >= RUN_DATE]
```

Pass the run date as a CLI/config parameter, pin it in the experiment config, or save it as metadata rather than reading the wall clock in analysis logic.

Related checks: `LC037`, `LC055`

---

## Set-derived ordering

Fragile pattern:

```python
labels = list(set(raw_labels))
for label in set(raw_labels):
    export_label_report(label)
```

Sets are useful for membership, but their iteration order is not a reproducibility contract. A fresh Python process can produce a different label order because hash randomization changes.

Better pattern:

```python
labels = sorted(set(raw_labels))
for label in labels:
    export_label_report(label)
```

If first-seen order matters, preserve it explicitly:

```python
labels = list(dict.fromkeys(raw_labels))
```

Related checks: `LC038`, `LC056`

---

## Python hash-based splits

Fragile pattern:

```python
bucket = hash(user_id) % 10
split = "test" if bucket == 0 else "train"
```

Python's built-in `hash()` is intentionally randomized for strings and many objects between processes, so the same user can move between train and test on another run.

Better pattern:

```python
import hashlib

digest = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()
bucket = int(digest[:8], 16) % 10
split = "test" if bucket == 0 else "train"
```

Use a stable digest or an explicit persisted split mapping for IDs, cache keys, artifact names, and seeded bucket assignment.

Related checks: `LC056`, `LC057`

---

## Output paths that fail on a fresh clone

Fragile pattern:

```python
metrics.to_csv("outputs/reports/metrics.csv")
```

If `outputs/reports` does not exist, the script may fail even though the fix is tiny.

Better pattern:

```python
from pathlib import Path

output_dir = Path("outputs") / "reports"
output_dir.mkdir(parents=True, exist_ok=True)
metrics.to_csv(output_dir / "metrics.csv")
```

Related checks: `LC009`, `LC035`, `LC037`, `LC077`

---

## Output artifacts without provenance notes

Fragile pattern:

```text
results/
  metrics.csv
  confusion_matrix.png
```

The files may be useful, but a reviewer cannot tell which command, inputs, code revision, or seed produced them.

Better pattern:

```text
results/
  README.md
  metrics.csv
  confusion_matrix.png
```

The README or a `*.provenance.json` sidecar should say how the result was generated and what inputs or source revision it depends on.

Related checks: `LC009`, `LC035`, `LC037`, `LC077`

---

## Local-only paths

Fragile pattern:

```python
df = pd.read_csv("<absolute-user-home>/Desktop/project/data/train.csv")
df = pd.read_csv("<colab-drive>/research/train.csv")
df = pd.read_csv("<kaggle-input>/private-dataset/train.csv")
```

Those paths might work for the author, Colab, or Kaggle, but they are not portable repo instructions.

Better pattern:

```python
from pathlib import Path

DATA_DIR = Path("data")
df = pd.read_csv(DATA_DIR / "train.csv")
```

If the data is intentionally external, document the restore step and expected location.

Related checks: `LC006`, `LC024`, `LC046`, `LC051`

---

## Working directory changes that hide path assumptions

Fragile pattern:

```python
import os

os.chdir("notebooks")
df = pd.read_csv("../data/train.csv")
```

```python
%cd notebooks
```

Changing the process working directory makes later relative paths depend on launch location, notebook cell order, and hidden session state.

Better pattern:

```python
from pathlib import Path

PROJECT_ROOT = Path.cwd()
DATA_DIR = PROJECT_ROOT / "data"
df = pd.read_csv(DATA_DIR / "train.csv")
```

If a workflow must be launched from a specific directory, document that requirement in the README or pass the base directory as an explicit argument.

Related checks: `LC051`

---

## Dependency declarations that do not rebuild

Fragile pattern:

```text
pandas
scikit-learn
-r shared-requirements.txt
```

Unpinned packages drift over time, and missing include files break installs.

Better pattern:

```text
pandas==2.2.2
scikit-learn==1.5.1
-r requirements-base.txt
```

Related checks: `LC003`, `LC004`, `LC012`, `LC019`, `LC020`, `LC023`, `LC027`, `LC028`, `LC043`, `LC045`, `LC048`

Conda edge case:

```yaml
dependencies:
  - python=3.11
  - pip:
    - -r requirements/pip.txt
```

If `requirements/pip.txt` is missing, the Conda environment can solve successfully and then fail during the pip phase. `LC023` catches that stale include too. When the file is present, Labcheck follows it for unpinned dependencies, moving VCS refs, local path dependencies, and declared import names.

Direct `pip:` entries are checked too:

```yaml
dependencies:
  - pip:
    - git+https://github.com/example/research-utils.git@main#egg=research-utils
    - -e ../local-lab-helper
```

That can trigger `LC043` for the moving VCS ref and `LC027` when the local helper path is not part of the shared repo.

---

## Floating infrastructure

Fragile pattern:

```dockerfile
FROM python:latest
```

```yaml
- uses: actions/setup-python@main
```

These may resolve to different environments later.

Better pattern:

```dockerfile
FROM python:3.11-slim
```

```yaml
- uses: actions/setup-python@v5
```

Related checks: `LC026`, `LC029`, `LC030`, `LC049`

---

## How to use this page

For maintainers: link the relevant section in an issue or PR comment instead of sending a vague "please improve reproducibility" note.

For labs and teams: use the patterns as a starter checklist for final project handoff.

For contributors: turn one fragile pattern into a minimal fixture, then add or refine a `labcheck` check around it.
