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
