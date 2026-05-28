# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class AccountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    lending_days = fields.Integer(u'Thời hạn thanh toán', required=1, default=15)
    lending_rate = fields.Float(u'Lãi vay theo ngày (%)', digits=(16, 3))
    purchase_default = fields.Boolean('Purchase Order Default')