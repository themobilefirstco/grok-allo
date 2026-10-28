"""In-process mock of the Allo MCP server.

Lets the workflow tests exercise the orchestrations the skills describe without
touching the production server. Two guarantees make it useful rather than
decorative:

  1. It validates arguments against the verified registry, so a workflow that
     calls a tool with an invented parameter fails here.
  2. `allo_send_sms` NEVER sends. It records the intent and returns a dry-run
     receipt. There is no code path in this file that performs network I/O.

Fixture data is small, synthetic, and uses 555 numbers reserved for fiction.
"""

import copy

from allo_registry import ENUMS, LIMITS, TOOLS, VERIFIED_PARAM_TOOLS


class MockMcpError(Exception):
    """Mirrors an MCP tool error, with the shape the skills must handle."""

    def __init__(self, code, message):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


# --- Fixtures -------------------------------------------------------------

USERS = [
    {"id": "usr-001", "name": "Sergio Ramos", "role": "AGENT"},
    {"id": "usr-002", "name": "Dana Wu", "role": "AGENT"},
    {"id": "usr-003", "name": "Priya Nair", "role": "ADMIN"},
]

NUMBERS = [
    {"number": "+15005550101", "name": "Sales", "sms": True, "voice": True},
    {"number": "+15005550102", "name": "Support", "sms": False, "voice": True},
]

SENDER_IDS = ["Allo"]

TAGS = [
    {"key": "warm_lead", "name": "Warm lead"},
    {"key": "meeting_booked", "name": "Meeting booked"},
    {"key": "not_interested", "name": "Not interested"},
]

ITEMS = [
    {
        "id": "cll-001",
        "type": "CALL",
        "direction": "INBOUND",
        "result": "VOICEMAIL",
        "date": "2026-09-10",
        "contact_number": "+15005559001",
        "user_id": "usr-001",
        "allo_number": "+15005550101",
        "menu_path": [{"node_id": "node-1", "digit": "1"}],
        "unread": True,
        "tags": [],
        "summary": "Caller asked about pricing for a 12-seat plan, left a voicemail.",
        "transcript": "Hi, I'm calling about your pricing for around twelve seats. Call me back.",
    },
    {
        "id": "cll-002",
        "type": "CALL",
        "direction": "INBOUND",
        "result": "VOICEMAIL",
        "date": "2026-09-10",
        "contact_number": "+15005559002",
        "user_id": "usr-002",
        "allo_number": "+15005550101",
        "menu_path": [{"node_id": "node-1", "digit": "2"}, {"node_id": "node-4", "digit": "1"}],
        "unread": True,
        "tags": [],
        "summary": "Existing customer, wants to cancel, frustrated about billing.",
        "transcript": "This is the third time I'm calling about being double charged. Cancel it.",
    },
    {
        "id": "cll-003",
        "type": "CALL",
        "direction": "OUTBOUND",
        "result": "ANSWERED",
        "date": "2026-09-10",
        "contact_number": "+15005559003",
        "user_id": "usr-001",
        "allo_number": "+15005550101",
        "unread": False,
        "tags": ["meeting_booked"],
        "summary": "Discovery call with Acme. Booked a demo for next Tuesday.",
        "transcript": "Pricing looks workable. Let's get a demo on the calendar for Tuesday.",
    },
    {
        "id": "cll-004",
        "type": "CALL",
        "direction": "INBOUND",
        "result": "ANSWERED",
        "date": "2026-09-09",
        "contact_number": "+15005559004",
        "user_id": "usr-003",
        "allo_number": "+15005550102",
        "unread": False,
        "tags": [],
        "summary": "Wrong number.",
        "transcript": "Sorry, I was trying to reach the dentist.",
    },
    {
        "id": "sms-001",
        "type": "SMS",
        "direction": "OUTBOUND",
        "result": None,
        "date": "2026-09-10",
        "contact_number": "+15005559003",
        "user_id": "usr-001",
        "allo_number": "+15005550101",
        "unread": False,
        "tags": [],
        "summary": "Confirmed Tuesday demo.",
        "transcript": None,
    },
]

