# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools

class AccountInvoiceReport(models.Model):
    _inherit = 'account.invoice.report'

    tags_text = fields.Char(string='Thẻ', readonly=True)
    invoice_order_id = fields.Many2one('account.move', string='Hóa đơn đối ứng', readonly=True)
    is_different_month = fields.Boolean(string='Có Hóa đơn tồn kho', readonly=True, 
                                        help='Đánh dấu BILL có INV tương ứng khác tháng (mua tháng trước, bán tháng sau)')
    payment_reference = fields.Char(string='Số hóa đơn', readonly=True)

    def _select(self):
        select_str = super()._select()
        select_str += ", move.tags_text as tags_text,\n"
        select_str += "move.invoice_order_id as invoice_order_id,\n"
        select_str += "move.payment_reference as payment_reference,\n"
        select_str += "CASE\n"
        select_str += "    WHEN move.invoice_order_id IS NOT NULL AND to_char(move.invoice_date, 'YYYY-MM') != to_char(move_opposite.invoice_date, 'YYYY-MM') AND move.invoice_date < move_opposite.invoice_date\n"
        select_str += "    THEN TRUE\n"
        select_str += "    ELSE FALSE\n"
        select_str += "END as is_different_month\n"
        return select_str

    def _from(self):
        from_str = super()._from()
        from_str += """
            LEFT JOIN account_move move_opposite ON move.invoice_order_id = move_opposite.id
        """
        return from_str

    def _where(self):
        return super(AccountInvoiceReport, self)._where()

    def _group_by(self):
        return super(AccountInvoiceReport, self)._group_by() + ", move.tags_text, move.invoice_order_id, is_different_month" 