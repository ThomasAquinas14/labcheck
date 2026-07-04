# Security Policy

`labcheck` is designed to avoid API-key exposure and hosted compute abuse.

The default architecture is:

- local CLI scans
- no paid API calls
- no backend service required
- static browser demo for small local-file audits
- GitHub Action wrapper that runs inside the user's repository workflow

## Supported versions

This project is pre-1.0. Security fixes should target the default branch until formal releases begin.

## Reporting a vulnerability

Please do not open a public issue for security-sensitive reports.

Email the maintainer or use a private GitHub security advisory if available. Include:

- affected version or commit
- reproduction steps
- affected command/page/workflow
- expected impact
- suggested fix, if known

## In scope

- path traversal or unsafe archive extraction
- unsafe handling of user-selected browser files
- XSS in static demo or generated HTML reports
- command injection in CLI or GitHub Action paths
- accidental secret exposure
- unbounded public-hosting risks introduced by new features

## Out of scope

- findings that are heuristic false positives
- scans of intentionally malicious repositories run locally by the user
- denial-of-service against a user's own machine from scanning huge local folders
- requests to host a public backend without strict limits

## Security expectations for contributors

- Do not add API-key requirements to the core scanner.
- Do not add public backend behavior as a default path.
- Escape user-controlled content before rendering HTML.
- Treat zip archives and filesystem paths as untrusted input.
- Keep generated reports safe to open locally.
