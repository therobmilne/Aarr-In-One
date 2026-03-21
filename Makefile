.PHONY: dev dev-backend dev-frontend test lint migrate docker-build docker-up

dev:
	./scripts/start-dev.sh

dev-backend:
	cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8686

dev-frontend:
	cd frontend && npm run dev

test:
	python -m pytest tests/ -v

lint:
	ruff check backend/ tests/
	ruff format --check backend/ tests/

format:
	ruff format backend/ tests/
	ruff check --fix backend/ tests/

migrate:
	alembic upgrade head

migrate-create:
	alembic revision --autogenerate -m "$(msg)"

docker-build:
	docker build -t mediaforge:latest .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f mediaforge
