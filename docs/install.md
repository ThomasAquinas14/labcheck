# Install labcheck

`labcheck` has no runtime dependencies beyond Python 3.11+ and does not require API keys.

Use this page when you want the quickest path from "interesting" to "I can run a scorecard on my repo."

---

## Recommended: pipx from GitHub

After the public repository exists, install the CLI into an isolated environment:

```bash
python -m pip install --user pipx
python -m pipx ensurepath
pipx install git+https://github.com/ThomasAquinas14/labcheck.git
```

Then run:

```bash
labcheck demo-repo
labcheck doctor labcheck-demo-repo
labcheck scorecard labcheck-demo-repo
labcheck scan labcheck-demo-repo --format markdown --output labcheck-report.md
```

Why this is the best first-user path:

- it does not require cloning the repo
- it gives first-time users a tiny intentionally broken repo to audit immediately
- it keeps `labcheck` isolated from the target project's environment
- it avoids API keys, hosted services, and paid inference dependencies

---

## Local development install

Use this path if you want to contribute, run tests, or inspect the source:

```bash
git clone https://github.com/ThomasAquinas14/labcheck.git
cd labcheck
python -m pip install -e .
pytest -q
```

Try the intentionally broken fixture first:

```bash
labcheck demo-repo --output-dir labcheck-demo-repo
labcheck doctor .
labcheck scorecard examples/broken-repo
labcheck pack examples/broken-repo --output-dir labcheck-audit --zip
```

---

## Public GitHub repo audit

For public repos, `labcheck` can clone into a temporary workspace, scan locally, and remove the temporary clone afterward:

```bash
labcheck doctor https://github.com/owner/repo
labcheck target-fit https://github.com/owner/repo --audience professor --output labcheck-target-fit.md
labcheck scorecard https://github.com/owner/repo --output labcheck-scorecard.md
labcheck demo-link https://github.com/owner/repo --audience professor --output labcheck-demo-link.txt
labcheck demo-link https://github.com/owner/repo --format markdown --auto-audit --audience professor --output labcheck-demo-link.md
labcheck pack https://github.com/owner/repo --output-dir labcheck-audit --zip --max-findings 50
```

Only audit public repos unless you have explicit permission. Do not share reports that expose private paths, internal dataset names, or unreleased work.

---

## GitHub Action install path

For CI, initialize a soft audit:

```bash
labcheck init .
```

This writes:

- `.labcheck.toml`
- `.github/workflows/labcheck.yml`

Start with `fail-on: none`, then create a baseline and enable gates once the team agrees on the standard.

See [github-action.md](github-action.md) for the full Action workflow.

---

## Browser demo only

If you do not want to install anything, use the static browser demo:

- local notebook or selected local files
- small local folder selections
- bounded public GitHub URL scans
- downloadable scorecard, audience-specific target-fit card, issue draft, outreach note, Markdown, and JSON

The browser demo is intentionally lighter than the CLI. Use it for first impressions, screenshots, and prefilled outreach links. Use the CLI or GitHub Action for full repo audits.

See [privacy-and-safety.md](privacy-and-safety.md) for the exact safety boundaries.
