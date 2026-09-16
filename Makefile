.PHONY: check test live dump help

help:
	@echo "make test    Offline validation + workflow tests (no network, no credentials)"
	@echo "make live    Live MCP connectivity and OAuth discovery (no credentials)"
	@echo "make check   Both"
	@echo "make dump    Print the served tool schemas (requires ALLO_API_KEY)"

test:
	@cd tests && python3 -m unittest discover -s . -p "test_*.py"

live:
	@python3 tests/live_check.py

check: test live

dump:
	@python3 tests/live_check.py --dump
