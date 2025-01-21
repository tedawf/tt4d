# Include .env file
include .env
export # Variables are available to both the Makefile AND any commands/processes it runs

# Database URL for golang-migrate
DATABASE_URL=postgres://$(DB_USER):$(DB_PASS)@$(DB_HOST):$(DB_PORT)/$(DB_NAME)?sslmode=disable

.DEFAULT_GOAL := help
.PHONY: help
help: # Display this help screen
	@grep -h -E '^[a-zA-Z_-]+:.*?# .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?# "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: env
env: # Display environment variables
	@echo "Database URL: $(DATABASE_URL)"
	@echo "Postgres User: $(DB_USER)"
	@echo "Postgres Name: $(DB_NAME)"
	@echo "Postgres Host: $(DB_HOST)"
	@echo "Postgres Port: $(DB_PORT)"
	@echo "Migration Path: $(MIGRATION_PATH)"

.PHONY: docker-up
docker-up: # Start Docker containers
	docker compose up -d --build

.PHONY: docker-down
docker-down: # Stop Docker containers
	docker compose down

.PHONY: migrate-new
migrate-new: # Create a new migration file
	@read -p "Enter migration name: " name; \
	migrate create -ext sql -dir $(MIGRATION_PATH) -seq $$name

.PHONY: migrate-up
migrate-up: # Run all pending migrations
	migrate -path $(MIGRATION_PATH) -database "$(DATABASE_URL)" up

.PHONY: migrate-down
migrate-down: # Rollback last migration
	migrate -path $(MIGRATION_PATH) -database "$(DATABASE_URL)" down 1

.PHONY: migrate-reset
migrate-reset: # Rollback all migrations
	migrate -path $(MIGRATION_PATH) -database "$(DATABASE_URL)" drop
	migrate -path $(MIGRATION_PATH) -database "$(DATABASE_URL)" up
