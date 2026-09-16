# Allo for Grok

**Run your Allo business phone system directly from Grok.**

Ask Grok about your calls, your customers, and your team's performance — and act
on the answer without leaving the conversation.

```
"Show me all missed calls from this week."
"Find calls from yesterday where the customer mentioned pricing."
"Which reps had the highest connect rate this week?"
"Send Sergio an SMS saying I'll call him tomorrow."
"Take the receptionist offline."
```

---

## What Allo is

[Allo](https://www.withallo.com) is a business phone system and AI phone platform
built for companies whose revenue comes from phone calls. Calls, SMS,
transcripts, call summaries, tagging, team analytics, a power dialer, and an AI
receptionist that answers when your team can't — in one system.

## What this plugin does

It connects Grok to your Allo workspace through Allo's hosted MCP server and
teaches Grok how to use it well.

The plugin is deliberately **thin**. It ships no server, no proxy, and no
backend of its own:

```
Grok  →  Allo plugin (skills + MCP config)  →  https://mcp.withallo.com/mcp  →  Allo API
```

All it contains is a manifest, a one-line MCP declaration, and the skills that
turn "what's happening with our calls?" into the right sequence of tool calls.
Your data goes from Allo to Grok directly.

## Which Grok does this work in?

"Grok" is three different products, and they take Allo by two different routes.
This matters before you install anything.

| Surface | What it is | How Allo connects |
|---|---|---|
| **Grok Build** | The terminal coding agent (`.grok/`, `/marketplace`, SKILL.md) | **This plugin** |
| **Grok** — grok.com and the mobile app | The chat assistant most people mean by "Grok" | **Custom connector** — no plugin |
| **Grok Bot** | Persistent cloud agent that keeps working after you close your laptop | Cursor plugin twin (`.cursor-plugin/` + `mcp.json` with static `CLIENT_ID`), or custom MCP URL |

**The Grok Build half of this repo** (`.grok-plugin/`, `.mcp.json`, xAI
marketplace) targets Grok Build. **The Cursor half** (`.cursor-plugin/`,
`mcp.json`) targets Cursor and Grok Bot. Neither format installs into the Grok
chat app at grok.com — that still uses a custom connector.

### Using Allo in the Grok chat app

You don't need a plugin — Grok supports bringing your own MCP server directly:

1. Go to [grok.com/connectors](https://grok.com/connectors)
2. **New Connector** → **Custom**
3. Server URL: `https://mcp.withallo.com/mcp`
4. Complete authentication

Grok then discovers Allo's tools and makes them available in conversation, the
same as its built-in connectors.

Two practical notes:

- **Use the MCP URL, not the OAuth authorize URL.** Pasting the authorize
  endpoint lets sign-in appear to succeed and then fails to load any tools,
  because Grok tries to speak MCP to an OAuth endpoint.
- **The same OAuth blocker applies.** Custom connectors authenticate via
  authorization-code + PKCE with dynamic client registration — exactly what
  Allo's authorization server does not yet advertise. See
  [Required Allo backend changes](#required-allo-backend-changes). That one fix
  unblocks the chat app, Grok Bot, and this plugin together.

Business and Enterprise workspaces may require an admin to provision connectors,
and some plans restrict custom MCP servers to an allowlist. If your users are on
a managed workspace, check with their admin before rollout.

### Which should you ship first?

If your users are salespeople and operators asking "what happened on our calls?",
they live in the **chat app** — the connector is the higher-value surface, and it
needs no plugin, no marketplace PR, and no xAI review. If your users are
developers, Grok Build and this plugin are the fit.

The skills in this repo are still worth having either way: they encode the
orchestration and safety rules that make Grok good at Allo rather than merely
connected to it. A connector gives Grok the tools; the skills teach it judgment.

## Features

| | |
|---|---|
| **Call search** | Find calls and SMS by date, direction, outcome, rep, line, tag, or keyword across transcripts and summaries |
| **Transcript analysis** | Read what was actually said; surface objections, sentiment, and themes across a set of calls |
| **Team analytics** | Call volume, talk time, answer rate, per-rep and per-line breakdowns, period-over-period comparison |
| **Outbound analytics** | Dial funnel, connect and conversion rates, leaderboard, best-time-to-call heatmap |
| **Tagging** | Classify calls with your workspace's tags, individually or in bulk |
| **SMS** | Draft and send texts from your Allo lines or a Sender ID |
| **AI receptionist** | Read and update its instructions, voice, status, and website knowledge |
| **Power dialer** | Inspect your queue and append numbers to it |

Everything runs against the same tools and permissions your Allo workspace
already enforces. The plugin grants no access your account doesn't have.

## Example prompts

**Finding and understanding calls**
```
What's happening with our calls?
Show me all missed calls from this week.
Find calls from yesterday where the customer mentioned pricing.
What did this prospect say on our last call?
Summarize our calls with Acme this month.
Show me the calls that still need follow-up.
Find frustrated customers from yesterday and summarize the issues.
What were the biggest objections in our sales calls this week?
```

**Performance**
```
Which reps had the highest connect rate this week?
Analyze our team's outbound performance.
Give me a report on the sales team last week vs the week before.
When is the best time of day for us to be dialing?
```

**Acting**
```
Tag the warm leads from yesterday.
Draft an SMS to the prospects who called yesterday.      ← drafts, does not send
Send Sergio an SMS saying I'll call him tomorrow.        ← sends
Add these numbers to my dialing queue.
```

**AI receptionist**
```
Configure my AI receptionist.
Take the receptionist offline.
Add this website to the receptionist's knowledge.
What is my receptionist telling callers right now?
```

**Slash commands**
```
/allo-briefing today
/allo-followups this week
/allo-report last week
```

## Installation

### From the Grok plugin marketplace

Inside Grok Build:

```
/marketplace
```

Find **allo**, press `i` to install, then restart Grok Build. On first use Grok
will prompt you to sign in to Allo (see [Authentication](#authentication)).

> **Status:** listing in the official xAI catalog requires a merged PR to
> [`xai-org/plugin-marketplace`](https://github.com/xai-org/plugin-marketplace).
> See [Distribution](#distribution) for the exact submission steps and the entry
> to submit — until that PR merges, use the direct install below.

### Direct install from this repository

```bash
git clone https://github.com/withallo/grok-allo.git ~/.grok/plugins/allo
```

Then restart Grok Build and confirm with `/plugins`.

To install for a single project instead of your whole user account, clone into
`./.grok/plugins/allo` inside that project.

Grok discovers plugins from:

| Path | Scope |
|---|---|
| `./.grok/plugins/` | Current project |
| `~/.grok/plugins/` | Your user account |
| `~/.grok/plugins/marketplaces/` | Marketplace installs |
| `[plugins] paths` in `~/.grok/config.toml` | Custom |
| `--plugin-dir <PATH>` | One session |


### Cursor and Grok Bot

This repo also ships a Cursor plugin twin (`.cursor-plugin/` + `mcp.json`) for
Cursor and Grok Bot. Those clients do not use the Grok Build marketplace; they
need a **static OAuth client ID** because Allo's authorization server has no
`registration_endpoint`.

`mcp.json` declares the public Grok Bot / Cursor Agents client:

```json
{
  "mcpServers": {
    "allo": {
      "url": "https://mcp.withallo.com/mcp",
      "auth": {
        "CLIENT_ID": "e3d79ef3-9e84-452c-9269-df9ed022753a"
      }
    }
  }
}
```

That ID is a public PKCE client (empty secret), the same pattern as Claude's
static client on [withallo.com/mcp](https://www.withallo.com/mcp). It is not an
API key. The OAuth app's redirect URI must include:

```
https://www.cursor.com/agents/mcp/oauth/callback
```

Optionally also `http://localhost:8787/callback` for Cursor desktop.

**Until this plugin is listed in the Cursor marketplace**, add the custom
connector with that URL and `CLIENT_ID`, or ask your Grok Bot to add the
custom MCP server with the same `auth.CLIENT_ID`.

`.cursor-plugin/plugin.json` pins `"mcpServers": "./mcp.json"` so a dual-format
checkout does not accidentally load the Grok Build `.mcp.json` (which has no
client ID).

## Authentication

**OAuth 2.1 with PKCE. No API key is stored in this repository, and you never
paste a secret into chat.**

The MCP declaration carries no credentials at all:

```json
{
  "mcpServers": {
    "allo": {
      "type": "http",
      "url": "https://mcp.withallo.com/mcp"
    }
  }
}
```

Authentication is negotiated at runtime between Grok and Allo. The flow, verified
against production:

1. Grok calls `https://mcp.withallo.com/mcp` with no token.
2. Allo answers `401` with
   `WWW-Authenticate: Bearer resource_metadata="https://mcp.withallo.com/.well-known/oauth-protected-resource"`.
3. Grok fetches that document and learns the authorization server is
   `https://api.withallo.com`.
4. Grok fetches `https://api.withallo.com/.well-known/oauth-authorization-server`
   for the endpoints:
   - authorize — `https://api.withallo.com/v1/oauth/authorize`
   - token — `https://api.withallo.com/v1/oauth/token`
   - revoke — `https://api.withallo.com/v1/oauth/revoke`
   - PKCE `S256`, `authorization_code` + `refresh_token` grants
5. Your browser opens, you approve access for your Allo workspace, and Grok
   stores the resulting token in its own credential store.

Verify the whole chain yourself at any time:

```bash
python3 tests/live_check.py
```

> ### ⚠️ One blocker before this works end to end
>
> Allo's authorization server does **not** currently advertise a
> `registration_endpoint`, so it does not support
> [RFC 7591 dynamic client registration](https://datatracker.ietf.org/doc/html/rfc7591).
> A client that has never been registered — which is what Grok is today — has no
> way to obtain a `client_id` automatically.
>
> Allo already solved this for Claude by issuing a static client ID
> (`b82803e6-…`, empty secret). **Grok needs the same treatment**: either
> implement dynamic client registration, or issue a dedicated Grok `client_id`.
> See [Required Allo backend changes](#required-allo-backend-changes).

### API key fallback

Allo also accepts a workspace API key as a plain `Authorization` header. This is
how Allo documents Claude Code, Cursor, and Codex today. It is a legitimate
fallback if OAuth isn't available to you yet, but **this plugin deliberately does
not ship it**, because it would mean committing a credential to a shared config
file.

If you must use a key while OAuth client registration is pending, configure it in
your own machine's Grok MCP settings (`/mcps`) rather than in this repository, and
never commit it. Generate and revoke keys in **Allo → Settings → API**; revoking a
key immediately disconnects every client using it.

## Permissions

Access is scoped by your Allo workspace. The authorization server advertises 22
scopes; the ones this plugin exercises:

| Capability | Scope |
|---|---|
| Read calls, SMS, transcripts, analytics | `CONVERSATIONS_READ` |
| Mark read/unread, archive, edit summaries | `CONVERSATIONS_WRITE` |
| Read and apply tags | `TAGS_READ`, `TAGS_WRITE` |
| Send SMS | `SMS_SEND` |
| List team members | `USERS_READ` |
| List phone lines | `PHONE_NUMBERS_READ` |
| Power dialer queue | `DIALING_QUEUE_READ_WRITE` |
| AI receptionist | `AGENTS_READ`, `AGENTS_WRITE` |
| Contacts and CRM | `CONTACTS_READ`, `CRM_READ`, `CRM_WRITE` |
| Notes and threads | `NOTES_READ`, `NOTES_WRITE`, `THREADS_READ`, `THREADS_WRITE` |

Grok calls `allo_get_me` at the start of a session to discover which of these you
actually hold, and adapts. If a capability is missing, it says so rather than
failing cryptically.

Grant only what the workspace needs. A read-only connection is a perfectly good
way to use this plugin — every analysis feature works without a single write
scope.

## Safety model

Phone systems touch customers. The skills encode explicit rules:

- **Read-only by default.** Analysis never writes.
- **"Draft" never sends.** Asking Grok to draft a text produces text and stops.
  Only "send" invokes `allo_send_sms`.
- **Confirmation before external side effects.** Sending SMS, changing or taking
  the receptionist offline, bulk tagging, queueing numbers, and deleting
  knowledge all require clear intent — and Grok shows you the exact recipients
  and message text before sending anything.
- **Bulk actions are staged.** Filter → validate the target set → summarize →
  confirm → execute → report what actually happened, including failures.
- **Reversible before destructive.** Asked to "remove" a receptionist knowledge
  source, Grok offers to disable it rather than silently deleting it.
- **No invented data.** No results means no results. Metrics Allo doesn't return
  are reported as unavailable, never estimated.
- **No secrets, ever.** API keys, tokens, and authorization headers are never
  printed, echoed, or logged.

## Security considerations

- **No credentials in this repository.** Enforced by a test that scans every file
  for key, token, and bearer patterns.
- **No code execution.** The plugin ships no hooks, no install scripts, and no
  local MCP process. It is a manifest, a URL, and markdown.
- **One network endpoint**, declared and auditable: `https://mcp.withallo.com/mcp`
  over TLS. A test asserts nothing else is added.
- **No telemetry.** The plugin collects nothing. Conversation data flows between
  Grok and Allo only.
- **Pinned distribution.** Marketplace installs pin a full 40-character commit
  SHA, which Grok re-verifies after cloning, so a force-push cannot silently ship
  new code to installed users.
- **Least privilege.** Grant the narrowest Allo scopes that cover your use.

Reporting a vulnerability: contact Allo via [help.withallo.com](https://help.withallo.com).

## Development

No build step, no dependencies. Python 3.9+ for the tests; that's it.

```bash
git clone https://github.com/withallo/grok-allo.git
cd grok-allo
make check
```

### Repository layout

```
.grok-plugin/plugin.json   Grok Build plugin manifest
.mcp.json                  Grok Build MCP declaration (URL only; OAuth at runtime)
.cursor-plugin/plugin.json Cursor / Grok Bot plugin manifest
mcp.json                   Cursor / Grok Bot MCP + static OAuth CLIENT_ID
skills/
  allo/                    Orchestration + safety; routes to focus skills
  allo-search/             Search conversations, calls, SMS, transcripts
  allo-sms/                Draft and send SMS
  allo-analytics/          Team and outbound reporting
  allo-receptionist/       AI receptionist setup and knowledge
  allo-call-flow/          Inbound call flow drafts (publish in Allo app)
commands/                  /allo-briefing, /allo-followups, /allo-report
assets/logo.svg
tests/
  allo_registry.py         Verified tool/enum/limit registry — source of truth
  mock_mcp.py              In-process Allo MCP mock (SMS is always dry-run)
  test_structure.py        Manifest, MCP config, skills, secrets
  test_workflows.py        Workflow + safety-contract tests
  live_check.py            Live connectivity, OAuth discovery, tool discovery
marketplace/               Catalog entry for the xAI marketplace PR
```

### Local testing

```bash
make test        # 70 offline tests — no network, no credentials
make live        # live connectivity + OAuth discovery (no credentials needed)
make check       # both
```

Authenticated tool discovery, which diffs the live server against the registry:

```bash
ALLO_API_KEY='your-key' python3 tests/live_check.py
ALLO_API_KEY='your-key' python3 tests/live_check.py --dump   # print served schemas
```

The key is read from the environment only — never pass it as an argument, where
it would land in your shell history.

**No real SMS is ever sent by the test suite.** `mock_mcp.py` has no network I/O;
its send path records a dry-run receipt in memory and returns.

### What the tests cover

| # | Check | Where |
|---|---|---|
| 1 | Plugin manifest validity | `test_structure.py` |
| 2 | MCP configuration validity | `test_structure.py` |
| 3 | Skill discovery and frontmatter | `test_structure.py` |
| 4 | MCP server connectivity | `live_check.py` |
| 5 | Authentication configuration, no committed secrets | `test_structure.py` |
| 6 | Tool discovery vs the registry | `live_check.py` |
| 7 | Read-only workflow | `test_workflows.py` |
| 8 | SMS workflow (dry-run) | `test_workflows.py` |
| 9 | Tagging workflow | `test_workflows.py` |
| 10 | Analytics workflow | `test_workflows.py` |
| 11 | AI receptionist workflow | `test_workflows.py` |
| 12 | Error handling | `test_workflows.py` |

Two checks are worth calling out because they prevent the failure mode that
matters most — drift from the real API:

- **No invented tools.** Every `allo_*` name appearing in any skill, command, or
  this README must exist in the verified registry.
- **Safety contract.** The safety rules are asserted to be *present in the skill
  text*, since a rule Grok can't read doesn't bind it.

### Testing against a local checkout

```bash
grok --plugin-dir /path/to/grok-allo
```

Then, inside Grok Build:

```
/plugins      confirm "allo" is loaded
/skills       confirm the four Allo skills are discovered
/mcps         confirm the Allo MCP connects and authenticates
```

## Distribution

Grok plugins are distributed through
[`xai-org/plugin-marketplace`](https://github.com/xai-org/plugin-marketplace),
an index repository. **Submitting an MCP URL is not sufficient** — you open a PR
adding a catalog entry that points Grok at this repository at a pinned commit.

xAI accepts third-party plugins by either vendoring a copy under
`external_plugins/` or referencing an upstream repo. For a plugin like this one,
a **remote source is recommended**: nothing is vendored, and you ship updates by
bumping the SHA.

### Submitting

1. Push this repository to a public URL under the **official Allo org** — not a
   personal account. xAI's review guidance calls out personal-account sources for
   branded plugins as a likely-impersonation signal and the single biggest cause
   of review delay.

2. Get the commit to pin:
   ```bash
   git ls-remote https://github.com/withallo/grok-allo.git HEAD
   ```

3. Fork `xai-org/plugin-marketplace`, and append the entry from
   [`marketplace/catalog-entry.json`](marketplace/catalog-entry.json) to the
   `plugins` array in `.grok-plugin/marketplace.json`, with the `sha` replaced by
   the real commit.

4. Regenerate the index and validate — this is exactly what their CI runs:
   ```bash
   python3 scripts/generate-plugin-index.py
   python3 scripts/validate-catalog.py
   python3 scripts/generate-plugin-index.py --check
   ```

5. Open the PR. CI runs the validator; a code-owner review is required.

Full detail and the review criteria: [`marketplace/README.md`](marketplace/README.md).

### Shipping updates

Bump the pinned `sha` in the catalog (or commit the files, for a vendored copy)
and regenerate the index. Never open a second, parallel entry for a plugin that
is already listed.

### Private distribution

You don't need the official catalog. You can run your own marketplace source via
`[[marketplace.sources]]` in `~/.grok/config.toml`, or have people install
directly from git — see [Installation](#installation). This is the right path for
a private beta.

## Troubleshooting

**The plugin doesn't appear after installing**
Restart Grok Build, then check `/plugins`. Confirm the clone landed in
`~/.grok/plugins/` or `./.grok/plugins/` and that `.grok-plugin/plugin.json`
exists at its root. Run `make test` against the checkout.

**Grok doesn't use Allo when I ask about calls**
Check `/skills` lists the four Allo skills. Naming Allo explicitly ("in Allo,
show me…") reliably triggers them. If the skills aren't listed, the frontmatter
didn't parse — `make test` catches that.

**Authentication fails or never prompts**
Run `python3 tests/live_check.py`. If OAuth discovery passes but Grok still
can't connect, you're most likely hitting the dynamic client registration gap
described in [Authentication](#authentication) — Grok has no `client_id` to use.
That needs the Allo-side change, not a config fix.

**"Authorization error" on one specific action**
Your connection lacks that scope. Ask Grok "what can I do in Allo?" — it reads
your granted scopes from `allo_get_me`. Reconnect the plugin to grant more, or
have a workspace admin adjust your permissions.

**A search returns nothing**
Keyword terms are AND'd with prefix matching, so extra words narrow hard. Try one
distinctive term. Also confirm the date range — Grok states the range it used.

**"Missed calls" numbers look off**
Allo exposes no `MISSED` filter. Grok uses inbound calls that went to voicemail
as the closest supported proxy and tells you so. If you define missed differently,
say so and Grok will filter accordingly.

**SMS won't send**
The sending line needs SMS capability — ask Grok to list your numbers. Recipients
must be E.164 (`+14155551234`). And confirm you actually said "send": "draft"
deliberately stops short.

**Analytics look wrong for conversions**
Conversions in outbound analytics are defined by the tag you choose. Tell Grok
which tag means "converted" (e.g. `meeting_booked`).

## Required Allo backend changes

Verified against production on 2026-09-11 with `tests/live_check.py`.

1. **Register Grok as an OAuth client — required, and it blocks every surface.**
   The authorization server at `https://api.withallo.com` advertises no
   `registration_endpoint`, so Grok cannot self-register. This blocks this
   plugin, custom connectors at grok.com, and Grok Bot alike — it is the single
   highest-leverage fix on this list. Either:
   - **(a)** implement RFC 7591 dynamic client registration — the general fix,
     and it makes every future MCP client work without per-client work; or
   - **(b)** issue a static `client_id` for Grok as was done for Claude, and
     document it.

   `token_endpoint_auth_methods_supported` already includes `none` and PKCE
   `S256` is supported, so a public client works — only the registration step is
   missing.

2. **Register Grok's OAuth redirect URI**, once xAI publishes it for their MCP
   client.

3. **Confirm the edge WAF doesn't challenge Grok's user agent.** A request with
   the default Python user agent gets a `403` from Cloudflare instead of the
   `401` carrying `WWW-Authenticate` — which would hide OAuth discovery entirely.
   Grok's client must be verified against the live edge, and MCP discovery paths
   should be excluded from bot challenges.

4. **Optional — a Grok-scoped consent screen.** The OAuth approval page naming
   Grok explicitly increases trust at the moment users decide.

Nothing else is required. The MCP server, tools, scopes, and rate limits are
already production-ready and need no changes for this plugin.

## Required Allo website changes

None are required to ship. Recommended:

1. Add Grok to [withallo.com/mcp](https://www.withallo.com/mcp) alongside the
   existing Claude, Cursor, and Codex setup instructions — and cover **both**
   routes: the grok.com custom connector (for the chat app, which is where most
   Allo users are) and this plugin (for Grok Build).
2. Publish the Grok OAuth `client_id` there once issued (item 1b above).
3. Add a Help Center article for the Grok plugin — install, connect, first
   prompts.
4. Optional: a `withallo.com/grok` landing page, useful as the `homepage` in the
   marketplace entry.

## xAI approval and review

Listing in the official catalog requires a merged PR, reviewed by a code owner
against published criteria: source legitimacy (official org, real pinned commit),
a static security audit of MCP config and skills, declared components, no
duplicate entries, and green CI.

This plugin is built to pass: no hooks, no scripts, no code execution, one
declared endpoint, no credentials, brand-scoped keywords. The two things that
need your action are pushing to the official Allo org and stating the license.

There is no separate xAI approval for the MCP server itself, and no review
required for direct or private distribution.

## Limitations

**Of the current Grok plugin system**

- **Plugins are Grok Build only.** There is no way to package skills for the
  Grok chat app or Grok Bot — those surfaces take a raw MCP connector, so the
  orchestration and safety guidance in `skills/` doesn't travel with it. On
  those surfaces Grok gets Allo's tools but not this repo's judgment about how
  to use them.
- The catalog is a single GitHub repo gated by PR review — no self-serve
  publishing, and updates ship at the speed of a merge.
- Remote sources pin one commit, so every update is a catalog PR.
- No per-tool permission UI: connecting the MCP grants everything your Allo
  scopes allow. Tool-level control has to come from Allo's scopes.
- Skills are advisory. They shape Grok's behavior strongly but are not an
  enforcement layer — a confirmation rule is a very good instruction, not a
  hard gate. Anything that must never happen should be enforced by scope.
- OAuth for remote MCP servers assumes a client can register itself; there's no
  published mechanism for a plugin to declare a pre-issued `client_id`, which is
  why item 1 above matters.

**Of this integration**

- No `MISSED` call filter exists; Grok uses a documented proxy.
- Conversion metrics depend on your tagging discipline.
- Call flows can be saved as a draft but never published from Grok — publishing
  requires a signed-in user opening the returned confirmation link. That's an
  intentional Allo safeguard.
- Analytics cover what Allo measures. Revenue and pipeline metrics live in your
  CRM, not here.

## Links

- Allo — https://www.withallo.com
- Allo MCP documentation — https://www.withallo.com/mcp
- Allo Help Center — https://help.withallo.com
- xAI plugin documentation — https://docs.x.ai/build/features/skills-plugins-marketplaces
- xAI plugin marketplace — https://github.com/xai-org/plugin-marketplace

## License

Proprietary. © Allo. See [LICENSE](LICENSE).
