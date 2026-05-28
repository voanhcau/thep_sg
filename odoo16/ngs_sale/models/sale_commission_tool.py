# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)


class SaleCommissionRate(models.Model):
    _name = 'sale.commission.rate'
    _description = u"Bảng quy định hoa hồng theo tháng/quý"

    name = fields.Char(u'Tên', required=1)
    from_qty = fields.Integer(u'Khối lượng từ', required=1)
    to_qty = fields.Integer(u'Khối lượng đến', required=1)
    supplier_id = fields.Many2one('res.partner', u'Nhà cung cấp', required=1)
    rate = fields.Integer(u'Hoa hồng (đ / kg)', required=1)
    type = fields.Selection([
        ('monthly', u'Hàng tháng'),
        ('quarterly', u'Theo quý')
    ], default='monthly', string=u'Chu kỳ', required=1)


class SaleCommissionTool(models.Model):
    _name = "sale.commission.tool"
    _description = u"Chạy lại giá vốn, từ chiết khấu nhà cung cấp theo tháng / quý"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(u'Tên', required=1)
    from_dt = fields.Datetime(u'Từ ngày', required=1, default=lambda self: fields.Datetime.now().replace(hour=17, minute=0, second=0))
    to_dt = fields.Datetime(u'Đến ngày', required=1, default=lambda self: fields.Datetime.now().replace(hour=16, minute=59, second=59))
    state = fields.Selection([
        ('draft', u'Nháp'),
        ('request', u'Yêu cầu duyệt'),
        ('approved', u'Đã duyệt')
    ], default='draft', string=u'Trạng thái')
    request_user_id = fields.Many2one('res.users', u'Người thực hiện')
    request_dt = fields.Datetime(u'Thời gian yêu cầu')
    approve_user_id = fields.Many2one('res.users', u'Người duyệt')
    approve_dt = fields.Datetime(u'Thời gian duyệt')
    type = fields.Selection([
        ('monthly', u'Hàng tháng'),
        ('quarterly', u'Theo quý')
    ], default='monthly', string=u'Chu kỳ', required=1)
    sale_ids = fields.One2many(
        'sale.order',
        'commission_tool_id',
        string=u'Dựa trên đơn hàng'
    )
    invoice_ids = fields.One2many(
        'account.move',
        'commission_tool_id',
        string=u'Dựa trên hoá đơn'
    )
    commission_ids = fields.One2many(
        'sale.commission.user',
        'commission_tool_id',
        string=u'Hoa hồng cho nhân viên'
    )
    commission_config_ids = fields.One2many(
        'sale.commission.config',
        'commission_tool_id',
        string=u'Cấu hình chiết khấu'
    )
    journal_id = fields.Many2one(
        'account.journal',
        string=u'Sổ nhật ký',
        help='Để ghi nhận bút toán hoa hồng',
        required=False
    )
    payment_ids = fields.One2many(
        'account.payment',
        'commission_tool_id',
        string=u'Phiếu chi hoa hồng'
    )
    tag_id = fields.Many2one('crm.tag', string=u'Thẻ', help=u'Lọc theo thẻ')
    apply_po_commission = fields.Boolean(u'Áp CK cho cả PO', default=False, help=u'Áp dụng chiết khấu cho cả đơn mua hàng')
    purchase_ids = fields.One2many(
        'purchase.order',
        'commission_tool_id',
        string=u'Dựa trên đơn mua hàng'
    )

    def action_approve(self):
        self.write({
            'approve_user_id': self.env.user.id,
            'approve_dt': fields.Datetime.now(),
            'state': 'approved'
        })

    def action_reset(self):
        self.write({
            'state': 'draft'
        })

    def action_cancel(self):
        for tool in self:
            tool.commission_ids.unlink()
            tool.sale_ids.write({'commission_tool_id': None})
            tool.invoice_ids.write({'commission_tool_id': None})
            tool.purchase_ids.write({'commission_tool_id': None})
            self.env['sale.order'].search([
                ('commission_tool_id', '=', tool.id)
            ]).write({
                'commission_tool_id': None
            })
            tool.sale_ids.write({
                'commission_tool_id': None
            })
            tool.purchase_ids.write({
                'commission_tool_id': None
            })
            for commission_config in tool.commission_config_ids:
                product_category = commission_config.category_id
                childs_category = self.env['product.category'].search([
                    ('complete_name', 'ilike', product_category.complete_name),
                ])
                childs_category_ids = [categ.id for categ in childs_category]
                # Thêm category gốc vào danh sách
                if product_category.id not in childs_category_ids:
                    childs_category_ids.append(product_category.id)
                _logger.info('childs_category_ids {0}'.format(childs_category_ids))
                if childs_category_ids:
                    # Process purchase sales lines
                    lines = self.env['sale.order.line'].search([
                        ('order_id', 'in', tool.sale_ids.ids),
                        ('product_id', '!=', None),
                        ('product_id.categ_id', '!=', None),
                        ('product_id.categ_id', 'in', childs_category_ids),
                    ])
                    lines.write({
                        'supplier_discount_peer_month': 0,
                        'supplier_discount_peer_quarter': 0,
                        'discount_value': 0,
                    })

                    # Process purchase orders lines
                    po_lines = self.env['purchase.order.line'].search([
                        ('order_id', 'in', tool.purchase_ids.ids),
                        ('product_id', '!=', None),
                        ('product_id.categ_id', '!=', None),
                        ('product_id.categ_id', 'in', childs_category_ids),
                    ])
                    po_lines.write({
                        'discount_value': 0,
                    })
        return True

    def action_compute_commission(self):
        for tool in self:
            tool.commission_ids.unlink()
            commission_peer_user = {}
            total_qty_peer_user = {}
            matched_sales = self.env['sale.order']
            purchases = self.env['purchase.order']
            invoices = self.env['account.move']
            tool.commission_ids.unlink()
            tool.sale_ids.write({'commission_tool_id': None})
            tool.purchase_ids.write({'commission_tool_id': None})
            tool.invoice_ids.write({'commission_tool_id': None})
            self.env['sale.order'].search([
                ('commission_tool_id', '=', tool.id)
            ]).write({
                'commission_tool_id': None
            })
            self.env['purchase.order'].search([
                ('commission_tool_id', '=', tool.id)
            ]).write({
                'commission_tool_id': None
            })
            tool.write({
                'request_user_id': self.env.user.id,
                'request_dt': fields.Datetime.now(),
            })
            for commission_config in tool.commission_config_ids:
                product_category = commission_config.category_id
                childs_category = self.env['product.category'].search([
                    ('complete_name', 'ilike', product_category.complete_name),
                ])
                childs_category_ids = [categ.id for categ in childs_category]
                # Thêm category gốc vào danh sách để đảm bảo lọc được cả sản phẩm thuộc category gốc
                if product_category.id not in childs_category_ids:
                    childs_category_ids.append(product_category.id)
                _logger.info('childs_category_ids {0}'.format(childs_category_ids))
                if childs_category_ids:
                    # Filter sales orders
                    domain = [
                        ('date_order', '>=', tool.from_dt),
                        ('date_order', '<=', tool.to_dt),
                        ('state', 'in', ['sale', 'done', 'approved']),
                        ('auto_purchase_order_id', '!=', None),
                        ('auto_purchase_order_id.partner_id', '=', commission_config.supplier_id.id),
                        ('user_id', '!=', None)
                    ]
                    # Don't filter by tag in the domain, we'll do it after search
                    if tool.tag_id:
                        domain.append(('tag_ids', 'in', [tool.tag_id.id]))
                    sales = self.env['sale.order'].search(domain)
                    
                    # Log initial sales count for debugging
                    _logger.info('Initial sales count before tag filtering: %s', len(sales))
                    
                    # Log chi tiết childs_category_ids để dễ dàng debug
                    _logger.info('childs_category_ids: %s', childs_category_ids)
                    for cat_id in childs_category_ids:
                        cat = self.env['product.category'].browse(cat_id)
                        _logger.info('  - Category ID: %s, Name: %s', cat_id, cat.complete_name)
                    
                    # Log chi tiết từng sale order và order lines để kiểm tra việc match category
                    for sale in sales:
                        _logger.info('Sale Order: %s, Partner: %s', sale.name, sale.partner_id.name)
                        for line in sale.order_line:
                            if line.product_id and line.product_id.categ_id:
                                _logger.info('  - Line ID: %s, Product: %s, Category: %s, Category ID: %s, Is in childs_category_ids: %s, childs_category_ids: %s',
                                    line.id,
                                    line.product_id.name,
                                    line.product_id.categ_id.complete_name,
                                    line.product_id.categ_id.id,
                                    line.product_id.categ_id.id in childs_category_ids,
                                    childs_category_ids
                                )
                    
                    sale_ids = [s.id for s in sales]

                    # Filter purchase orders if apply_po_commission is True
                    if tool.apply_po_commission:
                        po_domain = [
                            ('date_approve', '>=', tool.from_dt),
                            ('date_approve', '<=', tool.to_dt),
                            ('state', 'in', ['purchase', 'done']),
                            ('partner_id', '=', commission_config.supplier_id.id)
                        ]
                        if tool.tag_id:
                            po_domain.append(('tag_ids', 'in', [tool.tag_id.id]))
                        purchases = self.env['purchase.order'].search(po_domain)
                        purchase_ids = [p.id for p in purchases]

                    # Process sale order lines
                    lines = self.env['sale.order.line'].search([
                        ('order_id', 'in', sale_ids),
                        ('product_id', '!=', None),
                        ('product_id.categ_id', '!=', None),
                        ('product_id.categ_id', 'in', childs_category_ids),
                    ])
                    _logger.info('lines will apply discount and commission {0}'.format(lines))
                    # Tổng hợp các đơn hàng thỏa mãn điều kiện vào matched_sales
                    for line in lines:
                        matched_sales += line.order_id
                        invoices += line.order_id.invoice_ids
                        if not total_qty_peer_user.get(line.order_id.user_id.id, None):
                            total_qty_peer_user[line.order_id.user_id.id] = line.product_uom_qty
                        else:
                            total_qty_peer_user[line.order_id.user_id.id] += line.product_uom_qty
                    supplier_discount = commission_config.supplier_discount
                    for line in lines:
                        line.discount_value += supplier_discount

                    # Process purchase order lines if apply_po_commission is True
                    if tool.apply_po_commission and purchases:
                        po_lines = self.env['purchase.order.line'].search([
                            ('order_id', 'in', purchase_ids),
                            ('product_id', '!=', None),
                            ('product_id.categ_id', '!=', None),
                            ('product_id.categ_id', 'in', childs_category_ids),
                        ])
                        for line in po_lines:
                            line.discount_value += supplier_discount

            # Kiểm tra nếu không có đơn hàng nào thỏa mãn điều kiện
            if len(matched_sales) == 0 and (not tool.apply_po_commission or len(purchases) == 0):
                raise UserError(u'Không có đơn hàng được áp dụng')
            # Tính toán hoa hồng cho từng nhân viên
            for sale in matched_sales:
                if not commission_peer_user.get(sale.user_id.id, None):
                    commission_peer_user[sale.user_id.id] = sale.seller_commission
                else:
                    commission_peer_user[sale.user_id.id] += sale.seller_commission
            _logger.info('commission_peer_user {0}'.format(commission_peer_user))
            # Tạo bản ghi hoa hồng cho từng nhân viên
            for seller_id, seller_commission in commission_peer_user.items():
                vals = {
                    'commission_tool_id': tool.id,
                    'seller_commission': seller_commission,
                    'seller_id': seller_id,
                    'total_quantity': total_qty_peer_user.get(seller_id, 0),
                    'user_id': self.env.user.id,
                }
                self.env['sale.commission.user'].create(vals)
            # Cập nhật commission_tool_id cho các đơn hàng thỏa mãn điều kiện
            matched_sales.write({'commission_tool_id': tool.id})
            if tool.apply_po_commission:
                purchases.write({'commission_tool_id': tool.id})
            invoices.write({'commission_tool_id': tool.id})
            tool.write({
                'state': 'request',
                'request_dt': fields.Datetime.now(),
                'request_user_id': self.env.user.id
            })
        return True

    def make_payment(self):
        self.ensure_one()
        if not self.journal_id:
            raise UserError(_('Vui lòng chọn sổ nhật ký trước khi xuất phiếu chi!'))
        for result in self.commission_ids:
            accounting_partner = self.env["res.partner"]._find_accounting_partner(result.seller_id.partner_id)
            destination_account = accounting_partner.property_account_receivable_id
            payments = self.env['account.payment'].search([
                ('commission_tool_id', '=', self.id),
                ('partner_id', '=', result.seller_id.partner_id.id)
            ])
            payment_vals = {
                'amount': abs(result.seller_commission),
                'partner_id': result.seller_id.partner_id.id,
                'journal_id': self.journal_id.id,
                'destination_account_id': destination_account.id,
                'ref': _('%s') % (self.name),
                'payment_type': 'outbound',
                'commission_tool_id': self.id,
            }
            if payments:
                payments.write(payment_vals)
            else:
                self.env['account.payment'].create(payment_vals)
        return


class SaleCommissionUser(models.Model):
    _name = 'sale.commission.user'
    _description = u"Chạy lại giá vốn, từ chiết khấu nhà cung cấp theo tháng / quý"

    seller_id = fields.Many2one('res.users', u'Nhân viên kinh doanh', required=1)
    user_id = fields.Many2one('res.users', u'Người thực hiện')
    total_quantity = fields.Integer(u'Tổng kg bán ra', required=1)
    seller_commission = fields.Integer(u'Hoa hồng')
    commission_tool_id = fields.Many2one('sale.commission.tool', required=1, string='Phiếu hoa hồng')
    amount_total = fields.Integer(u'Hoa hồng nhân được')


class SaleCommissionConfig(models.Model):
    _name = "sale.commission.config"
    _description = u"Thiết lập chiết khấu theo danh mục"

    supplier_id = fields.Many2one('res.partner', u'Nhà cung cấp', required=1)
    supplier_discount = fields.Integer(u'Chiếu khấu nhà cung cấp  (đ/kg)', required=1)
    category_id = fields.Many2one('product.category', string=u'Danh mục', required=1)
    commission_tool_id = fields.Many2one('sale.commission.tool', required=1, string=u'Phiếu hoa hồng')
