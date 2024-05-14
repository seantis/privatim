FROM python:3.12.2-alpine3.19

# Set the working directory
WORKDIR /app

# Install PostgreSQL development packages required for psycopg
RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set the entrypoint to the script
ENTRYPOINT ["/app/entrypoint.sh"]
