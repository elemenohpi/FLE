#* Variables
SHELL := /usr/bin/env bash
PYTHON := python
PYTHONPATH := `pwd`

#* Prepare for development
.PHONY: develop
develop:
	poetry install --no-interaction
	- pyenv rehash
	poetry run pre-commit install
	make proto

#* Build
.PHONY: proto
proto:
	poetry run python -m grpc_tools.protoc --python_betterproto_out=src/fle/grpc/proto --proto_path=proto proto/fle/*.proto

.PHONY: dist
dist: proto
	poetry build

#* Formatters
.PHONY: codestyle
codestyle:
	clang-format -i proto/fle/*.proto
	poetry run pyupgrade --exit-zero-even-if-changed --py38-plus **/*.py
	poetry run isort --settings-path pyproject.toml ./
	poetry run black --config pyproject.toml ./

#* Static Analysis
.PHONY: pylint
pylint:
	poetry run pylint -j 2 src tests

.PHONY: check-codestyle
check-codestyle:
	clang-format --dry-run -Werror proto/fle/*.proto
	poetry run isort --diff --check-only --settings-path pyproject.toml ./
	poetry run black --diff --check --config pyproject.toml ./
	poetry run darglint --verbosity 2 src tests
	poetry run pylint -j 2 src tests

.PHONY: mypy
mypy:
	poetry run mypy ./

.PHONY: check-safety
check-safety:
	poetry check
	poetry export | poetry run safety check --stdin --full-report --db=$$(python -c 'import sysconfig; print(sysconfig.get_paths()["purelib"], end="")')/safety_db --ignore=44715
	poetry run bandit -ll --recursive src tests

#* Dynamic Analysis
.PHONY: pytest
pytest:
# The abspath $(CURDIR) seems necessary for the python subprocesses we run to get included in coverage
	poetry run pytest -c pyproject.toml --cov-report=html --cov=$(CURDIR)/src/fle
	poetry run coverage-badge -o assets/images/coverage.svg -f

.PHONY: tox
tox:
	poetry run tox --parallel

#* All Analysis
.PHONY: test
test: check-codestyle mypy check-safety pytest tox

.PHONY: update-dev-deps
update-dev-deps:
	poetry add -D bandit@latest darglint@latest "isort[colors]@latest" mypy@latest pre-commit@latest pydocstyle@latest pylint@latest pytest@latest pyupgrade@latest safety@latest coverage@latest coverage-badge@latest pytest-html@latest pytest-cov@latest
	poetry add -D --allow-prereleases black@latest

#* CI
.PHONY: ci
ci:
	python --version
	make develop
	make check-codestyle
	make check-safety
	make mypy
# Set GITHUB_ACTIONS to convince tox-gh-actions that this is CI
# which restricts tox to only the running python version
	GITHUB_ACTIONS=true TOX_PARALLEL_NO_SPINNER=1 make tox
