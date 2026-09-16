"""Verified Allô MCP tool registry.

This is the source of truth the tests validate the plugin's skills against.

Verification status — be precise about this:

  * TOOL NAMES     — fully verified against the live production MCP server at
                     https://mcp.withallo.com/mcp. Every name below is served.
  * ENUMS, LIMITS  — verified from the live JSON Schemas and `allo_get_me`.
  * PARAMETERS     — verified from the live schemas for the tools the skills
                     actually instruct Grok to call with named parameters
                     (search, both analytics tools, send_sms, add_call_tags).
                     For the remaining tools the lists are best-effort and are
                     NOT enforced by the test suite.

Accordingly the test suite hard-enforces tool *names* and enum members, and
treats parameter lists as advisory. Run `python3 tests/live_check.py --dump`
against a live credential to regenerate this file with full schemas.

The name check is the mechanism that stops the plugin inventing tools or
drifting from the server.
"""

# Tools that perform an external side effect. The safety tests assert that the
# skills document confirmation for each of these.
WRITE_TOOLS = {
    "allo_mark_conversation",
    "allo_update_conversation_item_summary",
    "allo_add_call_tags",
    "allo_remove_call_tag",
    "allo_send_sms",
    "allo_add_to_dialing_queue",
    "allo_update_agent",
    "allo_set_agent_prompt",
    "allo_set_agent_status",
    "allo_add_agent_knowledge_website",
    "allo_set_agent_knowledge_website_status",
    "allo_delete_agent_knowledge",
    "allo_create_conversation_note",
    "allo_update_conversation_note",
    "allo_delete_conversation_note",
    "allo_create_contact_note",
    "allo_update_contact_note",
    "allo_delete_contact_note",
    "allo_create_thread",
    "allo_add_thread_comment",
    "allo_update_thread_comment",
    "allo_resolve_thread",
    "allo_create_summary_template",
    "allo_update_summary_template",
    "allo_delete_summary_template",
    "allo_set_number_default_summary_template",
    "allo_save_call_flow_draft",
}

# Irreversible or customer-facing. These require explicit confirmation.
DESTRUCTIVE_TOOLS = {
    "allo_send_sms",
    "allo_delete_agent_knowledge",
    "allo_delete_conversation_note",
    "allo_delete_contact_note",
    "allo_delete_summary_template",
    "allo_set_agent_status",
}

# Tools whose parameter lists below were read from the live JSON Schema. Only
# these are parameter-enforced by the test suite.
VERIFIED_PARAM_TOOLS = {
    "allo_search_conversation_items",
    "allo_get_team_analytics",
    "allo_get_team_outbound_analytics",
    "allo_send_sms",
    "allo_add_call_tags",
    "allo_get_me",
}

