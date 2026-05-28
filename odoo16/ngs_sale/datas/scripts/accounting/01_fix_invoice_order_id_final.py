#!/usr/bin/env python3
"""
Final script để fix missing invoice_order_id
Sử dụng public method compute_invoice_order_id_public

Hỗ trợ 3 môi trường: prod, staging, local
Usage:
    python 01_fix_invoice_order_id_final.py          # Dùng default (PROD)
    python 01_fix_invoice_order_id_final.py prod     # Dùng PROD
    python 01_fix_invoice_order_id_final.py staging  # Dùng STAGING
    python 01_fix_invoice_order_id_final.py local    # Dùng LOCAL
"""
import sys
import xmlrpc.client
import time
import os
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    env_type = sys.argv[1] if len(sys.argv) > 1 else None
    url, db, username, password, models, uid = setup_odoo_connection(env_type)
    print(f"✅ Connected to {env_type or 'default'} environment")
except ImportError:
    # Fallback: dùng environment variables
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USERNAME")
    password = os.getenv("ODOO_PASSWORD")
    
    if not all([url, db, username, password]):
        print("❌ Error: Environment variables must be set")
        print("   Run: source load_env.sh [prod|staging|local]")
        sys.exit(1)
    
    common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
    models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url), allow_none=True)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Authentication failed")
        sys.exit(1)

def count_missing():
    """Count missing invoice_order_id"""
    print("==========================================")
    print("COUNT MISSING INVOICE ORDER ID")
    print("==========================================")
    
    if not uid:
        print("❌ Authentication failed!")
        return
    
    total = models.execute_kw(db, uid, password, 'account.move', 'search_count', 
        [[('move_type', 'in', ['in_invoice', 'out_invoice']), ('state', '=', 'posted')]])
    
    missing = models.execute_kw(db, uid, password, 'account.move', 'search_count',
        [[('move_type', 'in', ['in_invoice', 'out_invoice']), ('state', '=', 'posted'), ('invoice_order_id', '=', False)]])
    
    missing_vendor = models.execute_kw(db, uid, password, 'account.move', 'search_count',
        [[('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('invoice_order_id', '=', False)]])
    
    missing_customer = models.execute_kw(db, uid, password, 'account.move', 'search_count',
        [[('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('invoice_order_id', '=', False)]])
    
    print(f"THONG KE:")
    print(f"  Tong invoice posted: {total}")
    print(f"  Invoice thieu invoice_order_id: {missing}")
    print(f"    - Vendor bills: {missing_vendor}")
    print(f"    - Customer invoices: {missing_customer}")
    print(f"  Ti le thieu: {missing/total*100:.1f}%")
    print("==========================================")
    return missing

def fix_batch(limit=100):
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
        {'fields': ['id', 'name', 'move_type', 'partner_id'], 'limit': limit, 'order': 'create_date desc'})
    
    if not missing:
        print("✅ Khong co invoice nao thieu!")
        return
    
    print(f"Tim thay {len(missing)} invoice thieu invoice_order_id (newest first)")
    
    # Show samples
    print("\nSample (first 5):")
    for i, inv in enumerate(missing[:5]):
        partner_name = inv['partner_id'][1] if inv['partner_id'] else 'N/A'
        print(f"  {i+1}. {inv['move_type'].upper()}: {inv['name']} (ID: {inv['id']}) | Partner: {partner_name}")
    
    print(f"\nSẵn sàng fix {len(missing)} invoices...")
    confirm = input("Continue? (y/N): ")
    if confirm.lower() not in ['y', 'yes']:
        print("Cancelled.")
        return
    
    # Process
    print(f"\nBắt đầu fix...")
    fixed = 0
    errors = 0
    
    for i, inv in enumerate(missing):
        print(f"[{i+1}/{len(missing)}] {inv['move_type']} {inv['name']} (ID: {inv['id']})", end=" ")
        
        try:
            result = models.execute_kw(db, uid, password, 'account.move', 'compute_invoice_order_id_public', [[inv['id']]])
            
            if result and result.get('success') and result.get('invoice_order_id'):
                fixed += 1
                print(f"✅ → {result['invoice_order_name']}")
            else:
                print("❌ No counterpart")
                
            time.sleep(0.1)  # Small delay
            
        except Exception as e:
            errors += 1
            print(f"❌ ERROR: {e}")
    
    print(f"\n📊 KET QUA:")
    print(f"  Processed: {len(missing)}")
    print(f"  Fixed: {fixed}")
    print(f"  No counterpart: {len(missing) - fixed - errors}")
    print(f"  Errors: {errors}")
    print(f"  Success rate: {fixed/len(missing)*100:.1f}%")
    print("==========================================")

if __name__ == "__main__":
    if not uid:
        print("❌ Authentication failed!")
        exit(1)
        
    print(f"✅ Connected to {db} as user {uid}")
    
    # Auto run count first
    missing_count = count_missing()
    
    if missing_count > 0:
        print(f"\nCo {missing_count} invoice thieu invoice_order_id.")
        choice = input("Fix batch 100 invoices? (y/N): ")
        if choice.lower() in ['y', 'yes']:
            fix_batch(100)
        else:
            print("Skipped fix.")
    
    print("\nDone!")
