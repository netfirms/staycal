#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# This script is the entrypoint for the Docker container.
# It ensures dependencies are installed and the database is migrated
# before starting the main application.

echo "Installing/updating dependencies..."
pip install -r requirements.txt

echo "Running database migrations..."
alembic upgrade head

echo "Setup complete. Starting application..."

# Execute the command passed to this script (e.g., the uvicorn server command)
exec "$@"
