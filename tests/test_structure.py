"""Structural validation: manifest, MCP config, skills, commands, secrets.

Covers checks 1 (manifest), 2 (MCP config), 3 (skill discovery), and 5
(authentication configuration) from the plugin test plan. Stdlib only — no
dependencies, no network.

    python3 -m unittest discover -s tests -v
"""

import json
import re
import unittest
from pathlib import Path

from allo_registry import MCP_URL, TOOLS
from textutil import normalize

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / ".grok-plugin" / "plugin.json"
CURSOR_MANIFEST = ROOT / ".cursor-plugin" / "plugin.json"
MCP_CONFIG = ROOT / ".mcp.json"
CURSOR_MCP_CONFIG = ROOT / "mcp.json"
SKILLS_DIR = ROOT / "skills"
COMMANDS_DIR = ROOT / "commands"

# Public OAuth client for Cursor / Grok Bot (PKCE, empty secret). Not a secret.
CURSOR_GROK_BOT_CLIENT_ID = "e3d79ef3-9e84-452c-9269-df9ed022753a"

TOOL_MENTION_RE = re.compile(r"\ballo_[a-z0-9_]+\b")

# Identifiers that share the `allo_` prefix with tool names but aren't tools:
# MCP parameter names, and this repo's own module names. They are legitimately
# referenced in the docs and must not be reported as invented tools.
ALLO_NON_TOOL_NAMES = {
    "allo_number",
    "allo_numbers",
    "allo_sender_id",
    "allo_registry",
}


