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

router-show-tables:
	@python3 scripts_test/router_show_tables.py

router-connect-router:
	@python3 scripts_test/router_connect_router.py

user-connect-router:
	@python3 scripts_test/user_connect_router.py

user-connect-user:
	@python3 scripts_test/user_connect_user.py
