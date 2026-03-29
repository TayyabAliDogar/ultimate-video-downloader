#!/bin/bash

echo "========================================"
echo "Ultimate Video Downloader"
echo "========================================"
echo

if [ ! -d "venv" ]; then
    echo "ERROR: Virtual environment not found!"
    echo "Please run ./setup.sh first"
    exit 1
fi

echo "Starting application..."
source venv/bin/activate
python main.py
