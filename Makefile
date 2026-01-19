.PHONY: help

.PHONY: help
help:
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

pre-commit-install: ## Install pre-commit hooks
	@pre-commit install
	@pre-commit gc

pre-commit-uninstall: ## Uninstall pre-commit hooks
	@pre-commit uninstall

pre-commit-validate: ## Validate files with pre-commit hooks
	@pre-commit run --all-files

-include infra/helpers.mk

run-all: ## Start the Docker containers
	docker-compose up --build

docker-compose-down:
	docker-compose down

lock-dependencies: ## Generate Pipfile.lock using Docker (no local Python/pipenv needed)
	$(eval PYTHON_IMAGE := $(shell grep "^FROM python" Dockerfile | awk '{print $$2}'))
	@echo "Generating Pipfile.lock using image: $(PYTHON_IMAGE)"
	@docker run --rm \
		-v $(PWD)/$(BOOK_STORE_DIR):/app \
		-w /app \
		$(PYTHON_IMAGE) \
		bash -c "pip install --quiet --root-user-action ignore pipenv && pipenv lock"
	@echo "✓ Pipfile.lock generated successfully in $(BOOK_STORE_DIR)/"

#? build-black-duck-scan: Build the Black Duck scan Docker image
build-black-duck-scan:
	docker build -f Dockerfile.deps -t detect-deps --progress plain .

#? run-black-duck-scan: Run Black Duck scan
run-black-duck-scan:
	@docker run --rm -it -e BRIDGE_BLACKDUCKSCA_TOKEN=$(BRIDGE_BLACKDUCKSCA_TOKEN) \
		-v $(PWD)/input:/scan/input \
		detect-deps

compose-restart: ## Rebuild and restart multiple services
	@docker compose -f docker-compose.yaml up -d --build api
	@docker compose -f docker-compose.yaml up -d --build worker-1
