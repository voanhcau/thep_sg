# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    def set_master_data(self):
        master_caeg = self.search([
            ('name', '=', 'HP Cuộn D6-8')
        ], limit=1)
        if master_caeg:
            self.search([
                ('id', '!=', master_caeg.id)
            ]).write({
                'property_cost_method': master_caeg.property_cost_method,
                'property_valuation': master_caeg.property_valuation,
                'property_account_income_categ_id': master_caeg.property_account_income_categ_id.id if master_caeg.property_account_income_categ_id else None,
                'property_account_expense_categ_id': master_caeg.property_account_expense_categ_id.id if master_caeg.property_account_expense_categ_id else None,
                'property_stock_valuation_account_id': master_caeg.property_stock_valuation_account_id.id if master_caeg.property_stock_valuation_account_id else None,
                'property_stock_journal': master_caeg.property_stock_journal.id if master_caeg.property_stock_journal else None,
                'property_stock_account_input_categ_id': master_caeg.property_stock_account_input_categ_id.id if master_caeg.property_stock_account_input_categ_id else None,
                'property_stock_account_output_categ_id': master_caeg.property_stock_account_output_categ_id.id if master_caeg.property_stock_account_output_categ_id else None,
            })

        return True
