#!/bin/bash

# Ensure we are in the right Python environment
source .venv/bin/activate

# Start the scout service
echo "Starting Scout Service..."
python3 services/scout_service/main.py

# Deactivate virtual environment
deactivate