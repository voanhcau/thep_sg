#!/bin/bash
# Script to run fix_purchase_method_products.py

echo "=========================================="
echo "FIX PURCHASE METHOD PRODUCTS"
echo "=========================================="
echo "This script will fix products causing invoice creation error"
echo ""

# Copy login_local.py to current directory
echo "Copying login_local.py..."
cp ../login_configs/login_local.py .

# Set environment variable for non-interactive mode
export AUTO_CONFIRM=y

echo "Running fix_purchase_method_products.py..."
python3 fix_purchase_method_products.py

# Clean up
echo "Cleaning up..."
rm -f login_local.py

echo "Done!"



