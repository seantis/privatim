#!/bin/sh

if [ -z "$1" ]; then
  echo "No configuration file (input argument) provided. Exiting."
  exit 1
fi

echo "test"
echo "Running the entrypoint.sh script."

CONFIG_FILE=$1

# Run the upgrade script with the provided config file
python src/privatim/cli/upgrade.py "$CONFIG_FILE"

python src/privatim/cli/initialize_db.py

pserve "$CONFIG_FILE"
