#!/bin/bash

# Create project directory structure
mkdir -p app/{models,parsers,scrapers,utils}
mkdir -p data
mkdir -p logs

# Create __init__.py files for Python packages
touch app/__init__.py
touch app/models/__init__.py
touch app/parsers/__init__.py
touch app/scrapers/__init__.py
touch app/utils/__init__.py

# Copy .env.example to .env
cp .env.example .env

echo "Project structure created successfully!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your configuration"
echo "2. Add your news sources"
echo "3. Run: docker compose build"
echo "4. Run: docker compose up"
