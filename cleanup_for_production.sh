#!/bin/bash

"""
Production Cleanup Script
Cleans up test files and prepares for production commit
"""

echo "🧹 CLEANING UP TEST FILES AND PREPARING FOR PRODUCTION"
echo "================================================================"

# Remove test files
echo "🗑️ Removing test files..."
rm -f test_*.py
rm -f examine_worksheet.py
rm -f show_worksheet_demo.py
rm -f final_cache_test.py

# Keep sample files for documentation
echo "📁 Keeping sample files for inspection:"
ls -la sample_*.*

# Show git status
echo ""
echo "📊 Current git status:"
git status

echo ""
echo "✅ Cleanup completed!"
echo "📋 Ready for production commit"
