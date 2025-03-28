#!/bin/bash

# Ensure we are in the right Python environment
source .venv/bin/activate

# Start the author service
echo "Starting Site Generator Service..."
python3 services/site_generator_service/main.py

# Deactivate virtual environment
deactivate