# tool name -> (required params, optional params)
TOOLS = {
    # --- Discovery ---
    "allo_get_me": ((), ()),
    "allo_list_users": ((), ("page", "size")),
    "allo_list_numbers": ((), ("page", "size")),
    "allo_list_tags": ((), ()),
    # --- Conversations ---
    "allo_list_conversations": ((), ("allo_number", "page", "size", "unread")),
    "allo_search_conversation_items": (
        (),
        (
            "allo_number",
            "contact_number",
            "date_from",
            "date_to",
            "direction",
            "extend",
            "page",
            "result",
            "search",
            "size",
            "sort",
            "tags",
            "type",
            "unread",
            "user_id",
        ),
    ),
    "allo_get_conversation_item": (("id",), ("extend",)),
    "allo_batch_get_conversation_items": (("ids",), ("extend",)),
    "allo_mark_conversation": (("contact_number", "action"), ()),
    "allo_update_conversation_item_summary": (("id", "summary"), ()),
    # --- Actions ---
    "allo_add_call_tags": (("id", "tags"), ()),
    "allo_remove_call_tag": (("id", "tag"), ()),
    "allo_send_sms": (("to", "content"), ("allo_number", "allo_sender_id")),
    "allo_add_to_dialing_queue": (("numbers",), ()),
    "allo_get_dialing_queue": ((), ()),
    # --- AI receptionist ---
    "allo_get_agent": ((), ("allo_number",)),
    "allo_update_agent": ((), ("allo_number",)),
    "allo_set_agent_prompt": (("prompt",), ("allo_number",)),
    "allo_set_agent_status": (("status",), ("allo_number",)),
    "allo_list_voices": ((), ()),
    # --- Knowledge ---
    "allo_add_agent_knowledge_website": (("url",), ("allo_number",)),
    "allo_set_agent_knowledge_website_status": (("id", "status"), ()),
    "allo_delete_agent_knowledge": (("id",), ()),
    # --- Calendars ---
    "allo_list_calendars": ((), ()),
    "allo_get_calendar": (("id",), ()),
    # --- Analytics ---
    "allo_get_team_analytics": (
        ("date_from", "date_to"),
        ("allo_numbers", "compare_date_from", "compare_date_to", "user_ids"),
    ),
    "allo_get_team_outbound_analytics": (
        ("date_from", "date_to"),
        (
            "allo_numbers",
            "compare_date_from",
            "compare_date_to",
            "extend",
            "granularity",
            "page",
            "size",
            "stage",
            "tags",
            "user_ids",
        ),
    ),
    # --- CRM ---
    "allo_crm_search": (("entity",), ("id", "search", "filters", "page", "size")),
    # --- Notes ---
    "allo_list_conversation_notes": (("contact_number",), ()),
    "allo_get_conversation_note": (("id",), ()),
    "allo_create_conversation_note": (("contact_number", "content"), ()),
    "allo_update_conversation_note": (("id", "content"), ()),
    "allo_delete_conversation_note": (("id",), ()),
    "allo_list_contact_notes": (("person_id",), ()),
    "allo_create_contact_note": (("person_id", "content"), ()),
    "allo_update_contact_note": (("person_id", "note_id", "content"), ()),
    "allo_delete_contact_note": (("person_id", "note_id"), ()),
    # --- Threads ---
    "allo_get_thread": (("id",), ()),
    "allo_find_thread": (("entity_type", "entity_id"), ()),
    "allo_create_thread": (("entity_type", "entity_id", "content"), ()),
    "allo_add_thread_comment": (("id", "content"), ()),
    "allo_update_thread_comment": (("comment_id", "content"), ()),
    "allo_resolve_thread": (("id",), ("resolved",)),
    # --- Summary templates ---
    "allo_list_summary_templates": ((), ()),
    "allo_get_summary_template": (("id",), ()),
    "allo_create_summary_template": (("name", "content"), ()),
    "allo_update_summary_template": (("id",), ("name", "content")),
    "allo_delete_summary_template": (("id",), ()),
    "allo_set_number_default_summary_template": (("number",), ("template_id",)),
    # --- Call flows ---
    "allo_get_call_flow": (("number",), ("status",)),
    "allo_save_call_flow_draft": (("number", "definition", "lock_version"), ()),
}

# Enum values verified from the live schemas. The skills must not invent members.
ENUMS = {
    "search.result": ("ANSWERED", "VOICEMAIL", "TRANSFERRED"),
    "search.direction": ("INBOUND", "OUTBOUND"),
    "search.type": ("CALL", "SMS", "ALL"),
    "search.sort": ("DATE", "RELEVANCE"),
    "search.extend": ("transcript",),
    "outbound.stage": ("DIAL", "CONNECTED", "CONVERSATION", "CONVERSION"),
    "outbound.granularity": ("DAY", "WEEK", "MONTH"),
}

# Server-enforced limits, verified from allo_get_me and the tool schemas.
LIMITS = {
    "page_size_default": 20,
    "page_size_max": 100,
    "batch_get_max": 100,
    "dialing_queue_max": 1000,
    "read_per_second": 20,
    "write_per_second": 5,
}

MCP_URL = "https://mcp.withallo.com/mcp"
