# -*- coding: utf-8 -*-
"""
Script to fix Purchase Method for products causing invoice creation error
Error: "Không có dòng nào có thể lập hóa đơn. Nếu một sản phẩm có chính sách kiểm soát dựa trên số lượng đã nhận, vui lòng đảm bảo rằng đã nhận hàng"

This script will:
1. Find products with purchase_method = 'receive' (Received quantities)
2. Check if they have qty_received = 0 in purchase orders
3. Either change purchase_method to 'purchase' or ensure qty_received > 0
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

# Connection config - import from login_local
from login_local import uid, password, db, models

def fix_purchase_method_products():
    """Fix Purchase Method for products causing invoice creation error"""
    print("==========================================")
    print("FIX PURCHASE METHOD PRODUCTS")
    print("==========================================")
    print("Database:", db)
    print("User ID:", uid)
    print("Time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    try:
        # Find products with purchase_method = 'receive' (Received quantities)
        print("Finding products with purchase_method = 'receive'...")
        products = models.execute_kw(db, uid, password, 
            "product.product", "search_read",
            [[('purchase_method', '=', 'receive')]],
            {'fields': ['id', 'name', 'default_code', 'purchase_method']}
        )
        
        if not products:
            print("No products found with purchase_method = 'receive'!")
            return
        
        print("Found %d products with purchase_method = 'receive'" % len(products))
        print()
        
        # Show first 10 products
        print("PRODUCTS WITH PURCHASE_METHOD = 'RECEIVE' (first 10):")
        print("-" * 80)
        print("%-8s %-30s %-20s %-15s" % ("ID", "Name", "Default Code", "Purchase Method"))
        print("-" * 80)
        
        for i, product in enumerate(products[:10]):
            print("%-8s %-30s %-20s %-15s" % (
                product['id'],
                product.get('name', '')[:29],
                product.get('default_code', 'N/A')[:19],
                product.get('purchase_method', 'N/A')
            ))
        
        if len(products) > 10:
            print("... and %d other products" % (len(products) - 10))
        
        print("-" * 80)
        print()
        
        # Check purchase orders with these products
        print("Checking purchase orders with these products...")
        product_ids = [p['id'] for p in products]
        
        # Find purchase order lines with these products
        po_lines = models.execute_kw(db, uid, password, 
            "purchase.order.line", "search_read",
            [[('product_id', 'in', product_ids)]],
            {'fields': ['id', 'product_id', 'order_id', 'product_qty', 'qty_received', 'qty_invoiced', 'qty_to_invoice']}
        )
        
        if not po_lines:
            print("No purchase order lines found with these products!")
            return
        
        print("Found %d purchase order lines with these products" % len(po_lines))
        print()
        
        # Show first 10 purchase order lines
        print("PURCHASE ORDER LINES (first 10):")
        print("-" * 100)
        print("%-8s %-30s %-15s %-10s %-10s %-10s %-10s" % (
            "ID", "Product", "PO", "Qty", "Received", "Invoiced", "To Invoice"
        ))
        print("-" * 100)
        
        for i, line in enumerate(po_lines[:10]):
            product_name = line.get('product_id', [False, 'N/A'])[1] if line.get('product_id') else 'N/A'
            po_name = line.get('order_id', [False, 'N/A'])[1] if line.get('order_id') else 'N/A'
            
            print("%-8s %-30s %-15s %-10.2f %-10.2f %-10.2f %-10.2f" % (
                line['id'],
                product_name[:29],
                po_name[:14],
                line.get('product_qty', 0),
                line.get('qty_received', 0),
                line.get('qty_invoiced', 0),
                line.get('qty_to_invoice', 0)
            ))
        
        if len(po_lines) > 10:
            print("... and %d other lines" % (len(po_lines) - 10))
        
        print("-" * 100)
        print()
        
        # Find problematic lines (qty_received = 0, qty_to_invoice = 0)
        problematic_lines = []
        for line in po_lines:
            if line.get('qty_received', 0) == 0 and line.get('qty_to_invoice', 0) == 0:
                problematic_lines.append(line)
        
        print("PROBLEMATIC LINES (qty_received = 0, qty_to_invoice = 0):")
        print("Found %d problematic lines" % len(problematic_lines))
        print()
        
        if problematic_lines:
            print("PROBLEMATIC LINES DETAILS:")
            print("-" * 100)
            print("%-8s %-30s %-15s %-10s %-10s %-10s %-10s" % (
                "ID", "Product", "PO", "Qty", "Received", "Invoiced", "To Invoice"
            ))
            print("-" * 100)
            
            for line in problematic_lines:
                product_name = line.get('product_id', [False, 'N/A'])[1] if line.get('product_id') else 'N/A'
                po_name = line.get('order_id', [False, 'N/A'])[1] if line.get('order_id') else 'N/A'
                
                print("%-8s %-30s %-15s %-10.2f %-10.2f %-10.2f %-10.2f" % (
                    line['id'],
                    product_name[:29],
                    po_name[:14],
                    line.get('product_qty', 0),
                    line.get('qty_received', 0),
                    line.get('qty_invoiced', 0),
                    line.get('qty_to_invoice', 0)
                ))
            
            print("-" * 100)
            print()
            
            # Show options to fix
            print("OPTIONS TO FIX:")
            print("1. Change purchase_method from 'receive' to 'purchase' for all products")
            print("2. Set qty_received = product_qty for problematic lines")
            print("3. Show more details about specific products")
            print("4. Exit without fixing")
            print()
            
            # Allow non-interactive confirmation via AUTO_CONFIRM environment variable
            auto_confirm = os.environ.get('AUTO_CONFIRM', '').lower()
            if auto_confirm == 'y':
                choice = '1'  # Default to option 1
            else:
                choice = input("Choose option (1-4): ").strip()
            
            if choice == '1':
                print("Changing purchase_method from 'receive' to 'purchase'...")
                success_count = 0
                error_count = 0
                
                for product in products:
                    try:
                        models.execute_kw(db, uid, password, 
                            "product.product", "write",
                            [product['id'], {'purchase_method': 'purchase'}])
                        print("  ✅ Product %s: Changed to 'purchase'" % product.get('name', 'N/A'))
                        success_count += 1
                    except Exception as e:
                        print("  ❌ Product %s: Error - %s" % (product.get('name', 'N/A'), str(e)))
                        error_count += 1
                
                print("\nRESULTS:")
                print("  Success:", success_count)
                print("  Errors:", error_count)
                print("  Total:", len(products))
                
            elif choice == '2':
                print("Setting qty_received = product_qty for problematic lines...")
                success_count = 0
                error_count = 0
                
                for line in problematic_lines:
                    try:
                        models.execute_kw(db, uid, password, 
                            "purchase.order.line", "write",
                            [line['id'], {'qty_received': line.get('product_qty', 0)}])
                        print("  ✅ Line %s: Set qty_received = %.2f" % (line['id'], line.get('product_qty', 0)))
                        success_count += 1
                    except Exception as e:
                        print("  ❌ Line %s: Error - %s" % (line['id'], str(e)))
                        error_count += 1
                
                print("\nRESULTS:")
                print("  Success:", success_count)
                print("  Errors:", error_count)
                print("  Total:", len(problematic_lines))
                
            elif choice == '3':
                print("Showing detailed product information...")
                for product in products[:5]:  # Show first 5
                    print("\nProduct: %s (ID: %s)" % (product.get('name', 'N/A'), product['id']))
                    print("  Default Code: %s" % product.get('default_code', 'N/A'))
                    print("  Purchase Method: %s" % product.get('purchase_method', 'N/A'))
                
            else:
                print("Exiting without fixing...")
                return
        
        else:
            print("No problematic lines found!")
            print("All products with purchase_method = 'receive' have qty_received > 0")
        
    except Exception as e:
        print("ERROR: %s" % str(e))
        __logger.error("Fix purchase method error: %s" % str(e))

def main():
    """Main function"""
    start_time = time.time()
    print("==========================================")
    print("SCRIPT FIX PURCHASE METHOD PRODUCTS")
    print("==========================================")
    print("Start time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Database:", db)
    print("Purpose: Fix Purchase Method causing invoice creation error")
    print()
    
    try:
        fix_purchase_method_products()
        
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



