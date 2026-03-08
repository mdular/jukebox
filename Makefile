SHELL := /bin/sh

PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
VENV_PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
PYTEST := $(VENV)/bin/pytest

.DEFAULT_GOAL := help

.PHONY: help python-check venv install run lint typecheck test check clean

help:
	@printf '%s\n' \
		'Available targets:' \
		'  make venv       Create a local virtualenv and install dev dependencies' \
		'  make run        Run the scaffold locally' \
		'  make lint       Run ruff' \
		'  make typecheck  Run mypy' \
		'  make test       Run pytest' \
		'  make check      Run lint, typecheck, and test' \
		'  make clean      Remove local build and cache artifacts'

python-check:
	@$(PYTHON) -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else "Python 3.11+ is required.")'

$(VENV_PYTHON): python-check
	$(PYTHON) -m venv $(VENV)
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -e '.[dev]'

venv: $(VENV_PYTHON)

install: venv

run:
	./scripts/run-local.sh

lint: venv
	$(RUFF) check src tests

typecheck: venv
	$(MYPY)

test: venv
	PYTHONPATH=src $(PYTEST)

check: lint typecheck test

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache build dist *.egg-info src/*.egg-info .coverage
