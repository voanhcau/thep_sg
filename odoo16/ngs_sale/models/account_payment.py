# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)
from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    commission_tool_id = fields.Many2one('sale.commission.tool', string=u'Phiếu hoa hồng')
    user_id = fields.Many2one('res.users', string='Người tạo thanh toán', default=lambda self: self.env.user)
    salesperson_id = fields.Many2one('res.users', string='Nhân viên kinh doanh', tracking=True)

    @api.model
    def default_get(self, fields_list):
        """Override default_get to set user_id and salesperson_id from partner_id.user_id if partner exists"""
        result = super().default_get(fields_list)
        
        # Nếu có partner_id trong context hoặc default values
        partner_id = result.get('partner_id') or self.env.context.get('default_partner_id')
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            if partner.user_id:
                if 'user_id' in fields_list:
                    result['user_id'] = self.env.user.id
                if 'salesperson_id' in fields_list:
                    result['salesperson_id'] = partner.user_id.id
        
        return result

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Update user_id and salesperson_id when partner changes"""
        if self.partner_id and self.partner_id.user_id:
            self.salesperson_id = self.partner_id.user_id

    def _trigger_invoice_actual_payment_days_recompute(self):
        """Trigger recomputation of actual_payment_days for related invoices"""
        _logger.info('=== BẮT ĐẦU TÍNH TOÁN SỐ NGÀY TRẢ THỰC TẾ ===')
        for payment in self:
            payment.move_id._compute_actual_payment_days()

    def write(self, vals):
        """Override write to trigger recomputation when payment changes"""
        result = super().write(vals)
        
        # Trigger recomputation nếu có thay đổi về state hoặc date
        if 'state' in vals or 'date' in vals:
            self._trigger_invoice_actual_payment_days_recompute()
        return result

    def action_post(self):
        """Override action_post to trigger recomputation when payment is posted"""
        result = super().action_post()
        self._trigger_invoice_actual_payment_days_recompute()
        return result

    def action_draft(self):
        """Override action_draft to trigger recomputation when payment is set to draft"""
        result = super().action_draft()
        self._trigger_invoice_actual_payment_days_recompute()
        return result

    def action_cancel(self):
        """Override action_cancel to trigger recomputation when payment is cancelled"""
        result = super().action_cancel()
        self._trigger_invoice_actual_payment_days_recompute()
        return result