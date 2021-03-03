.PHONY: test-watch
test-watch:
	pytest -f --color=yes tests

.PHONY: test-tox
test-tox:
	tox

.PHONY: test
test:
	pytest -f  --cov=src --color=yes tests
