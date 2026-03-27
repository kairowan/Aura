#!/usr/bin/env bash

# Automatically change to the directory where the script is located
cd "$(dirname "$0")"

echo "=========================================="
echo " Starting Optimized Aura "
echo "=========================================="
echo "This script starts Aura in Production mode, which statically"
echo "compiles the frontend and disables file watchers to drastically"
echo "reduce CPU and Memory usage."
echo ""

# Ensure config exists
if [ ! -f "config.yaml" ]; then
    cp config.example.yaml config.yaml
    echo "✓ Created config.yaml from template"
fi

# Ensure frontend .env exists to prevent Docker Compose crash
if [ ! -f "frontend/.env" ]; then
    touch frontend/.env
    echo "✓ Created frontend/.env to prevent Docker errors"
fi

# Ensure global .env exists
if [ ! -f ".env" ]; then
    touch .env
    echo "✓ Created global .env"
fi

# Stop any dangling dev containers just in case
make docker-stop 2>/dev/null || true

# Start the application in production optimized mode (make up)
echo "Starting services in optimized mode (Low CPU/Memory)..."
make up

echo ""
echo "=========================================="
echo " Aura is starting!"
echo " It might take a minute to compile the optimized frontend."
echo " Once ready, please open http://localhost:2026"
echo " To stop it later, run: make down"
echo "=========================================="
