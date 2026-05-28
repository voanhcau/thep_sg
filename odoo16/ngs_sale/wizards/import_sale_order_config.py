# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import logging
import tempfile
import binascii
import datetime

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug("Cannot `import csv`.")

try:
    import xlrd
except ImportError:
    _logger.debug("Cannot `import xlrd`.")


class ImportSaleOrderConfig(models.Model):
    _name = "import.sale.order.config"
    _description = "Import Sale Order Configuration"
    _check_company_auto = True

    company_id = fields.Many2one('res.company', string=u'Công ty', required=True, default=lambda self: self.env.company)
    payment_term_id = fields.Many2one('account.payment.term', string=u'Điều khoản thanh toán', required=True, check_company=True)
    pricelist_id = fields.Many2one('product.pricelist', string=u'Bảng giá bán', required=True, check_company=True)
    warehouse_id = fields.Many2one('stock.warehouse', string=u'Kho hàng', required=True, check_company=True)
    purchase_pricelist_id = fields.Many2one('product.pricelist', string=u'Bảng giá mua', required=True, check_company=True)