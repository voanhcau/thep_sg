# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class InvoicePaymentAnalysisReport(models.Model):
    _name = 'invoice.payment.analysis.report'
    _description = 'Báo cáo phân tích thanh toán hóa đơn'
    _auto = False
    _order = 'name'

    invoice_id = fields.Many2one('account.move', string='Hóa đơn', readonly=True)
    name = fields.Char(string='Số hóa đơn', readonly=True)
    invoice_date = fields.Date(string='Ngày hóa đơn', readonly=True)
    delivery_date = fields.Date(string='Ngày nhận hàng', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Khách hàng/Nhà cung cấp', readonly=True)
    partner_name = fields.Char(string='Tên đối tác', readonly=True)
    amount_total = fields.Float(string='Tổng tiền', readonly=True)
    amount_residual = fields.Float(string='Số tiền còn lại', readonly=True)
    amount_paid = fields.Float(string='Số tiền đã thanh toán', readonly=True)
    payment_state = fields.Selection([
        ('not_paid', 'Chưa thanh toán'),
        ('in_payment', 'Đang thanh toán'),
        ('paid', 'Đã thanh toán'),
        ('partial', 'Thanh toán một phần'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
        ('reversed', 'Đảo ngược'),
    ], string='Trạng thái thanh toán', readonly=True)
    
    # Thông tin thời hạn thanh toán
    invoice_date_due = fields.Date(string='Ngày phải trả', readonly=True)
    payment_term_id = fields.Many2one('account.payment.term', string='Điều khoản thanh toán', readonly=True)
    
    # Thông tin phân tích
    payment_delay = fields.Integer(string='Số ngày phải trả', readonly=True, 
                                 help='Số ngày trên điều khoản thanh toán')
    actual_payment_days = fields.Float(string='Số ngày TT quá hạn', readonly=True,
                                      digits=(16, 2),
                                      help='Số ngày quá hạn tính theo công thức weighted: (Ngày TT L1 - Ngày HĐ)*(số tiền TT L1/Tổng tiền) + ... - Thời hạn TT')
    is_overdue = fields.Boolean(string='Quá hạn', readonly=True)
    move_type = fields.Selection([
        ('entry', 'Bút toán'),
        ('out_invoice', 'Hóa đơn khách hàng'),
        ('out_refund', 'Hoàn tiền khách hàng'),
        ('in_invoice', 'Hóa đơn nhà cung cấp'),
        ('in_refund', 'Hoàn tiền nhà cung cấp'),
    ], string='Loại hóa đơn', readonly=True)
    
    # Thông tin công ty
    company_id = fields.Many2one('res.company', string='Công ty', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Tiền tệ', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'invoice_payment_analysis_report')
        self._cr.execute("""
            CREATE OR REPLACE VIEW invoice_payment_analysis_report AS (
                SELECT 
                    row_number() over(ORDER BY am.invoice_date DESC, am.name) as id,
                    am.id as invoice_id,
                    am.name as name,
                    am.invoice_date,
                    am.order_received_date as delivery_date,
                    am.partner_id,
                    rp.name as partner_name,
                    am.amount_total,
                    am.amount_residual,
                    (am.amount_total - am.amount_residual) as amount_paid,
                    am.payment_state,
                    am.invoice_date_due,
                    am.invoice_payment_term_id as payment_term_id,
                    COALESCE(aptl.max_days, 0) as payment_delay,
                    COALESCE(am.actual_payment_days, 0) as actual_payment_days,
                    CASE 
                        WHEN am.payment_state != 'paid' AND am.invoice_date_due IS NOT NULL 
                        AND am.invoice_date_due < CURRENT_DATE
                        THEN true 
                        ELSE false 
                    END as is_overdue,
                    am.move_type,
                    am.company_id,
                    am.currency_id
                FROM account_move am
                LEFT JOIN res_partner rp ON am.partner_id = rp.id
                LEFT JOIN (
                    SELECT payment_id, MAX(days) as max_days
                    FROM account_payment_term_line
                    GROUP BY payment_id
                ) aptl ON aptl.payment_id = am.invoice_payment_term_id
                WHERE am.move_type IN ('out_invoice', 'in_invoice')
                AND am.state = 'posted'
                AND am.amount_total > 0
                GROUP BY am.id, am.name, am.invoice_date, am.order_received_date, am.partner_id, rp.name, am.amount_total, am.amount_residual, am.payment_state, am.invoice_date_due, am.invoice_payment_term_id, aptl.max_days, am.actual_payment_days, am.move_type, am.company_id, am.currency_id
            )
        """)

    @api.model
    def action_invoice_payment_analysis(self):
        """Action để mở báo cáo phân tích thanh toán hóa đơn"""
        domain = []
        if self.env.context.get('active_ids'):
            domain = [('invoice_id', 'in', self.env.context.get('active_ids', []))]

        return {
            'name': 'Phân tích thanh toán hóa đơn',
            'type': 'ir.actions.act_window',
            'res_model': 'invoice.payment.analysis.report',
            'view_mode': 'pivot,graph,tree',
            'domain': domain,
            'context': {
                'search_default_overdue': True,
                'search_default_company': True,
                'search_default_partner': True,
                'group_expand': True,
            }
        }