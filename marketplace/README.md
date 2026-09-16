# Marketplace submission

How to list **Allô** in the official Grok plugin catalog.

The catalog is [`xai-org/plugin-marketplace`](https://github.com/xai-org/plugin-marketplace) —
an **index**, not a host. You don't upload anything and you don't submit an MCP
URL. You open a PR adding one entry that points Grok at this repository, pinned
to a commit.

[`catalog-entry.json`](catalog-entry.json) in this directory is that entry, ready
to paste once you replace the placeholder SHA.

## Before you submit

- [ ] This repo is **public**, under the official Allô GitHub org. A branded
      plugin sourced from a personal account reads as possible impersonation and
      will be questioned — xAI names this as the single biggest cause of review
      delay.
- [ ] `make check` passes.
- [ ] `LICENSE` is present and the license is stated in `plugin.json`.
- [ ] The commit you intend to pin is pushed and reachable.

## Submit

**1. Get the commit SHA to pin.**

```bash
git ls-remote https://github.com/withallo/grok-allo.git HEAD
```

Must be the full 40-character lowercase SHA. The validator rejects branches,
tags, and abbreviated SHAs — a moving ref would let a later force-push ship new
code to every installed user silently.

**2. Fork the catalog and add the entry.**

```bash
git clone https://github.com/<you>/plugin-marketplace.git
cd plugin-marketplace
git checkout -b add-allo-plugin
```

Append `catalog-entry.json` to the `plugins` array in
`.grok-plugin/marketplace.json`, with the real `sha`.

**3. Regenerate the index and validate.** This is exactly what their CI runs.

```bash
python3 scripts/generate-plugin-index.py
python3 scripts/validate-catalog.py
python3 scripts/generate-plugin-index.py --check
```

Never hand-edit `.grok-plugin/plugin-index.json` — it is generated, and CI fails
if it's stale.

**4. Open the PR**, fill in the template, and wait for CI plus code-owner review.

## Why a remote source

xAI accepts two source types. A **remote** source — used here — keeps the
plugin's files in this repo and vendors nothing in the catalog; updates ship by
bumping the SHA. A **local** source vendors a copy under `external_plugins/allo/`
and requires a catalog PR touching real files for every change.

Remote is the better fit: Allô owns the code, and releases don't require
re-vendoring.

## What review checks

| Dimension | What they look for |
|---|---|
| Source legitimacy | Official org (not personal), repo public, SHA pinned, brand matches source |
| Security | Static audit of MCP config, hooks, scripts, skills |
| Components | What the plugin actually ships |
| Duplication | Not already listed; not a parallel entry |
| Conventions & CI | Validator passes, valid JSON, kebab-case name, README + homepage |

Automatic rejections: arbitrary code execution (`curl | bash`, postinstall
fetch-and-run), secret or data exfiltration, undisclosed telemetry, over-broad
hooks or MCP scope, obfuscated payloads, and prompt injection planted in
`SKILL.md`.

**This plugin ships none of those.** No hooks, no scripts, no install step, no
local process, one declared HTTPS endpoint, no credentials, no telemetry. The
`README.md` declares the endpoint and the credentials needed, which xAI asks for
explicitly.

## Keywords and domains

These power Grok's plugin CTA — the prompt that proactively suggests Allô — so
they must be **brand-scoped**. Generic terms like `phone`, `calls`, `sms`, or
`crm` mis-fire the CTA on unrelated requests and get pushed back in review.

Every keyword in `catalog-entry.json` is Allô-specific, and `domains` lists only
hosts Allô owns. A test in `tests/test_structure.py` enforces this against the
manifest so it can't regress.

## Updating a live listing

Bump the `sha` in the existing entry and regenerate the index. Do **not** open a
second entry for a plugin already in the catalog.

## Private distribution

You don't need the catalog to ship. Both of these work today, with no xAI review:

- **Direct install** — `git clone … ~/.grok/plugins/allo`
- **Your own marketplace source** — publish an index repo with a
  `.grok-plugin/marketplace.json` and have users add it under
  `[[marketplace.sources]]` in `~/.grok/config.toml`

Either is the right way to run a private beta before the public listing lands.
