# Support

Thanks for trying `labcheck`.

The fastest support path depends on what you need.

## Request an audit of a public repo

Open an **Audit request** issue when you want a lightweight reproducibility read on a public research, ML, data, or notebook-heavy repository.

Include:

- the public repository URL
- the audience or handoff context
- known external datasets, generated folders, or archival notebooks
- any files that should not be over-interpreted

Please do not upload private repos, unpublished datasets, secrets, credentials, or private reviewer material into public issues.

## Report a bug

Open a **Bug report** issue for crashes, confusing output, false positives, or false negatives.

Helpful details:

- exact `labcheck` command
- target type: folder, notebook, zip, public GitHub URL, Action, or browser demo
- operating system and Python version
- finding ID if relevant
- a minimal public fixture when possible

## Suggest a new check

Open a **Check proposal** issue for a new deterministic reproducibility rule.

Good proposals include:

- the real handoff failure mode
- the static signal `labcheck` should inspect
- example evidence text
- likely false positives
- why the rule can run without API keys or executing user code

## Security reports

Please do not file public issues for vulnerabilities, path traversal problems, browser XSS, unsafe archive handling, or GitHub Action input issues.

Use the private security advisory link from the issue chooser or follow [SECURITY.md](SECURITY.md).

## Scope

`labcheck` is a deterministic static auditor. Findings are reproducibility signals, not a claim that a repo is scientifically invalid.

The project does not provide private code review, hosted scans of private repositories, or scientific peer review of results.
