up:
	@docker compose down --remove-orphans
	@echo "start" > router/start.txt
	@docker compose up

up_background:
	@echo "" > router/start.txt
	@docker compose down --remove-orphans
	@docker compose up -d
	@echo "start" > router/start.txt

ger_fila:
	@python3 docker_compose_ger_fila.py

ger_enu:
	@python3 docker_compose_ger_enu.py 

ger_cir:
	@python3 docker_compose_ger_cir.py $(qtd) ${with_host} ${qtd_max_test}

down:
	@docker compose down --remove-orphans
	@echo "" > router/start.txt

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

test_time_conversion:
	@python3 scripts_test/test_time_conversion.py

test_qtd_packets:
	@python3 scripts_test/test_qtd_packets.py