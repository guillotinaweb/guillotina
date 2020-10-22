#The shell we use
SHELL := /bin/bash

# We like colors
# # From: https://coderwall.com/p/izxssa/colored-makefile-for-golang-projects
RED=`tput setaf 1`
GREEN=`tput setaf 2`
RESET=`tput sgr0`
YELLOW=`tput setaf 3`

# Vars
mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
current_dir := $(notdir $(patsubst %/,%,$(dir $(mkfile_path))))

.PHONY: help
help: ## This help message
	@echo -e "$$(grep -hE '^\S+:.*##' $(MAKEFILE_LIST) | sed -e 's/:.*##\s*/:/' -e 's/^\(.\+\):\(.*\)/\\x1b[36m\1\\x1b[m:\2/' | column -c2 -t -s :)"

.PHONY: run-postgres
run-postgres: ## Run PostgreSQL
	@echo ""
	@echo "$(YELLOW)==> Running PostgreSQL $(VERSION)$(RESET)"
	@docker run --rm -e POSTGRES_DB=guillotina -e POSTGRES_USER=postgres \
		-p 127.0.0.1:5432:5432 --name postgres postgres:9.6

.PHONY: run-redis
run-redis: ## Run Redis
	@echo ""
	@echo "$(YELLOW)==> Running Redis"
	@docker run -p 127.0.0.1:32958:6379 --rm redis:5.0.7