def parse_frontmatter(path: Path):
    """Parse YAML frontmatter the way the xAI catalog indexer does.

    Mirrors scripts/plugin_catalog.py in xai-org/plugin-marketplace: simple
    `key: value` lines plus `>`/`|` block scalars. If this parser can't read a
    field, neither can the marketplace index — so the test uses the same rules
    rather than a permissive YAML library.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text
    fields, i = {}, 1
    while i < len(lines):
        line = lines[i]
        if line.strip() in ("---", "..."):
            i += 1
            break
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        if re.match(r"^[|>][+-]?$", value):
            block, j = [], i + 1
            while j < len(lines) and (lines[j].startswith((" ", "\t")) or not lines[j].strip()):
                if lines[j].strip():
                    block.append(lines[j].strip())
                j += 1
            value, i = " ".join(block), j
        else:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            i += 1
        fields[key] = value
    return fields, "\n".join(lines[i:])


def skill_files():
    return sorted(SKILLS_DIR.glob("*/SKILL.md"))


def command_files():
    return sorted(COMMANDS_DIR.glob("*.md"))


class TestManifest(unittest.TestCase):
    """Check 1 — plugin manifest validity."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_is_at_the_path_grok_loads(self):
        self.assertTrue(MANIFEST.is_file(), ".grok-plugin/plugin.json must exist")

    def test_required_fields(self):
        for field in ("name", "version", "description"):
            self.assertIn(field, self.manifest)
            self.assertTrue(str(self.manifest[field]).strip(), f"{field} is empty")

    def test_name_is_kebab_case(self):
        # The marketplace requires a kebab-case, unique plugin id.
        self.assertRegex(self.manifest["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")

    def test_version_is_semver(self):
        self.assertRegex(self.manifest["version"], r"^\d+\.\d+\.\d+")

    def test_has_discovery_metadata(self):
        # homepage + keywords power the marketplace listing and the plugin CTA.
        self.assertTrue(self.manifest.get("homepage"))
        self.assertTrue(self.manifest.get("keywords"))

    def test_keywords_are_brand_scoped(self):
        # xAI rejects generic keywords: they mis-fire the plugin CTA on
        # unrelated requests. Every keyword must be Allô-specific.
        generic = {"phone", "calls", "sms", "crm", "api", "analytics", "voice", "ai"}
        for kw in self.manifest["keywords"]:
            self.assertNotIn(
                kw.lower(), generic, f"keyword {kw!r} is too generic for the marketplace CTA"
            )

    def test_logo_exists_if_declared(self):
        logo = self.manifest.get("logo")
        if logo:
            self.assertTrue((ROOT / logo).is_file(), f"declared logo missing: {logo}")


class TestMcpConfig(unittest.TestCase):
    """Check 2 — MCP configuration validity."""

    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(MCP_CONFIG.read_text(encoding="utf-8"))

    def test_declares_the_allo_server(self):
        self.assertIn("mcpServers", self.config)
        self.assertIn("allo", self.config["mcpServers"])

    def test_uses_remote_http_transport(self):
        server = self.config["mcpServers"]["allo"]
        self.assertEqual(server.get("type"), "http")
        self.assertEqual(server.get("url"), MCP_URL)

    def test_points_at_production_over_tls(self):
        self.assertTrue(self.config["mcpServers"]["allo"]["url"].startswith("https://"))

    def test_declares_exactly_one_server(self):
        # The plugin is a thin wrapper over the hosted MCP. A second server
        # would mean we started proxying, which this architecture avoids.
        self.assertEqual(len(self.config["mcpServers"]), 1)

    def test_does_not_spawn_a_local_process(self):
        server = self.config["mcpServers"]["allo"]
        for forbidden in ("command", "args"):
            self.assertNotIn(
                forbidden, server, "remote MCP must not execute anything locally"
            )


class TestCursorManifest(unittest.TestCase):
    """Cursor / Grok Bot plugin manifest (`.cursor-plugin/plugin.json`)."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(CURSOR_MANIFEST.read_text(encoding="utf-8"))

    def test_manifest_exists(self):
        self.assertTrue(CURSOR_MANIFEST.is_file(), ".cursor-plugin/plugin.json must exist")

    def test_required_fields(self):
        for field in ("name", "version", "description"):
            self.assertIn(field, self.manifest)
            self.assertTrue(str(self.manifest[field]).strip(), f"{field} is empty")

    def test_name_matches_grok_plugin(self):
        grok = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(self.manifest["name"], grok["name"])

    def test_pins_cursor_mcp_config(self):
        # Dual .mcp.json + mcp.json repos must pin so Cursor does not load the
        # Grok Build file (which has no static OAuth client id).
        self.assertEqual(self.manifest.get("mcpServers"), "./mcp.json")

    def test_logo_exists_if_declared(self):
        logo = self.manifest.get("logo")
        if logo:
            self.assertTrue((ROOT / logo).is_file(), f"declared logo missing: {logo}")


class TestCursorMcpConfig(unittest.TestCase):
    """Cursor / Grok Bot MCP config (`mcp.json`) with static OAuth client id."""

    @classmethod
    def setUpClass(cls):
        cls.config = json.loads(CURSOR_MCP_CONFIG.read_text(encoding="utf-8"))

    def test_config_exists(self):
        self.assertTrue(CURSOR_MCP_CONFIG.is_file(), "mcp.json must exist")

    def test_declares_the_allo_server(self):
        self.assertIn("mcpServers", self.config)
        self.assertIn("allo", self.config["mcpServers"])

    def test_points_at_production_over_tls(self):
        server = self.config["mcpServers"]["allo"]
        self.assertEqual(server.get("url"), MCP_URL)
        self.assertTrue(server["url"].startswith("https://"))

    def test_ships_static_oauth_client_id(self):
        # Cursor and Grok Bot need a pre-registered public client when the
        # authorization server has no registration_endpoint.
        auth = self.config["mcpServers"]["allo"].get("auth") or {}
        self.assertEqual(auth.get("CLIENT_ID"), CURSOR_GROK_BOT_CLIENT_ID)
        self.assertNotIn("CLIENT_SECRET", auth)

    def test_does_not_ship_api_key_headers(self):
        server = self.config["mcpServers"]["allo"]
        self.assertNotIn("headers", server)
        for forbidden in ("command", "args"):
            self.assertNotIn(forbidden, server)

    def test_declares_exactly_one_server(self):
        self.assertEqual(len(self.config["mcpServers"]), 1)


class TestAuthConfiguration(unittest.TestCase):
    """Check 5 — authentication configuration, and no committed secrets."""

    def test_no_hardcoded_credentials_in_grok_mcp_config(self):
        # Grok Build discovers OAuth at runtime. Do not put API keys or bearer
        # headers in .mcp.json. The Cursor twin (mcp.json) may ship a public
        # CLIENT_ID under auth — that is not a secret.
        raw = MCP_CONFIG.read_text(encoding="utf-8")
        for token in ("Authorization", "apiKey", "api_key", "Bearer", "headers", "CLIENT_ID"):
            self.assertNotIn(
                token, raw, f"{token!r} in .mcp.json — Grok Build auth is runtime OAuth only"
            )

    def test_cursor_mcp_has_no_api_key_headers(self):
        raw = CURSOR_MCP_CONFIG.read_text(encoding="utf-8")
        for token in ("Authorization", "apiKey", "api_key", "Bearer", '"headers"'):
            self.assertNotIn(
                token, raw, f"{token!r} in mcp.json — use auth.CLIENT_ID, not API keys"
            )

    def test_no_secrets_anywhere_in_the_repo(self):
        # Allô key/token shapes plus generic high-entropy assignments.
        patterns = [
            re.compile(r"\boat-[A-Fa-f0-9]{16,}"),          # Allô API key
            re.compile(r"\btem-[A-Fa-f0-9]{16,}"),          # Allô team id
            re.compile(r"Bearer\s+[A-Za-z0-9_\-.]{20,}"),   # bearer token
            re.compile(r"(?i)\b(api[_-]?key|secret|token|password)\s*[:=]\s*[\"'][^\"'{}$<]{16,}[\"']"),
        ]
        skip_dirs = {".git", "__pycache__", "node_modules"}
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(p in skip_dirs for p in path.parts):
                continue
            if path.suffix not in {".md", ".json", ".py", ".toml", ".yml", ".yaml", ".svg"}:
                continue
            # This file contains the detection patterns themselves.
            if path.resolve() == Path(__file__).resolve():
                continue
            content = path.read_text(encoding="utf-8", errors="replace")
            for pattern in patterns:
                self.assertIsNone(
                    pattern.search(content), f"possible secret in {path.relative_to(ROOT)}"
                )

    def test_skills_forbid_exposing_credentials(self):
        text = normalize((SKILLS_DIR / "allo" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn("never", text)
        for term in ("api key", "token", "authorization"):
            self.assertIn(term, text, f"skill must address handling of {term}")


class TestSkillDiscovery(unittest.TestCase):
    """Check 3 — skills are discoverable and well-formed."""

    def test_skills_exist(self):
        self.assertTrue(skill_files(), "no skills/*/SKILL.md found")

    def test_primary_skill_present(self):
        self.assertTrue((SKILLS_DIR / "allo" / "SKILL.md").is_file())

    def test_frontmatter_parses_and_has_required_fields(self):
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                fields, body = parse_frontmatter(path)
                self.assertTrue(fields, "frontmatter did not parse")
                self.assertIn("name", fields)
                self.assertIn("description", fields)
                self.assertTrue(body.strip(), "skill body is empty")

    def test_name_matches_directory(self):
        # Grok defaults a skill's name to its directory; a mismatch makes the
        # skill addressable under a name that isn't what the docs reference.
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                fields, _ = parse_frontmatter(path)
                self.assertEqual(fields["name"], path.parent.name)

    def test_descriptions_carry_trigger_language(self):
        # The description is the only thing Grok sees when deciding whether to
        # load the skill, so it must contain trigger vocabulary, not just a
        # title. 120 chars is the catalog's own display truncation point.
        for path in skill_files():
            with self.subTest(skill=path.parent.name):
                desc = parse_frontmatter(path)[0]["description"]
                self.assertGreater(len(desc), 120, "description too thin to trigger on")
                self.assertIn("allo", normalize(desc))

    def test_skill_names_are_unique(self):
        names = [parse_frontmatter(p)[0]["name"] for p in skill_files()]
        self.assertEqual(len(names), len(set(names)))


class TestCommands(unittest.TestCase):
    """Slash commands are discoverable and documented."""

    def test_commands_have_descriptions(self):
        for path in command_files():
            with self.subTest(command=path.stem):
                fields, body = parse_frontmatter(path)
                self.assertTrue(fields.get("description"), "command needs a description")
                self.assertTrue(body.strip(), "command body is empty")


class TestNoInventedTools(unittest.TestCase):
    """Every allo_* tool named anywhere in the plugin must exist on the server.

    This is the check that enforces "do not invent tools or schemas". Tool names
    in the registry were verified against the live MCP.
    """

    def _sources(self):
        return skill_files() + command_files() + [ROOT / "README.md"]

    def test_every_mentioned_tool_is_real(self):
        for path in self._sources():
            if not path.is_file():
                continue
            mentioned = set(TOOL_MENTION_RE.findall(path.read_text(encoding="utf-8")))
            unknown = sorted(mentioned - set(TOOLS) - ALLO_NON_TOOL_NAMES)
            with self.subTest(file=path.name):
                self.assertEqual(unknown, [], f"unknown Allô tools referenced: {unknown}")

    def test_primary_skill_covers_the_core_surface(self):
        text = (SKILLS_DIR / "allo" / "SKILL.md").read_text(encoding="utf-8")
        for tool in (
            "allo_get_me",
            "allo_search_conversation_items",
            "allo_send_sms",
            "allo_get_team_analytics",
            "allo_set_agent_status",
        ):
            self.assertIn(tool, text, f"primary skill should orchestrate {tool}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
