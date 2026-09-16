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

VOICES = [
    {"id": "voice-aurora", "name": "Aurora", "style": "warm"},
    {"id": "voice-atlas", "name": "Atlas", "style": "neutral"},
]


class MockAlloMcp:
    """A callable fake of the Allo MCP tool surface."""

    def __init__(self, scopes=None, fail_with=None):
        # `scopes=None` means "everything"; pass a set to simulate a restricted
        # connection. `fail_with` forces an error for error-handling tests.
        self.scopes = scopes
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
