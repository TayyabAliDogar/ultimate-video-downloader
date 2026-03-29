#!/bin/bash

echo "========================================"
echo "Ultimate Video Downloader - Android Build"
echo "========================================"
echo

# Check if buildozer is installed
if ! command -v buildozer &> /dev/null; then
    echo "Buildozer not found. Installing..."
    pip install buildozer
    pip install cython
fi

# Check for required tools
echo "Checking build requirements..."

if ! command -v java &> /dev/null; then
    echo "WARNING: Java not found. Please install JDK 8 or higher"
fi

# Clean previous builds (optional)
read -p "Clean previous builds? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleaning..."
    buildozer android clean
fi

# Build debug APK
echo
echo "Building debug APK..."
buildozer android debug

# Check if build was successful
if [ $? -eq 0 ]; then
    echo
    echo "========================================"
    echo "Build successful!"
    echo "========================================"
    echo
    echo "APK location: bin/*.apk"
    echo
    echo "To install on device:"
    echo "  adb install bin/*.apk"
    echo
    echo "To build release version:"
    echo "  ./build_release.sh"
else
    echo
    echo "========================================"
    echo "Build failed!"
    echo "========================================"
    echo
    echo "Common issues:"
    echo "  1. Missing Android SDK/NDK"
    echo "  2. Missing Java JDK"
    echo "  3. Missing build tools"
    echo
    echo "Run: buildozer android debug -v"
    echo "for detailed error messages"
fi
