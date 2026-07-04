# GitHub Publish Guide

Use this when you are ready to turn the local standalone `labcheck` repository into the public GitHub project.

This is the final public step, so keep it deliberate:

1. verify the release gate
2. verify local publish readiness
3. create and push the public repo
4. set description, homepage, and topics
5. enable GitHub Pages

---

## 1. Verify Release Readiness

```bash
python scripts/release_check.py
```

This gate runs tests, regenerates sample audits, builds the static site export, checks launch hygiene, smoke-tests standalone export, verifies the self-scan stays clean, and proves the intentionally broken fixture fails a high-severity CI gate.

Do not publish if this fails.

---

## 2. Verify Publish Readiness

```bash
python scripts/check_publish_ready.py
```

This confirms the local standalone repo is on `main`, has commits, has a clean working tree, has no conflicting `origin`, and prints the exact publish commands.

It also checks whether the GitHub CLI is available and authenticated.

---

## 3. Create And Push The Public Repo

```bash
gh repo create ThomasAquinas14/labcheck --public --source=. --remote=origin --push
```

This creates the public GitHub repository, adds `origin`, and pushes the current `main` branch.

---

## 4. Set Repo Metadata

```bash
gh repo edit ThomasAquinas14/labcheck \
  --description "No-key reproducibility audits for notebook-heavy research and ML repos." \
  --homepage "https://thomasaquinas14.github.io/labcheck/" \
  --add-topic "reproducibility,jupyter-notebook,machine-learning,research-software,data-science,github-action,static-analysis,notebook,ci,open-source"
```

If the homepage URL is not live yet, set it after the Pages deployment succeeds.

---

## 5. Enable GitHub Pages

The repo already includes `.github/workflows/pages.yml`.

After the first push:

1. Open the GitHub repository settings.
2. Go to **Pages**.
3. Use **GitHub Actions** as the Pages source.
4. Run or wait for the `pages` workflow.
5. Confirm the public URL opens the static landing page and browser demo.

Expected public URL:

```text
https://thomasaquinas14.github.io/labcheck/
```

---

## 6. Smoke-Test The Public Links

After Pages deploys, check:

- README loads and shows the scorecard preview SVG.
- Browser demo opens.
- Sample HTML audit opens.
- GitHub Action guide opens.
- Launch kit opens.
- Public deploy guide opens.

---

## 7. First Outreach Batch

Use the snippets in [launch-kit.md](launch-kit.md) and [outreach-playbook.md](outreach-playbook.md).

Start with:

- 10 professors/labs with notebook-heavy public repos
- 10 ML/data founders or technical leads

Best ask:

```text
If useful, I can run it on one of your public repos and send a short scorecard.
```

That is much easier to say yes to than a call.
