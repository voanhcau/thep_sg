# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare


class ProductPriceList(models.Model):
    _inherit = 'product.pricelist'

    type = fields.Selection([
        ('sale', u'Bảng giá bán'),
        ('purchase', u'Bảng giá mua'),
    ], default='sale', string=u'Loại bảng giá')


class ProductPriceListItem(models.Model):
    _inherit = 'product.pricelist.item'

    discount_value = fields.Float('Chiết khấu tiền mặt')

    def _compute_price(self, product, quantity, uom, date, currency=None):
        price = super(ProductPriceListItem, self)._compute_price(product=product, quantity=quantity, uom=uom, date=date,
                                                                 currency=currency)
        if self.compute_price == 'formula' and self.discount_value != 0:
            price -= self.discount_value
        return price
