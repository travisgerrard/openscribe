#!/bin/bash

# Get the directory where this script is located
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$DIR"

# Make sure we're in the right directory
if [ ! -f "transcribeV4.py" ]; then
    echo "Error: transcribeV4.py not found in $DIR"
    exit 1
fi

# Run the Python script
echo "Starting Citrix Transcriber..."
python3 transcribeV4.py 