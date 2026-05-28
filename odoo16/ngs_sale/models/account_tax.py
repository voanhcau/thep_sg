# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools.misc import formatLang

import logging

_logger = logging.getLogger(__name__)


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None):
        datas = super(AccountTax, self)._prepare_tax_totals(base_lines=base_lines, currency=currency, tax_lines=tax_lines)
        datas['amount_tax'] = 0
        for key, values in datas['groups_by_subtotal'].items():
            for value in values:
                datas['amount_tax'] += value['tax_group_amount']
        datas['amount_tax_str'] = formatLang(self.env, datas['amount_tax'], currency_obj=currency)
        return datas

