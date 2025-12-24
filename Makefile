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
