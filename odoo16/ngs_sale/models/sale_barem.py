# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare


class SaleBarem(models.Model):
    _name = 'sale.barem'
    _description = u"Nơi lưu trữ barem nhà máy (đã chuyển về lưu thẳng trên res.partner)"

    supplier_id = fields.Many2one('res.partner', u'Nhà cung cấp')
    code = fields.Char(u'Mã', required=1)
    size = fields.Char(u'Phi', required=1)
    product_id = fields.Many2one('product.product', string=u'Sản phẩm')
    quantity_supplier = fields.Float(u'Khối lượng nhà cung cấp (công bố)')
    quantity_tcvn = fields.Float(u'Khối lượng theo TCVN')


