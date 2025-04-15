test:
	python3 test.py

up:
	@docker compose up --build

down:
	@docker compose down

clear:
	@docker network prune -f