#!/bin/bash

# Go to project directory
cd /home/pi/offline-speech-translation || exit 1

# Activate virtual environment
source .venv/bin/activate

# Optional: wait for system to settle (Wi-Fi, audio, etc.)
sleep 10

# Run the Python program
python3 translatorfull.py
