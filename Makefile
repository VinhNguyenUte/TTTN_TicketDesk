.PHONY: dev-up dev-down migrate makemigrations shell test

dev-up:
	docker-compose -f docker/dev/docker-compose.yml up -d --build

dev-down:
	docker-compose -f docker/dev/docker-compose.yml down

migrate:
	docker-compose -f docker/dev/docker-compose.yml exec web python src/manage.py migrate

makemigrations:
	docker-compose -f docker/dev/docker-compose.yml exec web python src/manage.py makemigrations

shell:
	docker-compose -f docker/dev/docker-compose.yml exec web python src/manage.py shell

test:
	docker-compose -f docker/dev/docker-compose.yml exec web pytest