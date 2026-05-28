#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script để kiểm tra fix cho order_received_date field trên vendor bills
"""

import xmlrpc.client
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
_logger = logging.getLogger(__name__)

def test_order_received_date_fix():
    """
    Test fix cho order_received_date field
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
        
        _logger.info("=== TESTING ORDER_RECEIVED_DATE FIX ===")
        
        # Test 1: Tìm vendor bills thiếu order_received_date
        _logger.info("1. Searching for vendor bills missing order_received_date...")
        vendor_bills = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
            [('move_type', '=', 'in_invoice'), ('state', '=', 'posted'), ('order_received_date', '=', False)]
        ], {'fields': ['id', 'name', 'partner_id', 'invoice_origin', 'order_received_date'], 'limit': 10})
        
        _logger.info(f"Found {len(vendor_bills)} vendor bills missing order_received_date")
        
        if not vendor_bills:
            _logger.info("No vendor bills missing order_received_date found!")
            return True
        
        # Test 2: Recompute order_received_date cho vendor bills
        _logger.info("2. Recomputing order_received_date for vendor bills...")
        for bill in vendor_bills:
            _logger.info(f"Processing vendor bill: {bill['name']} (ID: {bill['id']})")
            _logger.info(f"  Partner: {bill['partner_id'][1] if bill['partner_id'] else 'N/A'}")
            _logger.info(f"  Origin: {bill['invoice_origin']}")
            _logger.info(f"  Current order_received_date: {bill['order_received_date']}")
            
            # Gọi method recompute
            result = models.execute_kw(db, uid, password, 'account.move', 'recompute_order_received_date', [[bill['id']]])
            
            # Kiểm tra kết quả sau khi recompute
            updated_bill = models.execute_kw(db, uid, password, 'account.move', 'read', [[bill['id']]], 
                                           {'fields': ['order_received_date']})
            
            new_received_date = updated_bill[0]['order_received_date']
            _logger.info(f"  New order_received_date: {new_received_date}")
            
            if new_received_date:
                _logger.info(f"✅ SUCCESS: Fixed order_received_date for {bill['name']}")
            else:
                _logger.info(f"❌ NO CHANGE: Still no order_received_date for {bill['name']}")
        
        # Test 3: Kiểm tra customer invoices cũng hoạt động bình thường
        _logger.info("3. Testing customer invoices...")
        customer_invoices = models.execute_kw(db, uid, password, 'account.move', 'search_read', [
            [('move_type', '=', 'out_invoice'), ('state', '=', 'posted')]
        ], {'fields': ['id', 'name', 'order_received_date'], 'limit': 5})
        
        _logger.info(f"Found {len(customer_invoices)} customer invoices")
        for invoice in customer_invoices:
            _logger.info(f"Customer invoice {invoice['name']}: order_received_date = {invoice['order_received_date']}")
        
        _logger.info("=== TEST COMPLETED ===")
        return True
        
    except Exception as e:
        _logger.error(f"Error during test: {str(e)}")
        return False

if __name__ == "__main__":
    test_order_received_date_fix()