AGENT = {
    "status": "ONLINE",
    "voice": "voice-aurora",
    "prompt": "You are the receptionist for Acme Co. Greet callers, take a message.",
    "knowledge": [
        {"id": "knw-001", "url": "https://acme.example/pricing", "status": "ENABLED"},
        {"id": "knw-002", "url": "https://acme.example/old-faq", "status": "ENABLED"},
    ],
}

# Lines each user can access, as the server's line-access rule would resolve it.
LINE_ACCESS = {
    "usr-001": {"+15005550101", "+15005550102", "+15005550301"},
    "usr-002": {"+15005550101"},
    "usr-003": {"+15005550101", "+15005550102"},
}

# Which workspace each line belongs to. +15005550301 is a line usr-001 also
# works in another workspace, which the admin below doesn't manage.
LINE_WORKSPACE = {
    "+15005550101": "ws-main",
    "+15005550102": "ws-main",
    "+15005550301": "ws-other",
}

# Workspaces each admin or manager manages.
MANAGED_WORKSPACES = {"usr-003": {"ws-main"}}

# The published phone menu on the Sales line: 1 = Sales FR, 2 = Support FR,
# which opens a second menu where 1 = Billing. Shapes mirror api-allo: every
# option carries a ready MENU_BRANCH `condition` whose single branch is its path.
def _menu_option(path, digits, label):
    return {
        "node_id": path[-1]["node_id"],
        "path": path,
        "digits": digits,
        "label": label,
        "condition": {"type": "MENU_BRANCH", "branches": [path], "include_no_choice": False},
    }


MENU_OPTIONS = {
    "+15005550101": [
        _menu_option([{"node_id": "node-1", "digit": "1"}], "1", "Sales FR"),
        _menu_option([{"node_id": "node-1", "digit": "2"}], "2", "Support FR"),
        _menu_option(
            [{"node_id": "node-1", "digit": "2"}, {"node_id": "node-4", "digit": "1"}],
            "2>1",
            "Billing",
        ),
    ],
    # Not routed by the call-flow engine, so it has no menu to read.
    "+15005550102": [],
}

# Suggestions carry a ready `source` (one line, conditions filled in), and no emoji.
INBOX_SUGGESTIONS = [
    {
        "allo_number": "+15005550101",
        "name": "Sales",
        "description": "Everything on the Sales line",
        "branch": None,
        "answered": 3, "rung": 4, "texted": 1, "score": 90,
        "source": {"allo_number": "+15005550101", "conditions": []},
    },
    {
        "allo_number": "+15005550102",
        "name": "Support",
        "description": "Everything on the Support line",
        "branch": None,
        "answered": 1, "rung": 1, "texted": 0, "score": 40,
        "source": {"allo_number": "+15005550102", "conditions": []},
    },
    {
        "allo_number": "+15005550101",
        "name": "Sales FR",
        "description": "Callers who pressed 1 on Sales",
        "branch": [{"node_id": "node-1", "digit": "1"}],
        "answered": 1, "rung": 1, "texted": 0, "score": 70,
        "source": {
            "allo_number": "+15005550101",
            "conditions": [dict(MENU_OPTIONS["+15005550101"][0]["condition"])],
        },
    },
]

INBOX_FILTER_TYPES = (
    "INBOUND_CALL",
    "OUTBOUND_CALL",
    "TRANSFERRED",
    "INBOUND_TEXT_MESSAGE",
    "OUTBOUND_TEXT_MESSAGE",
    "VOICEMAIL",
    "AI_ASSISTANT",
)
INBOX_FILTER_KEYS = {"types", "user_ids", "contact_ids", "contact_list_ids", "unread"}


def _activity_types(item):
    """The inbox filter types one conversation item counts as."""
    if item["type"] == "SMS":
        return {f"{item['direction']}_TEXT_MESSAGE"}
    kinds = {f"{item['direction']}_CALL"}
    if item["result"] == "VOICEMAIL":
        kinds.add("VOICEMAIL")
    if item["result"] == "TRANSFERRED":
        kinds.add("TRANSFERRED")
    return kinds


VOICES = [
    {"id": "voice-aurora", "name": "Aurora", "style": "warm"},
    {"id": "voice-atlas", "name": "Atlas", "style": "neutral"},
]


