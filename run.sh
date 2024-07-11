#!/bin/bash

# Start PostgreSQL container for database tests

# Stop and remove any existing containers with the same name
docker stop postgres12-pytest 2>/dev/null || true
docker rm postgres12-pytest 2>/dev/null || true

docker run --name postgres12-pytest \
  -e POSTGRES_DB=test_db_1 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  -p 5433:5432 \
  --rm -d postgres:12 \
#  -c fsync=off \
#  -c full_page_writes=off \
#  -c synchronous_commit=off


# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to initialize..."
sleep 10  # Increased from 5 to 10 seconds

DOCKER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' postgres12-pytest)

# Run pytest
# -s to redirect stdout

echo "Running pytest..."
PYTHONUNBUFFERED=1 pytest -o log_cli=true -o log_cli_level=DEBUG -k 'test_search_client' \
  --postgresql-host=$DOCKER_IP \
  --postgresql-port=5433 \
  --postgresql-user=postgres \
  --postgresql-password=password \



# Stop the container
docker stop postgres12-pytest
