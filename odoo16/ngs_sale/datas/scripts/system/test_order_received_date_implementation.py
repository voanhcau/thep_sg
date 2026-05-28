#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script để kiểm tra implementation đã tối ưu của order_received_date field

Implementation mới:
- Customer Invoice: Lấy received_date từ Sale Order
- Vendor Bill: Lấy date_planned từ Purchase Order (ưu tiên PO.date_planned > PO Line.date_planned > SO.received_date)
- Code đã được tối ưu với helper methods và comment rõ ràng
"""

import xmlrpc.client
import logging
from datetime import datetime

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

def test_order_received_date_implementation():
    """
    Test implementation mới của order_received_date field
    """
    try:
        # Import login credentials
        from login_local import url, db, username, password
        
        # Kết nối XML-RPC
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            _logger.error("Authentication failed!")
            return False
            
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
        
        _logger.info("=== TESTING ORDER_RECEIVED_DATE IMPLEMENTATION ===")
        
        # Test 1: Customer Invoices - should get received_date from Sale Order
        _logger.info("1. Testing Customer Invoices (should get SO.received_date)...")
        customer_invoices = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
            [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
        ], {'fields': ['id', 'name', 'partner_id', 'invoice_origin', 'order_received_date'], 'limit': 5})
        
        _logger.info(f"Found {len(customer_invoices)} customer invoices")
        for invoice in customer_invoices:
            _logger.info(f"Customer Invoice: {invoice['name']}")
            _logger.info(f"  Partner: {invoice['partner_id'][1] if invoice['partner_id'] else 'N/A'}")
            _logger.info(f"  Origin: {invoice['invoice_origin']}")
            _logger.info(f"  Current order_received_date: {invoice['order_received_date']}")
            
            # Recompute để test
            models.execute_kw(db, uid, password, 'account.move', 'recompute_order_received_date', [[invoice['id']]])
            
            # Kiểm tra kết quả
            updated_invoice = models.execute_kw(db, uid, password, 'account.move', 'read', [[invoice['id']]], 
                                              {'fields': ['order_received_date']})
            new_received_date = updated_invoice[0]['order_received_date']
            _logger.info(f"  After recompute: {new_received_date}")
            _logger.info("---")
        
        # Test 2: Vendor Bills - should get date_planned from Purchase Order
        _logger.info("2. Testing Vendor Bills (should get PO.date_planned)...")
        vendor_bills = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
            [('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]
        ], {'fields': ['id', 'name', 'partner_id', 'invoice_origin', 'order_received_date'], 'limit': 5})
        
        _logger.info(f"Found {len(vendor_bills)} vendor bills")
        for bill in vendor_bills:
            _logger.info(f"Vendor Bill: {bill['name']}")
            _logger.info(f"  Partner: {bill['partner_id'][1] if bill['partner_id'] else 'N/A'}")
            _logger.info(f"  Origin: {bill['invoice_origin']}")
            _logger.info(f"  Current order_received_date: {bill['order_received_date']}")
            
            # Recompute để test
            models.execute_kw(db, uid, password, 'account.move', 'recompute_order_received_date', [[bill['id']]])
            
            # Kiểm tra kết quả
            updated_bill = models.execute_kw(db, uid, password, 'account.move', 'read', [[bill['id']]], 
                                           {'fields': ['order_received_date']})
            new_received_date = updated_bill[0]['order_received_date']
            _logger.info(f"  After recompute: {new_received_date}")
            _logger.info("---")
        
        # Test 3: Kiểm tra Purchase Orders có date_planned
        _logger.info("3. Checking Purchase Orders with date_planned...")
        purchase_orders = models.execute_kw(db, uid, password, 'purchase.order', 'search_read', [
            [('state', '=', 'purchase')]
        ], {'fields': ['id', 'name', 'partner_id', 'date_planned'], 'limit': 5})
        
        _logger.info(f"Found {len(purchase_orders)} purchase orders")
        for po in purchase_orders:
            _logger.info(f"Purchase Order: {po['name']}")
            _logger.info(f"  Partner: {po['partner_id'][1] if po['partner_id'] else 'N/A'}")
            _logger.info(f"  date_planned: {po.get('date_planned', 'N/A')}")
            _logger.info("---")
        
        # Test 4: Kiểm tra Sale Orders có received_date
        _logger.info("4. Checking Sale Orders with received_date...")
        sale_orders = models.execute_kw(db, uid, password, 'sale.order', 'search_read', [
            [('state', '=', 'sale')]
        ], {'fields': ['id', 'name', 'partner_id', 'received_date'], 'limit': 5})
        
        _logger.info(f"Found {len(sale_orders)} sale orders")
        for so in sale_orders:
            _logger.info(f"Sale Order: {so['name']}")
            _logger.info(f"  Partner: {so['partner_id'][1] if so['partner_id'] else 'N/A'}")
            _logger.info(f"  received_date: {so.get('received_date', 'N/A')}")
            _logger.info("---")
        
        # Test 5: Thống kê tổng quan
        _logger.info("5. Overall Statistics...")
        
        # Customer invoices với order_received_date
        customer_with_date = models.execute_kw(db, uid, password, 'account.move', 'search_count', [
            [('move_type', '=', 'out_invoice'), ('state', '=', 'posted'), ('order_received_date', '!=', False)]
        ])
        customer_total = models.execute_kw(db, uid, password, 'account.move', 'search_count', [
            [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
        ])
        
        # Vendor bills với order_received_date
        vendor_with_date = models.execute_kw(db, uid, password, 'account.move', 'search_count', [
            [('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('order_received_date', '!=', False)]
        ])
        vendor_total = models.execute_kw(db, uid, password, 'account.move', 'search_count', [
            [('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]
        ])
        
        _logger.info(f"Customer Invoices: {customer_with_date}/{customer_total} have order_received_date")
        _logger.info(f"Vendor Bills: {vendor_with_date}/{vendor_total} have order_received_date")
        
        _logger.info("=== TEST COMPLETED ===")
        return True
        
    except Exception as e:
        _logger.error(f"Error during test: {str(e)}")
        import traceback
        _logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    test_order_received_date_implementation()
