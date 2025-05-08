#!/bin/bash
# setup_history.sh - Simple setup for history functionality

echo "Setting up history functionality..."

# Step 1: Run the database migration
echo "Setting up database..."
python -m src.db.migrations.add_history_support

# Step 2: Restart the application
echo "Setup complete! Please restart your Flask application."
echo "Run: python run_dev.py"