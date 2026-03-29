#!/bin/bash

echo "========================================"
echo "Ultimate Video Downloader - Setup"
echo "========================================"
echo

echo "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

python3 --version

echo
echo "Creating virtual environment..."
python3 -m venv venv

echo
echo "Activating virtual environment..."
source venv/bin/activate

echo
echo "Upgrading pip..."
pip install --upgrade pip

echo
echo "Installing dependencies..."
pip install -r requirements.txt

echo
echo "========================================"
echo "Setup complete!"
echo "========================================"
echo
echo "To run the application:"
echo "  1. Run: ./run.sh"
echo "  OR"
echo "  2. Activate venv: source venv/bin/activate"
echo "  3. Run: python main.py"
echo
