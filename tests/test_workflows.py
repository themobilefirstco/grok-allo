"""Workflow and safety tests against the mock MCP.

Covers checks 7-12 of the plugin test plan: read-only, SMS, tagging, analytics,
receptionist, and error handling.

Two kinds of test live here:

  * **Workflow tests** replay the orchestration the skills prescribe against the
    mock and assert the tool sequence is correct and efficient. They prove the
    documented workflow is executable with real parameters.
  * **Contract tests** assert the skill text itself states the safety rules —
    the rules only bind Grok if they're actually written down.

No real SMS is ever sent: the mock's send path is dry-run with no network I/O.
"""

import re
import unittest
from pathlib import Path

from allo_registry import DESTRUCTIVE_TOOLS, ENUMS, TOOLS
from mock_mcp import MockAlloMcp, MockMcpError
from textutil import normalize

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

YESTERDAY = "2026-09-10"


def skill_text(name):
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def all_skill_text():
    return "\n".join(p.read_text(encoding="utf-8") for p in SKILLS.glob("*/SKILL.md"))


class TestReadOnlyWorkflow(unittest.TestCase):
    """Check 7 — read-only analysis performs no writes."""

    def setUp(self):
        self.mcp = MockAlloMcp()

    def test_missed_calls_uses_the_documented_proxy(self):
        # No MISSED filter exists; the skill prescribes INBOUND + VOICEMAIL.
        result = self.mcp.call(
            "allo_search_conversation_items",
            direction="INBOUND",
            result="VOICEMAIL",
            date_from=YESTERDAY,
            date_to=YESTERDAY,
        )
        ids = {row["id"] for row in result["data"]}
        self.assertEqual(ids, {"cll-001", "cll-002"})

    def test_missed_is_not_a_valid_result_value(self):
        # Guards against the skill ever being edited to claim a MISSED filter.
        self.assertNotIn("MISSED", ENUMS["search.result"])
        with self.assertRaises(MockMcpError):
            self.mcp.call("allo_search_conversation_items", result="MISSED")

    def test_count_before_fetch_uses_size_one(self):
        result = self.mcp.call("allo_search_conversation_items", size=1, type="CALL")
        self.assertEqual(result["pagination"]["total_count"], 4)
        self.assertEqual(len(result["data"]), 1, "counting must not fetch rows")

    def test_narrow_then_deepen_batches_the_drilldown(self):
        found = self.mcp.call(
            "allo_search_conversation_items", direction="INBOUND", result="VOICEMAIL"
        )
        ids = [row["id"] for row in found["data"]]
        self.mcp.call("allo_batch_get_conversation_items", ids=ids)
        # One batch call, not one call per item.
        self.assertEqual(self.mcp.count("allo_get_conversation_item"), 0)
        self.assertEqual(self.mcp.count("allo_batch_get_conversation_items"), 1)

    def test_transcripts_excluded_unless_requested(self):
        plain = self.mcp.call("allo_search_conversation_items", type="CALL")
        self.assertNotIn("transcript", plain["data"][0])
        extended = self.mcp.call(
            "allo_search_conversation_items", type="CALL", extend="transcript"
        )
        self.assertIn("transcript", extended["data"][0])

    def test_keyword_search_is_and_prefix_matched(self):
        hit = self.mcp.call(
            "allo_search_conversation_items", search="pricing", sort="RELEVANCE"
        )
        self.assertTrue(hit["data"], "prefix match should find 'pricing'")
        miss = self.mcp.call(
            "allo_search_conversation_items", search="pricing unicorn", sort="RELEVANCE"
        )
        self.assertEqual(miss["data"], [], "terms are AND'd")

    def test_no_writes_occurred(self):
        self.mcp.call("allo_search_conversation_items", date_from=YESTERDAY, date_to=YESTERDAY)
        self.mcp.call("allo_get_team_analytics", date_from=YESTERDAY, date_to=YESTERDAY)
        self.assertEqual(self.mcp.sent_sms, [])
        self.assertEqual(self.mcp.applied_tags, [])

    def test_empty_result_is_representable(self):
        result = self.mcp.call("allo_search_conversation_items", date_from="2030-01-01")
        self.assertEqual(result["data"], [])
        self.assertEqual(result["pagination"]["total_count"], 0)


