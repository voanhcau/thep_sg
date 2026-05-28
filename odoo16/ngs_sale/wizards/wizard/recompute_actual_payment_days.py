# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class RecomputeActualPaymentDaysWizard(models.TransientModel):
    _name = 'recompute.actual.payment.days.wizard'
    _description = 'Wizard để tính toán lại số ngày trả thực tế'

    def action_recompute_all(self):
        """Tính toán lại số ngày trả thực tế cho tất cả hóa đơn"""
        try:
            # Lấy tất cả hóa đơn đã posted
            invoices = self.env['account.move'].search([
                ('move_type', 'in', ['out_invoice', 'in_invoice']),
                ('state', '=', 'posted')
            ])
            
            _logger.info(f'Bắt đầu tính toán lại số ngày trả thực tế cho {len(invoices)} hóa đơn')
            
            # Tính toán lại cho từng hóa đơn
            for invoice in invoices:
                invoice._compute_actual_payment_days()
            
            _logger.info('Hoàn thành tính toán lại số ngày trả thực tế')
            
            # Hiển thị thông báo thành công
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành công'),
                    'message': _('Đã tính toán lại số ngày trả thực tế cho %d hóa đơn') % len(invoices),
                    'type': 'success',
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error(f'Lỗi khi tính toán lại số ngày trả thực tế: {str(e)}')
            raise UserError(_('Có lỗi xảy ra khi tính toán lại số ngày trả thực tế: %s') % str(e)) 