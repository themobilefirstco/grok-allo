#!/usr/bin/env python3
"""Live checks against the production Allô MCP server.

Covers checks 4 (MCP server connectivity) and 6 (tool discovery) of the plugin
test plan. Kept out of the default unittest run because it needs the network.

Two modes:

  Anonymous (no credentials needed) — verifies the server is reachable and that
  it advertises OAuth per the MCP authorization spec: an unauthenticated call
  must return 401 with a `WWW-Authenticate` header pointing at the protected
  resource metadata. This is what lets Grok start the OAuth flow on first
  connect, so it is the single most important thing to assert.

  Authenticated (set ALLO_API_KEY) — additionally initializes a session, lists
  tools, and diffs them against tests/allo_registry.py.

    python3 tests/live_check.py                 # anonymous
    ALLO_API_KEY=... python3 tests/live_check.py
    ALLO_API_KEY=... python3 tests/live_check.py --dump   # print served schemas

Exit code 0 = pass. The API key is read from the environment only; never pass a
key as a command-line argument, where it would land in your shell history.
"""

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from allo_registry import MCP_URL, TOOLS  # noqa: E402

TIMEOUT = 20
USER_AGENT = "allo-grok-plugin-live-check/1.0"
PASS, FAIL, INFO = "  ok  ", " FAIL ", " ..   "

_failures = []


def report(status, message):
    print(f"[{status}] {message}")
    if status == FAIL:
        _failures.append(message)