class MockAlloMcp:
    """A callable fake of the Allo MCP tool surface."""

    def __init__(self, scopes=None, fail_with=None, caller="usr-003", read_lag=False):
        # `scopes=None` means "everything"; pass a set to simulate a restricted
        # connection. `fail_with` forces an error for error-handling tests.
        # `caller` is the user the connection acts as (default: the admin).
        # `read_lag` makes a fresh inbox miss its first lookup, as a replica would.
        self.scopes = scopes
        self.caller = caller
        self.read_lag = read_lag
        self.unsettled = set()
        self._next_inbox = 0
        self.inboxes = []          # created inboxes, as the API returns them
        self.inbox_owners = {}     # inbox id -> owning user (server-side only, never returned)
        self.pins = []             # [(allo_number, contact_number)] for the caller
        self.fail_with = fail_with or {}
        self.calls = []            # [(tool, args)] in order
        self.sent_sms = []         # dry-run receipts; never leaves the process
        self.applied_tags = []
        self.agent = dict(AGENT, knowledge=[dict(k) for k in AGENT["knowledge"]])

    # -- plumbing --

    def call(self, tool, **args):
        if tool not in TOOLS:
            raise MockMcpError("TOOL_NOT_FOUND", f"unknown tool {tool!r}")

        required, optional = TOOLS[tool]
        if tool in VERIFIED_PARAM_TOOLS:
            allowed = set(required) | set(optional)
            unknown = sorted(set(args) - allowed)
            if unknown:
                raise MockMcpError("INVALID_ARGUMENT", f"unknown params for {tool}: {unknown}")
            missing = sorted(set(required) - set(args))
            if missing:
                raise MockMcpError("INVALID_ARGUMENT", f"missing required params: {missing}")

        self.calls.append((tool, args))

        if tool in self.fail_with:
            code, message = self.fail_with[tool]
            raise MockMcpError(code, message)

        handler = getattr(self, f"_{tool}", None)
        if handler is None:
            raise MockMcpError("NOT_IMPLEMENTED", f"mock has no handler for {tool}")
        return handler(**args)

    def tools_used(self):
        return [name for name, _ in self.calls]

    def count(self, tool):
        return sum(1 for name, _ in self.calls if name == tool)

    def _require(self, scope):
        if self.scopes is not None and scope not in self.scopes:
            raise MockMcpError("FORBIDDEN", f"missing scope {scope}")

    # -- discovery --

    def _allo_get_me(self):
        return {
            "team": {"id": "tem-mock", "name": "Mock Co"},
            "scopes": sorted(self.scopes) if self.scopes is not None else ["*"],
            "rate_limits": {
                "read_per_second": LIMITS["read_per_second"],
                "write_per_second": LIMITS["write_per_second"],
            },
        }

    def _allo_list_users(self, **_):
        self._require("USERS_READ")
        return {"data": USERS}

    def _allo_list_numbers(self, **_):
        self._require("PHONE_NUMBERS_READ")
        return {"data": NUMBERS, "sender_ids": SENDER_IDS}

    def _allo_list_tags(self):
        self._require("TAGS_READ")
        return {"data": TAGS}

    # -- conversations --

    def _allo_search_conversation_items(self, **args):
        self._require("CONVERSATIONS_READ")
        for key, enum_key in (
            ("result", "search.result"),
            ("direction", "search.direction"),
            ("type", "search.type"),
            ("sort", "search.sort"),
            ("extend", "search.extend"),
        ):
            if key in args and args[key] not in ENUMS[enum_key]:
                raise MockMcpError(
                    "INVALID_ARGUMENT", f"{key}={args[key]!r} not in {ENUMS[enum_key]}"
                )

        size = args.get("size", LIMITS["page_size_default"])
        if size > LIMITS["page_size_max"]:
            raise MockMcpError("INVALID_ARGUMENT", "size exceeds 100")

        rows = list(ITEMS)
        if args.get("type", "ALL") != "ALL":
            rows = [r for r in rows if r["type"] == args["type"]]
        for field in ("direction", "result", "user_id", "allo_number", "contact_number"):
            if args.get(field):
                rows = [r for r in rows if r.get(field) == args[field]]
        if args.get("date_from"):
            rows = [r for r in rows if r["date"] >= args["date_from"]]
        if args.get("date_to"):
            rows = [r for r in rows if r["date"] <= args["date_to"]]
        if args.get("unread") is not None:
            rows = [r for r in rows if r["unread"] == args["unread"]]
        if args.get("tags"):
            rows = [r for r in rows if set(args["tags"]) & set(r["tags"])]
        if args.get("search"):
            # Mirrors the server: terms AND'd, prefix matching.
            terms = args["search"].lower().split()
            def matches(row):
                hay = " ".join(
                    str(row.get(f) or "") for f in ("summary", "transcript")
                ).lower()
                return all(any(w.startswith(t) for w in hay.split()) for t in terms)
            rows = [r for r in rows if matches(r)]

        total = len(rows)
        page = args.get("page", 1)
        window = rows[(page - 1) * size : page * size]
        keep_transcript = args.get("extend") == "transcript"
        data = [
            {k: v for k, v in r.items() if keep_transcript or k != "transcript"}
            for r in window
        ]
        return {"data": data, "pagination": {"total_count": total, "page": page, "size": size}}

    def _allo_get_conversation_item(self, id, **_):
        self._require("CONVERSATIONS_READ")
        for row in ITEMS:
            if row["id"] == id:
                return {"data": row}
        raise MockMcpError("NOT_FOUND", f"no item {id}")

    def _allo_batch_get_conversation_items(self, ids, **_):
        self._require("CONVERSATIONS_READ")
        if len(ids) > LIMITS["batch_get_max"]:
            raise MockMcpError("INVALID_ARGUMENT", "max 100 ids")
        return {"data": [r for r in ITEMS if r["id"] in set(ids)]}

    def _allo_mark_conversation(self, contact_number, action):
        self._require("CONVERSATIONS_WRITE")
        return {"data": {"contact_number": contact_number, "action": action}}

    # -- actions --

    def _allo_add_call_tags(self, id, tags):
        self._require("TAGS_WRITE")
        valid = {t["key"] for t in TAGS}
        unknown = sorted(set(tags) - valid)
        if unknown:
            raise MockMcpError("INVALID_ARGUMENT", f"unknown tag keys: {unknown}")
        row = next((r for r in ITEMS if r["id"] == id), None)
        if row is None:
            raise MockMcpError("NOT_FOUND", f"no call {id}")
        if set(tags) & set(row["tags"]):
            raise MockMcpError("TAG_ALREADY_EXISTS", "tag already applied")
        self.applied_tags.append((id, tuple(tags)))
        return {"data": {"id": id, "tags": tags}}

    def _allo_remove_call_tag(self, id, tag):
        self._require("TAGS_WRITE")
        return {"data": {"id": id, "removed": tag}}

    def _allo_send_sms(self, to, content, allo_number=None, allo_sender_id=None):
        """DRY RUN ONLY — records intent, never transmits."""
        self._require("SMS_SEND")
        if bool(allo_number) == bool(allo_sender_id):
            raise MockMcpError(
                "INVALID_ARGUMENT", "provide exactly one of allo_number or allo_sender_id"
            )
        if not to.startswith("+"):
            raise MockMcpError("INVALID_ARGUMENT", "recipient must be E.164")
        if allo_number:
            line = next((n for n in NUMBERS if n["number"] == allo_number), None)
            if line is None:
                raise MockMcpError("NOT_FOUND", f"unknown line {allo_number}")
            if not line["sms"]:
                raise MockMcpError("INVALID_ARGUMENT", f"{allo_number} has no SMS capability")
        receipt = {
            "dry_run": True,
            "to": to,
            "content": content,
            "from": allo_number or allo_sender_id,
        }
        self.sent_sms.append(receipt)
        return {"data": receipt}

    def _allo_add_to_dialing_queue(self, numbers):
        self._require("DIALING_QUEUE_READ_WRITE")
        if len(numbers) > LIMITS["dialing_queue_max"]:
            raise MockMcpError("INVALID_ARGUMENT", "queue max is 1000")
        return {"data": {"added": len(numbers)}}

    def _allo_get_dialing_queue(self):
        self._require("DIALING_QUEUE_READ_WRITE")
        return {"data": {"numbers": []}}

    # -- analytics --

    def _analytics_guard(self, args):
        self._require("CONVERSATIONS_READ")
        if args.get("user_ids") and args.get("allo_numbers"):
            raise MockMcpError(
                "INVALID_ARGUMENT", "cannot combine user_ids and allo_numbers"
            )

    def _allo_get_team_analytics(self, date_from, date_to, **args):
        self._analytics_guard(args)
        rows = [r for r in ITEMS if date_from <= r["date"] <= date_to and r["type"] == "CALL"]
        answered = [r for r in rows if r["result"] == "ANSWERED"]
        payload = {
            "total_calls": len(rows),
            "answered": len(answered),
            "answer_rate": round(len(answered) / len(rows), 3) if rows else 0.0,
            "talk_time_seconds": 60 * len(answered),
        }
        if args.get("user_ids"):
            payload["by_user"] = [
                {"user_id": uid, "total_calls": sum(1 for r in rows if r["user_id"] == uid)}
                for uid in args["user_ids"]
            ]
        if args.get("compare_date_from"):
            payload["comparison"] = {"total_calls": 2, "answer_rate": 0.5}
        return {"data": payload}

    def _allo_get_team_outbound_analytics(self, date_from, date_to, **args):
        self._analytics_guard(args)
        rows = [
            r
            for r in ITEMS
            if date_from <= r["date"] <= date_to
            and r["type"] == "CALL"
            and r["direction"] == "OUTBOUND"
        ]
        conversion_tags = set(args.get("tags") or [])
        funnel = {
            "DIAL": len(rows),
            "CONNECTED": sum(1 for r in rows if r["result"] == "ANSWERED"),
            "CONVERSATION": sum(1 for r in rows if r["result"] == "ANSWERED"),
            "CONVERSION": sum(1 for r in rows if conversion_tags & set(r["tags"])),
        }
        payload = {"funnel": funnel, "leaderboard": [{"user_id": "usr-001", "dials": len(rows)}]}
        if args.get("extend") == "items":
            if not args.get("stage"):
                raise MockMcpError("INVALID_ARGUMENT", "extend=items requires stage")
            if args["stage"] not in ENUMS["outbound.stage"]:
                raise MockMcpError("INVALID_ARGUMENT", "bad stage")
            payload["items"] = [{"id": r["id"]} for r in rows]
        return {"data": payload}

    # -- receptionist --

    def _allo_get_agent(self, **_):
        return {"data": self.agent}

    def _allo_update_agent(self, **args):
        self.agent.update({k: v for k, v in args.items() if k != "allo_number"})
        return {"data": self.agent}

    def _allo_set_agent_prompt(self, prompt, **_):
        self.agent["prompt"] = prompt
        return {"data": {"prompt": prompt}}

    def _allo_set_agent_status(self, status, **_):
        if status not in ("ONLINE", "OFFLINE"):
            raise MockMcpError("INVALID_ARGUMENT", "status must be ONLINE or OFFLINE")
        self.agent["status"] = status
        return {"data": {"status": status}}

    def _allo_list_voices(self):
        return {"data": VOICES}

    def _allo_add_agent_knowledge_website(self, url, **_):
        entry = {"id": f"knw-{len(self.agent['knowledge']) + 1:03d}", "url": url, "status": "ENABLED"}
        self.agent["knowledge"].append(entry)
        return {"data": entry}

    def _allo_set_agent_knowledge_website_status(self, id, status):
        for entry in self.agent["knowledge"]:
            if entry["id"] == id:
                entry["status"] = status
                return {"data": entry}
        raise MockMcpError("NOT_FOUND", f"no knowledge source {id}")

    def _allo_delete_agent_knowledge(self, id):
        before = len(self.agent["knowledge"])
        self.agent["knowledge"] = [k for k in self.agent["knowledge"] if k["id"] != id]
        if len(self.agent["knowledge"]) == before:
            raise MockMcpError("NOT_FOUND", f"no knowledge source {id}")
        return {"data": {"deleted": id}}

    # -- inboxes --

    UPDATABLE_INBOX_FIELDS = {"name", "emoji", "sources", "filters", "notifications_muted"}

    def _inbox_owner(self, user_id):
        """The user an inbox call acts for, enforcing the teammate rule."""
        if user_id is None or user_id == self.caller:
            return self.caller
        role = next(u["role"] for u in USERS if u["id"] == self.caller)
        # Unknown and unmanaged users look the same: the caller may not act for them.
        if user_id not in LINE_ACCESS or role not in ("ADMIN", "MANAGER"):
            raise MockMcpError("FORBIDDEN", "only admins and managers manage a teammate's inboxes")
        return user_id

    def _require_line(self, user, line):
        if line not in LINE_ACCESS.get(user, set()):
            raise MockMcpError("ALLO_NUMBER_FORBIDDEN", f"{user} cannot access {line}")

    def _check_sources(self, owner, sources):
        if not sources:
            raise MockMcpError("INVALID_INBOX_SOURCE", "an inbox needs at least one source")
        lines = [s.get("allo_number") for s in sources]
        if len(set(lines)) != len(lines):
            raise MockMcpError("INVALID_INBOX_SOURCE", "one source per line")
        for source in sources:
            line = source.get("allo_number")
            self._require_line(owner, line)
            # The API rejects menu nodes and steps that aren't in the line's published menu.
            known_steps = {
                (step["node_id"], step["digit"])
                for option in MENU_OPTIONS.get(line, [])
                for step in option["path"]
            }
            conditions = source.get("conditions") or []
            if conditions and not MENU_OPTIONS.get(line):
                raise MockMcpError(
                    "INVALID_INBOX_SOURCE", f"{line} has no phone menu, so it takes no menu conditions"
                )
            if sum(1 for c in conditions if c.get("type") == "MENU_BRANCH") > 1:
                raise MockMcpError(
                    "INVALID_INBOX_SOURCE",
                    "at most one MENU_BRANCH per source: concatenate the branches instead",
                )
            option_nodes = []
            branch_nodes = set()
            for cond in conditions:
                if not isinstance(cond.get("include_no_choice"), bool):
                    raise MockMcpError("INVALID_INBOX_SOURCE", "include_no_choice is required")
                if cond.get("type") == "MENU_OPTION":
                    node = cond.get("node_id")
                    if node not in {n for n, _ in known_steps}:
                        raise MockMcpError("INVALID_INBOX_SOURCE", f"unknown menu node {node}")
                    option_nodes.append(node)
                elif cond.get("type") == "MENU_BRANCH":
                    branches = cond.get("branches") or []
                    if not branches:
                        raise MockMcpError("INVALID_INBOX_SOURCE", "MENU_BRANCH needs branches")
                    for branch in branches:
                        for step in branch:
                            if (step.get("node_id"), step.get("digit")) not in known_steps:
                                raise MockMcpError(
                                    "INVALID_INBOX_SOURCE", f"unknown menu step {step}"
                                )
                            branch_nodes.add(step["node_id"])
                else:
                    raise MockMcpError("INVALID_INBOX_SOURCE", f"unknown condition {cond.get('type')}")
            if len(set(option_nodes)) != len(option_nodes) or set(option_nodes) & branch_nodes:
                raise MockMcpError("INVALID_INBOX_SOURCE", "a menu node appears in two conditions")

    @staticmethod
    def _normalize_filters(filters):
        """Validate like the API (keys, types, blank ids, 50 users) and fill all five keys."""
        filters = filters or {}
        if set(filters) - INBOX_FILTER_KEYS:
            raise MockMcpError("INVALID_INBOX_FILTERS", f"unknown filter keys {sorted(set(filters) - INBOX_FILTER_KEYS)}")
        if set(filters.get("types") or []) - set(INBOX_FILTER_TYPES):
            raise MockMcpError("INVALID_INBOX_FILTERS", "unknown activity type")
        user_ids = filters.get("user_ids") or []
        if len(user_ids) > 50:
            raise MockMcpError("INVALID_INBOX_FILTERS", "at most 50 user ids")
        for key in ("user_ids", "contact_ids", "contact_list_ids"):
            if any(not str(v).strip() for v in filters.get(key) or []):
                raise MockMcpError("INVALID_INBOX_FILTERS", f"blank id in {key}")
        return {
            "types": list(filters.get("types") or []),
            "user_ids": list(user_ids),
            "contact_ids": list(filters.get("contact_ids") or []),
            "contact_list_ids": list(filters.get("contact_list_ids") or []),
            "unread": bool(filters.get("unread", False)),
        }

    def _managed_lines(self, sources):
        """The sources' lines that sit in a workspace the caller manages."""
        managed = MANAGED_WORKSPACES.get(self.caller, set())
        return {s["allo_number"] for s in sources if LINE_WORKSPACE.get(s["allo_number"]) in managed}

    def _visible(self, inbox, owner):
        # For a teammate, an admin only sees inboxes with a line in a workspace they manage.
        return owner == self.caller or bool(self._managed_lines(inbox["sources"]))

    def _check_teammate_write(self, owner, sources):
        if owner != self.caller and not self._managed_lines(sources):
            raise MockMcpError(
                "INVALID_INBOX_SOURCE", "a teammate's inbox needs a line in a workspace you manage"
            )

    def seed_inbox(self, owner, name, sources):
        """Test helper: an inbox the user made themselves, bypassing the caller's checks."""
        self._next_inbox += 1
        inbox = {
            "id": f"inb_{self._next_inbox:03d}",
            "name": name,
            "emoji": None,
            "sources": copy.deepcopy(sources),
            "filters": self._normalize_filters(None),
            "notifications_muted": False,
        }
        self.inboxes.append(inbox)
        self.inbox_owners[inbox["id"]] = owner
        return copy.deepcopy(inbox)

    def _find_inbox(self, inbox_id, owner):
        if inbox_id in self.unsettled:
            # Read-after-create lag: the first lookup of a fresh inbox misses once.
            self.unsettled.discard(inbox_id)
            raise MockMcpError("INBOX_NOT_FOUND", f"no inbox {inbox_id}")
        inbox = next((i for i in self.inboxes if i["id"] == inbox_id), None)
        # Inboxes are personal: someone else's inbox is indistinguishable from a missing one.
        if inbox is None or self.inbox_owners[inbox_id] != owner or not self._visible(inbox, owner):
            raise MockMcpError("INBOX_NOT_FOUND", f"no inbox {inbox_id}")
        return inbox

    def _allo_list_inboxes(self, user_id=None):
        self._require("INBOXES_READ")
        owner = self._inbox_owner(user_id)
        return {
            "data": [
                copy.deepcopy(i)
                for i in self.inboxes
                if self.inbox_owners[i["id"]] == owner and self._visible(i, owner)
            ]
        }

    def _allo_get_inbox_suggestions(self):
        # The caller's own suggestions only: there is no user_id.
        self._require("INBOXES_READ")
        return {"data": copy.deepcopy(INBOX_SUGGESTIONS)}

    def _allo_list_menu_options(self, number):
        self._require("INBOXES_READ")
        self._require_line(self.caller, number)
        # Lines not routed by the call-flow engine have no menu: empty, not an error.
        return {"data": copy.deepcopy(MENU_OPTIONS.get(number, []))}

    def _allo_create_inbox(
        self, name, sources, emoji=None, filters=None, notifications_muted=False, user_id=None
    ):
        self._require("INBOXES_WRITE")
        if not name or not name.strip():
            raise MockMcpError("INBOX_NAME_REQUIRED", "name is required")
        owner = self._inbox_owner(user_id)
        owned = sum(1 for o in self.inbox_owners.values() if o == owner)
        if owned >= LIMITS["inboxes_per_user_max"]:
            raise MockMcpError("INBOX_LIMIT_REACHED", "This user already has the maximum of 50 inboxes.")
        self._check_sources(owner, sources)
        self._check_teammate_write(owner, sources)
        self._next_inbox += 1
        inbox = {
            "id": f"inb_{self._next_inbox:03d}",
            "name": name,
            "emoji": emoji,
            "sources": copy.deepcopy(sources),
            "filters": self._normalize_filters(filters),
            "notifications_muted": bool(notifications_muted),
        }
        self.inboxes.append(inbox)
        self.inbox_owners[inbox["id"]] = owner
        if self.read_lag:
            self.unsettled.add(inbox["id"])
        return {"data": copy.deepcopy(inbox)}

    def _allo_update_inbox(self, inbox_id, user_id=None, **changes):
        self._require("INBOXES_WRITE")
        unknown = sorted(set(changes) - self.UPDATABLE_INBOX_FIELDS)
        if unknown:
            raise MockMcpError("INVALID_ARGUMENT", f"cannot update {unknown}")
        owner = self._inbox_owner(user_id)
        inbox = self._find_inbox(inbox_id, owner)
        if "name" in changes and (not changes["name"] or not changes["name"].strip()):
            raise MockMcpError("INBOX_NAME_REQUIRED", "name is required")
        if "sources" in changes:
            self._check_sources(owner, changes["sources"])
            self._check_teammate_write(owner, changes["sources"])
            changes["sources"] = copy.deepcopy(changes["sources"])
        if "filters" in changes:
            # Replaced wholesale; null clears them.
            changes["filters"] = self._normalize_filters(changes["filters"])
        inbox.update(changes)
        return {"data": copy.deepcopy(inbox)}

    def _allo_delete_inbox(self, inbox_id, user_id=None):
        self._require("INBOXES_WRITE")
        owner = self._inbox_owner(user_id)
        inbox = self._find_inbox(inbox_id, owner)
        if owner != self.caller:
            lines = {s["allo_number"] for s in inbox["sources"]}
            if lines - self._managed_lines(inbox["sources"]):
                raise MockMcpError(
                    "FORBIDDEN", "this inbox also holds lines in a workspace you don't manage"
                )
        self.inboxes.remove(inbox)
        del self.inbox_owners[inbox_id]
        return {"deleted": True, "id": inbox_id}

    @staticmethod
    def _source_matches(source, item):
        if item["allo_number"] != source["allo_number"]:
            return False
        conditions = source.get("conditions") or []
        if not conditions:
            return True
        path = [(s["node_id"], s["digit"]) for s in item.get("menu_path") or []]
        for cond in conditions:
            if cond["type"] == "MENU_BRANCH":
                for branch in cond["branches"]:
                    steps = [(s["node_id"], s["digit"]) for s in branch]
                    if path[: len(steps)] == steps:
                        return True
            elif cond["type"] == "MENU_OPTION":
                if any(n == cond["node_id"] and d in cond.get("digits", []) for n, d in path):
                    return True
        return False

    @staticmethod
    def _filters_match(filters, items):
        # A saved `unread` is NOT applied: in the app it is a client-side toggle.
        if filters.get("types") and not any(
            _activity_types(i) & set(filters["types"]) for i in items
        ):
            return False
        if filters.get("user_ids") and not any(i["user_id"] in filters["user_ids"] for i in items):
            return False
        return True

    def _allo_list_conversations(self, allo_number=None, inbox_id=None, pinned=None, unread=None, **_):
        self._require("CONVERSATIONS_READ")
        if bool(allo_number) == bool(inbox_id):
            raise MockMcpError("INVALID_REQUEST", "provide exactly one of allo_number or inbox_id")
        if inbox_id:
            inbox = self._find_inbox(inbox_id, self.caller)
            items = [i for i in ITEMS if any(self._source_matches(s, i) for s in inbox["sources"])]
            filters = inbox["filters"]
        else:
            items = [i for i in ITEMS if i["allo_number"] == allo_number]
            filters = {}
        groups = {}
        for item in items:
            groups.setdefault((item["allo_number"], item["contact_number"]), []).append(item)
        data = [
            {
                "contact_number": contact,
                "allo_number": line,
                "pinned": (line, contact) in self.pins,
                "unread": any(i["unread"] for i in group),
            }
            for (line, contact), group in groups.items()
            if self._filters_match(filters, group)
        ]
        if pinned is not None:
            data = [r for r in data if r["pinned"] == pinned]
        if unread is not None:
            data = [r for r in data if r["unread"] == unread]
        return {"data": data, "pagination": {"total_count": len(data)}}

    def _allo_pin_conversation(self, contact_number, allo_number):
        self._require("CONVERSATIONS_WRITE")
        self._require_line(self.caller, allo_number)
        key = (allo_number, contact_number)
        if key not in self.pins:
            if len(self.pins) >= LIMITS["pinned_conversations_max"]:
                raise MockMcpError(
                    "PIN_LIMIT_REACHED",
                    "You already pinned the maximum of 10 conversations.",
                )
            self.pins.append(key)
        return {"pinned": True, "contact_number": contact_number, "allo_number": allo_number}

    def _allo_unpin_conversation(self, contact_number, allo_number):
        self._require("CONVERSATIONS_WRITE")
        self._require_line(self.caller, allo_number)
        key = (allo_number, contact_number)
        if key in self.pins:
            self.pins.remove(key)
        return {"pinned": False, "contact_number": contact_number, "allo_number": allo_number}
