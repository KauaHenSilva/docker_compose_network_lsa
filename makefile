up:
	@docker compose down
	@docker compose up --build

ger_fila:
	@python3 docker_compose_ger_fila.py



down:
	@docker compose down

clear:
	@docker compose down --rmi all --volumes --remove-orphans
	@docker network prune -f

show-tables:
	@python3 scripts_test/show_tables.py

test-connectivity:
	@python3 scripts_test/test_connectivity.py



