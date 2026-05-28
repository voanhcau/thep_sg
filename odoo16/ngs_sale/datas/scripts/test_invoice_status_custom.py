#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test cho logic invoice_status_custom mới

Test các trường hợp:
1. Đơn hàng chưa có hóa đơn
2. Đơn hàng có hóa đơn nhưng chưa vào sổ
3. Đơn hàng có hóa đơn đã vào sổ nhưng chưa thanh toán
4. Đơn hàng đã thanh toán một phần
5. Đơn hàng đã thanh toán đầy đủ
6. Đơn hàng đã hủy thanh toán
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, '/Users/brucenguyen/Source/16')

import odoo
from odoo import api, fields, models

def test_invoice_status_custom():
    """Test logic invoice_status_custom"""
    
    # Initialize Odoo
    odoo.cli.server.main()
    
    # Get the environment
    env = api.Environment(odoo.registry('nsgerp'), 1, {})
    
    print("=== TESTING INVOICE_STATUS_CUSTOM LOGIC ===")
    
    # Test Sale Orders
    print("\n1. Testing Sale Orders:")
    sale_orders = env['sale.order'].search([('state', 'in', ['sale', 'done'])], limit=5)
    
    for order in sale_orders:
        print(f"\nSale Order: {order.name}")
        print(f"  - State: {order.state}")
        print(f"  - Invoice Count: {len(order.invoice_ids)}")
        
        if order.invoice_ids:
            for inv in order.invoice_ids:
                print(f"    Invoice: {inv.name}, State: {inv.state}, Payment State: {inv.payment_state}")
        
        print(f"  - invoice_status_custom: {order.invoice_status_custom}")
        print(f"  - invoice_state: {order.invoice_state}")
    
    # Test Purchase Orders
    print("\n2. Testing Purchase Orders:")
    purchase_orders = env['purchase.order'].search([('state', 'in', ['purchase', 'done'])], limit=5)
    
    for order in purchase_orders:
        print(f"\nPurchase Order: {order.name}")
        print(f"  - State: {order.state}")
        print(f"  - Invoice Count: {len(order.invoice_ids)}")
        
        if order.invoice_ids:
            for inv in order.invoice_ids:
                print(f"    Invoice: {inv.name}, State: {inv.state}, Payment State: {inv.payment_state}")
        
        print(f"  - invoice_status_custom: {order.invoice_status_custom}")
    
    print("\n=== TEST COMPLETED ===")

if __name__ == '__main__':
    test_invoice_status_custom()
