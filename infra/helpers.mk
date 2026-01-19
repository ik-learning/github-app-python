# Determine the directory of this helper makefile
INFRASTRUCTURE_DIR := infrastructure

docker-python-deps: ## Build dockerfile.python to install python dependencies
    docker build -f $(INFRASTRUCTURE_DIR)/Dockerfile.python -t github-app
	docker-compose -f $(INFRASTRUCTURE_DIR)/docker-compose.yml up --build

