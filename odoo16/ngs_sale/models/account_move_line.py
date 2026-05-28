# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    # Store invoice_date_due từ account.move xuống account.move.line
    invoice_date_due_custom = fields.Date(
        string='Thời hạn thanh toán',
        related='move_id.invoice_date_due_custom',
        store=True,
        help='Ngày đến hạn thanh toán từ hóa đơn liên quan'
    )

    def _trigger_invoice_actual_payment_days_recompute(self):
        """Trigger recomputation of actual_payment_days for related invoices"""
        related_invoices = self.env['account.move']
        
        # Lấy hóa đơn từ move hiện tại
        if self.move_id.move_type in ['out_invoice', 'in_invoice']:
            related_invoices |= self.move_id
        
        # Lấy hóa đơn từ các reconciliation
        for match in self.matched_debit_ids:
            if match.credit_move_id.move_id.move_type in ['out_invoice', 'in_invoice']:
                related_invoices |= match.credit_move_id.move_id
        
        for match in self.matched_credit_ids:
            if match.debit_move_id.move_id.move_type in ['out_invoice', 'in_invoice']:
                related_invoices |= match.debit_move_id.move_id
        
        # Trigger recomputation cho các hóa đơn liên quan
        if related_invoices:
            _logger.info(f'Triggering actual_payment_days recomputation for invoices: {related_invoices.mapped("name")}')
            related_invoices._compute_actual_payment_days()

    def write(self, vals):
        """Override write to trigger recomputation when move line changes"""
        result = super().write(vals)
        
        # Trigger recomputation nếu có thay đổi về reconciliation
        if 'matched_debit_ids' in vals or 'matched_credit_ids' in vals:
            self._trigger_invoice_actual_payment_days_recompute()
        
        return result 