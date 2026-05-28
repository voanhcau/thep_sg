# -*- coding: utf-8 -*-
import json

from odoo import models, _, fields


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        result = super()._get_aml_values(options, partner_ids, offset=offset, limit=limit)
        for partner_id in partner_ids:
            if result.get(partner_id, None):
                for value in result.get(partner_id, None):
                    aml_id = value['id']
                    aml = self.env['account.move.line'].browse(aml_id)
                    value['payment_reference'] = aml.move_id.payment_reference
        return result