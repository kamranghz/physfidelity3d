.PHONY: install validate reproduce test lint

install:
	pip install -e ".[dev]"

validate:
	python -m physfidelity3d validate

reproduce:
	python -m physfidelity3d reproduce --out outputs

test:
	pytest -q

lint:
	ruff check physfidelity3d tests
	ruff format --check physfidelity3d tests
