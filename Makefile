.PHONY: install lint type test

install:
	python -m pip install -U pip
	pip install -e ".[dev]"

lint:
	ruff check src tests

type:
	mypy src

test:
	pytest -q
