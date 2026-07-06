# Makefile for FuzeAgent Database Service

# Variables
DOCKER_IMAGE_NAME = fuzeagent-db
DOCKER_CONTAINER_NAME = fuzeagent-db
DB_HOST = localhost
DB_PORT = 5432
DB_NAME = ai_context
DB_USER = postgres
DB_PASSWORD = password

# Default target
.PHONY: help
help:
	@echo "FuzeAgent Database Service - Makefile Commands"
	@echo "=============================================="
	@echo "build              - Build the database Docker image"
	@echo "run                - Run the database container"
	@echo "stop               - Stop the database container"
	@echo "clean              - Remove the database container"
	@echo "rebuild            - Rebuild the database image"
	@echo "logs               - View database logs"
	@echo "psql               - Connect to database with psql"
	@echo "test-connection    - Test database connection with Python script"
	@echo "init-sample-data   - Initialize database with sample data"
	@echo "backup             - Create a database backup"
	@echo "restore            - Restore database from backup"
	@echo "status             - Check container status"

# Build the database Docker image
.PHONY: build
build:
	docker build -t $(DOCKER_IMAGE_NAME) ./database_service

# Run the database container
.PHONY: run
run:
	docker run -d \
		--name $(DOCKER_CONTAINER_NAME) \
		-p $(DB_PORT):$(DB_PORT) \
		-e POSTGRES_DB=$(DB_NAME) \
		-e POSTGRES_USER=$(DB_USER) \
		-e POSTGRES_PASSWORD=$(DB_PASSWORD) \
		-v db_data:/var/lib/postgresql/data \
		$(DOCKER_IMAGE_NAME)

# Stop the database container
.PHONY: stop
stop:
	docker stop $(DOCKER_CONTAINER_NAME)

# Remove the database container
.PHONY: clean
clean:
	docker rm $(DOCKER_CONTAINER_NAME)

# Rebuild the database image
.PHONY: rebuild
rebuild: clean build

# View database logs
.PHONY: logs
logs:
	docker logs -f $(DOCKER_CONTAINER_NAME)

# Connect to database with psql
.PHONY: psql
psql:
	docker exec -it $(DOCKER_CONTAINER_NAME) psql -U $(DB_USER) $(DB_NAME)

# Test database connection with Python script
.PHONY: test-connection
test-connection:
	cd database_service && python3 -m venv venv
	cd database_service && source venv/bin/activate && pip install -r requirements.txt
	cd database_service && source venv/bin/activate && python test_connection.py

# Initialize database with sample data
.PHONY: init-sample-data
init-sample-data:
	cd database_service && python3 -m venv venv
	cd database_service && source venv/bin/activate && pip install -r requirements.txt
	cd database_service && source venv/bin/activate && python init_sample_data.py

# Create a database backup
.PHONY: backup
backup:
	docker exec $(DOCKER_CONTAINER_NAME) pg_dump -U $(DB_USER) $(DB_NAME) > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "Backup created: backup_$(shell date +%Y%m%d_%H%M%S).sql"

# Restore database from backup (requires BACKUP_FILE variable)
.PHONY: restore
restore:
ifndef BACKUP_FILE
	@echo "Error: Please specify BACKUP_FILE variable"
	@echo "Example: make restore BACKUP_FILE=backup_20230101_120000.sql"
	exit 1
endif
	docker exec -i $(DOCKER_CONTAINER_NAME) psql -U $(DB_USER) $(DB_NAME) < $(BACKUP_FILE)
	@echo "Database restored from $(BACKUP_FILE)"

# Check container status
.PHONY: status
status:
	docker ps -f name=$(DOCKER_CONTAINER_NAME)