class TestSmsWorkflow(unittest.TestCase):
    """Check 8 — SMS. Dry-run only; nothing leaves the process."""

    def setUp(self):
        self.mcp = MockAlloMcp()

    def test_send_is_dry_run(self):
        result = self.mcp.call(
            "allo_send_sms",
            to="+15005559001",
            content="Hi, following up on your call.",
            allo_number="+15005550101",
        )
        self.assertTrue(result["data"]["dry_run"])
        self.assertEqual(len(self.mcp.sent_sms), 1)

    def test_requires_exactly_one_sender(self):
        with self.assertRaises(MockMcpError):
            self.mcp.call("allo_send_sms", to="+15005559001", content="hi")
        with self.assertRaises(MockMcpError):
            self.mcp.call(
                "allo_send_sms",
                to="+15005559001",
                content="hi",
                allo_number="+15005550101",
                allo_sender_id="Allo",
            )

    def test_rejects_non_e164_recipient(self):
        with self.assertRaises(MockMcpError):
            self.mcp.call(
                "allo_send_sms", to="4155551234", content="hi", allo_number="+15005550101"
            )

    def test_rejects_line_without_sms_capability(self):
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call(
                "allo_send_sms", to="+15005559001", content="hi", allo_number="+15005550102"
            )
        self.assertIn("SMS capability", ctx.exception.message)

    def test_draft_workflow_sends_nothing(self):
        # "Draft an SMS to yesterday's voicemails" — research only, no send.
        found = self.mcp.call(
            "allo_search_conversation_items", direction="INBOUND", result="VOICEMAIL"
        )
        self.mcp.call(
            "allo_batch_get_conversation_items", ids=[r["id"] for r in found["data"]]
        )
        self.assertEqual(self.mcp.sent_sms, [], "drafting must never call send")

    def test_skill_distinguishes_draft_from_send(self):
        text = skill_text("allo")
        self.assertRegex(text, r'(?i)"draft"\s+never sends|draft.{0,40}do not send')
        self.assertIn("allo_send_sms", text)

    def test_skill_requires_confirmation_before_sending(self):
        text = normalize(skill_text("allo"))
        self.assertTrue(
            re.search(r"(confirm|go-ahead|authoriz)", text),
            "skill must require confirmation before sending SMS",
        )
        self.assertIn("exact message", text)


class TestTaggingWorkflow(unittest.TestCase):
    """Check 9 — tagging."""

    def setUp(self):
        self.mcp = MockAlloMcp()

    def test_tag_keys_are_validated_against_the_workspace(self):
        keys = {t["key"] for t in self.mcp.call("allo_list_tags")["data"]}
        self.assertIn("warm_lead", keys)
        with self.assertRaises(MockMcpError):
            self.mcp.call("allo_add_call_tags", id="cll-001", tags=["totally_made_up"])

    def test_tagging_a_validated_target_set(self):
        found = self.mcp.call(
            "allo_search_conversation_items",
            direction="INBOUND",
            result="VOICEMAIL",
            date_from=YESTERDAY,
            date_to=YESTERDAY,
        )
        for row in found["data"]:
            self.mcp.call("allo_add_call_tags", id=row["id"], tags=["warm_lead"])
        self.assertEqual(len(self.mcp.applied_tags), 2)

    def test_duplicate_tag_is_a_no_op_error(self):
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call("allo_add_call_tags", id="cll-003", tags=["meeting_booked"])
        self.assertEqual(ctx.exception.code, "TAG_ALREADY_EXISTS")

    def test_skill_requires_keys_not_display_names(self):
        text = skill_text("allo")
        self.assertIn("allo_list_tags", text)
        self.assertRegex(text, r"(?i)keys?\b.{0,60}(not|rather than).{0,30}display names?")


