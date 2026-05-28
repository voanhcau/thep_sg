# -*- coding: utf-8 -*-
"""
Update invoice_status for Purchase Orders and Sale Orders with unexpected values

Rules:
- Purchase Orders: update when invoice_status NOT IN ('no', 'to invoice', 'invoiced')
- Sale Orders: update when invoice_status NOT IN ('upselling', 'invoiced', 'to invoice', 'no')

Actions:
- For each qualifying Purchase Order: call recompute_invoice_status
- For each qualifying Sale Order: call compute_invoice_status
"""

try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib
import time
import logging
import sys
import codecs

# Ensure UTF-8 stdout
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

__logger = logging.getLogger(__name__)

# Connection config - absolute path used in this workspace
import sys
sys.path.insert(0, '/Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/login_configs')

try:
    from login_prod import uid, password, db, models
except ImportError as e:
    print("ERROR: Cannot import login_local:", str(e))
    print("Please check if the file exists at:")
    print("/Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/login_configs/login_local.py")
    sys.exit(1)


PURCHASE_ALLOWED = ['no', 'to invoice', 'invoiced']
SALE_ALLOWED = ['upselling', 'invoiced', 'to invoice', 'no']


def find_purchase_orders_to_update():
    """Return IDs of purchase orders whose invoice_status is not in allowed list."""
    domain = [('invoice_status', 'not in', PURCHASE_ALLOWED)]
    return models.execute_kw(db, uid, password, 'purchase.order', 'search', [domain])


def find_sale_orders_to_update():
    """Return IDs of sale orders whose invoice_status is not in allowed list."""
    domain = [('invoice_status', 'not in', SALE_ALLOWED)]
    return models.execute_kw(db, uid, password, 'sale.order', 'search', [domain])


def update_purchase_orders(po_ids):
    if not po_ids:
        return 0, 0
    success = 0
    errors = 0
    for po_id in po_ids:
        try:
            models.execute_kw(db, uid, password, 'purchase.order', 'recompute_invoice_status', [[po_id]])
            success += 1
            if success % 50 == 0:
                print("Processed %d Purchase Orders..." % success)
        except Exception as e:
            print("Error updating Purchase Order %d: %s" % (po_id, str(e)))
            errors += 1
    return success, errors


def update_sale_orders(so_ids):
    if not so_ids:
        return 0, 0
    success = 0
    errors = 0
    for so_id in so_ids:
        try:
            models.execute_kw(db, uid, password, 'sale.order', 'recompute_invoice_status', [[so_id]])
            success += 1
            if success % 50 == 0:
                print("Processed %d Sale Orders..." % success)
        except Exception as e:
            print("Error updating Sale Order %d: %s" % (so_id, str(e)))
            errors += 1
    return success, errors


def main():
    start_time = time.time()
    print("==========================================")
    print("UPDATE FILTERED INVOICE STATUS")
    print("==========================================")
    print("Start time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Database:", db)
    print()

    try:
        po_ids = find_purchase_orders_to_update()
        so_ids = find_sale_orders_to_update()

        print("Found %d Purchase Orders to update (unexpected invoice_status)" % len(po_ids))
        print("Found %d Sale Orders to update (unexpected invoice_status)" % len(so_ids))

        po_success, po_errors = update_purchase_orders(po_ids)
        so_success, so_errors = update_sale_orders(so_ids)

        print("\nRESULTS:")
        print("  - Purchase Orders updated: %d (errors: %d)" % (po_success, po_errors))
        print("  - Sale Orders updated: %d (errors: %d)" % (so_success, so_errors))

        duration = time.time() - start_time
        print("\n==========================================")
        print("COMPLETED")
        print("==========================================")
        print("End time:", time.strftime("%Y-%m-%d %H:%M:%S"))
        print("Processing time: %.2f seconds" % duration)
    except Exception as e:
        print("FATAL ERROR:", str(e))
        __logger.error("Script error: %s" % str(e))


if __name__ == '__main__':
    main()


