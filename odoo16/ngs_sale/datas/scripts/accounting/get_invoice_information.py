# coding=utf-8
import xmlrpclib
import logging
from login_prod import uid, password, db, models

__logger = logging.getLogger(__name__)

def process_sale_orders():
    # Get all sale orders
    sale_orders = models.execute_kw(db, uid, password, 
        "sale.order", "search_read",
        [[]],  # Empty domain to get all sale orders
        {'fields': ['id', 'name', 'state']}
    )

    if not sale_orders:
        print("No sale orders found")
        return

    print "Found %s sale orders" % len(sale_orders)

    # Process each sale order
    for order in sale_orders:
        order_id = order['id']
        order_name = order['name']
        order_state = order['state']
        
        try:
            # Call the _get_invoice_information function
            invoice_info = models.execute_kw(db, uid, password, 
                "sale.order", "get_invoice_information",
                [order_id]
            )
            
            print "Successfully retrieved invoice information for order %s" % order_name
            print "Invoice information: %s" % invoice_info
                
        except Exception as e:
            print "Error processing order %s: %s" % (order_name, str(e))

if __name__ == '__main__':
    process_sale_orders() 