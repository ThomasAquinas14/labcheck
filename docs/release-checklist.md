# Release Checklist

Use this before tagging a release, publishing the static site, or sending `labcheck` to professors, founders, or maintainers.

The goal is to prove the public-facing story still holds:

- the package tests pass
- the install/target preflight command passes
- the compact scorecard command works
- the sample audits are regenerated from the current scanner
- the static site export builds
- the launch hygiene guard confirms required public assets and secret-ignore patterns
- the standalone repo export smoke-test can produce a clean temporary publish folder
- the repository passes its own `labcheck` audit with a score of 100
- the clean example stays clean
- the shareable audit-pack command can generate folder and zip artifacts
- the intentionally broken example still fails a high-severity CI gate

Run the full gate:

```bash
python scripts/release_check.py
```

Preview the commands without running them:

```bash
python scripts/release_check.py --list
```

Show underlying command output while the gate runs:

```bash
python scripts/release_check.py --verbose
```

The release gate intentionally includes one expected failure:

```bash
python -m labcheck.cli scan examples/broken-repo --fail-on high
```

That command should exit with code `2`, because the broken fixture is supposed to prove that CI gating catches high-severity reproducibility problems.

Before a public launch, also check:

- `README.md` points to the correct GitHub repo and public demo URL.
- `docs/sample-audits/` reflects the current broken example output from `python scripts/build_sample_audits.py`.
- `dist/site/` was rebuilt with `python scripts/build_static_site.py`.
- `python scripts/check_launch_hygiene.py` passes before you create or update the standalone public repo.
- `python scripts/export_standalone_repo.py .tmp-standalone-labcheck` can create a clean publish folder without caches, static export output, local env files, or parent-project artifacts.
- The GitHub Pages workflow is enabled in the repository settings.
- `labcheck doctor . --config .labcheck.toml` passes in the environment you plan to demo from.
- `labcheck scorecard examples/broken-repo` gives a crisp, one-screen summary suitable for outreach.
- No generated reports, caches, virtualenvs, or local experiment files are staged.
