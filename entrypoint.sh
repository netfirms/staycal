#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# This script can be used for pre-start tasks.
# For now, it just executes the main command.

echo "Starting application..."

# Execute the command passed to this script (the Uvicorn server command)
exec "$@"
