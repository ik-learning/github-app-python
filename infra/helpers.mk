# Determine the directory of this helper makefile
INFRA_DIR := infra

docker-python-deps: ## Build dockerfile.python to install python dependencies
	@docker build -f $(INFRA_DIR)/Dockerfile.python -t python-deps .

docker-smee: ## Build dockerfile.smee to create smee client image
	@docker build -f $(INFRA_DIR)/Dockerfile.smee -t nodejs-smee .

docker-blackduck: ## Build dockerfile.blackduck to create blackduck client image
	@docker build -f $(INFRA_DIR)/Dockerfile.blackduck -t blackduck-deps .

docker-kicks: ## Build dockerfile.kicks to create kicks client image
	@docker build -f $(INFRA_DIR)/Dockerfile.kicks -t kicks-deps .
