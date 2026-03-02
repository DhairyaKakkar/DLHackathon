.PHONY: install test lint api dashboard benchmark clean

install:
	pip install -e ".[dev,api,dashboard]"

test:
	pytest tests/ -v

lint:
	ruff check cvengine/ api/ tests/

api:
	uvicorn api.main:app --reload --port 8000

dashboard:
	streamlit run dashboard/app.py

benchmark:
	python scripts/benchmark.py

docker-build:
	docker build -t cvengine .

docker-run:
	docker run -p 8000:8000 cvengine

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	rm -rf *.egg-info dist build runs checkpoints
