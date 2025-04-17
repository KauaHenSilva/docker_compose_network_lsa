
ger:
	@python3 docker_compose_ger.py

up:
	@docker compose down
	@docker compose up --build

down:
	@docker compose down

clear:
	@docker compose down --rmi all --volumes --remove-orphans
	@docker network prune -f

show-tables:
	@./scripts_test/show_tables.sh

test-connectivity:
	@./scripts_test/test_connectivity.sh


