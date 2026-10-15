.PHONY: format check

format:
	@echo "Formatting Python files..."
	@uv run ruff format src/ali_tool/
	@echo "Formatting YAML files..."
	@yamlfmt src/ali_tool/
	@echo "✓ Formatting complete"

check:
	@uv run ruff check src/ali_tool/
	@uv run basedpyright src/ali_tool/
	@uv run pytest -q