class TestAnalyticsWorkflow(unittest.TestCase):
    """Check 10 — analytics."""

    def setUp(self):
        self.mcp = MockAlloMcp()

    def test_multi_user_comparison_is_a_single_call(self):
        self.mcp.call(
            "allo_get_team_analytics",
            date_from="2026-09-09",
            date_to="2026-09-10",
            user_ids=["usr-001", "usr-002", "usr-003"],
        )
        self.assertEqual(self.mcp.count("allo_get_team_analytics"), 1, "must not loop per rep")

    def test_cannot_combine_user_ids_and_numbers(self):
        with self.assertRaises(MockMcpError):
            self.mcp.call(
                "allo_get_team_analytics",
                date_from="2026-09-09",
                date_to="2026-09-10",
                user_ids=["usr-001"],
                allo_numbers=["+15005550101"],
            )

    def test_comparison_period_returns_a_delta(self):
        result = self.mcp.call(
            "allo_get_team_analytics",
            date_from="2026-09-10",
            date_to="2026-09-10",
            compare_date_from="2026-09-09",
            compare_date_to="2026-09-09",
        )
        self.assertIn("comparison", result["data"])

    def test_dates_are_required(self):
        with self.assertRaises(MockMcpError):
            self.mcp.call("allo_get_team_analytics")

    def test_conversion_depends_on_tags(self):
        untagged = self.mcp.call(
            "allo_get_team_outbound_analytics", date_from="2026-09-10", date_to="2026-09-10"
        )
        self.assertEqual(untagged["data"]["funnel"]["CONVERSION"], 0)
        tagged = self.mcp.call(
            "allo_get_team_outbound_analytics",
            date_from="2026-09-10",
            date_to="2026-09-10",
            tags=["meeting_booked"],
        )
        self.assertEqual(tagged["data"]["funnel"]["CONVERSION"], 1)

    def test_drilldown_requires_a_stage(self):
        with self.assertRaises(MockMcpError):
            self.mcp.call(
                "allo_get_team_outbound_analytics",
                date_from="2026-09-10",
                date_to="2026-09-10",
                extend="items",
            )
        ok = self.mcp.call(
            "allo_get_team_outbound_analytics",
            date_from="2026-09-10",
            date_to="2026-09-10",
            extend="items",
            stage="CONNECTED",
        )
        self.assertIn("items", ok["data"])

    def test_skill_forbids_inventing_metrics(self):
        text = normalize(skill_text("allo-analytics"))
        self.assertIn("only what allo returns", text)
        self.assertRegex(text, r"revenue|close rate|cost per lead")


class TestReceptionistWorkflow(unittest.TestCase):
    """Check 11 — AI receptionist."""

    def setUp(self):
        self.mcp = MockAlloMcp()

    def test_read_before_write(self):
        current = self.mcp.call("allo_get_agent")["data"]
        self.assertEqual(current["status"], "ONLINE")
        self.mcp.call("allo_set_agent_status", status="OFFLINE")
        self.assertEqual(self.mcp.tools_used()[0], "allo_get_agent")
        self.assertEqual(self.mcp.call("allo_get_agent")["data"]["status"], "OFFLINE")

    def test_status_is_constrained(self):
        with self.assertRaises(MockMcpError):
            self.mcp.call("allo_set_agent_status", status="PAUSED")

    def test_prompt_edit_preserves_existing_content(self):
        current = self.mcp.call("allo_get_agent")["data"]["prompt"]
        edited = current + " Our hours are 9-5 Eastern."
        self.mcp.call("allo_set_agent_prompt", prompt=edited)
        new = self.mcp.call("allo_get_agent")["data"]["prompt"]
        self.assertIn("Greet callers", new, "editing must not drop the original prompt")
        self.assertIn("9-5 Eastern", new)

    def test_disable_is_reversible_delete_is_not(self):
        self.mcp.call("allo_set_agent_knowledge_website_status", id="knw-002", status="DISABLED")
        still_there = [k for k in self.mcp.call("allo_get_agent")["data"]["knowledge"]]
        self.assertIn("knw-002", {k["id"] for k in still_there})

        self.mcp.call("allo_delete_agent_knowledge", id="knw-002")
        remaining = {k["id"] for k in self.mcp.call("allo_get_agent")["data"]["knowledge"]}
        self.assertNotIn("knw-002", remaining)
        with self.assertRaises(MockMcpError):
            self.mcp.call("allo_delete_agent_knowledge", id="knw-002")

    def test_voice_ids_come_from_the_list(self):
        voices = {v["id"] for v in self.mcp.call("allo_list_voices")["data"]}
        self.assertIn(self.mcp.call("allo_get_agent")["data"]["voice"], voices)

    def test_skill_offers_disable_before_delete(self):
        text = normalize(skill_text("allo-receptionist"))
        self.assertIn("offer disable before delete", text)
        self.assertRegex(text, r"not undoable|permanent")


