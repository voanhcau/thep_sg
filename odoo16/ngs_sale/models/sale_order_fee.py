# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare


class SaleOrderFee(models.Model):
    _name = 'sale.order.fee'
    _description = u"Chi phí của đơn hàng"

    name = fields.Selection([
        ('ship', u'Vận chuyển'),
        ('commission', u'Hoa hồng'),
        ('move', u'Bẻ'),
        ('other', u'Khác')
    ], required=True, string=u'Tên')
    sale_id = fields.Many2one('sale.order', required=True)
    amount = fields.Float('Tổng chi phí', required=True)

