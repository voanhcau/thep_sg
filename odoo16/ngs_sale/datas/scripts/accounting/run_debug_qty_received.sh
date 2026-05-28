#!/bin/bash
# Script to run debug_qty_received.py

echo "=========================================="
echo "DEBUG QTY_RECEIVED = 0"
echo "=========================================="
echo "This script will debug why qty_received = 0 in Purchase Orders"
echo ""

# Copy login_local.py to current directory
echo "Copying login_local.py..."
cp ../login_configs/login_local.py .

echo "Running debug_qty_received.py..."
python3 debug_qty_received.py

# Clean up
echo "Cleaning up..."
rm -f login_local.py

echo "Done!"



