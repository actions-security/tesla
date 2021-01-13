.PHONY: run clean clean-test clean-pyc clean-build build test docker-test

SHELL=/bin/bash

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -type f -exec rm -f {} +

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache

test: clean
	source activate tesla && pytest tests -n auto --cov=tesla

docker-test:
	ACTIONS_PRODUCTION=false conda devenv

pymodsecurity:
	source activate tesla && pushd /suite/pymodsecurity && conda install pybind11 gcc && python setup.py install && popd
	source activate tesla && conda clean --all
	rm -rf /suite/pymodsecurity

format:
	yapf -ri tesla/ tests/
	isort -rc tesla/ tests/
