.PHONY: test-watch
test-watch:
	poetry run pytest -f --color=yes tests

.PHONY: test-tox
test-tox:
	poetry run tox

.PHONY: test
test:
	poetry run pytest --cov=src --color=yes tests
