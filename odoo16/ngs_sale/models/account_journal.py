# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def update_account_move_line(self):
        journals = self.search([('type', '=', 'bank'), ('default_account_id', '!=', None)])
        for jour in journals:
            moves = self.env['account.move'].search([('journal_id', '=', jour.id)])
            for move in moves:
                lines = move.invoice_line_ids.filtered(lambda l: l.account_id and l.account_id.id != jour.default_account_id.id and l.account_id.id != 77 and l.account_id.code in ['1125', '1126'])
                for line in lines:
                    if not line.last_account_id:
                        line.last_account_id = line.account_id.id
                    line.account_id = jour.default_account_id
                    _logger.info('%s-%s-%s' % (move.id, line.account_id.name, jour.default_account_id.name))
        return True
