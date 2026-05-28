# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class ResPartnerType(models.Model):
    _name = 'res.partner.type'
    _description = u"Phân loại khách hàng, để tính hoa hồng"

    name = fields.Char(u'Tên')
    commission_type = fields.Selection([
        ('value', u'đ / kg'),
        ('percent', u' % ')
    ], default='percent', string=u'Loại hoa hồng')
    commission = fields.Float(u'Hoa hồng')
    commission_type_order = fields.Selection([
        ('margin', u'Dựa trên lợi nhuận'),
        ('total', u'Giá trị đơn hàng')
    ], default='margin', required=1, string=u'Hoa hồng dựa trên')
    is_default = fields.Boolean(u'Dùng làm mặc định', help=u'Dùng làm mặc định khi tạo mới khách hàng')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    type_id = fields.Many2one('res.partner.type', string=u'Loại khách hàng')
    
    # Thông tin hợp đồng
    contract_number = fields.Char(string=u'Số hợp đồng', help=u'Số hợp đồng ký kết với khách hàng')
    contract_from_date = fields.Date(string=u'Từ ngày', help=u'Ngày bắt đầu hiệu lực hợp đồng')
    contract_to_date = fields.Date(string=u'Đến ngày', help=u'Ngày kết thúc hiệu lực hợp đồng')
    contract_representative = fields.Char(string=u'Đại diện', help=u'Tên người đại diện ký hợp đồng')
    contract_position = fields.Char(string=u'Chức vụ', help=u'Chức vụ của người đại diện')
    max_overdue_days = fields.Integer(
        u'Ngày quá hạn', 
        compute='_compute_max_overdue_days',
        store=True,
        index=True,
        help=u'Số ngày quá hạn tối đa của các hóa đơn')
    total_due = fields.Monetary(
        compute='_compute_total_due',
        store=True,
        string="Dư nợ",
        groups='account.group_account_readonly,account.group_account_invoice')
    total_overdue = fields.Monetary(
        compute='_compute_total_due',
        store=True,
        string="Tổng Quá Hạn",
        groups='account.group_account_readonly,account.group_account_invoice')

    @api.depends('unreconciled_aml_ids.amount_residual', 
                 'unreconciled_aml_ids.blocked', 
                 'unreconciled_aml_ids.date_maturity', 
                 'followup_next_action_date')
    @api.depends_context('company', 'allowed_company_ids')
    def _compute_total_due(self):
        _logger.info("Starting _compute_total_due computation")
        today = fields.Date.context_today(self)
        _logger.info(f"Today's date: {today}")
        
        for partner in self:
            _logger.info(f"Processing partner: {partner.name} (ID: {partner.id})")
            total_overdue = 0
            total_due = 0
            aml_count = len(partner.unreconciled_aml_ids)
            _logger.info(f"Partner {partner.name} has {aml_count} unreconciled account move lines")
            
            for aml in partner.unreconciled_aml_ids:
                is_overdue = today > aml.date_maturity if aml.date_maturity else today > aml.date
                amount_residual = aml.amount_residual_currency
                total_due += amount_residual
                
                _logger.debug(f"AML ID: {aml.id}, Date: {aml.date}, Date Maturity: {aml.date_maturity}, "
                             f"Amount Residual: {amount_residual}, Is Overdue: {is_overdue}")
                
                if is_overdue:
                    total_overdue += amount_residual
                    _logger.debug(f"Added {amount_residual} to overdue amount")
            
            partner.total_due = total_due
            partner.total_overdue = total_overdue
            _logger.info(f"Partner {partner.name} - Total Due: {total_due}, Total Overdue: {total_overdue}")
        
        _logger.info("Completed _compute_total_due computation")

    @api.depends('unreconciled_aml_ids', 
                 'unreconciled_aml_ids.date_maturity', 
                 'unreconciled_aml_ids.amount_residual',
                 'unreconciled_aml_ids.date',
                 'followup_next_action_date')
    @api.depends_context('company', 'allowed_company_ids')
    def _compute_max_overdue_days(self):
        """Tự động tính lại khi có thay đổi ở hóa đơn ảnh hưởng đến logic ngày quá hạn"""
        today = fields.Date.context_today(self)
        
        for partner in self:
            partner.max_overdue_days = 0
            max_days_overdue = 0
            for aml in partner.unreconciled_aml_ids:
                # Kiểm tra quá hạn: có date_maturity và đã quá hạn, số tiền còn lại >= 0
                if aml.date_maturity and aml.date_maturity < today and aml.amount_residual >= 0:
                    days_overdue = (today - aml.date_maturity).days
                    if days_overdue > max_days_overdue:
                        max_days_overdue = days_overdue
            partner.max_overdue_days = max_days_overdue

    @api.model_create_multi
    def create(self, vals_list):
        for val in vals_list:
            if not val.get('type_id', None):
                types = self.env['res.partner.type'].search([('is_default', '=', True)])
                if types:
                    val.update({
                        'type_id': types[0].id
                    })
        return super().create(vals_list)
    
    def open_partner_reconciliation(self):
        self.ensure_one()
        # Create a wizard instance with default values
        wizard = self.env['account.partner.reconciliation'].create({
            'partner_id': self.id,
            'company_id': self.env.company.id,
        })
        # Return action to open the wizard
        return {
            'name': _('Biên bản đối chiếu công nợ'),
            'view_mode': 'form',
            'res_model': 'account.partner.reconciliation',
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_partner_id': self.id}
        }

    def action_recompute_overdue_days(self):
        """Tính lại ngày quá hạn"""
        try:
            self._compute_max_overdue_days()
            self._compute_total_due()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành công'),
                    'message': _('Đã tính lại số ngày quá hạn'),
                    'sticky': False,
                    'type': 'success',
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Lỗi'),
                    'message': _('Không thể tính lại số ngày quá hạn: %s') % str(e),
                    'sticky': True,
                    'type': 'danger',
                }
            }

