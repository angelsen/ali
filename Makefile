.PHONY: format check

format:
	@echo "Formatting Python files..."
	@ruff format src/ali/
	@echo "Formatting YAML files..."
	@yamlfmt src/ali/
	@echo "✓ Formatting complete"

check:
	@ruff check src/ali/
	@basedpyright src/ali/