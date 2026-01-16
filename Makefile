.PHONY: help
#? help: Get more info on available commands
help: Makefile
	@sed -n 's/^#?//p' $< | column -t -s ':' |  sort | sed -e 's/^/ /'

#? pre-commit-install: Install pre-commit hooks
pre-commit-install:
	@pre-commit install
	@pre-commit gc

#? pre-commit-uninstall: Uninstall pre-commit hooks
pre-commit-uninstall:
	@pre-commit uninstall

#? pre-commit-validate: Validate files with pre-commit hooks
pre-commit-validate:
	@pre-commit run --all-files

#? docker-build: Build the Docker image for the GitHub App (--no-cache option can be added if needed)
docker-build:
	docker build -t githubapp --progress plain  .

#? docker-run: Run the Docker container for the GitHub App
docker-run:
	@docker run --rm -it -p 8080:8000 \
		-e GITHUB_APP_ID=$(GITHUB_APP_ID) \
		-e GITHUB_APP_PRIVATE_KEY=$(GITHUB_APP_PRIVATE_KEY) \
		-e GITHUB_WEBHOOK_SECRET=$(GITHUB_WEBHOOK_SECRET) \
		githubapp

#? docker-compose-up: Start the Docker containers using docker-compose
docker-compose-up:
	docker-compose up --build

docker-compose-down:
	docker-compose down

#? docker-restart-app: Restart the web-app service
docker-restart-app:
	docker-compose restart web-app

#? docker-restart-smee: Restart the smee service
docker-restart-smee:
	docker-compose restart smee

#? docker-logs-app: View logs for web-app service
docker-logs-app:
	docker-compose logs -f web-app

#? docker-logs-smee: View logs for smee service
docker-logs-smee:
	docker-compose logs -f smee

#? docker-rebuild-app: Rebuild and restart web-app service
docker-rebuild-app:
	docker-compose up -d --build web-app

#? test: Run tests with pytest
test:
	pipenv run pytest

#? test-verbose: Run tests with verbose output
test-verbose:
	pipenv run pytest -vv

#? test-coverage: Run tests with coverage report
test-coverage:
	pipenv run pytest --cov=src --cov-report=term-missing --cov-report=html

#? test-unit: Run only unit tests
test-unit:
	pipenv run pytest -m unit

#? test-integration: Run only integration tests
test-integration:
	pipenv run pytest -m integration

#? test-watch: Run tests in watch mode (requires pytest-watch)
test-watch:
	pipenv run ptw

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
