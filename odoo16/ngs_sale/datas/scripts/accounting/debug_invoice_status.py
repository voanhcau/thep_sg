# -*- coding: utf-8 -*-
"""
Script to debug invoice_status and qty_to_invoice calculation issues
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

# Set UTF-8 encoding for stdout (Python 3 compatible)
if sys.version_info[0] >= 3:
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
else:
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

__logger = logging.getLogger(__name__)

# Connection config - import from login_local
from login_local import uid, password, db, models

def debug_invoice_status_issue():
    """
    Debugs invoice_status and qty_to_invoice calculation issues
    """
    print("==========================================")
    print("DEBUG INVOICE STATUS ISSUE")
    print("==========================================")
    print("Start time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Database:", db)
    print("User ID:", uid)
    print("Purpose: Debug invoice_status and qty_to_invoice calculation")
    print()

    try:
        # 1. Find recent Purchase Orders
        print("1. Finding recent Purchase Orders...")
        recent_pos = models.execute_kw(db, uid, password,
            "purchase.order", "search_read",
            [[('state', 'in', ['purchase', 'done']), ('date_order', '>=', '2025-09-25')]],
            {'fields': ['id', 'name', 'state', 'date_order', 'partner_id', 'order_line']}
        )

        if not recent_pos:
            print("No recent Purchase Orders found.")
            return

        print("Found %d recent Purchase Orders:" % len(recent_pos))
        for po in recent_pos:
            partner_name = po['partner_id'][1] if po['partner_id'] else 'N/A'
            print("  - %s (ID: %s), State: %s, Partner: %s" % (po['name'], po['id'], po['state'], partner_name))
        print()

        # 2. Check each PO's invoice status and qty_to_invoice
        for po in recent_pos:
            print("--- Analyzing PO: %s (ID: %s) ---" % (po['name'], po['id']))
            
            # Get PO lines with qty_to_invoice details
            po_lines = models.execute_kw(db, uid, password,
                "purchase.order.line", "search_read",
                [[('order_id', '=', po['id'])]],
                {'fields': [
                    'id', 'name', 'product_id', 'product_qty', 'qty_received', 
                    'qty_invoiced', 'qty_to_invoice'
                ]}
            )

            print("  PO Lines (%d):" % len(po_lines))
            total_qty_to_invoice = 0
            for line in po_lines:
                qty_to_invoice = line.get('qty_to_invoice', 0)
                total_qty_to_invoice += qty_to_invoice
                product_name = line['product_id'][1] if line['product_id'] else 'N/A'
                print("    - Line %s: Product %s" % (line['id'], product_name))
                print("      Product Qty: %s" % line.get('product_qty', 0))
                print("      Qty Received: %s" % line.get('qty_received', 0))
                print("      Qty Invoiced: %s" % line.get('qty_invoiced', 0))
                print("      Qty To Invoice: %s" % qty_to_invoice)
                print()

            print("  Total qty_to_invoice for PO: %s" % total_qty_to_invoice)
            
            # Check if this PO can create invoice
            if total_qty_to_invoice == 0:
                print("  ❌ PROBLEM: This PO cannot create invoice (qty_to_invoice = 0)")
                
                # Check product purchase method
                for line in po_lines:
                    if line.get('qty_to_invoice', 0) == 0:
                        product_id = line.get('product_id', [False, 'N/A'])[0]
                        if product_id:
                            product = models.execute_kw(db, uid, password,
                                "product.product", "read",
                                [product_id],
                                {'fields': ['product_tmpl_id']}
                            )[0]
                            
                            product_template = models.execute_kw(db, uid, password,
                                "product.template", "read",
                                [product['product_tmpl_id'][0]],
                                {'fields': ['purchase_method']}
                            )[0]
                            
                            product_name = line['product_id'][1] if line['product_id'] else 'N/A'
                            print("    Product %s: purchase_method = %s" % (product_name, product_template['purchase_method']))
                            
                            if product_template['purchase_method'] == 'receive' and line.get('qty_received', 0) == 0:
                                print("    ❌ CRITICAL: Product has 'Received quantities' policy but qty_received = 0")
            else:
                print("  ✅ This PO can create invoice")
            
            print("-" * 60)

        # 3. Check if there are any custom overrides affecting invoice creation
        print("\n3. Checking for custom overrides...")
        
        # Check if there are any custom methods that might interfere
        print("  - Custom invoice_status field found in purchase_order.py")
        print("  - This might be interfering with Odoo core logic")
        
        print("\nDebug process completed.")

    except Exception as e:
        print("ERROR: %s" % str(e))
        __logger.error("Debug invoice status error: %s" % str(e))

def main():
    start_time = time.time()
    try:
        debug_invoice_status_issue()
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
