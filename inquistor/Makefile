.PHONY: build up down test clean shell-attacker shell-client shell-server

# Default target
all: build up

# Build all docker images
build:
	@echo "Building Docker images..."
	docker-compose build

# Start the containers
up:
	@echo "Starting containers..."
	docker-compose up -d
	@echo "Containers started!"
	@echo "Use 'make shell-attacker' to access the attacker container."
	@echo "Use 'make shell-client' to access the FTP client container."
	@echo "Use 'make shell-server' to access the FTP server container."

# Stop the containers
down:
	@echo "Stopping containers..."
	docker-compose down

# Run the test scenario
test: up
	@echo "Setting up test environment..."
	@echo "Creating test files..."
	docker exec -it ftp-client bash -c "echo 'This is a test file for upload' > /home/ftpuser/files/upload-test.txt"
	docker exec -it ftp-server bash -c "echo 'This is a test file for download' > /home/ftpuser/ftp/download-test.txt"
	
	@echo "\nStarting ARP poisoning attack in the background..."
	docker exec -d attacker python3 /app/inquisitor.py 172.20.0.3 172.20.0.2 -i eth0 -v
	
	@echo "Waiting for attack to initialize..."
	sleep 3
	
	@echo "\nPerforming FTP transfer test..."
	docker exec -it ftp-client bash -c "echo 'open ftp-server 21\nuser ftpuser ftppassword\nget download-test.txt\nput upload-test.txt\nbye' | ftp -n"
	
	@echo "\nTest completed. Check the attacker container output for captured FTP commands."
	@echo "To see the attacker logs, run: docker logs attacker"
	@echo "To stop the attack, enter the attacker container and press Ctrl+C"

# Access attacker container shell
shell-attacker:
	@echo "Accessing attacker container..."
	docker exec -it attacker bash

# Access client container shell
shell-client:
	@echo "Accessing FTP client container..."
	docker exec -it ftp-client bash

# Access server container shell
shell-server:
	@echo "Accessing FTP server container..."
	docker exec -it ftp-server bash

# Clean up everything
clean: down
	@echo "Removing containers and images..."
	docker-compose down --rmi all --volumes --remove-orphans
	@echo "Cleanup complete."