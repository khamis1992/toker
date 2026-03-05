#!/bin/bash
# Setup script for the TikTok Dashboard bot environment
# Run this once after cloning the repo or setting up a new server

set -e

PYTHON=/usr/bin/python3
PIP="$PYTHON -m pip"

echo "=== Installing Python dependencies ==="
sudo $PIP install -q \
    django \
    playwright \
    fake-useragent \
    aiohttp \
    textblob \
    beautifulsoup4 \
    psutil \
    requests \
    asgiref

echo "=== Installing Playwright Chromium browser ==="
$PYTHON -m playwright install chromium

echo "=== Running Django migrations ==="
$PYTHON manage.py migrate

echo "=== Environment setup complete ==="
echo "You can now start the dashboard with: python manage.py runserver 0.0.0.0:8080"
