# Contributing to labcheck

Thanks for helping make research and ML repositories easier to rerun.

`labcheck` is intentionally no-key, local-first, and heuristic. Good contributions should preserve those constraints.

## Good first contributions

- Add a small, well-explained reproducibility check.
- Improve an existing check to reduce false positives.
- Add a public repo case study with a concise interpretation.
- Improve docs, static demo copy, or GitHub Action examples.
- Add regression tests for a real failure mode.
- Improve citation, adoption, or teaching materials without adding hosted infrastructure.

## Development setup

```bash
python -m pip install -e .
python -m pip install pytest
pytest -q
```

Run the CLI locally:

```bash
labcheck scan examples/broken-repo --format markdown
labcheck checks
labcheck explain LC005
```

Build the static public site export:

```bash
python scripts/build_static_site.py
```

Before tagging, publishing the static site, or sharing a release candidate publicly, run the maintainer release gate:

```bash
python scripts/release_check.py
```

## Check design principles

- Prefer deterministic static analysis over runtime execution.
- Do not require API keys, paid services, background workers, or hosted infrastructure.
- Report evidence that a maintainer can verify.
- Include a clear `why_it_matters` and a specific `suggested_fix`.
- Avoid absolute claims. Findings are heuristic signals, not proof that a repo is broken.
- Keep false positives explainable and suppressible with `.labcheck.toml`.

## Adding a new check

1. Add or update scanner logic in `src/labcheck`.
2. Add the check to `src/labcheck/check_catalog.py`.
3. Add tests under `tests/`.
4. Update `README.md` if the check is user-facing.
5. Regenerate sample audits only when the public examples materially change.

## Pull request checklist

- Tests pass with `pytest -q`.
- Release checks pass with `python scripts/release_check.py` when preparing public-facing changes.
- New behavior has a regression test.
- Human reports remain readable on large repos.
- JSON/SARIF output stays complete for automation.
- No new network dependency or API key requirement was added.
- Static demo changes are safe for public hosting.
