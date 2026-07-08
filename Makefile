.PHONY: install run-backend run-frontend docker-up test lint format security

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt
	cd frontend && npm install

run-backend:
	python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

run-frontend:
	cd frontend && npm run dev

docker-up:
	docker compose up --build

test:
	pytest

lint:
	ruff check .

format:
	ruff check --fix .
	ruff format .

security:
	bandit -r .
