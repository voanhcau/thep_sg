# -*- coding: utf-8 -*-
"""
Fix invoice status for Purchase Orders
Purpose: Fix "No invoiceable line" error when creating invoices from PO
"""
try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib
import time
import logging
import sys
import codecs
import os

# Set UTF-8 encoding for stdout
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

__logger = logging.getLogger(__name__)

# Connection config - import from absolute path
import sys
sys.path.insert(0, '/Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/login_configs')

try:
    from login_prod import uid, password, db, models
except ImportError as e:
    print("ERROR: Cannot import login_local:", str(e))
    print("Please check if the file exists at:")
    print("/Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/login_configs/login_local.py")
    sys.exit(1)

def analyze_before():
    """Analyze current status before fix"""
    try:
        print("=== ANALYZING CURRENT STATUS ===")
        
        # Count Sale Orders
        so_domain = [('state', '!=', 'done')]
        so_count = models.execute_kw(db, uid, password,
            "sale.order", "search_count",
            [so_domain]
        )
        
        # Count Purchase Orders
        po_domain = [('state', '!=', 'done')]
        po_count = models.execute_kw(db, uid, password,
            "purchase.order", "search_count",
            [po_domain]
        )
        
        # Check problematic POs
        problematic_count = 0
        recent_po_domain = [
            ('state', 'in', ['purchase', 'done']),
            ('create_date', '>=', '2025-09-30')
        ]
        
        recent_pos = models.execute_kw(db, uid, password,
            "purchase.order", "search_read",
            [recent_po_domain],
            {'fields': ['id', 'name', 'state']}
        )
        
        for po in recent_pos:
            po_lines = models.execute_kw(db, uid, password,
                "purchase.order.line", "search_read",
                [[('order_id', '=', po['id'])]],
                {'fields': ['qty_to_invoice']}
            )
            
            total_qty_to_invoice = sum(line.get('qty_to_invoice', 0) for line in po_lines)
            if total_qty_to_invoice == 0 and po['state'] == 'purchase':
                problematic_count += 1
        
        print("BEFORE FIX:")
        print("  - Sale Orders to process: %d" % so_count)
        print("  - Purchase Orders to process: %d" % po_count)
        print("  - Recent Purchase Orders: %d" % len(recent_pos))
        print("  - Problematic Purchase Orders: %d" % problematic_count)
        
        return {
            'so_count': so_count,
            'po_count': po_count,
            'problematic_count': problematic_count,
            'recent_count': len(recent_pos)
        }
        
    except Exception as e:
        print("ERROR in analysis: %s" % str(e))
        return {'so_count': 0, 'po_count': 0, 'problematic_count': 0, 'recent_count': 0}

def fix_sale_orders():
    """Fix Sale Order invoice status"""
    try:
        print("\n=== FIXING SALE ORDERS ===")
        
        so_domain = [('state', '!=', 'done')]
        so_ids = models.execute_kw(db, uid, password,
            "sale.order", "search",
            [so_domain]
        )
        
        if not so_ids:
            print("No Sale Orders found.")
            return 0, 0
        
        print("Found %d Sale Orders to process" % len(so_ids))
        
        success_count = 0
        error_count = 0
        
        for so_id in so_ids:
            try:
                models.execute_kw(db, uid, password,
                    "sale.order", "write",
                    [[so_id], {}]
                )
                success_count += 1
                
                if success_count % 50 == 0:
                    print("Processed %d Sale Orders..." % success_count)
                    
            except Exception as e:
                print("Error processing SO ID %d: %s" % (so_id, str(e)))
                error_count += 1
        
        print("SALE ORDER RESULTS:")
        print("  Success: %d" % success_count)
        print("  Errors: %d" % error_count)
        
        return success_count, error_count
        
    except Exception as e:
        print("ERROR in Sale Order fix: %s" % str(e))
        return 0, 0

def fix_purchase_orders():
    """Fix Purchase Order invoice status"""
    try:
        print("\n=== FIXING PURCHASE ORDERS ===")
        
        po_domain = [('state', '!=', 'done')]
        po_ids = models.execute_kw(db, uid, password,
            "purchase.order", "search",
            [po_domain]
        )
        
        if not po_ids:
            print("No Purchase Orders found.")
            return 0, 0
        
        print("Found %d Purchase Orders to process" % len(po_ids))
        
        success_count = 0
        error_count = 0
        
        for po_id in po_ids:
            try:
                models.execute_kw(db, uid, password,
                    "purchase.order", "write",
                    [[po_id], {}]
                )
                success_count += 1
                
                if success_count % 50 == 0:
                    print("Processed %d Purchase Orders..." % success_count)
                    
            except Exception as e:
                print("Error processing PO ID %d: %s" % (po_id, str(e)))
                error_count += 1
        
        print("PURCHASE ORDER RESULTS:")
        print("  Success: %d" % success_count)
        print("  Errors: %d" % error_count)
        
        return success_count, error_count
        
    except Exception as e:
        print("ERROR in Purchase Order fix: %s" % str(e))
        return 0, 0

