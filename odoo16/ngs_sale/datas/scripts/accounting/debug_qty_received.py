# -*- coding: utf-8 -*-
"""
Script to debug why qty_received = 0 in Purchase Orders
This script will investigate the root cause of qty_received = 0
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

def debug_qty_received():
    """Debug why qty_received = 0 in Purchase Orders"""
    print("==========================================")
    print("DEBUG QTY_RECEIVED = 0")
    print("==========================================")
    print("Database:", db)
    print("User ID:", uid)
    print("Time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    try:
        # Find purchase orders with qty_received = 0
        print("Finding purchase orders with qty_received = 0...")
        po_lines = models.execute_kw(db, uid, password, 
            "purchase.order.line", "search_read",
            [[('qty_received', '=', 0)]],
            {'fields': [
                'id', 'product_id', 'order_id', 'product_qty', 'qty_received', 
                'qty_invoiced', 'qty_to_invoice', 'state', 'date_planned'
            ]}
        )
        
        if not po_lines:
            print("No purchase order lines found with qty_received = 0!")
            return
        
        print("Found %d purchase order lines with qty_received = 0" % len(po_lines))
        print()
        
        # Show first 10 lines
        print("PURCHASE ORDER LINES WITH QTY_RECEIVED = 0 (first 10):")
        print("-" * 120)
        print("%-8s %-30s %-20s %-10s %-10s %-10s %-10s %-15s" % (
            "ID", "Product", "PO", "Qty", "Received", "Invoiced", "To Invoice", "State"
        ))
        print("-" * 120)
        
        for i, line in enumerate(po_lines[:10]):
            product_name = line.get('product_id', [False, 'N/A'])[1] if line.get('product_id') else 'N/A'
            po_name = line.get('order_id', [False, 'N/A'])[1] if line.get('order_id') else 'N/A'
            
            print("%-8s %-30s %-20s %-10.2f %-10.2f %-10.2f %-10.2f %-15s" % (
                line['id'],
                product_name[:29],
                po_name[:19],
                line.get('product_qty', 0),
                line.get('qty_received', 0),
                line.get('qty_invoiced', 0),
                line.get('qty_to_invoice', 0),
                line.get('state', 'N/A')
            ))
        
        if len(po_lines) > 10:
            print("... and %d other lines" % (len(po_lines) - 10))
        
        print("-" * 120)
        print()
        
        # Check purchase order states
        print("PURCHASE ORDER STATES:")
        po_states = {}
        for line in po_lines:
            po_id = line.get('order_id', [False, 'N/A'])[0] if line.get('order_id') else None
            if po_id:
                po_states[po_id] = po_states.get(po_id, 0) + 1
        
        print("Purchase Orders with qty_received = 0:")
        for po_id, count in po_states.items():
            try:
                po_info = models.execute_kw(db, uid, password, 
                    "purchase.order", "read",
                    [po_id],
                    {'fields': ['name', 'state', 'date_order', 'partner_id']})
                
                if po_info:
                    po = po_info[0]
                    print("  - %s: %s (%s) - %d lines" % (
                        po.get('name', 'N/A'),
                        po.get('state', 'N/A'),
                        po.get('date_order', 'N/A'),
                        count
                    ))
            except:
                print("  - PO ID %s: Error reading info - %d lines" % (po_id, count))
        
        print()
        
        # Check if there are stock moves for these products
        print("CHECKING STOCK MOVES...")
        product_ids = list(set([line.get('product_id', [False, 'N/A'])[0] for line in po_lines if line.get('product_id')]))
        
        if product_ids:
            stock_moves = models.execute_kw(db, uid, password, 
                "stock.move", "search_read",
                [[('product_id', 'in', product_ids)]],
                {'fields': ['id', 'product_id', 'origin', 'state', 'quantity_done', 'product_uom_qty']}
            )
            
            print("Found %d stock moves for these products" % len(stock_moves))
            
            if stock_moves:
                print("STOCK MOVES (first 10):")
                print("-" * 100)
                print("%-8s %-30s %-20s %-15s %-10s %-10s" % (
                    "ID", "Product", "Origin", "State", "Qty Done", "Qty UOM"
                ))
                print("-" * 100)
                
                for i, move in enumerate(stock_moves[:10]):
                    product_name = move.get('product_id', [False, 'N/A'])[1] if move.get('product_id') else 'N/A'
                    
                    print("%-8s %-30s %-20s %-15s %-10.2f %-10.2f" % (
                        move['id'],
                        product_name[:29],
                        move.get('origin', 'N/A')[:19],
                        move.get('state', 'N/A'),
                        move.get('quantity_done', 0),
                        move.get('product_uom_qty', 0)
                    ))
                
                if len(stock_moves) > 10:
                    print("... and %d other moves" % (len(stock_moves) - 10))
                
                print("-" * 100)
                print()
                
                # Check stock move states
                move_states = {}
                for move in stock_moves:
                    state = move.get('state', 'N/A')
                    move_states[state] = move_states.get(state, 0) + 1
                
                print("STOCK MOVE STATES:")
                for state, count in move_states.items():
                    print("  - %s: %d moves" % (state, count))
                
                print()
                
                # Check if stock moves are linked to purchase orders
                print("CHECKING STOCK MOVES LINKED TO PURCHASE ORDERS...")
                po_origins = [line.get('order_id', [False, 'N/A'])[1] for line in po_lines if line.get('order_id')]
                
                linked_moves = []
                for move in stock_moves:
                    origin = move.get('origin', '')
                    if any(po_name in origin for po_name in po_origins):
                        linked_moves.append(move)
                
                print("Found %d stock moves linked to purchase orders" % len(linked_moves))
                
                if linked_moves:
                    print("LINKED STOCK MOVES (first 10):")
                    print("-" * 100)
                    print("%-8s %-30s %-20s %-15s %-10s %-10s" % (
                        "ID", "Product", "Origin", "State", "Qty Done", "Qty UOM"
                    ))
                    print("-" * 100)
                    
                    for i, move in enumerate(linked_moves[:10]):
                        product_name = move.get('product_id', [False, 'N/A'])[1] if move.get('product_id') else 'N/A'
                        
                        print("%-8s %-30s %-20s %-15s %-10.2f %-10.2f" % (
                            move['id'],
                            product_name[:29],
                            move.get('origin', 'N/A')[:19],
                            move.get('state', 'N/A'),
                            move.get('quantity_done', 0),
                            move.get('product_uom_qty', 0)
                        ))
                    
                    if len(linked_moves) > 10:
                        print("... and %d other linked moves" % (len(linked_moves) - 10))
                    
                    print("-" * 100)
                    print()
                    
                    # Check if stock moves are done
                    done_moves = [m for m in linked_moves if m.get('state') == 'done']
                    print("DONE STOCK MOVES: %d" % len(done_moves))
                    
                    if done_moves:
                        print("DONE STOCK MOVES (first 10):")
                        print("-" * 100)
                        print("%-8s %-30s %-20s %-15s %-10s %-10s" % (
                            "ID", "Product", "Origin", "State", "Qty Done", "Qty UOM"
                        ))
                        print("-" * 100)
                        
                        for i, move in enumerate(done_moves[:10]):
                            product_name = move.get('product_id', [False, 'N/A'])[1] if move.get('product_id') else 'N/A'
                            
                            print("%-8s %-30s %-20s %-15s %-10.2f %-10.2f" % (
                                move['id'],
                                product_name[:29],
                                move.get('origin', 'N/A')[:19],
                                move.get('state', 'N/A'),
                                move.get('quantity_done', 0),
                                move.get('product_uom_qty', 0)
                            ))
                        
                        if len(done_moves) > 10:
                            print("... and %d other done moves" % (len(done_moves) - 10))
                        
                        print("-" * 100)
                        print()
                        
                        # Check if qty_received should be updated
                        print("ANALYZING QTY_RECEIVED UPDATE...")
                        for move in done_moves[:5]:  # Check first 5
                            product_id = move.get('product_id', [False, 'N/A'])[0] if move.get('product_id') else None
                            origin = move.get('origin', '')
                            quantity_done = move.get('quantity_done', 0)
                            
                            if product_id and origin:
                                print("Move %s: Product %s, Origin %s, Qty Done %.2f" % (
                                    move['id'], product_id, origin, quantity_done
                                ))
                                
                                # Find corresponding purchase order line
                                try:
                                    po_line = models.execute_kw(db, uid, password, 
                                        "purchase.order.line", "search_read",
                                        [[('product_id', '=', product_id), ('order_id.name', '=', origin)]],
                                        {'fields': ['id', 'product_qty', 'qty_received', 'qty_invoiced']})
                                    
                                    if po_line:
                                        line = po_line[0]
                                        print("  -> PO Line %s: Qty %.2f, Received %.2f, Invoiced %.2f" % (
                                            line['id'], line.get('product_qty', 0), 
                                            line.get('qty_received', 0), line.get('qty_invoiced', 0)
                                        ))
                                        
                                        if line.get('qty_received', 0) == 0 and quantity_done > 0:
                                            print("  -> ⚠️  MISMATCH: Stock move done but qty_received = 0!")
                                    else:
                                        print("  -> No corresponding PO line found")
                                        
                                except Exception as e:
                                    print("  -> Error finding PO line: %s" % str(e))
                                
                                print()
        
        else:
            print("No product IDs found to check stock moves")
        
        print("==========================================")
        print("ANALYSIS COMPLETE")
        print("==========================================")
        print("Possible causes of qty_received = 0:")
        print("1. Stock moves not created for purchase orders")
        print("2. Stock moves created but not done")
        print("3. Stock moves done but qty_received not updated")
        print("4. Purchase orders not confirmed")
        print("5. Products have purchase_method = 'receive' but no stock moves")
        print("==========================================")
        
    except Exception as e:
        print("ERROR: %s" % str(e))
        __logger.error("Debug qty_received error: %s" % str(e))

def main():
    """Main function"""
    start_time = time.time()
    print("==========================================")
    print("SCRIPT DEBUG QTY_RECEIVED = 0")
    print("==========================================")
    print("Start time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Database:", db)
    print("Purpose: Debug why qty_received = 0 in Purchase Orders")
    print()
    
    try:
        debug_qty_received()
        
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
