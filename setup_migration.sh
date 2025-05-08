#!/bin/bash
# setup_migration.sh

# Ensure we're in the project root
cd "$(dirname "$0")"

# Create the migrations directory structure if it doesn't exist
echo "Creating migration directory structure..."
mkdir -p src/db/migrations

# Copy the migration script
echo "Copying migration script..."
cp -f src/db/migrations/add_history_support.py src/db/migrations/

# Make the directory an importable Python package
echo "Creating __init__.py files..."
touch src/db/migrations/__init__.py

echo "Setup complete. You can now run the migration with:"
echo "python -m src.db.migrations.add_history_support"