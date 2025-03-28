#!/bin/bash

# Ensure we are in the right Python environment
source .venv/bin/activate

# Start the author service
echo "Starting Author Service..."
python3 services/author_service/main.py

# Deactivate virtual environment
deactivate
