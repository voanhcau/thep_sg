# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from datetime import datetime, timedelta
import calendar

import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    no_output_invoice = fields.Boolean(string=u'Không xuất hoá đơn')
    commission_tool_id = fields.Many2one('sale.commission.tool', string='Phiếu hoa hồng')
    posted_date = fields.Datetime(u'Ngày thanh toán')
    tag_ids = fields.Many2many('crm.tag', 'account_move_crm_tag_rel', 'account_move_id', 'crm_tag_id', string='Thẻ')
    tags_text = fields.Char(string='Tags Text', compute='_compute_tags_text', store=True)
    tags_text = fields.Char(string='Tags Text', compute='_compute_tags_text', store=True)
    product_type = fields.Char(string='Loại sản phẩm')
    
    total_quantity = fields.Float(
        string='KL (kg)',
        compute='_compute_total_quantity',
        store=True,
        index=True,
        help='Tổng khối lượng (kg) của các sản phẩm trong hóa đơn'
    )

    order_received_date = fields.Date(
        string='Ngày nhận hàng',
        compute='_compute_order_received_date',
        store=True,
        help="""Ngày nhận hàng được tính toán dựa trên loại hóa đơn:
        • Customer Invoice: Lấy từ SO.received_date
        • Vendor Bill: Lấy từ PO.date_planned (ưu tiên PO > PO Line > SO fallback)
        
        Trường này được sử dụng để:
        - Tính toán thời hạn thanh toán (khi cấu hình payment_term_calculation = 'receipt_date')
        - Báo cáo phân tích thanh toán
        - Tính toán số ngày quá hạn thanh toán"""
    )

    invoice_date_due_custom = fields.Date(
        string='Thời hạn thanh toán',
        compute='_compute_invoice_date_due_custom',
        store=True,
        help='Ngày đến hạn được tính toán dựa trên cấu hình cách tính thời hạn thanh toán.'
    )

    actual_payment_days = fields.Float(
        string='Số ngày TT quá hạn',
        compute='_compute_actual_payment_days',
        store=True,
        digits=(16, 2),
        help='Số ngày quá hạn tính theo công thức weighted: (Ngày TT L1 - Ngày HĐ)*(số tiền TT L1/Tổng tiền) + ... - Thời hạn TT'
    )

    invoice_order_id = fields.Many2one(
        'account.move',
        string='Invoice Order',
        compute='_compute_invoice_order_id',
        store=True,
        help='Liên kết hóa đơn đối ứng giữa mua và bán theo logic đặc thù.'
    )
    transfer_cost = fields.Float(string='XLVC')
    transfer_text = fields.Text(string='Ghi chú')

    def compute_self_invoice_order(self):
        self._compute_invoice_order_id()

    def compute_invoice_order(self):
        moves = self.env['account.move'].search([
            ('state', 'in', ['posted']),
            ('move_type', 'in', ['in_invoice', 'out_invoice'])
        ])
        moves._compute_invoice_order_id()

    @api.depends('move_type', 'invoice_line_ids', 'partner_id', 'state', 'payment_state', 'ref')
    def _compute_invoice_order_id(self):
        """
        - Nếu là hóa đơn nhà cung cấp (in_invoice):
            + Lấy 1 dòng purchase line (invoice_line_ids.purchase_line_id)
            + Lấy sale_order_id từ purchase line
            + Lấy hóa đơn khách hàng (out_invoice) của sale_order_id
            + Lưu vào invoice_order_id
        - Nếu là hóa đơn khách hàng (out_invoice):
            + Lấy sale order (từ sale_line_ids.order_id)
            + Lấy 1 purchase order line có sale_order_id đó
            + Lấy purchase order từ purchase line
            + Lấy hóa đơn nhà cung cấp (in_invoice) của purchase order
            + Lưu vào invoice_order_id
        """
        for move in self:
            _logger.info(f"\n========== INVOICE ORDER ID COMPUTE START ==========")
            _logger.info(f"[INVOICE_ORDER_ID] Move Info:")
            _logger.info(f"  - ID: {move.id}")
            _logger.info(f"  - Name: {move.name}")
            _logger.info(f"  - Move Type: {move.move_type}")
            _logger.info(f"  - Partner: {move.partner_id.name if move.partner_id else 'N/A'} (ID: {move.partner_id.id if move.partner_id else 'N/A'})")
            _logger.info(f"  - State: {move.state}")
            _logger.info(f"  - Payment State: {move.payment_state}")
            _logger.info(f"  - Reference: {move.ref}")
            _logger.info(f"  - Invoice Origin: {move.invoice_origin}")
            _logger.info(f"  - Total Lines: {len(move.invoice_line_ids)}")
            _logger.info(f"  - Current invoice_order_id: {move.invoice_order_id.id if move.invoice_order_id else 'None'}")
            
            move.invoice_order_id = False
            
            if move.move_type == 'in_invoice':
                _logger.info(f"[INVOICE_ORDER_ID] Processing VENDOR BILL (in_invoice)")
                
                # Debug invoice lines
                _logger.info(f"[INVOICE_ORDER_ID] Invoice Lines Debug:")
                for idx, line in enumerate(move.invoice_line_ids):
                    _logger.info(f"  Line {idx + 1}:")
                    _logger.info(f"    - ID: {line.id}")
                    _logger.info(f"    - Product: {line.product_id.name if line.product_id else 'N/A'}")
                    _logger.info(f"    - Purchase Line: {line.purchase_line_id.id if line.purchase_line_id else 'None'}")
                    if line.purchase_line_id:
                        _logger.info(f"    - Purchase Order: {line.purchase_line_id.order_id.name if line.purchase_line_id.order_id else 'None'}")
                        _logger.info(f"    - Sale Order from PO: {line.purchase_line_id.order_id.sale_id.name if line.purchase_line_id.order_id and line.purchase_line_id.order_id.sale_id else 'None'}")
                
                # Vendor bill: link to customer invoice
                purchase_lines = move.invoice_line_ids.mapped('purchase_line_id')
                _logger.info(f"[INVOICE_ORDER_ID] Found {len(purchase_lines)} purchase lines: {[pl.id for pl in purchase_lines]}")
                
                purchase_line = purchase_lines[:1]
                _logger.info(f"[INVOICE_ORDER_ID] Using first purchase line: {purchase_line.id if purchase_line else 'None'}")
                
                if purchase_line:
                    _logger.info(f"[INVOICE_ORDER_ID] Purchase Line Details:")
                    _logger.info(f"  - Purchase Order: {purchase_line.order_id.name if purchase_line.order_id else 'None'}")
                    _logger.info(f"  - Purchase Order ID: {purchase_line.order_id.id if purchase_line.order_id else 'None'}")
                    _logger.info(f"  - Purchase Order Partner: {purchase_line.order_id.partner_id.name if purchase_line.order_id and purchase_line.order_id.partner_id else 'None'}")
                    _logger.info(f"  - Sale Order from PO: {purchase_line.order_id.sale_id.name if purchase_line.order_id and purchase_line.order_id.sale_id else 'None'}")
                    
                    if purchase_line.order_id and purchase_line.order_id.sale_id:
                        sale_order = purchase_line.order_id.sale_id
                        _logger.info(f"[INVOICE_ORDER_ID] Sale Order Details:")
                        _logger.info(f"  - Name: {sale_order.name}")
                        _logger.info(f"  - ID: {sale_order.id}")
                        _logger.info(f"  - Partner: {sale_order.partner_id.name} (ID: {sale_order.partner_id.id})")
                        _logger.info(f"  - State: {sale_order.state}")
                        
                        # Find customer invoice for this sale order - Method 1: by invoice_origin
                        _logger.info(f"[INVOICE_ORDER_ID] Searching customer invoice by invoice_origin = '{sale_order.name}'")
                        customer_invoice = self.env['account.move'].search([
                            ('move_type', '=', 'out_invoice'),
                            ('state', 'in', ['posted', 'draft']),
                            ('invoice_origin', '=', sale_order.name)
                        ], limit=1)
                        _logger.info(f"[INVOICE_ORDER_ID] Customer invoice by invoice_origin: {customer_invoice.name if customer_invoice else 'None'} (ID: {customer_invoice.id if customer_invoice else 'None'})")
                        
                        if not customer_invoice:
                            # Fallback: try by partner and sale order
                            _logger.info(f"[INVOICE_ORDER_ID] Fallback: Searching by partner_id = {sale_order.partner_id.id} and sale_order_id = {sale_order.id}")
                            customer_invoice = self.env['account.move'].search([
                                ('move_type', '=', 'out_invoice'),
                                ('state', 'in', ['posted', 'draft']),
                                ('partner_id', '=', sale_order.partner_id.id),
                                ('invoice_line_ids.sale_line_ids.order_id', '=', sale_order.id)
                            ], limit=1)
                            _logger.info(f"[INVOICE_ORDER_ID] Customer invoice by partner & sale_order: {customer_invoice.name if customer_invoice else 'None'} (ID: {customer_invoice.id if customer_invoice else 'None'})")
                        
                        if customer_invoice:
                            move.invoice_order_id = customer_invoice.id
                            _logger.info(f"[INVOICE_ORDER_ID] SUCCESS: Set invoice_order_id = {move.invoice_order_id} ({customer_invoice.name})")
                        else:
                            _logger.info(f"[INVOICE_ORDER_ID] WARNING: No customer invoice found for sale order {sale_order.name}")
                    else:
                        _logger.info(f"[INVOICE_ORDER_ID] WARNING: Purchase line has no order or order has no sale_id")
                else:
                    _logger.info(f"[INVOICE_ORDER_ID] WARNING: No purchase line found")
                
                # Fallback method if still no invoice_order_id found
                if not move.invoice_order_id:
                    _logger.info(f"[INVOICE_ORDER_ID] Fallback: Searching sale order by ref = '{move.ref}'")
                    sale_order = self.env['sale.order'].search([('name', '=', move.ref)], limit=1)
                    _logger.info(f"[INVOICE_ORDER_ID] Sale order by ref: {sale_order.name if sale_order else 'None'} (ID: {sale_order.id if sale_order else 'None'})")
                    
                    if sale_order:
                        _logger.info(f"[INVOICE_ORDER_ID] Searching customer invoice for sale order {sale_order.name}")
                        customer_invoice = self.env['account.move'].search([
                            ('move_type', '=', 'out_invoice'),
                            ('state', 'in', ['posted', 'draft']),
                            ('invoice_origin', '=', sale_order.name)
                        ], limit=1)
                        if customer_invoice:
                            move.invoice_order_id = customer_invoice.id
                            _logger.info(f"[INVOICE_ORDER_ID] FALLBACK SUCCESS: Set invoice_order_id = {move.invoice_order_id} ({customer_invoice.name})")
                        else:
                            _logger.info(f"[INVOICE_ORDER_ID] FALLBACK FAILED: No customer invoice found for sale order {sale_order.name}")
                    else:
                        _logger.info(f"[INVOICE_ORDER_ID] FALLBACK FAILED: No sale order found by ref")
                        
            elif move.move_type == 'out_invoice':
                _logger.info(f"[INVOICE_ORDER_ID] Processing CUSTOMER INVOICE (out_invoice)")
                
                # Debug move lines
                _logger.info(f"[INVOICE_ORDER_ID] Move Lines Debug (total: {len(move.line_ids)}):")
                sale_line_count = 0
                for idx, line in enumerate(move.line_ids):
                    if line.sale_line_ids:
                        sale_line_count += len(line.sale_line_ids)
                        _logger.info(f"  Line {idx + 1} (ID: {line.id}):")
                        _logger.info(f"    - Account: {line.account_id.name}")
                        _logger.info(f"    - Sale Lines: {len(line.sale_line_ids)} - {[sl.id for sl in line.sale_line_ids]}")
                        for sl in line.sale_line_ids:
                            _logger.info(f"      * Sale Line {sl.id}: Order {sl.order_id.name if sl.order_id else 'None'}")
                
                _logger.info(f"[INVOICE_ORDER_ID] Total sale lines found: {sale_line_count}")
                
                # Customer invoice: link to vendor bill
                sale_orders = move.line_ids.mapped('sale_line_ids.order_id')
                _logger.info(f"[INVOICE_ORDER_ID] Found {len(sale_orders)} sale orders: {[so.name for so in sale_orders]}")
                
                sale_order = sale_orders[:1] if sale_orders else False
                if sale_order:
                    _logger.info(f"[INVOICE_ORDER_ID] Using first sale order: {sale_order.name} (ID: {sale_order.id})")
                    _logger.info(f"[INVOICE_ORDER_ID] Sale Order Details:")
                    _logger.info(f"  - Partner: {sale_order.partner_id.name} (ID: {sale_order.partner_id.id})")
                    _logger.info(f"  - State: {sale_order.state}")
                    _logger.info(f"  - Auto Purchase Order: {sale_order.auto_purchase_order_id.name if sale_order.auto_purchase_order_id else 'None'}")
                    
                    purchase_order = sale_order.auto_purchase_order_id
                    if purchase_order:
                        _logger.info(f"[INVOICE_ORDER_ID] Purchase Order Details:")
                        _logger.info(f"  - Name: {purchase_order.name}")
                        _logger.info(f"  - ID: {purchase_order.id}")
                        _logger.info(f"  - Partner: {purchase_order.partner_id.name} (ID: {purchase_order.partner_id.id})")
                        _logger.info(f"  - State: {purchase_order.state}")
                        
                        # Find vendor bill for this purchase order - Method 1: by invoice_origin
                        _logger.info(f"[INVOICE_ORDER_ID] Searching vendor bill by invoice_origin = '{purchase_order.name}'")
                        vendor_bill = self.env['account.move'].search([
                            ('move_type', '=', 'in_invoice'),
                            ('state', 'in', ['posted', 'draft']),
                            ('invoice_origin', '=', purchase_order.name)
                        ], limit=1)
                        _logger.info(f"[INVOICE_ORDER_ID] Vendor bill by invoice_origin: {vendor_bill.name if vendor_bill else 'None'} (ID: {vendor_bill.id if vendor_bill else 'None'})")
                        
                        if not vendor_bill:
                            # Fallback: try by partner and purchase order
                            _logger.info(f"[INVOICE_ORDER_ID] Fallback: Searching by partner_id = {purchase_order.partner_id.id} and purchase_order_id = {purchase_order.id}")
                            vendor_bill = self.env['account.move'].search([
                                ('move_type', '=', 'in_invoice'),
                                ('state', 'in', ['posted', 'draft']),
                                ('partner_id', '=', purchase_order.partner_id.id),
                                ('invoice_line_ids.purchase_line_id.order_id', '=', purchase_order.id)
                            ], limit=1)
                            _logger.info(f"[INVOICE_ORDER_ID] Vendor bill by partner & purchase_order: {vendor_bill.name if vendor_bill else 'None'} (ID: {vendor_bill.id if vendor_bill else 'None'})")
                        
                        if vendor_bill:
                            move.invoice_order_id = vendor_bill.id
                            _logger.info(f"[INVOICE_ORDER_ID] SUCCESS: Set invoice_order_id = {move.invoice_order_id} ({vendor_bill.name})")
                        else:
                            _logger.info(f"[INVOICE_ORDER_ID] WARNING: No vendor bill found for purchase order {purchase_order.name}")
                    else:
                        _logger.info(f"[INVOICE_ORDER_ID] WARNING: Sale order has no auto_purchase_order_id")
                else:
                    _logger.info(f"[INVOICE_ORDER_ID] WARNING: No sale order found from move lines")
            else:
                _logger.info(f"[INVOICE_ORDER_ID] Skipping move type: {move.move_type}")
            
            _logger.info(f"[INVOICE_ORDER_ID] FINAL RESULT:")
            _logger.info(f"  - Move: {move.name} (ID: {move.id})")
            _logger.info(f"  - Type: {move.move_type}")
            _logger.info(f"  - invoice_order_id: {move.invoice_order_id.id if move.invoice_order_id else 'None'}")
            if move.invoice_order_id:
                _logger.info(f"  - Linked Invoice: {move.invoice_order_id.name}")
                _logger.info(f"  - Linked Invoice Type: {move.invoice_order_id.move_type}")
                _logger.info(f"  - Linked Invoice Partner: {move.invoice_order_id.partner_id.name}")
            _logger.info(f"========== INVOICE ORDER ID COMPUTE END ==========\n")
        store=False
    

    order_received_date = fields.Date(
        string='Ngày nhận hàng',
        compute='_compute_order_received_date',
        store=True,
        help='Ngày nhận hàng từ Đơn bán hàng liên quan.'
    )

    invoice_date_due_custom = fields.Date(
        string='Thời hạn thanh toán',
        compute='_compute_invoice_date_due_custom',
        store=True,
        help='Ngày đến hạn được tính toán dựa trên cấu hình cách tính thời hạn thanh toán.'
    )

    actual_payment_days = fields.Float(
        string='Số ngày TT quá hạn',
        compute='_compute_actual_payment_days',
        store=True,
        digits=(16, 2),
        help='Số ngày quá hạn tính theo công thức weighted: (Ngày TT L1 - Ngày HĐ)*(số tiền TT L1/Tổng tiền) + ... - Thời hạn TT'
    )

    invoice_order_id = fields.Many2one(
        'account.move',
        string='Invoice Order',
        compute='_compute_invoice_order_id',
        store=True,
        help='Liên kết hóa đơn đối ứng giữa mua và bán theo logic đặc thù.'
    )
    transfer_cost = fields.Float(string='XLVC')
    transfer_text = fields.Text(string='Ghi chú')

    def compute_self_invoice_order(self):
        self._compute_invoice_order_id()

    def compute_invoice_order(self):
        moves = self.env['account.move'].search([
            ('state', 'in', ['posted']),
            ('move_type', 'in', ['in_invoice', 'out_invoice'])
        ])
        moves._compute_invoice_order_id()

    @api.depends('move_type', 'invoice_line_ids', 'partner_id', 'state', 'payment_state', 'ref')
    def _compute_invoice_order_id(self):
        """
        - Nếu là hóa đơn nhà cung cấp (in_invoice):
            + Lấy 1 dòng purchase line (invoice_line_ids.purchase_line_id)
            + Lấy sale_order_id từ purchase line
            + Lấy hóa đơn khách hàng (out_invoice) của sale_order_id
            + Lưu vào invoice_order_id
        - Nếu là hóa đơn khách hàng (out_invoice):
            + Lấy sale order (từ sale_line_ids.order_id)
            + Lấy 1 purchase order line có sale_order_id đó
            + Lấy purchase order từ purchase line
            + Lấy hóa đơn nhà cung cấp (in_invoice) của purchase order
            + Lưu vào invoice_order_id
        """
        for move in self:
            _logger.info(f"\n========== INVOICE ORDER ID COMPUTE START ==========")
            _logger.info(f"[INVOICE_ORDER_ID] Move Info:")
            _logger.info(f"  - ID: {move.id}")
            _logger.info(f"  - Name: {move.name}")
            _logger.info(f"  - Move Type: {move.move_type}")
            _logger.info(f"  - Partner: {move.partner_id.name if move.partner_id else 'N/A'} (ID: {move.partner_id.id if move.partner_id else 'N/A'})")
            _logger.info(f"  - State: {move.state}")
            _logger.info(f"  - Payment State: {move.payment_state}")
            _logger.info(f"  - Reference: {move.ref}")
            _logger.info(f"  - Invoice Origin: {move.invoice_origin}")
            _logger.info(f"  - Total Lines: {len(move.invoice_line_ids)}")
            _logger.info(f"  - Current invoice_order_id: {move.invoice_order_id.id if move.invoice_order_id else 'None'}")
            
            move.invoice_order_id = False
            
            if move.move_type == 'in_invoice':
                _logger.info(f"[INVOICE_ORDER_ID] Processing VENDOR BILL (in_invoice)")
                
                # Debug invoice lines
                _logger.info(f"[INVOICE_ORDER_ID] Invoice Lines Debug:")
                for idx, line in enumerate(move.invoice_line_ids):
                    _logger.info(f"  Line {idx + 1}:")
                    _logger.info(f"    - ID: {line.id}")
                    _logger.info(f"    - Product: {line.product_id.name if line.product_id else 'N/A'}")
                    _logger.info(f"    - Purchase Line: {line.purchase_line_id.id if line.purchase_line_id else 'None'}")
                    if line.purchase_line_id:
                        _logger.info(f"    - Purchase Order: {line.purchase_line_id.order_id.name if line.purchase_line_id.order_id else 'None'}")
                        _logger.info(f"    - Sale Order from PO: {line.purchase_line_id.order_id.sale_id.name if line.purchase_line_id.order_id and line.purchase_line_id.order_id.sale_id else 'None'}")
                
                # Vendor bill: link to customer invoice
                purchase_lines = move.invoice_line_ids.mapped('purchase_line_id')
                _logger.info(f"[INVOICE_ORDER_ID] Found {len(purchase_lines)} purchase lines: {[pl.id for pl in purchase_lines]}")
                
                purchase_line = purchase_lines[:1]
                _logger.info(f"[INVOICE_ORDER_ID] Using first purchase line: {purchase_line.id if purchase_line else 'None'}")
                
                if purchase_line:
                    _logger.info(f"[INVOICE_ORDER_ID] Purchase Line Details:")
                    _logger.info(f"  - Purchase Order: {purchase_line.order_id.name if purchase_line.order_id else 'None'}")
                    _logger.info(f"  - Purchase Order ID: {purchase_line.order_id.id if purchase_line.order_id else 'None'}")
                    _logger.info(f"  - Purchase Order Partner: {purchase_line.order_id.partner_id.name if purchase_line.order_id and purchase_line.order_id.partner_id else 'None'}")
                    _logger.info(f"  - Sale Order from PO: {purchase_line.order_id.sale_id.name if purchase_line.order_id and purchase_line.order_id.sale_id else 'None'}")
                    
                    if purchase_line.order_id and purchase_line.order_id.sale_id:
                        sale_order = purchase_line.order_id.sale_id
                        _logger.info(f"[INVOICE_ORDER_ID] Sale Order Details:")
                        _logger.info(f"  - Name: {sale_order.name}")
                        _logger.info(f"  - ID: {sale_order.id}")
                        _logger.info(f"  - Partner: {sale_order.partner_id.name} (ID: {sale_order.partner_id.id})")
                        _logger.info(f"  - State: {sale_order.state}")
                        
                        # Find customer invoice for this sale order - Method 1: by invoice_origin
                        _logger.info(f"[INVOICE_ORDER_ID] Searching customer invoice by invoice_origin = '{sale_order.name}'")
                        customer_invoice = self.env['account.move'].search([
                            ('move_type', '=', 'out_invoice'),
                            ('state', 'in', ['posted', 'draft']),
                            ('invoice_origin', '=', sale_order.name)
                        ], limit=1)
                        _logger.info(f"[INVOICE_ORDER_ID] Customer invoice by invoice_origin: {customer_invoice.name if customer_invoice else 'None'} (ID: {customer_invoice.id if customer_invoice else 'None'})")
                        
                        if not customer_invoice:
                            # Fallback: try by partner and sale order
                            _logger.info(f"[INVOICE_ORDER_ID] Fallback: Searching by partner_id = {sale_order.partner_id.id} and sale_order_id = {sale_order.id}")
                            customer_invoice = self.env['account.move'].search([
                                ('move_type', '=', 'out_invoice'),
                                ('state', 'in', ['posted', 'draft']),
                                ('partner_id', '=', sale_order.partner_id.id),
                                ('invoice_line_ids.sale_line_ids.order_id', '=', sale_order.id)
                            ], limit=1)
                            _logger.info(f"[INVOICE_ORDER_ID] Customer invoice by partner & sale_order: {customer_invoice.name if customer_invoice else 'None'} (ID: {customer_invoice.id if customer_invoice else 'None'})")
                        
                        if customer_invoice:
                            move.invoice_order_id = customer_invoice.id
                            _logger.info(f"[INVOICE_ORDER_ID] SUCCESS: Set invoice_order_id = {move.invoice_order_id} ({customer_invoice.name})")
                        else:
                            _logger.info(f"[INVOICE_ORDER_ID] WARNING: No customer invoice found for sale order {sale_order.name}")
                    else:
                        _logger.info(f"[INVOICE_ORDER_ID] WARNING: Purchase line has no order or order has no sale_id")
                else:
                    _logger.info(f"[INVOICE_ORDER_ID] WARNING: No purchase line found")
                
                # Fallback method if still no invoice_order_id found
                if not move.invoice_order_id:
                    _logger.info(f"[INVOICE_ORDER_ID] Fallback: Searching sale order by ref = '{move.ref}'")
                    sale_order = self.env['sale.order'].search([('name', '=', move.ref)], limit=1)
                    _logger.info(f"[INVOICE_ORDER_ID] Sale order by ref: {sale_order.name if sale_order else 'None'} (ID: {sale_order.id if sale_order else 'None'})")
                    
                    if sale_order:
                        _logger.info(f"[INVOICE_ORDER_ID] Searching customer invoice for sale order {sale_order.name}")
                        customer_invoice = self.env['account.move'].search([
                            ('move_type', '=', 'out_invoice'),
                            ('state', 'in', ['posted', 'draft']),
                            ('invoice_origin', '=', sale_order.name)
                        ], limit=1)
                        if customer_invoice:
                            move.invoice_order_id = customer_invoice.id
                            _logger.info(f"[INVOICE_ORDER_ID] FALLBACK SUCCESS: Set invoice_order_id = {move.invoice_order_id} ({customer_invoice.name})")
                        else:
                            _logger.info(f"[INVOICE_ORDER_ID] FALLBACK FAILED: No customer invoice found for sale order {sale_order.name}")
                    else:
                        _logger.info(f"[INVOICE_ORDER_ID] FALLBACK FAILED: No sale order found by ref")
                        
            elif move.move_type == 'out_invoice':
                _logger.info(f"[INVOICE_ORDER_ID] Processing CUSTOMER INVOICE (out_invoice)")
                
                # Debug move lines
                _logger.info(f"[INVOICE_ORDER_ID] Move Lines Debug (total: {len(move.line_ids)}):")
                sale_line_count = 0
                for idx, line in enumerate(move.line_ids):
                    if line.sale_line_ids:
                        sale_line_count += len(line.sale_line_ids)
                        _logger.info(f"  Line {idx + 1} (ID: {line.id}):")
                        _logger.info(f"    - Account: {line.account_id.name}")
                        _logger.info(f"    - Sale Lines: {len(line.sale_line_ids)} - {[sl.id for sl in line.sale_line_ids]}")
                        for sl in line.sale_line_ids:
                            _logger.info(f"      * Sale Line {sl.id}: Order {sl.order_id.name if sl.order_id else 'None'}")
                
                _logger.info(f"[INVOICE_ORDER_ID] Total sale lines found: {sale_line_count}")
                
                # Customer invoice: link to vendor bill
                sale_orders = move.line_ids.mapped('sale_line_ids.order_id')
                _logger.info(f"[INVOICE_ORDER_ID] Found {len(sale_orders)} sale orders: {[so.name for so in sale_orders]}")
                
                sale_order = sale_orders[:1] if sale_orders else False
                if sale_order:
                    _logger.info(f"[INVOICE_ORDER_ID] Using first sale order: {sale_order.name} (ID: {sale_order.id})")
                    _logger.info(f"[INVOICE_ORDER_ID] Sale Order Details:")
                    _logger.info(f"  - Partner: {sale_order.partner_id.name} (ID: {sale_order.partner_id.id})")
                    _logger.info(f"  - State: {sale_order.state}")
                    _logger.info(f"  - Auto Purchase Order: {sale_order.auto_purchase_order_id.name if sale_order.auto_purchase_order_id else 'None'}")
                    
                    purchase_order = sale_order.auto_purchase_order_id
                    if purchase_order:
                        _logger.info(f"[INVOICE_ORDER_ID] Purchase Order Details:")
                        _logger.info(f"  - Name: {purchase_order.name}")
                        _logger.info(f"  - ID: {purchase_order.id}")
                        _logger.info(f"  - Partner: {purchase_order.partner_id.name} (ID: {purchase_order.partner_id.id})")
                        _logger.info(f"  - State: {purchase_order.state}")
                        
                        # Find vendor bill for this purchase order - Method 1: by invoice_origin
                        _logger.info(f"[INVOICE_ORDER_ID] Searching vendor bill by invoice_origin = '{purchase_order.name}'")
                        vendor_bill = self.env['account.move'].search([
                            ('move_type', '=', 'in_invoice'),
                            ('state', 'in', ['posted', 'draft']),
                            ('invoice_origin', '=', purchase_order.name)
                        ], limit=1)
                        _logger.info(f"[INVOICE_ORDER_ID] Vendor bill by invoice_origin: {vendor_bill.name if vendor_bill else 'None'} (ID: {vendor_bill.id if vendor_bill else 'None'})")
                        
                        if not vendor_bill:
                            # Fallback: try by partner and purchase order
                            _logger.info(f"[INVOICE_ORDER_ID] Fallback: Searching by partner_id = {purchase_order.partner_id.id} and purchase_order_id = {purchase_order.id}")
                            vendor_bill = self.env['account.move'].search([
                                ('move_type', '=', 'in_invoice'),
                                ('state', 'in', ['posted', 'draft']),
                                ('partner_id', '=', purchase_order.partner_id.id),
                                ('invoice_line_ids.purchase_line_id.order_id', '=', purchase_order.id)
                            ], limit=1)
                            _logger.info(f"[INVOICE_ORDER_ID] Vendor bill by partner & purchase_order: {vendor_bill.name if vendor_bill else 'None'} (ID: {vendor_bill.id if vendor_bill else 'None'})")
                        
                        if vendor_bill:
                            move.invoice_order_id = vendor_bill.id
                            _logger.info(f"[INVOICE_ORDER_ID] SUCCESS: Set invoice_order_id = {move.invoice_order_id} ({vendor_bill.name})")
                        else:
                            _logger.info(f"[INVOICE_ORDER_ID] WARNING: No vendor bill found for purchase order {purchase_order.name}")
                    else:
                        _logger.info(f"[INVOICE_ORDER_ID] WARNING: Sale order has no auto_purchase_order_id")
                else:
                    _logger.info(f"[INVOICE_ORDER_ID] WARNING: No sale order found from move lines")
            else:
                _logger.info(f"[INVOICE_ORDER_ID] Skipping move type: {move.move_type}")
            
            _logger.info(f"[INVOICE_ORDER_ID] FINAL RESULT:")
            _logger.info(f"  - Move: {move.name} (ID: {move.id})")
            _logger.info(f"  - Type: {move.move_type}")
            _logger.info(f"  - invoice_order_id: {move.invoice_order_id.id if move.invoice_order_id else 'None'}")
            if move.invoice_order_id:
                _logger.info(f"  - Linked Invoice: {move.invoice_order_id.name}")
                _logger.info(f"  - Linked Invoice Type: {move.invoice_order_id.move_type}")
                _logger.info(f"  - Linked Invoice Partner: {move.invoice_order_id.partner_id.name}")
            _logger.info(f"========== INVOICE ORDER ID COMPUTE END ==========\n")

    @api.depends('amount_residual', 'move_type', 'state', 'company_id')
    def _compute_payment_state(self):
        _logger.info('begin _compute_payment_state')
        
        # Lưu trạng thái thanh toán trước khi tính toán lại
        payment_states_before = {move.id: move.payment_state for move in self if move.id}
        
        super()._compute_payment_state()

        # Log trạng thái trước khi compute
        for move in self:
            _logger.info(f"""
            Before compute:
            - Move ID: {move.id}
            - Amount Residual: {move.amount_residual}
            - Amount Total: {move.amount_total}
            - State: {move.state}
            - Payment State: {move.payment_state}
            """)
        
        # Log trạng thái sau khi compute
        for move in self:
            # Chỉ trigger tính toán lãi khi hóa đơn vừa mới chuyển sang trạng thái "paid"
            previous_state = payment_states_before.get(move.id)
            if move.payment_state == 'paid' and move.id and previous_state and previous_state != 'paid':
                _logger.info(f"""
                    After compute:
                    - Move ID: {move.id}
                    - Amount Residual: {move.amount_residual}
                    - Amount Total: {move.amount_total}
                    - State: {move.state}
                    - Payment State: {move.payment_state}
                    """)
                _logger.info(f"Invoice just changed to paid state (from {previous_state}), calculating interest")
                # Lọc đơn bán hàng có cùng khách hàng với hóa đơn
                sale_orders = move.line_ids.sale_line_ids.order_id.filtered(
                    lambda order: order.partner_id.id == move.partner_id.id
                )
                _logger.info("Found sale orders with matching customer: %s", sale_orders)
                for order in sale_orders:
                    _logger.info("Calculating interest for sale order: %s", order.name)
                    order.sudo().calculate_interest()

    @api.depends('invoice_line_ids', 
                 'invoice_line_ids.quantity', 
                 'invoice_line_ids.product_id',
                 'invoice_line_ids.display_type',
                 'move_type')
    def _compute_total_quantity(self):
        """Tự động tính lại khi có thay đổi ở invoice lines"""
        for move in self:
            # Only compute for customer invoices and vendor bills
            if move.move_type in ('out_invoice', 'out_refund', 'in_invoice', 'in_refund'):
                total_quantity = sum(
                    line.quantity for line in move.invoice_line_ids.filtered(lambda l: l.product_id and l.display_type == 'product')
                )
                move.total_quantity = total_quantity
            else:
                move.total_quantity = 0.0

    @api.depends('line_ids.sale_line_ids.order_id.received_date', 
                 'invoice_line_ids.purchase_line_id.order_id.date_planned', 
                 'invoice_line_ids.purchase_line_id.date_planned')
    def _compute_order_received_date(self):
        """
        Tính toán ngày nhận hàng cho hóa đơn dựa trên loại hóa đơn:
        
        1. Customer Invoice (out_invoice):
           - Lấy received_date từ Sale Order liên quan
           - Chỉ lấy SO có cùng khách hàng với hóa đơn
           
        2. Vendor Bill (in_invoice):
           - Ưu tiên 1: Lấy date_planned từ Purchase Order (computed từ các PO lines)
           - Ưu tiên 2: Lấy date_planned từ Purchase Order Line đầu tiên
           - Ưu tiên 3: Fallback - lấy received_date từ Sale Order liên quan (nếu có)
           
        Logic này đảm bảo cả customer invoice và vendor bill đều có ngày nhận hàng
        để phục vụ tính toán thời hạn thanh toán và các báo cáo.
        """
        for move in self:
            # Chỉ xử lý customer invoice và vendor bill
            if move.move_type not in ['out_invoice', 'in_invoice']:
                move.order_received_date = False
                continue
                
            _logger.info(f'[ORDER_RECEIVED_DATE] Computing for {move.move_type} {move.name} (ID: {move.id})')
            
            old_received_date = move.order_received_date
            received_date = False
            
            if move.move_type == 'out_invoice':
                received_date = self._get_received_date_from_sale_order(move)
            elif move.move_type == 'in_invoice':
                received_date = self._get_received_date_from_purchase_order(move)
            
            # Cập nhật giá trị mới
            move.order_received_date = received_date
            _logger.info(f'[ORDER_RECEIVED_DATE] Final result: {move.order_received_date}')
            
            # Trigger cập nhật date_maturity khi order_received_date thay đổi
            if move.order_received_date != old_received_date and move.state == 'posted':
                _logger.info(f'Order received date changed for invoice {move.name}, recomputing payment terms')
                move._recompute_payment_terms_lines()

    def _get_received_date_from_sale_order(self, move):
        """
        Lấy ngày nhận hàng từ Sale Order cho Customer Invoice
        
        Args:
            move: Customer Invoice record
            
        Returns:
            date: received_date từ Sale Order hoặc False nếu không tìm thấy
        """
        _logger.info(f'[ORDER_RECEIVED_DATE] Customer invoice - getting received_date from Sale Order')
        
        # Lấy tất cả Sale Orders liên quan qua invoice lines
        sale_orders = move.line_ids.sale_line_ids.order_id
        
        if not sale_orders:
            _logger.info(f'[ORDER_RECEIVED_DATE] No sale orders found in invoice lines')
            return False
            
        # Lọc Sale Orders cùng khách hàng (đảm bảo tính nhất quán)
        filtered_sale_orders = sale_orders.filtered(lambda so: so.partner_id.id == move.partner_id.id)
        _logger.info(f'[ORDER_RECEIVED_DATE] Found {len(filtered_sale_orders)} matching sale orders: {[so.name for so in filtered_sale_orders]}')
        
        if filtered_sale_orders:
            received_date = filtered_sale_orders[:1].received_date
            _logger.info(f'[ORDER_RECEIVED_DATE] SO received_date: {received_date}')
            return received_date
            
        return False

    def _get_received_date_from_purchase_order(self, move):
        """
        Lấy ngày nhận hàng từ Purchase Order cho Vendor Bill
        
        Thứ tự ưu tiên:
        1. PO.date_planned (computed từ các PO lines)
        2. PO Line.date_planned (từ line đầu tiên)
        3. SO.received_date (từ Sale Order liên quan - fallback)
        
        Args:
            move: Vendor Bill record
            
        Returns:
            date: date_planned từ Purchase Order/Line hoặc received_date từ SO, False nếu không tìm thấy
        """
        _logger.info(f'[ORDER_RECEIVED_DATE] Vendor bill - getting date_planned from Purchase Order')
        
        # Lấy tất cả Purchase Lines từ invoice lines
        purchase_lines = move.invoice_line_ids.mapped('purchase_line_id')
        
        if not purchase_lines:
            _logger.info(f'[ORDER_RECEIVED_DATE] No purchase lines found in invoice lines')
            return False
            
        _logger.info(f'[ORDER_RECEIVED_DATE] Found {len(purchase_lines)} purchase lines: {[pl.id for pl in purchase_lines]}')
        
        # Lấy Purchase Order từ purchase line đầu tiên
        purchase_order = purchase_lines[:1].order_id
        
        if not purchase_order:
            _logger.info(f'[ORDER_RECEIVED_DATE] No purchase order found from purchase lines')
            return False
            
        # Ưu tiên 1: PO.date_planned (computed từ các PO lines - thường là ngày sớm nhất)
        if purchase_order.date_planned:
            received_date = purchase_order.date_planned.date()
            _logger.info(f'[ORDER_RECEIVED_DATE] Using PO.date_planned: {received_date}')
            return received_date
        
        # Ưu tiên 2: PO Line.date_planned (từ line đầu tiên)
        first_line = purchase_lines[:1]
        if first_line.date_planned:
            received_date = first_line.date_planned.date()
            _logger.info(f'[ORDER_RECEIVED_DATE] Using PO Line.date_planned: {received_date}')
            return received_date
        
        # Ưu tiên 3: Fallback - SO.received_date (nếu PO được tạo từ SO)
        if purchase_order.sale_id and purchase_order.sale_id.received_date:
            received_date = purchase_order.sale_id.received_date
            _logger.info(f'[ORDER_RECEIVED_DATE] Fallback to SO.received_date: {received_date}')
            return received_date
        
        _logger.info(f'[ORDER_RECEIVED_DATE] No date found from any source')
        return False

    def write(self, vals):
        """Override write để trigger recompute invoice_order_id khi state chuyển sang posted"""
        # Lưu trạng thái cũ trước khi update
        old_states = {move.id: move.state for move in self if move.id}
        
        result = super().write(vals)
        
        # Trigger recompute nếu có move chuyển sang state 'posted'
        if 'state' in vals and vals['state'] == 'posted':
            moves_newly_posted = self.filtered(lambda m: m.id and old_states.get(m.id) != 'posted')
            if moves_newly_posted:
                moves_newly_posted._trigger_counterpart_invoice_order_id_recompute()
        
        return result
    
    def _trigger_counterpart_invoice_order_id_recompute(self):
        """
        Trigger recompute invoice_order_id cho các invoice đối ứng
        Logic:
        - Nếu là vendor bill: tìm customer invoice đối ứng và recompute
        - Nếu là customer invoice: tìm vendor bill đối ứng và recompute
        """
        for move in self:
            if move.move_type not in ['in_invoice', 'out_invoice']:
                continue
                
            _logger.info(f'[TRIGGER_RECOMPUTE] Processing {move.move_type} {move.name} (ID: {move.id})')
            
            if move.move_type == 'in_invoice':
                # Vendor bill: tìm customer invoice đối ứng
                counterpart_invoices = self._find_counterpart_customer_invoices(move)
                for invoice in counterpart_invoices:
                    _logger.info(f'[TRIGGER_RECOMPUTE] Recomputing customer invoice {invoice.name} (ID: {invoice.id})')
                    invoice._compute_invoice_order_id()
                    
            elif move.move_type == 'out_invoice':
                # Customer invoice: tìm vendor bill đối ứng
                counterpart_invoices = self._find_counterpart_vendor_bills(move)
                for invoice in counterpart_invoices:
                    _logger.info(f'[TRIGGER_RECOMPUTE] Recomputing vendor bill {invoice.name} (ID: {invoice.id})')
                    invoice._compute_invoice_order_id()
    
    def _find_counterpart_customer_invoices(self, vendor_bill):
        """Tìm customer invoice đối ứng với vendor bill"""
        counterpart_invoices = self.env['account.move']
        
        # Lấy purchase lines từ vendor bill
        purchase_lines = vendor_bill.invoice_line_ids.mapped('purchase_line_id')
        if not purchase_lines:
            return counterpart_invoices
            
        # Lấy sale order từ purchase line đầu tiên
        purchase_line = purchase_lines[:1]
        if not (purchase_line.order_id and purchase_line.order_id.sale_id):
            return counterpart_invoices
            
        sale_order = purchase_line.order_id.sale_id
        
        # Tìm customer invoice theo invoice_origin
        customer_invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', 'in', ['posted', 'draft']),
            ('invoice_origin', '=', sale_order.name)
        ])
        
        return customer_invoices
    
    def _find_counterpart_vendor_bills(self, customer_invoice):
        """Tìm vendor bill đối ứng với customer invoice"""
        counterpart_invoices = self.env['account.move']
        
        # Lấy sale orders từ customer invoice
        sale_orders = customer_invoice.line_ids.mapped('sale_line_ids.order_id')
        if not sale_orders:
            return counterpart_invoices
            
        sale_order = sale_orders[:1]
        if not sale_order.auto_purchase_order_id:
            return counterpart_invoices
            
        purchase_order = sale_order.auto_purchase_order_id
        
        # Tìm vendor bill theo invoice_origin
        vendor_bills = self.env['account.move'].search([
            ('move_type', '=', 'in_invoice'),
            ('state', 'in', ['posted', 'draft']),
            ('invoice_origin', '=', purchase_order.name)
        ])
        
        return vendor_bills

    def cron_fix_missing_invoice_order_id(self):
            return True
        # """
        # Cron job để fix các invoice thiếu invoice_order_id
        # Chạy hàng ngày để đảm bảo tất cả invoice đều có liên kết đúng
        # """
        # _logger.info('=== CRON: Starting fix missing invoice_order_id ===')
        
        # # Tìm các invoice thiếu invoice_order_id
        # missing_invoices = self.search([
        #     ('move_type', 'in', ['in_invoice', 'out_invoice']),
        #     ('state', '=', 'posted'),
        #     ('invoice_order_id', '=', False)
        # ])
        
        # # Log thống kê chi tiết
        # vendor_bills = missing_invoices.filtered(lambda x: x.move_type == 'in_invoice')
        # customer_invoices = missing_invoices.filtered(lambda x: x.move_type == 'out_invoice')
        
        # _logger.info(f'=== MISSING INVOICE_ORDER_ID STATISTICS ===')
        # _logger.info(f'Total missing: {len(missing_invoices)}')
        # _logger.info(f'  - Vendor Bills (in_invoice): {len(vendor_bills)}')
        # _logger.info(f'  - Customer Invoices (out_invoice): {len(customer_invoices)}')
        
        # # Log chi tiết từng invoice thiếu
        # _logger.info(f'=== DETAILED LIST OF MISSING INVOICES ===')
        # for invoice in missing_invoices:
        #     partner_name = invoice.partner_id.name if invoice.partner_id else 'N/A'
        #     _logger.info(f'  {invoice.move_type.upper()}: {invoice.name} (ID: {invoice.id}) | Partner: {partner_name} | Ref: {invoice.ref} | Origin: {invoice.invoice_origin}')
        
        # if not missing_invoices:
        #     _logger.info('No invoices missing invoice_order_id found!')
        #     return {
        #         'total_processed': 0,
        #         'fixed_count': 0,
        #         'vendor_bills_missing': 0,
        #         'customer_invoices_missing': 0
        #     }
        
        # # Bắt đầu fix
        # _logger.info(f'=== STARTING FIX PROCESS ===')
        # fixed_count = 0
        # fixed_vendor_bills = 0
        # fixed_customer_invoices = 0
        
        # for invoice in missing_invoices:
        #     _logger.info(f'Processing {invoice.move_type} {invoice.name} (ID: {invoice.id})')
            
        #     # Lưu trạng thái trước khi compute
        #     old_invoice_order_id = invoice.invoice_order_id
            
        #     # Compute lại invoice_order_id
        #     invoice._compute_invoice_order_id()
            
        #     # Kiểm tra xem có được fix không
        #     if invoice.invoice_order_id and invoice.invoice_order_id != old_invoice_order_id:
        #         fixed_count += 1
        #         if invoice.move_type == 'in_invoice':
        #             fixed_vendor_bills += 1
        #         else:
        #             fixed_customer_invoices += 1
                    
        #         linked_invoice = invoice.invoice_order_id
        #         _logger.info(f'✅ FIXED: {invoice.name} → {linked_invoice.name} ({linked_invoice.move_type})')
        #     else:
        #         _logger.info(f'❌ NO FIX: {invoice.name} - no valid counterpart found')
        
        # # Log kết quả cuối cùng
        # _logger.info(f'=== FINAL RESULTS ===')
        # _logger.info(f'Total processed: {len(missing_invoices)}')
        # _logger.info(f'Successfully fixed: {fixed_count}')
        # _logger.info(f'  - Fixed vendor bills: {fixed_vendor_bills}')
        # _logger.info(f'  - Fixed customer invoices: {fixed_customer_invoices}')
        # _logger.info(f'Still missing: {len(missing_invoices) - fixed_count}')
        # _logger.info('=== CRON: Fix missing invoice_order_id completed ===')
        
        # return {
        #     'total_processed': len(missing_invoices),
        #     'fixed_count': fixed_count,
        #     'fixed_vendor_bills': fixed_vendor_bills,
        #     'fixed_customer_invoices': fixed_customer_invoices,
        #     'vendor_bills_missing': len(vendor_bills),
        #     'customer_invoices_missing': len(customer_invoices),
        #     'still_missing': len(missing_invoices) - fixed_count
        # }
    
    def manual_fix_missing_invoice_order_id(self):
        """
        Method để manual fix các invoice thiếu invoice_order_id
        Có thể gọi từ UI hoặc script
        """
        return self.cron_fix_missing_invoice_order_id()
    
    def compute_invoice_order_id_public(self):
        """
        Public method để compute invoice_order_id cho XML-RPC
        Wrapper cho _compute_invoice_order_id
        """
        self._compute_invoice_order_id()
        return {
            'success': True,
            'invoice_order_id': self.invoice_order_id.id if self.invoice_order_id else False,
            'invoice_order_name': self.invoice_order_id.name if self.invoice_order_id else False
        }
    
    def test_trigger_recompute_for_move(self, move_id):
        """
        Method để test trigger recompute cho một move cụ thể
        Simulate việc move được posted để trigger logic
        """
        move = self.browse(move_id)
        if not move.exists():
            _logger.info(f'Move {move_id} not found')
            return False
            
        _logger.info(f'Testing trigger recompute for move {move.name} (ID: {move_id})')
        move._trigger_counterpart_invoice_order_id_recompute()
        return True

    def action_reset_to_draft_sql(self):
        """Đưa hóa đơn về trạng thái dự thảo và xóa các bản ghi liên quan"""
        for move in self:
            _logger.info(f'Resetting invoice {move.name} to draft state')
            
            # Xóa các stock valuation layers
            self.env.cr.execute("""
                DELETE FROM stock_valuation_layer 
                WHERE account_move_id = %s OR account_move_line_id IN (
                    SELECT id FROM account_move_line WHERE move_id = %s
                )
            """, (move.id, move.id))

            # Xóa các stock move line
            self.env.cr.execute("""
                DELETE FROM stock_move_line 
                WHERE move_id IN (
                    SELECT id FROM stock_move WHERE origin = %s
                )
            """, (move.name,))

            # Xóa các stock move
            self.env.cr.execute("""
                DELETE FROM stock_move 
                WHERE origin = %s
            """, (move.name,))

            # Cập nhật trạng thái của hóa đơn
            self.env.cr.execute("""
                UPDATE account_move 
                SET state = 'draft', 
                    posted_date = NULL 
                WHERE id = %s
            """, (move.id,))
            
            # Cập nhật trạng thái của các bút toán
            self.env.cr.execute("""
                UPDATE account_move_line 
                SET parent_state = 'draft' 
                WHERE move_id = %s
            """, (move.id,))
            
            _logger.info(f'Invoice {move.name} has been reset to draft state with related records deleted')

    def recompute_all_total_quantity(self):
        """Tính toán lại tổng số lượng cho tất cả hóa đơn"""
        moves = self.search([
            ('move_type', 'in', ['out_invoice', 'out_refund', 'in_invoice', 'in_refund'])
        ])
        _logger.info(f'Recomputing total quantity for {len(moves)} invoices')
        for move in moves:
            _logger.info(f'Recomputing total quantity for invoice {move.name}')
            move._compute_total_quantity()
        _logger.info('Finished recomputing total quantity')
        return True

    def recompute_all_actual_payment_days(self):
        """Tính toán lại số ngày trả thực tế cho tất cả hóa đơn"""
        moves = self.search([
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '=', 'posted')
        ])
        _logger.info(f'Recomputing actual payment days for {len(moves)} invoices')
        for move in moves:
            _logger.info(f'Recomputing actual payment days for invoice {move.name}')
            move._compute_actual_payment_days()
        _logger.info('Finished recomputing actual payment days')
        return True
    
    def recompute_actual_payment_days(self):
        """Tính toán lại số ngày trả thực tế cho hóa đơn"""
        for move in self:
            _logger.info(f'Recomputing actual payment days for invoice {move.name}')
            move._compute_actual_payment_days()
        _logger.info('Finished recomputing actual payment days')
        return True

    @api.depends('tag_ids')
    def _compute_tags_text(self):
        for record in self:
            record.tags_text = ', '.join(record.tag_ids.mapped('name')) if record.tag_ids else ''

    @api.depends('needed_terms', 'order_received_date')
    def _compute_invoice_date_due(self):
        today = fields.Date.context_today(self)
        for move in self:
            # Lấy cấu hình cách tính thời hạn thanh toán
            payment_term_calculation = self.env['ir.config_parameter'].sudo().get_param('nsgerp.payment_term_calculation', 'invoice_date')
            
            if payment_term_calculation == 'receipt_date' and move.order_received_date:
                # Tính từ ngày nhận hàng
                if move.invoice_payment_term_id:
                    # Tính toán ngày đến hạn dựa trên điều khoản thanh toán và ngày nhận hàng
                    payment_term_lines = move.invoice_payment_term_id.line_ids
                    if payment_term_lines:
                        # Kiểm tra xem có điều khoản "Cuối tháng" không
                        end_month_lines = payment_term_lines.filtered(lambda line: line.end_month)
                        if end_month_lines:
                            # Xử lý trường hợp "Cuối tháng" hoặc "Cuối tháng kế tiếp"
                            receipt_date = move.order_received_date
                            
                            # Lấy tháng và năm hiện tại
                            current_year = receipt_date.year
                            current_month = receipt_date.month
                            
                            # Tính ngày đến hạn cho tất cả các điều khoản "Cuối tháng"
                            # và lấy ngày xa nhất
                            max_due_date = None
                            
                            for line in end_month_lines:
                                # Tính tháng đích cho dòng này
                                line_target_month = current_month + line.months
                                line_target_year = current_year
                                
                                # Xử lý trường hợp vượt quá 12 tháng
                                while line_target_month > 12:
                                    line_target_month -= 12
                                    line_target_year += 1
                                
                                # Lấy ngày cuối tháng của tháng đích
                                last_day_of_line_month = calendar.monthrange(line_target_year, line_target_month)[1]
                                
                                # Tạo ngày cuối tháng cho dòng này
                                line_target_date = receipt_date.replace(year=line_target_year, month=line_target_month, day=last_day_of_line_month)
                                
                                # Thêm days_after nếu có
                                if line.days_after and line.days_after > 0:
                                    line_target_date = line_target_date + timedelta(days=line.days_after)
                                
                                # So sánh với ngày xa nhất hiện tại
                                if max_due_date is None or line_target_date > max_due_date:
                                    max_due_date = line_target_date
                            
                            move.invoice_date_due = max_due_date
                        else:
                            # Lấy ngày đến hạn xa nhất từ các điều khoản thanh toán
                            max_days = max(payment_term_lines.mapped('days'))
                            move.invoice_date_due = move.order_received_date + timedelta(days=max_days)
                    else:
                        move.invoice_date_due = move.order_received_date
                else:
                    move.invoice_date_due = move.order_received_date
            else:
                # Tính theo cách mặc định của Odoo (từ needed_terms)
                move.invoice_date_due = move.needed_terms and max(
                    (k['date_maturity'] for k in move.needed_terms.keys() if k),
                    default=False,
                ) or move.invoice_date_due or today

    @api.depends('needed_terms', 'order_received_date')
    def _compute_invoice_date_due_custom(self):
        """
        Tính toán ngày đến hạn thanh toán tùy chỉnh cho hóa đơn
        Logic:
        1. Kiểm tra cấu hình cách tính thời hạn thanh toán từ system parameter
        2. Nếu cấu hình là 'receipt_date' và có ngày nhận hàng:
           - Tính từ ngày nhận hàng + số ngày trong điều khoản thanh toán
           - Lấy số ngày lớn nhất nếu có nhiều dòng điều khoản
           - Nếu không có điều khoản thì dùng luôn ngày nhận hàng
        3. Trường hợp còn lại: Tính theo cách mặc định của Odoo từ needed_terms
        """
        today = fields.Date.context_today(self)
        for move in self:
            # Lấy cấu hình cách tính thời hạn thanh toán từ system parameter
            # Mặc định là 'invoice_date' nếu không có cấu hình
            payment_term_calculation = self.env['ir.config_parameter'].sudo().get_param('nsgerp.payment_term_calculation', 'invoice_date')
            
            # Kiểm tra nếu cấu hình là tính từ ngày nhận hàng và có ngày nhận hàng
            if payment_term_calculation == 'receipt_date' and move.order_received_date:
                # Tính từ ngày nhận hàng
                if move.invoice_payment_term_id:
                    # Có điều khoản thanh toán: tính toán ngày đến hạn dựa trên điều khoản và ngày nhận hàng
                    payment_term_lines = move.invoice_payment_term_id.line_ids
                    if payment_term_lines:
                        # Kiểm tra xem có điều khoản "Cuối tháng" không
                        end_month_lines = payment_term_lines.filtered(lambda line: line.end_month)
                        if end_month_lines:
                            # Xử lý trường hợp "Cuối tháng" hoặc "Cuối tháng kế tiếp"
                            receipt_date = move.order_received_date
                            
                            # Lấy tháng và năm hiện tại
                            current_year = receipt_date.year
                            current_month = receipt_date.month
                            
                            # Tính ngày đến hạn cho tất cả các điều khoản "Cuối tháng"
                            # và lấy ngày xa nhất
                            max_due_date = None
                            
                            for line in end_month_lines:
                                # Tính tháng đích cho dòng này
                                line_target_month = current_month + line.months
                                line_target_year = current_year
                                
                                # Xử lý trường hợp vượt quá 12 tháng
                                while line_target_month > 12:
                                    line_target_month -= 12
                                    line_target_year += 1
                                
                                # Lấy ngày cuối tháng của tháng đích
                                last_day_of_line_month = calendar.monthrange(line_target_year, line_target_month)[1]
                                
                                # Tạo ngày cuối tháng cho dòng này
                                line_target_date = receipt_date.replace(year=line_target_year, month=line_target_month, day=last_day_of_line_month)
                                
                                # Thêm days_after nếu có
                                if line.days_after and line.days_after > 0:
                                    line_target_date = line_target_date + timedelta(days=line.days_after)
                                
                                # So sánh với ngày xa nhất hiện tại
                                if max_due_date is None or line_target_date > max_due_date:
                                    max_due_date = line_target_date
                            
                            move.invoice_date_due_custom = max_due_date
                        else:
                            # Lấy số ngày lớn nhất từ các dòng điều khoản thanh toán
                            # Ví dụ: nếu có 2 dòng 15 ngày và 30 ngày, lấy 30 ngày
                            max_days = max(payment_term_lines.mapped('days'))
                            # Ngày đến hạn = Ngày nhận hàng + Số ngày lớn nhất
                            move.invoice_date_due_custom = move.order_received_date + timedelta(days=max_days)
                    else:
                        # Có điều khoản thanh toán nhưng không có dòng chi tiết
                        # Sử dụng luôn ngày nhận hàng làm ngày đến hạn
                        move.invoice_date_due_custom = move.order_received_date
                else:
                    # Không có điều khoản thanh toán
                    # Sử dụng luôn ngày nhận hàng làm ngày đến hạn
                    move.invoice_date_due_custom = move.order_received_date
            else:
                # Tính theo cách mặc định của Odoo (từ needed_terms)
                # needed_terms chứa các thông tin về ngày đáo hạn từ điều khoản thanh toán
                # Lấy ngày đáo hạn xa nhất từ needed_terms, nếu không có thì dùng giá trị hiện tại hoặc hôm nay
                move.invoice_date_due_custom = move.needed_terms and max(
                    (k['date_maturity'] for k in move.needed_terms.keys() if k),
                    default=False,
                ) or move.invoice_date_due_custom or today

    @api.depends('invoice_date', 'line_ids.matched_debit_ids.debit_move_id.payment_id.date', 'line_ids.matched_credit_ids.credit_move_id.payment_id.date', 'payment_state', 'line_ids.full_reconcile_id', 'order_received_date', 'invoice_payment_term_id')
    def _compute_actual_payment_days(self):
        _logger.info('=== BẮT ĐẦU TÍNH TOÁN SỐ NGÀY TT QUÁ HẠN (WEIGHTED) ===')
        for move in self:
            _logger.info(f'Đang xử lý hóa đơn ID: {move.id}, Tên: {move.name}, Loại: {move.move_type}')
            _logger.info(f'Ngày hóa đơn: {move.invoice_date}')
            _logger.info(f'Ngày nhận hàng: {move.order_received_date}')
            _logger.info(f'Tổng tiền hóa đơn: {move.amount_total}')
            _logger.info(f'Trạng thái thanh toán: {move.payment_state}')
            
            if move.move_type not in ['out_invoice', 'in_invoice']:
                _logger.info(f'Bỏ qua hóa đơn {move.id} - sai loại')
                move.actual_payment_days = 0
                continue
            
            # Xác định ngày bắt đầu tính toán (Ngày HĐ)
            invoice_date = move.order_received_date or move.invoice_date
            if not invoice_date:
                _logger.info(f'Bỏ qua hóa đơn {move.id} - không có ngày nhận hàng và ngày hóa đơn')
                move.actual_payment_days = 0
                continue
            
            _logger.info(f'Sử dụng ngày hóa đơn: {invoice_date}')
            
            # Tính thời hạn thanh toán (Payment Term)
            payment_term_days = 0
            if move.invoice_payment_term_id and move.invoice_payment_term_id.line_ids:
                payment_term_days = max(move.invoice_payment_term_id.line_ids.mapped('days'))
            _logger.info(f'Thời hạn thanh toán: {payment_term_days} ngày')
            
            # Lấy tất cả các payment liên quan đến hóa đơn này với số tiền
            payment_data = []
            
            _logger.info(f'Hóa đơn {move.id} có {len(move.line_ids)} dòng bút toán')
            
            # Lấy payments từ các bút toán đã reconcile
            for line in move.line_ids:
                if line.account_id.account_type not in ['asset_receivable', 'liability_payable']:
                    continue
                    
                _logger.info(f'Đang xử lý dòng ID: {line.id}, Tài khoản: {line.account_id.name}')
                _logger.info(f'Dòng có {len(line.matched_debit_ids)} debit matches và {len(line.matched_credit_ids)} credit matches')
                
                # Lấy payments từ debit matches
                for match in line.matched_debit_ids:
                    if match.debit_move_id.payment_id and match.debit_move_id.payment_id.state == 'posted':
                        payment = match.debit_move_id.payment_id
                        amount = match.amount
                        _logger.info(f'Tìm thấy payment từ debit match: {payment.name}, Số tiền: {amount}, Ngày: {payment.date}')
                        payment_data.append({
                            'payment': payment,
                            'amount': amount,
                            'date': payment.date
                        })
                
                # Lấy payments từ credit matches
                for match in line.matched_credit_ids:
                    if match.credit_move_id.payment_id and match.credit_move_id.payment_id.state == 'posted':
                        payment = match.credit_move_id.payment_id
                        amount = match.amount
                        _logger.info(f'Tìm thấy payment từ credit match: {payment.name}, Số tiền: {amount}, Ngày: {payment.date}')
                        payment_data.append({
                            'payment': payment,
                            'amount': amount,
                            'date': payment.date
                        })
            
            _logger.info(f'Tổng số payment data tìm thấy: {len(payment_data)}')
            
            if not payment_data or move.amount_total == 0:
                move.actual_payment_days = 0
                _logger.info('Không tìm thấy payment data hoặc tổng tiền = 0, đặt actual_payment_days = 0')
                continue
            
            # Tính toán theo công thức weighted average
            # Số ngày quá hạn = (Ngày TT L1 - Ngày HĐ)*(số tiền TT L1/Tổng tiền) + ... - Thời hạn TT
            weighted_days = 0
            total_payment_amount = 0
            
            for payment_info in payment_data:
                payment_date = payment_info['date']
                payment_amount = payment_info['amount']
                
                if payment_date and payment_amount > 0:
                    # Tính số ngày từ ngày hóa đơn đến ngày thanh toán
                    days_from_invoice = (payment_date - invoice_date).days
                    
                    # Tính trọng số (tỷ lệ số tiền thanh toán so với tổng tiền)
                    weight = payment_amount / move.amount_total
                    
                    # Cộng vào tổng weighted days
                    weighted_days += days_from_invoice * weight
                    total_payment_amount += payment_amount
                    
                    _logger.info(f'Payment: {payment_info["payment"].name}')
                    _logger.info(f'  - Ngày TT: {payment_date}')
                    _logger.info(f'  - Số tiền TT: {payment_amount}')
                    _logger.info(f'  - Số ngày từ HĐ: {days_from_invoice}')
                    _logger.info(f'  - Trọng số: {weight:.4f}')
                    _logger.info(f'  - Weighted days: {days_from_invoice * weight:.2f}')
            
            # Trừ đi thời hạn thanh toán
            final_overdue_days = weighted_days - payment_term_days
            
            _logger.info(f'Tổng weighted days: {weighted_days:.2f}')
            _logger.info(f'Thời hạn thanh toán: {payment_term_days}')
            _logger.info(f'Số ngày quá hạn cuối cùng: {final_overdue_days:.2f}')
            _logger.info(f'Tổng số tiền đã thanh toán: {total_payment_amount}')
            
            move.actual_payment_days = round(final_overdue_days, 2)
            
            _logger.info(f'Số ngày TT quá hạn cuối cùng cho hóa đơn {move.id}: {move.actual_payment_days}')
        
        _logger.info('=== KẾT THÚC TÍNH TOÁN SỐ NGÀY TT QUÁ HẠN (WEIGHTED) ===')

    def _recompute_payment_terms_lines(self):
        """
        Override để cập nhật date_maturity dựa trên logic tính từ ngày nhận hàng
        Chỉ thay đổi date_ref khi tính payment terms, giữ nguyên logic khác
        """
        # Gọi logic gốc của Odoo trước
        
        # Kiểm tra cấu hình cách tính thời hạn thanh toán
        payment_term_calculation = self.env['ir.config_parameter'].sudo().get_param('nsgerp.payment_term_calculation', 'invoice_date')
        
        # Chỉ xử lý khi cấu hình là 'receipt_date' và có ngày nhận hàng
        if payment_term_calculation == 'receipt_date' and self.order_received_date and self.is_invoice():
            if self.invoice_payment_term_id:
                # Tính toán lại payment terms với ngày nhận hàng làm date_ref
                sign = 1 if self.is_inbound() else -1
                if self.currency_id and self.currency_id != self.company_id.currency_id:
                    tax_amount_currency = self.amount_tax * sign
                    tax_amount = self.amount_tax_signed
                    untaxed_amount_currency = self.amount_untaxed * sign
                    untaxed_amount = self.amount_untaxed_signed
                else:
                    tax_amount_currency = self.amount_tax * sign
                    tax_amount = self.amount_tax_signed
                    untaxed_amount_currency = self.amount_untaxed * sign
                    untaxed_amount = self.amount_untaxed_signed
                
                # Tính payment terms với ngày nhận hàng
                invoice_payment_terms = self.invoice_payment_term_id._compute_terms(
                    date_ref=self.order_received_date,  # Sử dụng ngày nhận hàng thay vì ngày hóa đơn
                    currency=self.currency_id,
                    tax_amount_currency=tax_amount_currency,
                    tax_amount=tax_amount,
                    untaxed_amount_currency=untaxed_amount_currency,
                    untaxed_amount=untaxed_amount,
                    company=self.company_id,
                    sign=sign
                )
                
                # Cập nhật date_maturity cho các payment term lines
                payment_term_lines = self.line_ids.filtered(lambda l: l.display_type == 'payment_term')
                for i, (line, term) in enumerate(zip(payment_term_lines, invoice_payment_terms)):
                    new_date_maturity = fields.Date.to_date(term.get('date'))
                    if line.date_maturity != new_date_maturity:
                        # Force update date_maturity ngay cả khi hóa đơn đã posted
                        line.with_context(skip_account_move_synchronization=True).write({
                            'date_maturity': new_date_maturity
                        })
                        _logger.info(f'Updated date_maturity for line {line.id} to {new_date_maturity} (from receipt date)')
                
                # Cập nhật tất cả receivable/payable lines có cùng partner
                receivable_payable_lines = self.line_ids.filtered(
                    lambda l: l.account_id.account_type in ['asset_receivable', 'liability_payable'] and l.partner_id
                )
                if receivable_payable_lines and invoice_payment_terms:
                    # Lấy ngày đến hạn xa nhất
                    max_due_date = max(fields.Date.to_date(term.get('date')) for term in invoice_payment_terms)
                    for line in receivable_payable_lines:
                        if line.date_maturity != max_due_date:
                            line.with_context(skip_account_move_synchronization=True).write({
                                'date_maturity': max_due_date
                            })
                            _logger.info(f'Updated date_maturity for receivable/payable line {line.id} to {max_due_date}')
        
        return True

    def recompute_all_payment_terms_lines(self):
        """Tính toán lại payment terms lines (bao gồm date_maturity) cho tất cả hóa đơn"""
        moves = self.search([
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '=', 'posted')
        ])
        _logger.info(f'Recomputing payment terms lines for {len(moves)} invoices')
        for move in moves:
            _logger.info(f'Recomputing payment terms lines for invoice {move.name}')
            move._recompute_payment_terms_lines()
        _logger.info('Finished recomputing payment terms lines')
        return True

    def update_date_maturity_from_receipt_date(self):
        """
        Cập nhật date_maturity cho hóa đơn hiện tại dựa trên ngày nhận hàng
        Method này có thể gọi từ UI hoặc script
        """
        for move in self:
            if move.state == 'posted':
                _logger.info(f'Updating date_maturity for invoice {move.name} from receipt date')
                move._recompute_payment_terms_lines()
        return True

    def update_all_date_maturity_from_receipt_date(self):
        """
        Cập nhật date_maturity cho tất cả hóa đơn dựa trên ngày nhận hàng
        Chỉ chạy khi cấu hình payment_term_calculation = 'receipt_date'
        """
        payment_term_calculation = self.env['ir.config_parameter'].sudo().get_param('nsgerp.payment_term_calculation', 'invoice_date')
        
        if payment_term_calculation != 'receipt_date':
            _logger.info('Payment term calculation is not set to receipt_date, skipping update')
            return False
            
        moves = self.search([
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '=', 'posted'),
            ('order_received_date', '!=', False)
        ])
        
        _logger.info(f'Updating date_maturity for {len(moves)} invoices from receipt date')
        for move in moves:
            _logger.info(f'Updating date_maturity for invoice {move.name}')
            move._recompute_payment_terms_lines()
        _logger.info('Finished updating all date_maturity from receipt date')
        return True

    def action_update_date_maturity(self):
        """
        Action button để cập nhật date_maturity cho hóa đơn hiện tại
        """
        self.update_date_maturity_from_receipt_date()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Thành công',
                'message': 'Đã cập nhật ngày đến hạn thanh toán',
                'type': 'success'
            }
        }

    def recompute_all_order_received_date(self):
        """
        Tính toán lại ngày nhận hàng cho tất cả hóa đơn đã posted
        
        Method này hữu ích khi:
        - Cập nhật logic compute mới
        - Fix dữ liệu thiếu order_received_date
        - Migration hoặc data cleanup
        
        Returns:
            bool: True nếu thành công
        """
        moves = self.search([
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '=', 'posted')
        ])
        _logger.info(f'Recomputing order_received_date for {len(moves)} invoices')
        
        for move in moves:
            _logger.info(f'Recomputing order_received_date for invoice {move.name}')
            move._compute_order_received_date()
            
        _logger.info('Finished recomputing order_received_date')
        return True

    def recompute_order_received_date(self):
        """
        Tính toán lại ngày nhận hàng cho hóa đơn hiện tại
        
        Method này có thể được gọi từ:
        - UI button
        - XML-RPC script
        - Manual debugging
        
        Returns:
            bool: True nếu thành công
        """
        for move in self:
            _logger.info(f'Recomputing order_received_date for invoice {move.name}')
            move._compute_order_received_date()
            
        _logger.info('Finished recomputing order_received_date')
        return True