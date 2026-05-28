#!/bin/bash

# Navigate to the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Ensure login_local.py is accessible
LOGIN_CONFIGS_PATH="../login_configs"
if [ -f "$LOGIN_CONFIGS_PATH/login_local.py" ]; then
    export PYTHONPATH="$PYTHONPATH:$LOGIN_CONFIGS_PATH"
    echo "Added $LOGIN_CONFIGS_PATH to PYTHONPATH."
else
    echo "Warning: login_local.py not found in $LOGIN_CONFIGS_PATH."
fi

echo "=========================================="
echo "COMPREHENSIVE INVOICE STATUS FIX"
echo "=========================================="
echo "This script fixes invoice creation errors for:"
echo "  - Sale Orders (state != 'done')"
echo "  - Purchase Orders (state != 'done')"
echo ""

# Set AUTO_CONFIRM=y to skip interactive confirmation
export AUTO_CONFIRM=y

echo "Running 07_comprehensive_fix_invoice_status.py..."
python 07_comprehensive_fix_invoice_status.py

# Unset PYTHONPATH
unset PYTHONPATH

echo ""
echo "Script finished."

