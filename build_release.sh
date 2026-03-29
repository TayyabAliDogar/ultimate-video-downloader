#!/bin/bash

echo "========================================"
echo "Ultimate Video Downloader - Release Build"
echo "========================================"
echo

# Check if buildozer is installed
if ! command -v buildozer &> /dev/null; then
    echo "ERROR: Buildozer not found"
    echo "Please run: pip install buildozer"
    exit 1
fi

# Check for keystore
KEYSTORE="my-release-key.keystore"
if [ ! -f "$KEYSTORE" ]; then
    echo "Keystore not found. Creating new keystore..."
    echo
    echo "Please enter keystore information:"
    keytool -genkey -v -keystore $KEYSTORE -alias my-key-alias \
            -keyalg RSA -keysize 2048 -validity 10000

    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create keystore"
        exit 1
    fi
fi

# Clean previous builds
echo
echo "Cleaning previous builds..."
buildozer android clean

# Build release APK
echo
echo "Building release APK..."
buildozer android release

# Sign the APK
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
    echo "Note: The APK is signed with your keystore"
    echo "Keep your keystore file safe for future updates!"
else
    echo
    echo "========================================"
    echo "Build failed!"
    echo "========================================"
    exit 1
fi
