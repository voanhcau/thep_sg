#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script Template - Hỗ trợ 3 môi trường (prod/staging/local)

Usage:
    python SCRIPT_TEMPLATE.py          # Dùng default (PROD)
    python SCRIPT_TEMPLATE.py prod     # Dùng PROD
    python SCRIPT_TEMPLATE.py staging  # Dùng STAGING
    python SCRIPT_TEMPLATE.py local    # Dùng LOCAL

Hoặc set environment variables trước:
    source load_env.sh [prod|staging|local]
    python SCRIPT_TEMPLATE.py
"""

import sys
import os
import xmlrpc.client
from pathlib import Path

# Add login_configs to path để import env_loader
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False

def get_connection(env_type=None):
    """
    Lấy Odoo connection
    
    Args:
        env_type: 'prod', 'staging', 'local', hoặc None (dùng default)
    
    Returns:
        tuple: (url, db, username, password, models, uid)
    """
    if USE_ENV_LOADER:
        try:
            return setup_odoo_connection(env_type)
        except Exception as e:
            print(f"❌ Error loading environment: {e}")
            sys.exit(1)
    else:
        # Fallback: dùng environment variables trực tiếp
        url = os.getenv("ODOO_URL")
        db = os.getenv("ODOO_DB")
        username = os.getenv("ODOO_USERNAME")
        password = os.getenv("ODOO_PASSWORD")
        
        if not all([url, db, username, password]):
            print("❌ Missing environment variables. Please:")
            print("   1. Run: source load_env.sh [prod|staging|local]")
            print("   2. Or set: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD")
            sys.exit(1)
        
        # Connect manually
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("❌ Authentication failed")
            sys.exit(1)
        
        return url, db, username, password, models, uid

def main():
    # Lấy environment type từ command line argument
    env_type = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Get connection
    url, db, username, password, models, uid = get_connection(env_type)
    
    print(f"✅ Connected to {env_type or 'default'} environment")
    print(f"   URL: {url}")
    print(f"   DB: {db}")
    print(f"   Username: {username}")
    print(f"   User ID: {uid}")
    
    # ============================================
    # YOUR CODE HERE
    # ============================================
    
    # Example: Tìm đơn hàng
    # orders = models.execute_kw(
    #     db, uid, password,
    #     'sale.order', 'search',
    #     [[('id', '>', 0)]],
    #     {'limit': 10}
    # )
    # print(f"Found {len(orders)} orders")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
