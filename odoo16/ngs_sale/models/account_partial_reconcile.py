# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    def _trigger_invoice_actual_payment_days_recompute(self):
        """Trigger recomputation of actual_payment_days for related invoices"""
        related_invoices = self.env['account.move']
        
        # Lấy hóa đơn từ debit move
        if self.debit_move_id.move_id.move_type in ['out_invoice', 'in_invoice']:
            related_invoices |= self.debit_move_id.move_id
        
        # Lấy hóa đơn từ credit move
        if self.credit_move_id.move_id.move_type in ['out_invoice', 'in_invoice']:
            related_invoices |= self.credit_move_id.move_id
        
        # Trigger recomputation cho các hóa đơn liên quan
        if related_invoices:
            _logger.info(f'Triggering actual_payment_days recomputation for invoices: {related_invoices.mapped("name")}')
            related_invoices._compute_actual_payment_days()

    def create(self, vals_list):
        """Override create to trigger recomputation when reconciliation is created"""
        result = super().create(vals_list)
        
        # Trigger recomputation cho tất cả reconciliation mới tạo
        for reconcile in result:
            reconcile._trigger_invoice_actual_payment_days_recompute()
        
        return result

    def unlink(self):
        """Override unlink to trigger recomputation when reconciliation is deleted"""
        # Lưu thông tin về các hóa đơn liên quan trước khi xóa
        related_invoices = self.env['account.move']
        for reconcile in self:
            if reconcile.debit_move_id.move_id.move_type in ['out_invoice', 'in_invoice']:
                related_invoices |= reconcile.debit_move_id.move_id
            if reconcile.credit_move_id.move_id.move_type in ['out_invoice', 'in_invoice']:
                related_invoices |= reconcile.credit_move_id.move_id
        
        result = super().unlink()
        
        # Trigger recomputation cho các hóa đơn liên quan
        if related_invoices:
            _logger.info(f'Triggering actual_payment_days recomputation for invoices after reconciliation deletion: {related_invoices.mapped("name")}')
            related_invoices._compute_actual_payment_days()
        
        return result 