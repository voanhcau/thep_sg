#!/usr/bin/env python3
"""
Utility script to cancel vendor bill BILL/2025/11/0585 (id=179086)
via XML-RPC by first resetting it to draft and then cancelling it.
"""

import os
import sys
import xmlrpc.client
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False

MOVE_ID = 179086


def main():
    # Lấy environment type từ command line argument
    env_type = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        if USE_ENV_LOADER:
            URL, DB, USERNAME, PASSWORD, models, uid = setup_odoo_connection(env_type)
            print(f"✅ Connected to {env_type or 'default'} environment")
        else:
            # Fallback: dùng environment variables
            URL = os.getenv("ODOO_URL")
            DB = os.getenv("ODOO_DB")
            USERNAME = os.getenv("ODOO_USERNAME")
            PASSWORD = os.getenv("ODOO_PASSWORD")
            
            if not all([URL, DB, USERNAME, PASSWORD]):
                print("❌ Error: Environment variables must be set")
                print("   Run: source load_env.sh [prod|staging|local]")
                return 1
            
            common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", allow_none=True)
            uid = common.authenticate(DB, USERNAME, PASSWORD, {})
            if not uid:
                print("❌ Authentication failed")
            return 1

        models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)

        def call(method):
            try:
                return models.execute_kw(DB, uid, PASSWORD, "account.move", method, [[MOVE_ID]])
            except xmlrpc.client.Fault as fault:
                fault_msg = str(fault)
                if "cannot marshal None unless allow_none is enabled" in fault_msg:
                    # Method executed but server failed to marshal None. Treat as success.
                    return None
                raise

        print(f"Resetting move {MOVE_ID} to draft...")
        call("button_draft")
        state = models.execute_kw(DB, uid, PASSWORD, "account.move", "read", [[MOVE_ID]], {"fields": ["state"]})[0]["state"]
        if state != "draft":
            print(f"Unexpected state after reset: {state}")
            return 1

        print(f"Cancelling move {MOVE_ID}...")
        call("button_cancel")
        state = models.execute_kw(DB, uid, PASSWORD, "account.move", "read", [[MOVE_ID]], {"fields": ["state"]})[0]["state"]
        if state != "cancel":
            print(f"Unexpected state after cancel: {state}")
            return 1

        print(f"Setting move {MOVE_ID} back to draft...")
        call("button_draft")
        state = models.execute_kw(DB, uid, PASSWORD, "account.move", "read", [[MOVE_ID]], {"fields": ["state"]})[0]["state"]
        if state != "draft":
            print(f"Unexpected state after final draft: {state}")
            return 1

        print("Done.")
        return 0
    except xmlrpc.client.Fault as fault:
        print(f"XML-RPC Fault: {fault}")
        return 1
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())

