# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    quantity_supplier = fields.Float(u'Khối lượng nhà cung cấp (công bố)')
    quantity_tcvn = fields.Float(u'Khối lượng theo TCVN')
    quantity_another = fields.Float(u'SL cây/bó')
    is_commission = fields.Boolean(u'Là sản phẩm hoa hồng')

    def import_update_quantity_supplier_and_tcvn(self, vals={}):
        _logger.info(vals)
        default_code = vals.get('default_code', None)
        if default_code:
            products = self.search([
                ('default_code', '=', default_code)
            ])
            if not products:
                _logger.error('%s not found in product' % default_code)
                return False
            else:
                value = {
                    'quantity_supplier': vals.get('quantity_supplier'),
                    'quantity_tcvn': vals.get('quantity_tcvn'),
                    'quantity_another': vals.get('quantity_another', 0),
                }
                _logger.info(value)
                products.write(value)
                _logger.info(
                    'update quantity_supplier and quantity_another and quantity_tcvn done for code %s' % default_code)
        else:
            _logger.error('default_code not found')
            return False
        return True

    def import_product_supplierinfo(self, vals={}):
        default_code = vals.get('default_code', None)
        vat = vals.get('vat', None)
        product_code = vals.get('product_code', None)
        products = self.search([
            ('default_code', '=', default_code)
        ])
        if not products:
            _logger.error('not found product have default code {0}'.format(default_code))
            return False
        else:
            partners = self.env['res.partner'].search([
                ('vat', 'ilike', vat)
            ])
            if not partners:
                _logger.error('not found partners have vat {0}'.format(vat))
                return False
            else:
                _logger.info('-------------------------------')
                product_supplierinfos = self.env['product.supplierinfo'].search([
                    ('product_code', 'ilike', product_code),
                    ('partner_id', '=', partners[0].id),
                    ('product_tmpl_id', '=', products[0].id)
                ])
                vals = {
                    'partner_id': partners[0].id,
                    'product_tmpl_id': products[0].id,
                    'product_code': product_code
                }
                _logger.info(vals)
                if product_supplierinfos:
                    product_supplierinfos.write(vals)
                    _logger.info('update supplierinfo {0}'.format(product_supplierinfos))
                else:
                    product_supplierinfos = self.env['product.supplierinfo'].create(vals)
                    _logger.info('add new supplierinfo {0}'.format(product_supplierinfos))
        return True
