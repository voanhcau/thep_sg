# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare


class SupplierDeliveryType(models.Model):
    _name = 'supplier.delivery.type'
    _description = u"Quy cách giao hàng của nhà sản xuất"

    name = fields.Char(u'Tên', required=1)
    cost_price = fields.Integer('Giá cộng thêm (nếu có)', help='Giá sẻ đưa vào giá bán')
    is_default = fields.Boolean(u'Sử dụng làm mặc định khi làm đơn bán hàng')


