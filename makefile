test:
	python3 test.py

ger:
	python3 docker_compose_ger.py

up:
	@docker compose down
	@docker compose up --build

down:

clear:
	@docker-compose down --rmi all --volumes --remove-orphans
	@docker network prune -f