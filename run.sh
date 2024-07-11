#!/bin/bash

# Define container name
CONTAINER_NAME="postgres12-background"

# Check if the container already exists
if [ ! "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    if [ "$(docker ps -aq -f status=exited -f name=$CONTAINER_NAME)" ]; then
        # Cleanup
        echo "Removing old container..."
        docker rm $CONTAINER_NAME
    fi

    # Run new container
    echo "Starting new PostgreSQL container..."
    docker run --network=host --name $CONTAINER_NAME \
      -e POSTGRES_DB=test_db_1 \
      -e POSTGRES_USER=postgres \
      -e POSTGRES_PASSWORD=password \
      -p 5433:5433 \
      -d postgres:14

    echo "Waiting for PostgreSQL to initialize..."
    sleep 7
else
    echo "PostgreSQL container is already running."
fi

# Get container IP
DOCKER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTAINER_NAME)

echo "PostgreSQL container is ready at $DOCKER_IP:5433"

# Your test command (adjust as needed)
echo "Running pytest..."
PYTHONUNBUFFERED=1 pytest -o log_cli=true -o log_cli_level=DEBUG -k 'test_search' \

echo "Tests completed. The PostgreSQL container remains running in the background."

# docker logs postgres12-background  # Check for any startup errors
