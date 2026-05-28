# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

import logging
import datetime
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)


class PurchaseReportTool(models.Model):
    _name = "purchase.report.tool"
    _description = u"để tính CK, hỗ trợ bán hàng hoặc bảo lãnh giá cho các đơn đã mua"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(u'Tên', required=1)
    partner_ids = fields.Many2many(
        'res.partner',
        string='Nhà cung cấp',
        required=True
    )
    from_dt = fields.Datetime(
        u'Từ ngày',
        default=datetime.datetime.combine(datetime.datetime.today(),
                                          datetime.time(0, 00, 1,
                                                        000000)) - relativedelta(hours=7))
    to_dt = fields.Datetime(
        u'Đến ngày',
        default=datetime.datetime.combine(datetime.datetime.today(),
                                          datetime.time(23, 59, 59,
                                                        999999)) - relativedelta(hours=7))
    invoice_date_from = fields.Date(
        u'Từ ngày (Hóa đơn)',
        help=u'Lọc theo ngày hóa đơn từ ngày này (có thể bỏ trống)')
    invoice_date_to = fields.Date(
        u'Đến ngày (Hóa đơn)',
        help=u'Lọc theo ngày hóa đơn đến ngày này (có thể bỏ trống)')

    product_ids = fields.Many2many(
        'product.product',
        string=u'Sản phẩm'
    )
    categ_ids = fields.Many2many(
        'product.category',
        string=u'Danh mục sản phẩm'
    )
    order_line = fields.One2many(
        'purchase.order.line',
        'report_id',
        string='Chi tiết đơn mua'
    )

    def action_preview_purchase_line(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Chi tiết đơn mua'),
            'res_model': 'purchase.order.line',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.order_line.ids)],
        }
    @api.onchange('categ_ids')
    def _onchange_categ_ids(self):
        if self.categ_ids:
            self.product_ids = [(6, 0, [])]

    @api.onchange('product_ids')
    def _onchange_product_ids(self):
        if self.product_ids:
            self.categ_ids =  [(6, 0, [])]

    def action_building_report(self):
        self.ensure_one()
        self.order_line.write({'report_id': None})
        
        # Xây dựng domain cho date_planned
        date_domain = []
        if self.from_dt:
            date_domain.append(('date_planned', '>=', self.from_dt))
        if self.to_dt:
            date_domain.append(('date_planned', '<=', self.to_dt))
        
        # Tìm purchase orders
        domain = [('partner_id', 'in', [p.id for p in self.partner_ids])]
        domain.extend(date_domain)
        orders = self.env['purchase.order'].search(domain)
        
        # Filter theo ngày hóa đơn nếu có
        if self.invoice_date_from or self.invoice_date_to:
            filtered_orders = self.env['purchase.order']
            for order in orders:
                # Lấy tất cả hóa đơn của đơn hàng
                invoices = order.invoice_ids.filtered(lambda inv: inv.state in ('posted', 'draft'))
                if not invoices:
                    # Nếu không có hóa đơn và có filter ngày hóa đơn, bỏ qua đơn này
                    continue
                
                # Kiểm tra xem có hóa đơn nào thỏa mãn điều kiện ngày không
                invoice_match = False
                for inv in invoices:
                    if inv.invoice_date:
                        if self.invoice_date_from and self.invoice_date_to:
                            # Cả 2 ngày đều có: >= from AND <= to
                            if self.invoice_date_from <= inv.invoice_date <= self.invoice_date_to:
                                invoice_match = True
                                break
                        elif self.invoice_date_from:
                            # Chỉ có from: >= from
                            if inv.invoice_date >= self.invoice_date_from:
                                invoice_match = True
                                break
                        elif self.invoice_date_to:
                            # Chỉ có to: <= to
                            if inv.invoice_date <= self.invoice_date_to:
                                invoice_match = True
                                break
                
                if invoice_match:
                    filtered_orders |= order
            orders = filtered_orders
        
        other_lines = self.env['purchase.order.line']
        for o in orders:
            new_line = o.order_line
            if self.product_ids:
                new_line = o.order_line.filtered(
                    lambda l: l.product_id and l.product_id.id in [p.id for p in self.product_ids])
            if self.categ_ids:
                new_line = o.order_line.filtered(
                    lambda l: l.product_id and l.product_id.categ_id and l.product_id.categ_id.id in [c.id for c in
                                                                                                      self.categ_ids])
            # Filter theo ngày cho order lines
            if self.from_dt or self.to_dt:
                if self.from_dt and self.to_dt:
                    new_line = new_line.filtered(lambda l: l.date_planned >= self.from_dt and l.date_planned <= self.to_dt)
                elif self.from_dt:
                    new_line = new_line.filtered(lambda l: l.date_planned >= self.from_dt)
                elif self.to_dt:
                    new_line = new_line.filtered(lambda l: l.date_planned <= self.to_dt)
            
            if new_line:
                other_lines += new_line
        other_lines.write({'report_id': self.id})
        return True

    def action_reset(self):
        return True
