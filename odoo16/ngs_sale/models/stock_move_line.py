# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    quantity_another1 = fields.Integer(
        string='SL',
        help='Số cây/bành lấy từ dòng bán hàng, cho phép chỉnh trên phiếu giao nhận.'
    )

    @api.model
    def create(self, vals):
        # Mặc định copy SL từ sale line nếu có
        if not vals.get('quantity_another1'):
            # Lấy từ move_id.sale_line_id nếu có
            move_id = vals.get('move_id')
            if move_id:
                move = self.env['stock.move'].browse(move_id)
                if move.sale_line_id and move.sale_line_id.quantity_another1:
                    vals['quantity_another1'] = move.sale_line_id.quantity_another1
        res = super().create(vals)
        # Nếu sau khi create mà vẫn chưa có quantity_another1, thử lấy từ sale_line
        if not res.quantity_another1 and res.move_id and res.move_id.sale_line_id:
            if res.move_id.sale_line_id.quantity_another1:
                res.quantity_another1 = res.move_id.sale_line_id.quantity_another1
        return res

    # @api.model
    # def _auto_populate_quantity_another1_from_sale_line(self):
    #     """Tự động populate quantity_another1 từ sale_line cho các move_line đã tồn tại"""
    #     move_lines = self.search([
    #         ('quantity_another1', '=', 0),
    #         ('move_id.sale_line_id', '!=', False)
    #     ])
    #     for line in move_lines:
    #         if line.move_id and line.move_id.sale_line_id and line.move_id.sale_line_id.quantity_another1:
    #             line.quantity_another1 = line.move_id.sale_line_id.quantity_another1
    #     return len(move_lines)