class TestInboxWorkflow(unittest.TestCase):
    """Inboxes: set up, teammate inboxes, open by name, pin, mute, delete."""

    SALES = "+15005550101"
    SUPPORT = "+15005550102"

    def setUp(self):
        self.mcp = MockAlloMcp()

    def _set_up_from_suggestions(self, keep):
        """Suggestions -> user confirms `keep` -> one create per confirmed inbox, source as is."""
        suggestions = self.mcp.call("allo_get_inbox_suggestions")["data"]
        confirmed = [s for s in suggestions if s["name"] in keep]
        for s in confirmed:
            self.mcp.call("allo_create_inbox", name=s["name"], sources=[s["source"]])
        return confirmed

    def _option(self, line, digits):
        options = self.mcp.call("allo_list_menu_options", number=line)["data"]
        return next(o for o in options if o["digits"] == digits)

    def test_set_up_my_inboxes_starts_from_suggestions(self):
        confirmed = self._set_up_from_suggestions(keep={"Sales", "Sales FR"})
        used = self.mcp.tools_used()
        self.assertEqual(used[0], "allo_get_inbox_suggestions")
        self.assertEqual(self.mcp.count("allo_create_inbox"), 2, "only the confirmed inboxes")
        self.assertEqual(self.mcp.count("allo_list_menu_options"), 0, "suggestions need no menu lookup")
        mine = self.mcp.call("allo_list_inboxes")["data"]
        self.assertEqual({i["name"] for i in mine}, {"Sales", "Sales FR"})
        self.assertNotIn("owner", mine[0], "the API returns no owner field")
        self.assertEqual(
            mine[0]["filters"],
            {"types": [], "user_ids": [], "contact_ids": [], "contact_list_ids": [], "unread": False},
        )
        # The suggestion's source went through unchanged.
        by_name = {i["name"]: i for i in mine}
        for s in confirmed:
            self.assertEqual(by_name[s["name"]]["sources"], [s["source"]])

    def test_custom_branch_uses_the_menu_options_condition_as_is(self):
        # "Only callers who pressed 2 then 1 on Sales."
        option = self._option(self.SALES, "2>1")
        self.assertEqual(option["condition"]["type"], "MENU_BRANCH")
        source = {"allo_number": self.SALES, "conditions": [option["condition"]]}
        inbox = self.mcp.call("allo_create_inbox", name="Billing", sources=[source])["data"]
        rows = self.mcp.call("allo_list_conversations", inbox_id=inbox["id"])["data"]
        self.assertEqual([r["contact_number"] for r in rows], ["+15005559002"])

    def test_several_options_on_one_line_concatenate_into_one_branch_condition(self):
        # "Callers who pressed 1 or 2 on Sales."
        one, two = self._option(self.SALES, "1"), self._option(self.SALES, "2")
        merged = dict(one["condition"], branches=one["condition"]["branches"] + two["condition"]["branches"])
        inbox = self.mcp.call(
            "allo_create_inbox", name="FR", sources=[{"allo_number": self.SALES, "conditions": [merged]}]
        )["data"]
        rows = self.mcp.call("allo_list_conversations", inbox_id=inbox["id"])["data"]
        self.assertEqual({r["contact_number"] for r in rows}, {"+15005559001", "+15005559002"})

    def test_two_conditions_on_the_same_menu_are_rejected(self):
        one, two = self._option(self.SALES, "1"), self._option(self.SALES, "2")
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call(
                "allo_create_inbox",
                name="FR",
                sources=[{"allo_number": self.SALES, "conditions": [one["condition"], two["condition"]]}],
            )
        self.assertEqual(ctx.exception.code, "INVALID_INBOX_SOURCE")

    def test_invented_menu_branch_is_rejected(self):
        bogus = {"type": "MENU_BRANCH", "branches": [[{"node_id": "node-99", "digit": "1"}]], "include_no_choice": False}
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call("allo_create_inbox", name="Guess", sources=[{"allo_number": self.SALES, "conditions": [bogus]}])
        self.assertEqual(ctx.exception.code, "INVALID_INBOX_SOURCE")

    def test_set_up_one_for_a_teammate(self):
        # "...and one for Dana with Sales option 1." Suggestions are the caller's
        # own, so the teammate's source comes from the menu options or a whole line.
        users = self.mcp.call("allo_list_users")["data"]
        dana = next(u for u in users if u["name"].startswith("Dana"))
        option = self._option(self.SALES, "1")
        self.mcp.call(
            "allo_create_inbox",
            name="Sales FR",
            sources=[{"allo_number": self.SALES, "conditions": [option["condition"]]}],
            user_id=dana["id"],
        )
        used = self.mcp.tools_used()
        self.assertLess(used.index("allo_list_users"), used.index("allo_create_inbox"))
        self.assertNotIn("allo_get_inbox_suggestions", used, "suggestions take no user_id")
        theirs = self.mcp.call("allo_list_inboxes", user_id=dana["id"])["data"]
        self.assertEqual([i["name"] for i in theirs], ["Sales FR"])
        self.assertEqual(self.mcp.call("allo_list_inboxes")["data"], [], "not in the caller's switcher")

    def test_suggestions_take_no_user_id(self):
        self.assertEqual(TOOLS["allo_get_inbox_suggestions"], ((), ()))
        with self.assertRaises(TypeError):
            self.mcp.call("allo_get_inbox_suggestions", user_id="usr-002")

    def test_teammate_inbox_needs_their_line_access(self):
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call(
                "allo_create_inbox",
                name="Support",
                sources=[{"allo_number": self.SUPPORT, "conditions": []}],
                user_id="usr-002",
            )
        self.assertEqual(ctx.exception.code, "ALLO_NUMBER_FORBIDDEN")

    def test_teammate_inbox_needs_admin_or_manager(self):
        agent = MockAlloMcp(caller="usr-001")
        with self.assertRaises(MockMcpError) as ctx:
            agent.call(
                "allo_create_inbox",
                name="Sales",
                sources=[{"allo_number": self.SALES, "conditions": []}],
                user_id="usr-002",
            )
        self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_named_inbox_lists_its_conversations_by_inbox_id(self):
        # "Show me my Sales inbox."
        self._set_up_from_suggestions(keep={"Sales", "Support"})
        inboxes = self.mcp.call("allo_list_inboxes")["data"]
        sales = next(i for i in inboxes if i["name"].lower() == "sales")
        result = self.mcp.call("allo_list_conversations", inbox_id=sales["id"])
        _, args = self.mcp.calls[-1]
        self.assertNotIn("allo_number", args, "a named inbox is listed by inbox_id, not by line")
        contacts = {r["contact_number"] for r in result["data"]}
        self.assertEqual(contacts, {"+15005559001", "+15005559002", "+15005559003"})

    def test_inbox_rows_carry_their_line_for_pinning(self):
        # An inbox spanning two lines: act on each row with the row's own line.
        inbox = self.mcp.call(
            "allo_create_inbox",
            name="Everything",
            sources=[{"allo_number": self.SALES, "conditions": []}, {"allo_number": self.SUPPORT, "conditions": []}],
        )["data"]
        rows = self.mcp.call("allo_list_conversations", inbox_id=inbox["id"])["data"]
        self.assertEqual({r["allo_number"] for r in rows}, {self.SALES, self.SUPPORT})
        support_row = next(r for r in rows if r["allo_number"] == self.SUPPORT)
        self.mcp.call(
            "allo_pin_conversation",
            contact_number=support_row["contact_number"],
            allo_number=support_row["allo_number"],
        )
        pinned = self.mcp.call("allo_list_conversations", inbox_id=inbox["id"], pinned=True)["data"]
        self.assertEqual([(r["allo_number"], r["contact_number"]) for r in pinned], [(self.SUPPORT, "+15005559004")])

    def test_inbox_listing_applies_its_saved_filters(self):
        inbox = self.mcp.call(
            "allo_create_inbox",
            name="Sales voicemails",
            sources=[{"allo_number": self.SALES, "conditions": []}],
            filters={"types": ["VOICEMAIL"]},
        )["data"]
        rows = self.mcp.call("allo_list_conversations", inbox_id=inbox["id"])["data"]
        self.assertEqual({r["contact_number"] for r in rows}, {"+15005559001", "+15005559002"})

    def test_invalid_filters_are_rejected(self):
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call(
                "allo_create_inbox",
                name="Sales",
                sources=[{"allo_number": self.SALES, "conditions": []}],
                filters={"types": ["MISSED"]},
            )
        self.assertEqual(ctx.exception.code, "INVALID_INBOX_FILTERS")

    def test_inbox_limit_is_reported_not_worked_around(self):
        for n in range(50):
            self.mcp.call("allo_create_inbox", name=f"Inbox {n}", sources=[{"allo_number": self.SALES, "conditions": []}])
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call("allo_create_inbox", name="One more", sources=[{"allo_number": self.SALES, "conditions": []}])
        self.assertEqual(ctx.exception.code, "INBOX_LIMIT_REACHED")
        self.assertEqual(self.mcp.count("allo_delete_inbox"), 0, "never delete to make room")

    def test_not_found_right_after_create_is_retried_once(self):
        lagging = MockAlloMcp(read_lag=True)
        inbox = lagging.call(
            "allo_create_inbox", name="Sales", sources=[{"allo_number": self.SALES, "conditions": []}]
        )["data"]
        with self.assertRaises(MockMcpError) as ctx:
            lagging.call("allo_list_conversations", inbox_id=inbox["id"])
        self.assertEqual(ctx.exception.code, "INBOX_NOT_FOUND")
        retried = lagging.call("allo_list_conversations", inbox_id=inbox["id"])
        self.assertTrue(retried["data"])

    def test_list_conversations_takes_exactly_one_scope(self):
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call("allo_list_conversations")
        self.assertEqual(ctx.exception.code, "INVALID_REQUEST")

    def test_someone_elses_inbox_is_not_found(self):
        created = self.mcp.call(
            "allo_create_inbox",
            name="Sales",
            sources=[{"allo_number": self.SALES, "conditions": []}],
            user_id="usr-002",
        )["data"]
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call("allo_list_conversations", inbox_id=created["id"])
        self.assertEqual(ctx.exception.code, "INBOX_NOT_FOUND")

    def test_pin_and_unpin(self):
        self.mcp.call("allo_pin_conversation", contact_number="+15005559001", allo_number=self.SALES)
        pinned = self.mcp.call("allo_list_conversations", allo_number=self.SALES, pinned=True)["data"]
        self.assertEqual([r["contact_number"] for r in pinned], ["+15005559001"])
        self.mcp.call("allo_unpin_conversation", contact_number="+15005559001", allo_number=self.SALES)
        self.assertEqual(self.mcp.call("allo_list_conversations", allo_number=self.SALES, pinned=True)["data"], [])

    def test_pin_limit_is_reported_not_worked_around(self):
        self.mcp.pins = [(self.SALES, f"+150055580{i:02d}") for i in range(10)]
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call("allo_pin_conversation", contact_number="+15005559001", allo_number=self.SALES)
        self.assertEqual(ctx.exception.code, "PIN_LIMIT_REACHED")
        self.assertIn("10", ctx.exception.message)
        # The skill's recovery: show what is pinned and ask. Nothing gets unpinned automatically.
        self.assertEqual(len(self.mcp.pins), 10)
        self.assertEqual(self.mcp.count("allo_unpin_conversation"), 0)

    def test_mute_is_an_update_not_a_delete(self):
        self._set_up_from_suggestions(keep={"Support"})
        support = self.mcp.call("allo_list_inboxes")["data"][0]
        self.mcp.call("allo_update_inbox", inbox_id=support["id"], notifications_muted=True)
        self.assertTrue(self.mcp.call("allo_list_inboxes")["data"][0]["notifications_muted"])
        self.assertEqual(self.mcp.count("allo_delete_inbox"), 0)

    def test_setup_never_deletes(self):
        self._set_up_from_suggestions(keep={"Sales", "Support", "Sales FR"})
        self.assertEqual(self.mcp.count("allo_delete_inbox"), 0)

    def test_teammate_can_reuse_a_suggestion_source_on_their_line(self):
        sales = next(
            s for s in self.mcp.call("allo_get_inbox_suggestions")["data"] if s["name"] == "Sales"
        )
        self.mcp.call("allo_create_inbox", name="Sales", sources=[sales["source"]], user_id="usr-002")
        self.assertEqual(len(self.mcp.call("allo_list_inboxes", user_id="usr-002")["data"]), 1)

    def test_unknown_teammate_is_forbidden(self):
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call("allo_list_inboxes", user_id="usr-999")
        self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_saved_unread_is_not_applied_but_the_argument_is(self):
        inbox = self.mcp.call(
            "allo_create_inbox",
            name="Sales unread",
            sources=[{"allo_number": self.SALES, "conditions": []}],
            filters={"unread": True},
        )["data"]
        self.assertTrue(inbox["filters"]["unread"])
        everything = self.mcp.call("allo_list_conversations", inbox_id=inbox["id"])["data"]
        self.assertEqual(len(everything), 3, "a saved unread filter is not applied")
        unread = self.mcp.call("allo_list_conversations", inbox_id=inbox["id"], unread=True)["data"]
        self.assertEqual({r["contact_number"] for r in unread}, {"+15005559001", "+15005559002"})

    def test_filter_user_ids_are_not_resolved(self):
        # The API only rejects blanks and more than 50; it does not look ids up.
        self.mcp.call(
            "allo_create_inbox",
            name="Sales",
            sources=[{"allo_number": self.SALES, "conditions": []}],
            filters={"user_ids": ["usr-unknown"]},
        )
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call(
                "allo_create_inbox",
                name="Too many",
                sources=[{"allo_number": self.SALES, "conditions": []}],
                filters={"user_ids": [f"usr-{n}" for n in range(51)]},
            )
        self.assertEqual(ctx.exception.code, "INVALID_INBOX_FILTERS")

    def test_menu_options_need_line_access_and_a_routed_line(self):
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call("allo_list_menu_options", number="+15005550199")
        self.assertEqual(ctx.exception.code, "ALLO_NUMBER_FORBIDDEN")
        restricted = MockAlloMcp(caller="usr-002")
        with self.assertRaises(MockMcpError) as ctx:
            restricted.call("allo_list_menu_options", number=self.SUPPORT)
        self.assertEqual(ctx.exception.code, "ALLO_NUMBER_FORBIDDEN")
        # Accessible, but not routed by the engine: no menu, not an error.
        self.assertEqual(self.mcp.call("allo_list_menu_options", number=self.SUPPORT)["data"], [])

    def test_pin_needs_line_access(self):
        restricted = MockAlloMcp(caller="usr-002")
        with self.assertRaises(MockMcpError) as ctx:
            restricted.call("allo_pin_conversation", contact_number="+15005559004", allo_number=self.SUPPORT)
        self.assertEqual(ctx.exception.code, "ALLO_NUMBER_FORBIDDEN")

    def test_pin_unpin_and_delete_return_the_mcp_shapes(self):
        pinned = self.mcp.call("allo_pin_conversation", contact_number="+15005559001", allo_number=self.SALES)
        self.assertEqual(pinned, {"pinned": True, "contact_number": "+15005559001", "allo_number": self.SALES})
        unpinned = self.mcp.call("allo_unpin_conversation", contact_number="+15005559001", allo_number=self.SALES)
        self.assertFalse(unpinned["pinned"])
        inbox = self.mcp.call(
            "allo_create_inbox", name="Sales", sources=[{"allo_number": self.SALES, "conditions": []}]
        )["data"]
        self.assertEqual(self.mcp.call("allo_delete_inbox", inbox_id=inbox["id"]), {"deleted": True, "id": inbox["id"]})

    def test_create_stores_notifications_muted(self):
        inbox = self.mcp.call(
            "allo_create_inbox",
            name="Quiet",
            sources=[{"allo_number": self.SALES, "conditions": []}],
            notifications_muted=True,
        )["data"]
        self.assertTrue(inbox["notifications_muted"])

    def test_conditions_require_include_no_choice(self):
        option = self._option(self.SALES, "1")
        condition = {k: v for k, v in option["condition"].items() if k != "include_no_choice"}
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call(
                "allo_create_inbox", name="FR", sources=[{"allo_number": self.SALES, "conditions": [condition]}]
            )
        self.assertEqual(ctx.exception.code, "INVALID_INBOX_SOURCE")

    def test_update_only_touches_inbox_fields(self):
        inbox = self.mcp.call(
            "allo_create_inbox", name="Sales", sources=[{"allo_number": self.SALES, "conditions": []}]
        )["data"]
        with self.assertRaises(MockMcpError):
            self.mcp.call("allo_update_inbox", inbox_id=inbox["id"], id="inb_hijack")
        with self.assertRaises(MockMcpError) as ctx:
            self.mcp.call("allo_update_inbox", inbox_id=inbox["id"], name="   ")
        self.assertEqual(ctx.exception.code, "INBOX_NAME_REQUIRED")
        self.assertEqual(self.mcp.call("allo_list_inboxes")["data"][0]["id"], inbox["id"])

    def test_skill_documents_the_inbox_rules(self):
        text = normalize(skill_text("allo"))
        self.assertIn("allo_get_inbox_suggestions", text)
        self.assertRegex(text, r"ready `source`")
        self.assertRegex(text, r"ready `condition`; use it as is")
        self.assertRegex(text, r"merge them into \*\*one\*\* condition")
        self.assertRegex(text, r"confirm the final list before creating")
        self.assertRegex(text, r"admins and managers")
        self.assertRegex(text, r"suggestions take no teammate")
        self.assertRegex(text, r"reuse a suggestion's `source` on a line the teammate can access")
        self.assertRegex(text, r"ask the user which lines the teammate works")
        self.assertRegex(text, r"needs a published call flow with a phone menu")
        self.assertRegex(text, r"except \"unread only\"")
        self.assertRegex(text, r"pass `unread` set to true yourself")
        self.assertRegex(text, r"get the lines from `allo_list_numbers`")
        self.assertRegex(text, r"never change node_ids or digits")
        self.assertRegex(text, r"confirm the inbox by name and whose it is")
        self.assertIn("inbox_id", text)
        self.assertRegex(text, r"use the row's `allo_number`")
        self.assertRegex(text, r"already applies the inbox's saved filters")
        self.assertRegex(text, r"retry once")
        self.assertRegex(text, r"at most 10")
        self.assertRegex(text, r"inbox limit reached \(50\)")
        self.assertRegex(text, r"invalid filters")
        self.assertIn("notifications_muted", text)
        self.assertRegex(text, r"delete an inbox only when the user explicitly asks")
        self.assertIn("allo_delete_inbox", text)


