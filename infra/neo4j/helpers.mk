# Determine the directory of this helper makefile
INFRASTRUCTURE_NEO4J_DIR := infra/neo4j

compose-neo4j-up: ## Build neo4j services
	@echo "Starting Neo4J with docker-compose..."
	@echo "Application will be available at: http://localhost:8080"
	@echo "Health check: http://localhost:8080/healthz"
	@echo "Readiness check: http://localhost:8080/readyz"
	docker-compose -f docker-compose.yml up

compose-neo4j-down: ## Stop and remove neo4j containers (--volumes to also remove volumes)
	@echo "Stopping docker-compose services..."
	docker-compose -f docker-compose.yml down --remove-orphans --volumes

compose-neo4j-logs: ## Show docker compose logs
	@echo "Showing docker-compose logs..."
	docker-compose -f docker-compose.yml logs -f neo4j-init

compose-neo4j-init: ## Rebuild and restart multiple services
	@docker compose -f docker-compose.yml restart neo4j
# 	@docker compose -f docker-compose.yml up -d  neo4j-init
