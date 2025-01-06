#!/bin/bash
VENV_PYTHON="/Users/srvo/notebooks/.venv/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
    echo "Virtual environment Python not found at $VENV_PYTHON"
    exit 1
fi

# Run the specified script with arguments
$VENV_PYTHON "$@" 