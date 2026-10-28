# Changelog

## Unreleased

### Added

- Inboxes in the `allo` skill (TECH-8362): set up inboxes from Allo's
  suggestions (each carries a ready `source`) after the user confirms the list,
  custom phone-menu branch inboxes from the menu options' ready `condition`
  (several options on one line merge into one condition), inboxes for a
  teammate (admins and managers, sources built from menu options or whole
  lines), opening a named inbox and acting on each row's own line, pinning
  customers (max 10), muting an inbox, and deleting one only on an explicit
  request. Covers the 50-inbox limit, invalid filters, and one retry when a
  fresh inbox isn't found yet. `allo_create_inbox` and `allo_delete_inbox`
  join the high-consequence list.
- Registry and mock entries for `allo_list_inboxes`,
  `allo_get_inbox_suggestions`, `allo_list_menu_options`, `allo_create_inbox`,
  `allo_update_inbox`, `allo_delete_inbox`, `allo_pin_conversation` and
  `allo_unpin_conversation`, plus `inbox_id` and `pinned` on
  `allo_list_conversations`. The mock mirrors api-allo's shapes and errors.
  Requires the matching mcp.withallo.com release.
- Inbox workflow tests: set up for me, set up for a teammate, list a named
  inbox's conversations, combined menu branches, saved filters, and the pin,
  inbox-limit, filter and read-after-create errors.

## 1.0.0 — unreleased

First release of the Allo plugin for Grok.

### Added

- Remote MCP declaration for the hosted Allo MCP (`https://mcp.withallo.com/mcp`),
  authenticated via OAuth 2.1 + PKCE with no credentials in the repository.
- `allo` skill — orchestration, discovery, read/write policy, confirmation rules,
  error handling, and worked multi-step examples.
- `allo-search` skill — call search, transcript analysis, theme
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
