.PHONY: up down test lint build catalog audit-materials verify seed admin

up:
	docker compose up --build

down:
	docker compose down

test:
	cd backend && ../.venv/bin/pytest
	cd frontend && npm run test:run

lint:
	cd backend && ../.venv/bin/ruff check . ../scripts/build_catalog.py ../scripts/validate_material_urls.py

build:
	cd frontend && npm run build

catalog:
	.venv/bin/python scripts/build_catalog.py

audit-materials: catalog
	.venv/bin/python scripts/validate_material_urls.py

verify: test lint build
	docker compose --env-file .env.example config --quiet

seed:
	docker compose exec api flask --app wsgi import-catalog --sync /data/seed/catalog.json

admin:
	docker compose exec api flask --app wsgi create-admin
