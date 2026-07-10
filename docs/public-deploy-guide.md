# Public Deploy Guide

This guide is for publishing `labcheck` safely on a public URL without introducing the exact API-key and cost-exposure problem that motivated the project.

Because `labcheck` is deliberately built around:

- a local CLI
- static sample audits
- a static landing page
- a browser-side demo for local files and bounded public GitHub URL fetches

the safest public deployment model is:

> host static assets publicly, keep the heavier scanning flow local or user-run.

For the precise browser-demo, CLI, GitHub Action, and what-not-to-scan boundaries, read the [Privacy and Safety Model](privacy-and-safety.md).

---

## What is safe to host publicly

You can safely host these assets:

- `dist/site/index.html`
- `dist/site/demo.html`
- `dist/site/robots.txt`
- `dist/site/sitemap.xml`
- `dist/site/llms.txt`
- `dist/site/docs/sample-audits`
- `dist/site/docs/case-studies.md`

Why this is safe:

- no API keys in the browser
- no backend inference calls
- no per-request compute bill
- no queue for an attacker to abuse

---

## Recommended public deployment pattern

### Best pattern

1. Build the static export with `python scripts/build_static_site.py`
2. Host `dist/site` publicly
3. Let users try the browser demo with local files or bounded public GitHub URL fetches
4. Let serious users install the CLI locally for full scans

That gives you:

- a public demo URL
- zero wallet-drain risk
- a clear upgrade path from "interesting" to "useful"

---

## Option 1: GitHub Pages

Best for:

- fastest launch
- minimal infrastructure work
- portfolio/demo hosting

Good fit for:

- `dist/site/index.html`
- `dist/site/demo.html`
- static sample audits

Build the deployable folder:

```bash
python scripts/build_static_site.py
python scripts/check_static_export.py
```

Then publish `dist/site`. Do not publish `site/` directly unless you also copy the README and docs beside it; the exporter rewrites repo-relative links so the hosted package is self-contained. The static export checker confirms the deploy folder includes the expected public assets and does not leak local workspace paths from the development machine.

There is also a GitHub Pages workflow in `.github/workflows/pages.yml` that builds, checks, and publishes this folder automatically from `main`.

---

## Option 2: Netlify or Cloudflare Pages

Best for:

- clean deploy previews
- custom domains
- easier drag-and-drop/static publishing

Good fit for:

- the exact same static assets as GitHub Pages

This is often the easiest option if you want:

- a polished custom domain
- quick iteration
- a small marketing-style site without server maintenance

---

## Option 3: Oracle Cloud static hosting

Best for:

- keeping the deployment aligned with Oracle Cloud
- a public URL without running a VM or backend

Recommended OCI direction:

1. Run `python scripts/build_static_site.py`
2. Put the contents of `dist/site` in **OCI Object Storage**
3. Expose them with **OCI API Gateway** if you want a cleaner public route layer
4. Optionally put a CDN/domain layer in front later

Official Oracle references:

- [Set up OCI Object Storage and API Gateway for static website hosting](https://docs.oracle.com/en/learn/oci-api-gateway-web-hosting/index.html)
- [Deploy a static website using OCI API Gateway](https://docs.oracle.com/en/learn/apigw-static-website/index.html)
- [OCI Object Storage overview](https://docs.oracle.com/en-us/iaas/Content/Object/Concepts/objectstorageoverview.htm)

Why this path makes sense for `labcheck`:

- you only need to serve static files
- no Python runtime is required for the public site
- the CLI stays local, where the heavier scans belong

---

## What not to expose publicly yet

Do **not** rush into hosting a general-purpose backend that accepts arbitrary repos for full scanning.

Avoid for now:

- public background job queues
- server-side clone-and-scan for any repo URL
- multi-user upload processing without strong limits
- any feature that makes your hosted URL an unbounded compute surface

That would recreate the exact risk pattern you were trying to escape.

---

## Suggested first public release

Ship this first:

- landing page
- browser demo with local-file scans and bounded public GitHub URL fetches
- `robots.txt`, `sitemap.xml`, and `llms.txt` discovery assets
- sample HTML audit
- case studies
- README with CLI instructions

Build it with:

```bash
python scripts/build_static_site.py
python scripts/check_static_export.py
```

Then upload or deploy the generated `dist/site` folder.

After the public URL is live, run:

```bash
python scripts/check_public_urls.py https://thomasaquinas14.github.io/labcheck/
```

For a custom domain or OCI route, pass that public base URL instead. This checks the live landing page, browser demo, README, sample audit, GitHub Action guide, deploy guide, sitemap, and `llms.txt` for the expected public launch markers.

This is enough for:

- GitHub stars
- professor outreach
- founder outreach
- public demo links

without needing to operate infrastructure.

---

## Suggested Oracle-specific release path

If you want to keep it especially practical for Oracle Cloud:

1. publish the static site on OCI
2. use a custom domain if desired
3. keep the CLI local
4. later, if demand is real, add a tightly rate-limited hosted scan service only for tiny repo snapshots

That keeps the initial deployment simple, cheap, and safe.

---

## Bottom line

For `labcheck`, the right public deployment is not:

> "host the full engine as an always-on cloud backend"

It is:

> "host the static experience publicly, and let the heavier audit workflow stay local-first"

That is the whole strategic advantage of this project.