def _post(payload, api_key=None):
    """One JSON-RPC call. Returns (status, headers, parsed_body_or_text)."""
    headers = {
        "Content-Type": "application/json",
        # Streamable HTTP transport may answer with either content type.
        "Accept": "application/json, text/event-stream",
        # The edge WAF answers the default Python-urllib agent with a 403
        # challenge instead of the real 401, which would hide the OAuth
        # advertisement this check exists to verify.
        "User-Agent": USER_AGENT,
    }
    if api_key:
        headers["Authorization"] = api_key
    request = urllib.request.Request(
        MCP_URL, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return response.status, _headers(response.headers), _parse(response.read().decode())
    except urllib.error.HTTPError as error:
        return error.code, _headers(error.headers), _parse(error.read().decode())


def _headers(message):
    """Lowercase header names — HTTP/2 sends them lowercased, HTTP/1.1 does not."""
    return {name.lower(): value for name, value in message.items()}


def _parse(raw):
    """Accept a plain JSON body or an SSE frame carrying one."""
    text = raw.strip()
    if text.startswith("event:") or text.startswith("data:"):
        for line in text.splitlines():
            if line.startswith("data:"):
                text = line[5:].strip()
                break
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return raw


def check_reachable_and_advertises_oauth():
    """Check 4 — connectivity, and that OAuth discovery is advertised."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    try:
        status, headers, _ = _post(payload)
    except Exception as error:  # noqa: BLE001 - surface any transport failure
        report(FAIL, f"cannot reach {MCP_URL}: {error}")
        return

    report(PASS, f"{MCP_URL} reachable (HTTP {status})")

    challenge = headers.get("www-authenticate", "")
    if status == 401 and challenge:
        report(PASS, f"advertises OAuth: WWW-Authenticate: {challenge}")
    elif status == 401:
        report(FAIL, "401 without WWW-Authenticate — Grok cannot discover the OAuth flow")
    elif status == 200:
        report(FAIL, "unauthenticated tools/list succeeded — the server should require auth")
    else:
        report(
            FAIL,
            f"expected 401 on an unauthenticated call, got HTTP {status}. An edge WAF "
            f"challenge here would hide the OAuth advertisement from Grok.",
        )


def _get_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return json.loads(response.read().decode())


def check_oauth_discovery():
    """Walk the discovery chain Grok follows to start the OAuth flow.

    401 challenge -> protected resource metadata -> authorization server
    metadata. The last step also determines whether Grok can register itself
    as a client automatically (RFC 7591 dynamic client registration) or needs
    a client_id issued by Allô out of band.
    """
    base = MCP_URL.rsplit("/mcp", 1)[0]
    resource_url = f"{base}/.well-known/oauth-protected-resource"
    try:
        resource = _get_json(resource_url)
    except Exception as error:  # noqa: BLE001
        report(FAIL, f"protected resource metadata unavailable at {resource_url}: {error}")
        return

    servers = resource.get("authorization_servers") or []
    report(PASS, f"protected resource metadata: authorization_servers={servers}")
    if not servers:
        report(FAIL, "no authorization_servers advertised — Grok cannot find the OAuth server")
        return

    server_url = f"{servers[0].rstrip('/')}/.well-known/oauth-authorization-server"
    try:
        server = _get_json(server_url)
    except Exception as error:  # noqa: BLE001
        report(FAIL, f"authorization server metadata unavailable at {server_url}: {error}")
        return

    for field in ("authorization_endpoint", "token_endpoint"):
        if server.get(field):
            report(PASS, f"{field}: {server[field]}")
        else:
            report(FAIL, f"authorization server metadata missing {field}")

    if "S256" in (server.get("code_challenge_methods_supported") or []):
        report(PASS, "PKCE S256 supported")
    else:
        report(FAIL, "PKCE S256 not advertised — required for a public client like Grok")

    if server.get("registration_endpoint"):
        report(PASS, f"dynamic client registration: {server['registration_endpoint']}")
    else:
        report(
            INFO,
            "no registration_endpoint — Allô does not support RFC 7591 dynamic client "
            "registration, so Grok needs a pre-registered client_id (see README, "
            "'Required Allô backend changes')",
        )

    scopes = server.get("scopes_supported") or []
    report(PASS, f"{len(scopes)} scopes advertised")
    for scope in ("CONVERSATIONS_READ", "SMS_SEND", "TAGS_WRITE", "AGENTS_WRITE"):
        if scope not in scopes:
            report(INFO, f"scope {scope} not advertised by the authorization server")


def check_tools(api_key, dump=False):
    """Check 6 — tool discovery, diffed against the pinned registry."""
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "allo-grok-plugin-live-check", "version": "1.0.0"},
        },
    }
    status, _, body = _post(init, api_key)
    if status != 200 or not isinstance(body, dict) or "result" not in body:
        report(FAIL, f"initialize failed (HTTP {status}): {str(body)[:200]}")
        return
    server = body["result"].get("serverInfo", {})
    report(PASS, f"initialized: {server.get('name', '?')} {server.get('version', '')}".strip())

    status, _, body = _post(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, api_key
    )
    if status != 200 or not isinstance(body, dict) or "result" not in body:
        report(FAIL, f"tools/list failed (HTTP {status}): {str(body)[:200]}")
        return

    served = body["result"].get("tools", [])
    names = {tool["name"] for tool in served}
    report(PASS, f"tools/list returned {len(names)} tools")

    missing = sorted(set(TOOLS) - names)
    added = sorted(names - set(TOOLS))
    if missing:
        report(FAIL, f"registry lists tools the server no longer serves: {missing}")
    if added:
        report(INFO, f"server serves tools not in the registry: {added}")
    if not missing and not added:
        report(PASS, "registry matches the server exactly")

    if dump:
        print("\n--- served tool schemas ---")
        print(json.dumps(served, indent=2, sort_keys=True))


def main():
    dump = "--dump" in sys.argv
    api_key = os.environ.get("ALLO_API_KEY")

    print(f"Allô MCP live check — {MCP_URL}\n")
    check_reachable_and_advertises_oauth()
    check_oauth_discovery()

    if api_key:
        print()
        check_tools(api_key, dump=dump)
    else:
        print()
        report(INFO, "ALLO_API_KEY not set — skipping authenticated tool discovery")

    print()
    if _failures:
        print(f"FAILED ({len(_failures)}):")
        for failure in _failures:
            print(f"  - {failure}")
        return 1
    print("All live checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