class TestErrorHandling(unittest.TestCase):
    """Check 12 — error handling."""

    def test_authorization_error_surfaces_as_forbidden(self):
        restricted = MockAlloMcp(scopes={"CONVERSATIONS_READ"})
        with self.assertRaises(MockMcpError) as ctx:
            restricted.call("allo_send_sms", to="+15005559001", content="hi", allo_sender_id="Allo")
        self.assertEqual(ctx.exception.code, "FORBIDDEN")

    def test_get_me_reveals_the_restricted_scope_set(self):
        restricted = MockAlloMcp(scopes={"CONVERSATIONS_READ"})
        self.assertEqual(restricted.call("allo_get_me")["scopes"], ["CONVERSATIONS_READ"])

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(MockMcpError) as ctx:
            MockAlloMcp().call("allo_do_something_invented")
        self.assertEqual(ctx.exception.code, "TOOL_NOT_FOUND")

    def test_invented_parameter_is_rejected(self):
        with self.assertRaises(MockMcpError) as ctx:
            MockAlloMcp().call("allo_search_conversation_items", sentiment="frustrated")
        self.assertEqual(ctx.exception.code, "INVALID_ARGUMENT")

    def test_page_size_ceiling_enforced(self):
        with self.assertRaises(MockMcpError):
            MockAlloMcp().call("allo_search_conversation_items", size=500)

    def test_upstream_failure_propagates_with_a_code(self):
        flaky = MockAlloMcp(fail_with={"allo_list_tags": ("UNAVAILABLE", "upstream down")})
        with self.assertRaises(MockMcpError) as ctx:
            flaky.call("allo_list_tags")
        self.assertEqual(ctx.exception.code, "UNAVAILABLE")

    def test_skill_covers_each_error_class(self):
        text = normalize(skill_text("allo"))
        for phrase in ("authorization error", "no results", "unsupported operation", "rate limit"):
            self.assertIn(phrase, text, f"skill must cover: {phrase}")

    def test_skill_forbids_leaking_auth_details(self):
        text = normalize(skill_text("allo"))
        self.assertRegex(text, r"never expose.{0,80}(header|token|api key)")

    def test_skill_forbids_fabricating_results(self):
        self.assertRegex(normalize(all_skill_text()), r"never fabricate|do not fabricate")


class TestSafetyContract(unittest.TestCase):
    """The safety rules must actually be written in the skills."""

    def test_every_destructive_tool_is_documented(self):
        text = all_skill_text()
        for tool in DESTRUCTIVE_TOOLS:
            # Notes/templates are optional surfaces; enforce the core set.
            if tool in {
                "allo_send_sms",
                "allo_delete_agent_knowledge",
                "allo_set_agent_status",
                "allo_delete_inbox",
            }:
                self.assertIn(tool, text, f"{tool} must be documented as high-consequence")

    def test_bulk_action_protocol_is_specified(self):
        text = normalize(skill_text("allo"))
        for step in ("validate", "summarize", "report exactly what happened"):
            self.assertIn(step, text)

    def test_read_default_is_stated(self):
        self.assertIn("Read by default", skill_text("allo"))

    def test_e164_is_specified(self):
        self.assertIn("E.164", skill_text("allo"))

    def test_skills_do_not_instruct_users_to_name_tools(self):
        # The UX requirement: users ask in business language.
        text = normalize(skill_text("allo"))
        self.assertRegex(text, r"never tell a normal user to invoke a tool by name")


if __name__ == "__main__":
    unittest.main(verbosity=2)
