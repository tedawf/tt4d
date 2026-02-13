include .env
export # so env vars are available to both the Makefile AND any commands/processes it runs


.DEFAULT_GOAL := help
.PHONY: help
help: # Display this help screen
	@grep -h -E '^[a-zA-Z_-]+:.*?# .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?# "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: env
env: # Display environment variables
	@echo "Postgres User: $(DB_USER)"
	@echo "Postgres Name: $(DB_NAME)"
	@echo "Postgres Host: $(DB_HOST)"
	@echo "Postgres Port: $(DB_PORT)"

.PHONY: venv
venv: # Creates a venv
	python3 -m venv .venv

.PHONY: docker-up
docker-up: # Start Docker containers
	docker compose up -d --build

.PHONY: docker-down
docker-down: # Stop Docker containers
	docker compose down

.PHONY: migrate-new
migrate-new: # Create a new migration file
	@read -p "Enter migration name: " name; \
	alembic revision --autogenerate -m "$$name"

.PHONY: migrate-up
migrate-up: # Run all pending migrations
	alembic upgrade head

.PHONY: migrate-down
migrate-down: # Rollback last migration
	alembic downgrade -1

.PHONY: migrate-reset
migrate-reset: # DANGER: Rollback all migrations
	alembic downgrade base
	alembic upgrade head

.PHONY: test
test: # Run test suite
	pytest -q
