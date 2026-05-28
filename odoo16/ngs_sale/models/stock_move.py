# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.move'

    quantity_another1 = fields.Integer(
        string='SL',
        help='Số cây/bành lấy từ dòng bán hàng, cho phép chỉnh trên phiếu giao nhận.'
    )

    @api.model
    def create(self, vals):
        # Mặc định copy SL từ sale line nếu chưa được set
        sale_line_id = vals.get('sale_line_id')
        if sale_line_id and vals.get('quantity_another1') is None:
            sale_line = self.env['sale.order.line'].browse(sale_line_id)
            vals['quantity_another1'] = sale_line.quantity_another1
        return super().create(vals)
