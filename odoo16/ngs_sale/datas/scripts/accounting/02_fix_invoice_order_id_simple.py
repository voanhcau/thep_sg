#!/usr/bin/env python3
import os
import xmlrpc.client
import time
import sys
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False


# Config
# Get connection với hỗ trợ 3 môi trường
env_type = sys.argv[1] if len(sys.argv) > 1 else None

if USE_ENV_LOADER:
    try:
        url, db, username, password, models, uid = setup_odoo_connection(env_type)
        print(f"✅ Connected to {env_type or 'default'} environment")
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
    
    import xmlrpc.client
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Authentication failed")
        sys.exit(1)

def count_missing():
    """Count missing invoice_order_id"""
    print("==========================================")
    print("COUNT MISSING INVOICE ORDER ID")
    print("==========================================")
    print("Database:", db)
    print("User ID:", uid)
    print()
    
    if not uid:
        print("❌ Authentication failed!")
        return
    
    # Count total invoices
    total = models.execute_kw(db, uid, password, 'account.move', 'search_count', 
        [[('move_type', 'in', ['in_invoice', 'out_invoice']), ('state', '=', 'posted')]])
    
    # Count missing
    missing = models.execute_kw(db, uid, password, 'account.move', 'search_count',
        [[('move_type', 'in', ['in_invoice', 'out_invoice']), ('state', '=', 'posted'), ('invoice_order_id', '=', False)]])
    
    # Count by type
    missing_vendor = models.execute_kw(db, uid, password, 'account.move', 'search_count',
        [[('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('invoice_order_id', '=', False)]])
    
    missing_customer = models.execute_kw(db, uid, password, 'account.move', 'search_count',
        [[('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('invoice_order_id', '=', False)]])
    
    print("THONG KE:")
    print(f"  Tong invoice posted: {total}")
    print(f"  Invoice thieu invoice_order_id: {missing}")
    print(f"    - Vendor bills: {missing_vendor}")
    print(f"    - Customer invoices: {missing_customer}")
    print(f"  Ti le thieu: {missing/total*100:.1f}%")
    print("==========================================")

def test_invoice_120888():
    """Test fix invoice 120888"""
    print("==========================================")
    print("TEST FIX INVOICE 120888")
    print("==========================================")
    
    if not uid:
        print("❌ Authentication failed!")
        return
    
    invoice_id = 120888
    
    # Get current state
    invoice = models.execute_kw(db, uid, password, 'account.move', 'read', 
        [[invoice_id]], {'fields': ['id', 'name', 'move_type', 'invoice_order_id']})
    
    if not invoice:
        print("❌ Invoice 120888 not found!")
        return
    
    inv = invoice[0]
    current_order_id = inv['invoice_order_id']
    
    print("Thong tin truoc khi fix:")
    print(f"  ID: {inv['id']}")
    print(f"  Name: {inv['name']}")
    print(f"  Type: {inv['move_type']}")
    print(f"  invoice_order_id: {current_order_id[1] if current_order_id else 'NULL'}")
    print()
    
    # Fix
    print("Dang fix...")
    try:
        result = models.execute_kw(db, uid, password, 'account.move', '_compute_invoice_order_id', [[invoice_id]])
        
        # Check result
        updated = models.execute_kw(db, uid, password, 'account.move', 'read',
            [[invoice_id]], {'fields': ['invoice_order_id']})
        
        new_order_id = updated[0]['invoice_order_id'] if updated else None
        
        print("Ket qua:")
        if new_order_id and new_order_id != current_order_id:
            print(f"  ✅ THANH CONG: invoice_order_id = {new_order_id[1]}")
        else:
            print(f"  ❌ KHONG THAY DOI: {current_order_id[1] if current_order_id else 'NULL'}")
            
    except Exception as e:
        print(f"  ❌ LOI: {e}")
    
    print("==========================================")

def fix_batch(limit=50):
    """Fix batch missing invoices"""
    print("==========================================")
    print(f"FIX BATCH MISSING INVOICES (limit: {limit})")
    print("==========================================")
    
    if not uid:
        print("❌ Authentication failed!")
        return
    
    # Get missing invoices
    missing = models.execute_kw(db, uid, password, 'account.move', 'search_read',
        [[('move_type', 'in', ['in_invoice', 'out_invoice']), ('state', '=', 'posted'), ('invoice_order_id', '=', False)]],
        {'fields': ['id', 'name', 'move_type'], 'limit': limit})
    
    if not missing:
        print("✅ Khong co invoice nao thieu!")
        return
    
    print(f"Tim thay {len(missing)} invoice thieu invoice_order_id")
    print()
    
    # Confirm
    confirm = input(f"Fix {len(missing)} invoices? (y/N): ")
    if confirm.lower() not in ['y', 'yes']:
        print("Huy bo.")
        return
    
    # Process
    fixed = 0
    for i, inv in enumerate(missing):
        print(f"[{i+1}/{len(missing)}] Processing {inv['move_type']} {inv['name']} (ID: {inv['id']})")
        
        try:
            # Fix
            models.execute_kw(db, uid, password, 'account.move', '_compute_invoice_order_id', [[inv['id']]])
            
            # Check
            updated = models.execute_kw(db, uid, password, 'account.move', 'read',
                [[inv['id']]], {'fields': ['invoice_order_id']})
            
            if updated[0]['invoice_order_id']:
                fixed += 1
                print(f"  ✅ FIXED: {updated[0]['invoice_order_id'][1]}")
            else:
                print(f"  ❌ NO FIX")
                
            time.sleep(0.1)  # Small delay
            
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
    
    print(f"\nKet qua: Fixed {fixed}/{len(missing)} invoices ({fixed/len(missing)*100:.1f}%)")
    print("==========================================")

if __name__ == "__main__":
    if not uid:
        print("❌ Authentication failed! Check credentials.")
        exit(1)
        
    print("✅ Connected successfully!")
    print("Chon chuc nang:")
    print("1. Count missing invoices")
    print("2. Test fix invoice 120888")
    print("3. Fix batch (50 invoices)")
    print("4. Exit")
    
    choice = input("Nhap lua chon (1-4): ")
    
    if choice == '1':
        count_missing()
    elif choice == '2':
        test_invoice_120888()
    elif choice == '3':
        fix_batch(50)
    elif choice == '4':
        print("Exit.")
    else:
        print("Invalid choice!")
