all: format check

format: prettier black ruff

check: mypy pyright checkblack checkruff checkprettier

prettier:
	poetry run ./node_modules/.bin/prettier --write .
pyright:
	poetry run ./node_modules/.bin/pyright

mypy:
	poetry run mypy .

black:
	poetry run black .

ruff:
	poetry run ruff check . --fix

checkruff:
	poetry run ruff check .

checkprettier:
	poetry run ./node_modules/.bin/prettier --check .

checkblack:
	poetry run black --check .

checkeditorconfig:
	editorconfig-checker

test:
	PYTHONUNBUFFERED=1 \
	DEBUG=true \
	poetry run pytest
install-pre-commit-hook:
	@echo "Installing pre-commit hook to git"
	@echo "Uninstall the hook with poetry run pre-commit uninstall"
	poetry run pre-commit install

pre-commit:
	poetry run pre-commit run --all-files


checkbundle:
	@echo "skipping checkbundle"