def analyze_after():
    """Analyze status after fix"""
    try:
        print("\n=== ANALYZING AFTER FIX ===")
        
        recent_po_domain = [
            ('state', 'in', ['purchase', 'done']),
            ('create_date', '>=', '2025-09-30')
        ]
        
        recent_pos = models.execute_kw(db, uid, password,
            "purchase.order", "search_read",
            [recent_po_domain],
            {'fields': ['id', 'name', 'state']}
        )
        
        fixed_count = 0
        still_problematic = 0
        
        for po in recent_pos:
            po_lines = models.execute_kw(db, uid, password,
                "purchase.order.line", "search_read",
                [[('order_id', '=', po['id'])]],
                {'fields': ['qty_to_invoice']}
            )
            
            total_qty_to_invoice = sum(line.get('qty_to_invoice', 0) for line in po_lines)
            if total_qty_to_invoice > 0:
                fixed_count += 1
            elif po['state'] == 'purchase':
                still_problematic += 1
        
        print("AFTER FIX:")
        print("  - Total checked: %d" % len(recent_pos))
        print("  - Fixed: %d" % fixed_count)
        print("  - Still problematic: %d" % still_problematic)
        
        return {
            'fixed_count': fixed_count,
            'still_problematic': still_problematic,
            'total_checked': len(recent_pos)
        }
        
    except Exception as e:
        print("ERROR in after analysis: %s" % str(e))
        return {'fixed_count': 0, 'still_problematic': 0, 'total_checked': 0}

def main():
    """Main function"""
    start_time = time.time()
    print("==========================================")
    print("FIX INVOICE STATUS SCRIPT")
    print("==========================================")
    print("Start time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Database:", db)
    print("User ID:", uid)
    print("Purpose: Fix invoice creation errors")
    print()
    
    try:
        # Step 1: Analyze before
        before_status = analyze_before()
        
        # Auto-confirm
        auto_confirm = os.environ.get('AUTO_CONFIRM', '').lower()
        if auto_confirm != 'y':
            confirm = input("Continue? (y/n): ").lower().strip()
            if confirm != 'y':
                print("Operation cancelled.")
                return
        
        # Step 2: Fix Sale Orders
        so_success, so_errors = fix_sale_orders()
        
        # Step 3: Fix Purchase Orders
        po_success, po_errors = fix_purchase_orders()
        
        # Step 4: Analyze after
        after_status = analyze_after()
        
        # Step 5: Comparison
        print("\n=== COMPARISON BEFORE/AFTER ===")
        print("BEFORE:")
        print("  - Sale Orders: %d" % before_status['so_count'])
        print("  - Purchase Orders: %d" % before_status['po_count'])
        print("  - Problematic POs: %d" % before_status['problematic_count'])
        print()
        print("AFTER:")
        print("  - Sale Orders processed: %d (errors: %d)" % (so_success, so_errors))
        print("  - Purchase Orders processed: %d (errors: %d)" % (po_success, po_errors))
        print("  - POs fixed: %d" % after_status['fixed_count'])
        print("  - POs still problematic: %d" % after_status['still_problematic'])
        print()
        
        total_success = so_success + po_success
        total_errors = so_errors + po_errors
        
        print("FINAL RESULTS:")
        print("  - Total success: %d" % total_success)
        print("  - Total errors: %d" % total_errors)
        
        if total_errors == 0 and after_status['still_problematic'] == 0:
            print("  - Status: SUCCESS - All issues fixed!")
        elif total_errors == 0:
            print("  - Status: PARTIAL SUCCESS - Most issues fixed")
        else:
            print("  - Status: WARNING - Some errors occurred")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n==========================================")
        print("COMPLETED")
        print("==========================================")
        print("End time:", time.strftime("%Y-%m-%d %H:%M:%S"))
        print("Processing time: %.2f seconds" % duration)
        
    except Exception as e:
        print("FATAL ERROR: %s" % str(e))
        __logger.error("Script error: %s" % str(e))

if __name__ == '__main__':
    main()
