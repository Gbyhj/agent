.PHONY: test beta bench lint clean deploy

test:
	cd .. && python -m agent.main --test

beta:
	cd .. && source agent/.venv/Scripts/activate && PYTHONPATH=. python agent/tests/beta/test_scenarios.py

bench:
	cd .. && source agent/.venv/Scripts/activate && PYTHONPATH=. python agent/tests/benchmark.py

lint:
	ruff check src/ tests/ || true

clean:
	find . -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

deploy:
	docker build -t agent -f deploy/Dockerfile .
