# Changelog

## 1.0.0 — unreleased

First release of the Allo plugin for Grok.

### Added

- Remote MCP declaration for the hosted Allo MCP (`https://mcp.withallo.com/mcp`),
  authenticated via OAuth 2.1 + PKCE with no credentials in the repository.
- `allo` skill — orchestration, discovery, read/write policy, confirmation rules,
  error handling, and worked multi-step examples.
- `allo-call-intelligence` skill — call search, transcript analysis, theme
  extraction, follow-up detection, tagging.
- `allo-analytics` skill — team KPIs and outbound funnel reporting, with
  single-call multi-entity comparison and tag-defined conversions.
- `allo-receptionist` skill — AI receptionist configuration, status, voice, and
  knowledge sources, with disable-before-delete guidance.
- Slash commands: `/allo-briefing`, `/allo-followups`, `/allo-report`.
- Test suite: 70 offline tests plus a live connectivity and OAuth discovery
  check. SMS is dry-run only and never leaves the process.
- Marketplace submission package under `marketplace/`.
- Cursor / Grok Bot twin: `.cursor-plugin/plugin.json` and `mcp.json` with
  static OAuth `CLIENT_ID` `e3d79ef3-9e84-452c-9269-df9ed022753a` (public PKCE
  client; redirect `https://www.cursor.com/agents/mcp/oauth/callback`).

### Known blockers

- Allo's authorization server advertises no `registration_endpoint`, so Grok
  cannot dynamically register as an OAuth client. Requires either RFC 7591
  support or a static Grok `client_id`. See "Required Allo backend changes" in
  the README.
