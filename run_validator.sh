#!/bin/bash

# This script activates the virtual environment and runs the validator
# with the correct Python interpreter

# Activate the virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
    echo "Activated virtual environment at .venv"
else
    echo "Error: Virtual environment not found at .venv"
    echo "Please create and set up the virtual environment first:"
    echo "    python -m venv .venv"
    echo "    source .venv/bin/activate"
    echo "    pip install -r requirements.txt"
    exit 1
fi

# Set PYTHONPATH to include the current directory
export PYTHONPATH="$PYTHONPATH:."

# Run the validator with the venv's Python
python run_validator.py "$@" 