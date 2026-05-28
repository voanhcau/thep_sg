# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from datetime import datetime, timedelta
from lxml import etree
import json

import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    """
    Class kế thừa từ sale.order của Odoo, bổ sung các chức năng:
    - Quản lý đơn hàng bán với các trường thông tin bổ sung
    - Tính toán lợi nhuận, chiết khấu
    - Tự động tạo đơn mua hàng
    - Quản lý thanh toán và tính lãi vay
    """

    state = fields.Selection(
        selection_add=[
            ('approved', u'Đã duyệt')
        ],
        ondelete={
            'approved': 'set default'
        }
    )
    margin = fields.Monetary(
        u"Lợi nhuận",
        compute='_compute_margin',
        groups="sales_team.group_sale_salesman",
        store=True,
        precompute=True)
    margin_percent = fields.Float(
        u"Lợi nhuận (%)",
        compute='_compute_margin',
        store=True,
        groups="sales_team.group_sale_salesman",
        precompute=True,
        group_operator="avg")

    purchase_pricelist_id = fields.Many2one(
        'product.pricelist',
        domain=[('type', '=', 'purchase')],
        string=u'Bảng giá mua')
    shipping_cost = fields.Float(
        string='XLVC')
    xltl = fields.Float(
        string='XLTL',
        digits=(16, 2),
        help='XLTL (2 số thập phân)')
    sale_type = fields.Selection([
        ('0_1', u'Mua BRNM - Bán BRNM'),
        ('0_2', u'Mua BRNM - Bán TCVN'),
        ('0_3', u'Mua Etiket/KgTT - Bán BRNM'),
        ('0_4', u'Mua Etiket/KgTT - Bán TCVN'),
        ('0_5', u'Mua Etiket/KgTT - Bán Etiket/KgTT'),
    ], default='0_5', string=u'Kiểu mua bán')
    supplier_id = fields.Many2one('res.partner', string=u'Nhà cung cấp')
    sale_description = fields.Text(u'Nội dung và điều khoản bán hàng')
    margin_each_unit = fields.Float(
        u'Lợi nhuận trên 1 KG',
        compute='_compute_margin_each_unit',
        store=True, groups="sales_team.group_sale_salesman")
    seller_commission = fields.Float(
        u'Hoa hồng nhân viên KD',
        compute='_compute_seller_commission',
        store=True,
        groups="sales_team.group_sale_manager"
    )
    no_output_invoice = fields.Boolean(u'Không xuất hoá đơn')
    type_id = fields.Many2one('res.partner.type', string=u'Loại KH (SO)')
    type_partner_id = fields.Many2one(
        'res.partner.type',
        string=u'Loại KH (KH)',
        related='partner_id.type_id',
        readonly=True,
        store=True,
    )
    total_quantity_another1 = fields.Integer('Tổng SL cây/bành', compute='_get_detail_quantity')
    total_quantity_another2 = fields.Integer('Tổng SL cây/bó', compute='_get_detail_quantity')
    total_quantity_another3 = fields.Integer('Tổng SL bó', compute='_get_detail_quantity')
    total_product_uom_qty = fields.Integer('Tổng KL (kg)', compute='_get_detail_quantity')
    commission_tool_id = fields.Many2one('sale.commission.tool', string='Phiếu hoa hồng')
    purchase_ids = fields.One2many(
        'purchase.order',
        'sale_reference_id',
        string='Đơn mua hàng (chi phí)'
    )
    purchase_count = fields.Integer(compute='_purchase_order_count')
    support_user_id = fields.Many2one('res.users', u'Nhân viên hỗ trợ')
    partner_type_id = fields.Many2one(
        'res.partner.type',
        string=u'Loại đối tác',
        related='partner_id.type_id',
        readonly=True,
        store=True,
    )
    invoice_posted_date = fields.Date(
        compute='_get_invoice_information',
        string=u'Ngày thanh toán',
        store=True
    )
    invoice_state = fields.Selection([
        ('not_paid', u'Chưa thanh toán'),
        ('in_payment', u'Đang thanh toán'), 
        ('paid', u'Đã thanh toán'),
        ('partial', u'Thanh toán một phần'),
        ('reversed', u'Đã đảo bút toán'),
        ('invoicing_legacy', u'Hoá đơn từ hệ thống cũ')
    ], compute='_get_invoice_information',
        string=u'Trạng thái thanh toán',
        store=True)
    
    # Field tùy chỉnh thay vì override field core invoice_status
    invoice_status_custom = fields.Selection([
        ('no', u'Chưa có hóa đơn'),
        ('invoiced', u'Chờ thanh toán'),
        ('partial', u'Đã thanh toán 1 phần'),
        ('paid', u'Đã thanh toán'),
        ('reversed', u'Đã hủy thanh toán')
    ], compute='_compute_invoice_status_custom',
        string=u'Trạng thái hóa đơn',
        store=True,
        help=u'Trạng thái hóa đơn tùy chỉnh theo nghiệp vụ thực tế')

    has_purchase = fields.Boolean(
        compute='_has_purchase'
    )
    received_date = fields.Date(string="Ngày nhận hàng")
    interest_amount = fields.Float(
        string="Tổng lãi vay (VNĐ)",
        readonly=True,
        tracking=True,
        copy=False,
        groups="sales_team.group_sale_manager",
        help="Tổng lãi vay được tính dựa trên số ngày chậm thanh toán và số tiền còn nợ."
    )

    interest_per_kg = fields.Float(
        string="Lãi vay trên mỗi kg (VNĐ/kg)",
        readonly=True,
        tracking=True,
        groups="sales_team.group_sale_manager",
        help="Lãi vay trung bình trên mỗi kg của đơn hàng, được tính dựa trên tổng khối lượng."
    )

    total_product_qty = fields.Float(
        string='KL (kg)',
        compute='_compute_total_product_qty',
        store=True,
        help='Automatically computed total product quantity from all sale order lines.'
    )
    total_difference_qty = fields.Float(
        string=u'KL Chênh Lệch',
        compute='_compute_total_difference_qty',
        store=True,
        help='Tổng khối lượng chênh lệch từ tất cả các dòng đơn hàng'
    )

    def action_approve(self):
        """Chuyển trạng thái đơn hàng sang 'Đã duyệt'"""
        return self.write({'state': 'approved'})

    def _has_purchase(self):
        """Kiểm tra xem đơn hàng đã có đơn mua liên kết chưa"""
        for sale in self:
            if sale.auto_purchase_order_id:
                sale.has_purchase = True
            else:
                sale.has_purchase = False

    def get_invoice_information(self):
        """Lấy thông tin hóa đơn của đơn hàng"""
        self._get_invoice_information()

    @api.depends('invoice_ids.payment_state', 'invoice_ids.payment_id', 'invoice_ids.invoice_payments_widget')
    def _get_invoice_information(self):
        """
        Tính toán và cập nhật thông tin thanh toán của đơn hàng:
        - Trạng thái thanh toán
        - Ngày thanh toán
        - Số tiền đã thanh toán
        """
        for order in self:
            _logger.info(f"=== Bắt đầu tính toán thông tin thanh toán cho đơn hàng {order.name} ===")
            order.invoice_state = 'not_paid'
            order.invoice_posted_date = None
            if not order.invoice_ids:
                _logger.info("Không có hoá đơn -> set null")
                continue

            # Lấy hoá đơn cuối cùng
            posted_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            if not posted_invoices:
                _logger.info("Không có hoá đơn đã vào sổ -> set null")
                continue
            last_invoice = posted_invoices[-1]
            _logger.info(f"Hoá đơn cuối: {last_invoice.name}, Trạng thái: {last_invoice.payment_state}")
            
            # Gán trạng thái thanh toán
            order.invoice_state = last_invoice.payment_state

            not_paid_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted' and inv.payment_state != 'paid')
            if not_paid_invoices:
                _logger.info(f"Có {len(not_paid_invoices)} hoá đơn chưa thanh toán: {', '.join(inv.name for inv in not_paid_invoices)}")
                continue
            
            # Chỉ ghi nhận ngày thanh toán khi hoá đơn đã thanh toán đầy đủ
            if last_invoice.payment_state == 'paid':
                # Lấy thông tin thanh toán từ invoice_payments_widget
                payments_widget = last_invoice.invoice_payments_widget
                _logger.info(f"Thông tin thanh toán widget: {payments_widget}")
                
                if payments_widget and isinstance(payments_widget, dict):
                    if payments_widget.get('content'):
                        # Sắp xếp các thanh toán theo ngày và lấy ngày thanh toán cuối cùng
                        sorted_payments = sorted(payments_widget['content'], key=lambda p: p.get('date', ''))
                        _logger.info(f"Danh sách thanh toán đã sắp xếp: {sorted_payments}")
                        
                        if sorted_payments:
                            last_payment = sorted_payments[-1]
                            order.invoice_posted_date = last_payment.get('date')
                            _logger.info(f"Ngày thanh toán cuối cùng: {last_payment.get('date')}")
                        else:
                            _logger.info("Không có thanh toán nào")
                    else:
                        _logger.info("Không có nội dung thanh toán trong widget")
                else:
                    _logger.info("Không có thông tin thanh toán widget")
            else:
                _logger.info(f"Hoá đơn chưa thanh toán đầy đủ (payment_state: {last_invoice.payment_state})")
            
            _logger.info(f"=== Kết quả cuối cùng cho {order.name} ===")
            _logger.info(f"invoice_state: {order.invoice_state}")
            _logger.info(f"invoice_posted_date: {order.invoice_posted_date}")

    @api.depends('invoice_ids', 'invoice_ids.payment_state', 'invoice_ids.state')
    def _compute_invoice_status_custom(self):
        """
        Logic tính toán trạng thái hóa đơn custom theo nghiệp vụ.
        
        ===== LOGIC MỚI =====
        Logic này thay thế hoàn toàn logic Odoo core để phù hợp với nghiệp vụ:
        - no: Chưa tạo hóa đơn hoặc hóa đơn chưa vào sổ
        - invoiced: Đã tạo hóa đơn và vào sổ nhưng chưa thanh toán
        - partial: Đã thanh toán một phần
        - paid: Đã thanh toán đầy đủ
        - reversed: Đã hủy thanh toán
        
        ===== KHÁC BIỆT VỚI ODOO CORE =====
        Odoo core chỉ quan tâm đến việc tạo hóa đơn (qty_to_invoice, qty_invoiced),
        không quan tâm đến thanh toán. Logic này kết hợp cả 2 yếu tố.
        
        ===== TÁC ĐỘNG =====
        - Giải quyết vấn đề trong hình ảnh: PO P06906 và SO S07598
        - Trạng thái hiển thị chính xác theo nghiệp vụ thực tế
        - Tương thích với field invoice_state (trạng thái thanh toán)
        """
        for order in self:
            # ===== BƯỚC 1: KIỂM TRA CÓ HÓA ĐƠN KHÔNG =====
            if not order.invoice_ids:
                # Không có hóa đơn nào → Chưa tạo hóa đơn
                # Trường hợp: SO/PO mới tạo, chưa có hóa đơn
                order.invoice_status_custom = 'no'
                continue
            
            # ===== BƯỚC 2: KIỂM TRA HÓA ĐƠN NHÁP =====
            # Nếu có hóa đơn nháp (draft) thì trạng thái là 'invoiced' (chờ thanh toán)
            draft_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'draft')
            if draft_invoices:
                # Có hóa đơn nháp → Trạng thái: Chờ thanh toán
                order.invoice_status_custom = 'invoiced'
                continue
            
            # ===== BƯỚC 3: LỌC HÓA ĐƠN ĐÃ VÀO SỔ =====
            # Chỉ tính hóa đơn đã vào sổ (posted) để xác định trạng thái thanh toán
            posted_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            if not posted_invoices:
                # Có hóa đơn nhưng chưa vào sổ → Vẫn coi là chưa tạo hóa đơn
                # Trường hợp: Hóa đơn đang ở trạng thái draft
                order.invoice_status_custom = 'no'
                continue
            
            # ===== BƯỚC 4: LẤY HÓA ĐƠN CUỐI CÙNG =====
            # Sử dụng hóa đơn cuối cùng vì có thể có nhiều hóa đơn (credit note, refund)
            # Hóa đơn cuối cùng phản ánh trạng thái hiện tại chính xác nhất
            last_invoice = posted_invoices[-1]
            payment_state = last_invoice.payment_state
            
            # ===== BƯỚC 5: XÁC ĐỊNH TRẠNG THÁI DỰA TRÊN PAYMENT_STATE =====
            if payment_state == 'paid':
                # Đã thanh toán đầy đủ → Trạng thái: Đã thanh toán
                order.invoice_status_custom = 'paid'
            elif payment_state == 'partial':
                # Đã thanh toán một phần → Trạng thái: Thanh toán 1 phần
                order.invoice_status_custom = 'partial'
            elif payment_state == 'reversed':
                # Đã hủy thanh toán → Trạng thái: Đã hủy thanh toán
                order.invoice_status_custom = 'reversed'
            else:
                # Các trạng thái khác: not_paid, in_payment, etc.
                # → Đã tạo hóa đơn nhưng chưa thanh toán
                # Trạng thái: Chờ thanh toán
                order.invoice_status_custom = 'invoiced'

    def recompute_invoice_status(self):
        """
        Hàm public để gọi lại _compute_invoice_status_custom.
        
        Sử dụng trong script hoặc từ bên ngoài để tính lại trạng thái hóa đơn.
        
        Returns:
            dict: Kết quả cập nhật với thông tin trạng thái mới
        """
        self._compute_invoice_status_custom()
        
        result = {
            'updated_count': len(self),
            'orders': []
        }
        
        for order in self:
            result['orders'].append({
                'id': order.id,
                'name': order.name,
                'invoice_status_custom': order.invoice_status_custom
            })
        
        return result

    def recompute_all_invoice_status_custom(self):
        """
        Recompute invoice_status_custom cho tất cả đơn hàng
        
        Returns:
            dict: Kết quả cập nhật
        """
        # Sale Orders
        sale_orders = self.search([('state', 'in', ['sale', 'done'])])
        sale_orders._compute_invoice_status_custom()
        
        # Purchase Orders  
        purchase_orders = self.env['purchase.order'].search([('state', 'in', ['purchase', 'done'])])
        purchase_orders._compute_invoice_status_custom()
        
        return {
            'sale_orders_updated': len(sale_orders),
            'purchase_orders_updated': len(purchase_orders),
            'message': f'Đã cập nhật {len(sale_orders)} đơn bán và {len(purchase_orders)} đơn mua'
        }

    def _re_compute_invoice_status(self):
        """
        Compute the invoice status of a SO. Possible statuses:
        - no: if the SO is in status 'draft', we consider that there is nothing to
          invoice. This is also the default value if the conditions of no other status is met.
        - to invoice: if any SO line is 'to invoice', the whole SO is 'to invoice'
        - invoiced: if all SO lines are invoiced, the SO is invoiced.
        - upselling: if all SO lines are invoiced or upselling, the status is upselling.
        """
        # Only exclude draft orders from invoice status computation
        unconfirmed_orders = self.filtered(lambda so: so.state == 'draft')
        unconfirmed_orders.invoice_status = 'no'
        confirmed_orders = self - unconfirmed_orders
        if not confirmed_orders:
            return
        line_invoice_status_all = [
            (d['order_id'][0], d['invoice_status'])
            for d in self.env['sale.order.line'].read_group([
                    ('order_id', 'in', confirmed_orders.ids),
                    ('is_downpayment', '=', False),
                    ('display_type', '=', False),
                ],
                ['order_id', 'invoice_status'],
                ['order_id', 'invoice_status'], lazy=False)]
        for order in confirmed_orders:
            line_invoice_status = [d[1] for d in line_invoice_status_all if d[0] == order.id]
            # For any state other than draft, compute based on lines
            if order.state == 'draft':
                order.invoice_status = 'no'
            elif any(invoice_status == 'to invoice' for invoice_status in line_invoice_status):
                order.invoice_status = 'to invoice'
            elif line_invoice_status and all(invoice_status == 'invoiced' for invoice_status in line_invoice_status):
                order.invoice_status = 'invoiced'
            elif line_invoice_status and all(invoice_status in ('invoiced', 'upselling') for invoice_status in line_invoice_status):
                order.invoice_status = 'upselling'
            else:
                order.invoice_status = 'no'

    def _purchase_order_count(self):
        """Đếm số lượng đơn mua hàng liên kết với đơn bán"""
        for order in self:
            order.purchase_count = len(order.purchase_ids)

    def action_view_purchases(self):
        """Hiển thị danh sách đơn mua hàng liên kết"""
        self.ensure_one()
        return {
            'name': _('Chi phí'),
            'domain': [('id', 'in', [po.id for po in self.purchase_ids])],
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'context': {
                'default_sale_reference_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_buyer_id': self.user_id.id,
            },
        }

    def _rebuild_cost(self):
        """Tính toán lại chi phí cho đơn hàng dựa trên đơn mua"""
        self.ensure_one()
        self.order_line.write({'cost_price': 0})
        fee_amount = sum(
            po.amount_untaxed for po in self.purchase_ids.filtered(lambda p: p.state != 'cancel'))
        qty_order = sum(l.product_uom_qty for l in self.order_line)
        if qty_order > 0:
            fee_peer_unit = fee_amount / qty_order
            self.order_line.write({'cost_price': fee_peer_unit})
            self.message_post(body=_("Chi phí đơn hàng được cập nhật từ đơn mua %s.", fee_peer_unit))


    def _prepare_confirmation_values(self):
        """Chuẩn bị giá trị khi xác nhận đơn hàng"""
        res = super()._prepare_confirmation_values()
        # todo: we dont want core odoo change date_order, because we import order
        return {'state': 'sale'}

    @api.model
    def default_get(self, fields):
        """Lấy giá trị mặc định khi tạo đơn hàng mới"""
        result = super(SaleOrder, self).default_get(fields)
        result['sale_description'] = self.env.user.company_id.sale_description or ''
        purchase_pricelist = self.env['product.pricelist'].search([('type', '=', 'purchase')], limit=1)
        sale_pricelist = self.env['product.pricelist'].search([('type', '=', 'sale')], limit=1)
        if purchase_pricelist:
            result['purchase_pricelist_id'] = purchase_pricelist.id
        if sale_pricelist:
            result['pricelist_id'] = sale_pricelist.id
        if not result.get('user_id', None):
            result['user_id'] = self.env.user.id
        return result
    
    # allow user copy sale order, without sale admin
    def copy(self, default=None):
        """Cho phép tất cả user copy đơn hàng bán mà không cần phân quyền sale admin"""
        default = default or {}
        # Sử dụng sudo() để bypass phân quyền khi copy
        return super(SaleOrder, self.sudo()).copy(default)
    
    def write(self, vals):
        """Ghi đè phương thức write để cập nhật thông tin mô tả đơn hàng"""
        for sale in self:
            if not sale.sale_description and self.env.user.company_id and self.env.user.company_id.sale_description:
                vals.update({
                    'sale_description': self.env.user.company_id.sale_description
                })
        return super(SaleOrder, self).write(vals)

    def action_confirm(self):
        """Xác nhận đơn hàng và cập nhật giá gốc sản phẩm"""
        res = super(SaleOrder, self).action_confirm()
        # TODO: disable update standard_price 14.OCT.2025
        # for sale in self:
        #     # sale._rebuild_purchase_price()
        #     # order_lines_lost_base_price = sale.order_line.filtered(lambda x: x.base_price <= 0)
        #     # if order_lines_lost_base_price:
        #     #     products_lost_base_price = ' ,'.join(line.product_id.name for line in order_lines_lost_base_price)
        #     #     raise UserError(u"Vui lòng kiểm tra lại giá gốc các sản phẩm: %s" % products_lost_base_price)
        #     order_lines = sale.order_line.filtered(lambda x: x.base_price > 0)
        #     for line in order_lines:
        #         line.product_id.write({
        #             "standard_price": line.base_price
        #         })
        return res

    def import_discount_expense(self):
        """Import chiết khấu và chi phí từ bảng giá"""
        self.ensure_one()
        for line in self.order_line:
            rules = line.order_id.get_purchase_and_sale_pricelist_rule(line)
            purchase_pricelist_rule = rules.get('purchase_rule')
            pricelist_rule = rules.get('sale_rule')
            if line.purchase_price <= 0 and purchase_pricelist_rule:
                line.update({
                    'purchase_price': purchase_pricelist_rule.fixed_price,
                    'pricelist_item_id': purchase_pricelist_rule.id,
                })
            if not line.discount_value and pricelist_rule:
                line.update({
                    'discount_value': pricelist_rule.discount_value
                })
        return True

    def compute_invoice_status(self):
        return self._compute_invoice_status

    def import_from_excel(self, vals):
        """Import đơn hàng từ file Excel"""
        partner = self.env["res.partner"].search([("name", "=", "import")], limit=1)
        if not partner:
            raise UserError(_("Người dùng đã xoá khách hàng tên là import, vui lòng tạo lại khách hàng đó"))
        # Lấy config theo company để support multi-company
        # Ưu tiên lấy từ context hiện tại, fallback về user.company_id
        company = self.env.company or self.env.user.company_id
        _logger.info(f"Company context: {company.name} (ID: {company.id})")
        setting = self.env['import.sale.order.config'].search([
            ('company_id', '=', company.id)
        ], limit=1)
        
        # Fallback: Nếu không tìm thấy config theo company, lấy config đầu tiên (backward compatibility)
        if not setting:
            setting = self.env['import.sale.order.config'].search([], limit=1)
            if setting:
                _logger.warning(f"Không tìm thấy import.sale.order.config cho company {company.name}, sử dụng config mặc định (ID: {setting.id})")
        if not setting:
            raise UserError(_("Không tìm thấy cấu hình import đơn hàng, vui lòng liên hệ admin"))
        
        # Verify warehouse trong config thuộc về company đúng (dùng sudo để đọc được warehouse của company khác)
        config_warehouse = setting.sudo().warehouse_id
        if config_warehouse and config_warehouse.company_id != company:
            _logger.warning(f"Config có warehouse {config_warehouse.name} (ID: {config_warehouse.id}) thuộc company {config_warehouse.company_id.name}, nhưng config thuộc company {company.name}")
            # Tìm warehouse của company hiện tại
            company_warehouse = self.env['stock.warehouse'].search([
                ('company_id', '=', company.id)
            ], limit=1, order='id')
            if not company_warehouse:
                raise UserError(_(u"Config có warehouse không thuộc công ty %s và không tìm thấy warehouse nào cho công ty này. Vui lòng kiểm tra cấu hình import.sale.order.config và warehouse." % company.name))
            # Lưu warehouse đúng vào biến để dùng sau
            setting = setting.with_context(warehouse_override=company_warehouse.id)
            _logger.info(f"Sử dụng warehouse {company_warehouse.name} của company {company.name} thay thế")
        purchase_pricelist = self.env["product.pricelist"].search([("type", "=", "purchase")], limit=1)
        sale_pricelist = self.env["product.pricelist"].search([("type", "=", "sale")], limit=1)
        sale = None
        if partner and purchase_pricelist and sale_pricelist:
            origin = vals.get("origin")
            order_line = []
            for val in vals["order_line"]:
                product = self.env["product.product"].search(
                    [("default_code", "=", val.get("default_code").upper())],
                    limit=1)
                if product:
                    order_line.append((0, 0, {
                        "product_id": product.id,
                        "product_uom_qty": val.get("product_uom_qty"),
                        "price_unit": val.get("price_unit"),
                        "quantity_another1": val.get("quantity_another1"),
                        "quantity_another2": val.get("quantity_another2"),
                        "quantity_another3": val.get("quantity_another3"),
                        "base_price": val.get("base_price"),
                        "purchase_uom_qty": val.get("purchase_uom_qty"),
                        "quantity_extra": val.get("quantity_extra"),
                        "purchase_price": val.get("purchase_price"),
                    }))
                else:
                    raise UserError(_(u"Mã sản phẩm %s không tồn tại" % val.get("default_code")))
            if len(order_line) > 0:
                # Lấy warehouse từ config hoặc từ context override
                warehouse = None
                if hasattr(setting, '_context') and setting._context.get('warehouse_override'):
                    # Dùng warehouse từ override (đã verify đúng company)
                    warehouse = self.env['stock.warehouse'].browse(setting._context.get('warehouse_override'))
                    _logger.info(f"Sử dụng warehouse từ override: {warehouse.name} (ID: {warehouse.id})")
                else:
                    # Đọc warehouse từ config với sudo để tránh record rules
                    config_warehouse = setting.sudo().warehouse_id
                    if config_warehouse and config_warehouse.company_id == company:
                        warehouse = config_warehouse
                        _logger.info(f"Sử dụng warehouse từ config: {warehouse.name} (ID: {warehouse.id})")
                    else:
                        # Warehouse không thuộc company đúng, tìm warehouse của company
                        _logger.warning(f"Warehouse từ config ({config_warehouse.name if config_warehouse else 'None'}) không thuộc company {company.name}")
                        company_warehouse = self.env['stock.warehouse'].search([
                            ('company_id', '=', company.id)
                        ], limit=1, order='id')
                        if company_warehouse:
                            warehouse = company_warehouse
                            _logger.info(f"Sử dụng warehouse của company: {warehouse.name} (ID: {warehouse.id})")
                        else:
                            raise UserError(_(u"Không tìm thấy warehouse cho công ty %s. Vui lòng kiểm tra cấu hình import.sale.order.config và tạo warehouse cho công ty này." % company.name))
                
                # Verify các fields khác cũng thuộc về company đúng
                payment_term = setting.payment_term_id
                if payment_term and hasattr(payment_term, 'company_id') and payment_term.company_id and payment_term.company_id != company:
                    _logger.warning(f"Payment term {payment_term.name} thuộc company {payment_term.company_id.name}, nhưng cần của company {company.name}")
                    # Tìm payment term của company (hoặc dùng chung nếu không có company_id)
                    company_payment_term = self.env['account.payment.term'].search([
                        '|', ('company_id', '=', company.id), ('company_id', '=', False)
                    ], limit=1, order='company_id desc')  # Ưu tiên có company_id
                    if company_payment_term:
                        payment_term = company_payment_term
                        _logger.info(f"Sử dụng payment term {payment_term.name} của company {company.name} thay thế")
                
                pricelist = setting.pricelist_id
                if pricelist and pricelist.company_id and pricelist.company_id != company:
                    _logger.warning(f"Pricelist {pricelist.name} thuộc company {pricelist.company_id.name}, nhưng cần của company {company.name}")
                    # Tìm pricelist của company
                    company_pricelist = self.env['product.pricelist'].search([
                        ('company_id', '=', company.id),
                        ('type', '=', 'sale')
                    ], limit=1, order='id')
                    if company_pricelist:
                        pricelist = company_pricelist
                        _logger.info(f"Sử dụng pricelist {pricelist.name} của company {company.name} thay thế")
                
                purchase_pricelist = setting.purchase_pricelist_id
                if purchase_pricelist and purchase_pricelist.company_id and purchase_pricelist.company_id != company:
                    _logger.warning(f"Purchase pricelist {purchase_pricelist.name} thuộc company {purchase_pricelist.company_id.name}, nhưng cần của company {company.name}")
                    # Tìm purchase pricelist của company
                    company_purchase_pricelist = self.env['product.pricelist'].search([
                        ('company_id', '=', company.id),
                        ('type', '=', 'purchase')
                    ], limit=1, order='id')
                    if company_purchase_pricelist:
                        purchase_pricelist = company_purchase_pricelist
                        _logger.info(f"Sử dụng purchase pricelist {purchase_pricelist.name} của company {company.name} thay thế")
                
                value = {
                    "origin": origin,
                    "partner_id": partner.id,
                    "company_id": company.id,  # Set company_id để đảm bảo multi-company
                    "date_order": datetime.strptime(
                        vals.get("date_order") + '-%s' % fields.Datetime.now().year + " 07:00:00", "%d-%m-%Y %H:%M:%S"),
                    "purchase_pricelist_id": purchase_pricelist.id if purchase_pricelist else False,
                    "pricelist_id": pricelist.id if pricelist else False,
                    "warehouse_id": warehouse.id if warehouse else False,
                    "payment_term_id": payment_term.id if payment_term else False,
                    "order_line": order_line,
                }
                # Tạo đơn hàng với company context đúng để đảm bảo không bay sang công ty khác
                sale = self.with_company(company).create(value)
                _logger.info(f"Đã tạo đơn hàng {sale.name} (ID: {sale.id}) cho công ty {company.name} (ID: {company.id})")
                sale.import_discount_expense()
            else:
                raise UserError(_('Không tìm thấy dữ liệu hàng bán chi tiết để import'))
        else:
            raise UserError(_(">>>>>> partner %s | purchase_pricelist %s |  sale_pricelist %s not found" % (
                partner, purchase_pricelist, sale_pricelist)))
        return sale

    def _get_detail_quantity(self):
        """Tính toán tổng số lượng các loại đơn vị tính"""
        for sale in self:
            sale.total_quantity_another1 = 0
            sale.total_quantity_another2 = 0
            sale.total_quantity_another3 = 0
            sale.total_product_uom_qty = 0
            for line in sale.order_line:
                if line.product_id:
                    sale.total_quantity_another1 += line.quantity_another1
                    sale.total_quantity_another2 += line.quantity_another2
                    sale.total_quantity_another3 += line.quantity_another3
                    sale.total_product_uom_qty += line.product_uom_qty

    # TODO: no display taxes and taxes detail on report sale order
    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed', 'currency_id')
    def _compute_tax_totals(self):
        """Tính toán tổng thuế cho đơn hàng"""
        super(SaleOrder, self)._compute_tax_totals()
        for order in self:
            if order.sale_type != '0_0':
                order_lines = order.order_line.filtered(lambda x: not x.display_type)
                datas = self.env['account.tax']._prepare_tax_totals(
                    [x._convert_to_tax_base_line_dict() for x in order_lines],
                    order.currency_id or order.company_id.currency_id,
                )
                order.tax_totals = datas

    def _create_invoices(self, grouped=False, final=False, date=None):
        """Tạo hóa đơn cho đơn hàng"""
        moves = super(SaleOrder, self)._create_invoices(grouped=grouped, final=final, date=date)
        for order in self:
            if order.no_output_invoice:
                moves.write({'no_output_invoice': order.no_output_invoice})
        return moves

    @api.depends(
        'amount_total',
        'type_id',
        'order_line.margin',
        'order_line.supplier_discount_peer_month',
        'order_line.supplier_discount_peer_quarter',
        'order_line.supplier_commission_person',
        'order_line.sale_commission_person'
    )
    def _compute_seller_commission(self):
        """Tính toán hoa hồng cho nhân viên bán hàng"""
        for sale in self:
            if not sale.type_id:
                continue
            sale.seller_commission = 0
            if sale.type_id and sale.type_id.commission > 0:
                total_qty = 0
                for line in sale.order_line:
                    total_qty += line.product_uom_qty
                if sale.type_id.commission_type == 'value':
                    sale.seller_commission = total_qty * sale.type_id.commission
                else:
                    if sale.type_id.commission_type_order == 'margin':
                        sale.seller_commission = sale.margin * sale.type_id.commission / 100
                    else:
                        sale.seller_commission = sale.amount_total * sale.type_id.commission / 100
            # if sale.seller_commission <= 0:
            #     sale.seller_commission = 0

    # @api.depends('partner_id')
    # def _compute_pricelist_id(self):
    #     for order in self:
    #         if order.sale_type == '0_0':
    #             return super(SaleOrder, self)._compute_pricelist_id()
    #         else:
    #             pricelists = self.env['product.pricelist'].search([
    #                 ('type', '=', 'sale')
    #             ])
    #             if pricelists:
    #                 order.pricelist_id = pricelists[0]


    @api.depends('order_line.margin', 'amount_untaxed')
    def _compute_margin(self):
        """Tính toán lợi nhuận cho đơn hàng"""
        for order in self:
            if order.sale_type == '0_0':
                return super(SaleOrder, self)._compute_margin()
        else:
            if not all(self._ids):
                for order in self:
                    order.margin = sum(order.order_line.mapped('margin'))
                    amount_costing = sum(order.order_line.mapped('amount_costing'))
                    order.margin_percent = amount_costing and order.margin / amount_costing
            else:
                grouped_order_lines_data = self.env['sale.order.line'].read_group(
                    [
                        ('order_id', 'in', self.ids),
                    ], ['margin', 'order_id', 'amount_costing', 'price_landing', 'price_shipping', 'product_uom_qty'],
                    ['order_id'])
                total_landing = {m['order_id'][0]: m['price_landing'] * m['product_uom_qty'] for m in
                                 grouped_order_lines_data}
                total_shipping = {m['order_id'][0]: m['price_shipping'] * m['product_uom_qty'] for m in
                                  grouped_order_lines_data}
                total_margin = {m['order_id'][0]: m['margin'] for m in grouped_order_lines_data}
                total_costing = {m['order_id'][0]: m['amount_costing'] for m in grouped_order_lines_data}
                for order in self:
                    cost_price = total_costing.get(order.id, 0.0)
                    landing_cost = total_landing.get(order.id, 0.0)
                    shipping_cost = total_shipping.get(order.id, 0.0)
                    order.margin = total_margin.get(order.id, 0.0)
                    order.margin_percent = total_costing.get(order.id, 0.0) and order.margin / (
                            cost_price + landing_cost + shipping_cost)
                    _logger.info('=>>>>>>>>>>>>> margin %s margin_percent %s' % (order.margin, order.margin_percent))

    @api.depends('margin', 'margin_percent')
    def _compute_margin_each_unit(self):
        """Tính toán lợi nhuận trên mỗi đơn vị sản phẩm"""
        for sale in self:
            total_qty = 0
            for line in sale.order_line:
                total_qty += line.product_uom_qty
            if total_qty != 0:
                sale.margin_each_unit = sale.margin / total_qty
            else:
                sale.margin_each_unit = 0

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """Cập nhật loại khách hàng khi thay đổi đối tác"""
        if self.partner_id and self.partner_id.type_id:
            self.type_id = self.partner_id.type_id.id

    # todo: nếu người dùng ko click vào đề xuất giá bán mà nhập tay,
    def _rebuild_purchase_price(self):
        """Tính toán lại giá mua cho đơn hàng"""
        for sale in self:
            for line in self.order_line:
                if line.base_price != 0:
                    continue
                if line.quantity_another1 != 0 and line.product_id.quantity_supplier and line.product_id.quantity_tcvn != 0:
                    rules = self.get_purchase_and_sale_pricelist_rule(line)
                    purchase_pricelist_rule = rules.get('purchase_rule')
                    pricelist_rule = rules.get('sale_rule')
                    if not purchase_pricelist_rule or not pricelist_rule:
                        continue
                    if purchase_pricelist_rule and purchase_pricelist_rule.fixed_price:
                        if pricelist_rule.discount_value != 0 and purchase_pricelist_rule.fixed_price != 0:
                            line.purchase_price = purchase_pricelist_rule.fixed_price - pricelist_rule.discount_value
                            line.discount_value = pricelist_rule.discount_value
                        else:
                            line.purchase_price = purchase_pricelist_rule.fixed_price
                        kl_ban = line.quantity_another1 * line.product_id.quantity_tcvn
                        kl_mua = line.quantity_another1 * line.product_id.quantity_supplier
                        if sale.sale_type not in ['0_2', '0_4']:
                            kl_mua = kl_ban
                        gia_mua = purchase_pricelist_rule.fixed_price - pricelist_rule.discount_value
                        giamua_quydoi = gia_mua * (kl_mua / kl_ban)
                        line.base_price = giamua_quydoi + pricelist_rule.price_min_margin

    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        """Xử lý khi thay đổi bảng giá bán"""
        self.show_update_pricelist = True

    @api.onchange('purchase_pricelist_id')
    def _onchange_purchase_pricelist_id(self):
        """Xử lý khi thay đổi bảng giá mua"""
        self.show_update_pricelist = True

    @api.onchange('payment_term_id', 'amount_total')
    def _onchange_payment_term_id(self):
        """Tính toán lãi vay khi thay đổi điều khoản thanh toán"""
        self.show_update_pricelist = True
        if self.payment_term_id and self.payment_term_id.lending_days > 0 and self.payment_term_id.lending_rate >= 0:
            purchase = self.auto_purchase_order_id
            lending_days = self.payment_term_id.lending_days
            if purchase:
                lending_days = lending_days - purchase.payment_term_id.lending_days
            if lending_days <= 0:
                lending_days = 0
            lines = self.order_line.filtered(lambda l: l.product_uom_qty > 0)
            for line in lines:
                landing_cost = line.price_total * (line.order_id.payment_term_id.lending_rate / 100) * lending_days
                landing_cost_each_unit = landing_cost / line.product_uom_qty
                line.update({
                    'price_landing': float_round(landing_cost_each_unit, precision_digits=0, rounding_method='HALF-UP'),
                })
        else:
            for line in self.order_line:
                line.update({
                    'price_landing': 0,
                })

    def action_building_extra_cost(self):
        """Tính toán và cập nhật chi phí phát sinh"""
        self.ensure_one()
        self._rebuild_cost()
        self.action_remove_include_extra_cost()
        self.action_update_prices()
        return True

    @api.model
    def _prepare_purchase_order_data(self, company, company_partner):
        """Override để sử dụng logic warehouse selection tốt hơn (từ import.sale.order.config)"""
        _logger.info(f"=== _prepare_purchase_order_data: Tìm warehouse cho company {company.name} ===")
        warehouse = None
        
        # Ưu tiên 1: Lấy warehouse từ import.sale.order.config của company
        import_config = self.env['import.sale.order.config'].search([
            ('company_id', '=', company.id)
        ], limit=1)
        if import_config:
            config_warehouse = import_config.sudo().warehouse_id
            if config_warehouse and config_warehouse.company_id == company:
                warehouse = config_warehouse
                _logger.info(f"  → Sử dụng warehouse từ import.sale.order.config: {warehouse.name} (ID: {warehouse.id})")
            elif config_warehouse:
                _logger.warning(f"  → Warehouse từ config ({config_warehouse.name}) không thuộc company {company.name}")
        
        # Ưu tiên 2: Lấy warehouse từ sale order nếu có và thuộc đúng company
        if not warehouse and self.warehouse_id:
            if self.warehouse_id.company_id == company:
                warehouse = self.warehouse_id
                _logger.info(f"  → Sử dụng warehouse từ sale order: {warehouse.name} (ID: {warehouse.id})")
            else:
                _logger.warning(f"  → Warehouse từ sale order ({self.warehouse_id.name}) không thuộc company {company.name}")
        
        # Ưu tiên 3: Lấy warehouse từ company.warehouse_id (Odoo core field, nếu có)
        if not warehouse and hasattr(company, 'warehouse_id') and company.warehouse_id:
            if company.warehouse_id.company_id == company:
                warehouse = company.warehouse_id
                _logger.info(f"  → Sử dụng warehouse từ company settings: {warehouse.name} (ID: {warehouse.id})")
            else:
                _logger.warning(f"  → Warehouse từ company settings ({company.warehouse_id.name}) không thuộc company {company.name}")
        
        # Ưu tiên 4: Tìm warehouse đầu tiên của company
        if not warehouse:
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', company.id)
            ], order='id')
            if warehouses:
                warehouse = warehouses[0]
                _logger.info(f"  → Sử dụng warehouse đầu tiên của company: {warehouse.name} (ID: {warehouse.id})")
            else:
                _logger.error(f"  → Không tìm thấy warehouse nào cho company {company.name}")
                raise UserError(_('Cấu hình kho chính xác cho công ty (%s) từ Menu: Cài đặt/Người dùng/Công ty') % company.name)
        
        # Tìm picking type
        picking_type_id = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'), 
            ('warehouse_id', '=', warehouse.id),
            ('company_id', '=', company.id)
        ], limit=1)
        if not picking_type_id:
            intercompany_uid = company.intercompany_user_id.id
            picking_type_id = self.env['purchase.order'].with_user(intercompany_uid)._default_picking_type()
            _logger.warning(f"  → Không tìm thấy picking type cho warehouse {warehouse.name}, sử dụng default")
        
        _logger.info(f"  → Warehouse cuối cùng: {warehouse.name} (ID: {warehouse.id}), Picking Type: {picking_type_id.id if picking_type_id else 'None'}")
        
        # Build purchase order data (không gọi super vì super sẽ raise error nếu không có company.warehouse_id)
        intercompany_uid = company.intercompany_user_id.id
        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('purchase.order'),
            'origin': self.name,
            'partner_id': company_partner.id,
            'picking_type_id': picking_type_id.id if picking_type_id else False,
            'date_order': self.date_order,
            'company_id': company.id,
            'fiscal_position_id': company_partner.property_account_position_id.id if company_partner.property_account_position_id else False,
            'payment_term_id': company_partner.property_supplier_payment_term_id.id if company_partner.property_supplier_payment_term_id else False,
            'auto_generated': True,
            'auto_sale_order_id': self.id,
            'partner_ref': self.name,
            'currency_id': self.currency_id.id,
            'order_line': [],
        }

    def _prepare_purchase_order_line_data(self, so_line, date_order, company):
        """Chuẩn bị dữ liệu cho dòng đơn mua hàng"""
        line_val = super(SaleOrder, self)._prepare_purchase_order_line_data(so_line, date_order, company)
        price_unit = so_line.base_price  # todo:  not include discount_value when covert to PO  - so_line.discount_value
        if not price_unit:
            price_unit = so_line.purchase_price
        # todo: add cost of supplier_delivery_type
        if so_line.supplier_delivery_type_id and so_line.supplier_delivery_type_id.cost_price:
            price_unit += so_line.supplier_delivery_type_id.cost_price
        line_val['price_unit'] = price_unit
        line_val['quantity_another1'] = so_line.quantity_another1
        line_val['quantity_another2'] = so_line.quantity_another2
        line_val['quantity_another3'] = so_line.quantity_another3
        line_val['length'] = so_line.length
        quantity = so_line.product_id and so_line.product_uom._compute_quantity(so_line.product_uom_qty,
                                                                                so_line.product_id.uom_po_id) or so_line.product_uom_qty
        line_val['product_qty'] = quantity - so_line.quantity_extra
        line_val['discount_value'] = so_line.discount_value
        line_val['supplier_delivery_type_id'] = so_line.supplier_delivery_type_id.id if so_line.supplier_delivery_type_id else False
        # disable 1/1/2025
        # line_val['sale_line_id'] = so_line.id
        _logger.info(f"line_val: {line_val}")
        return line_val

    def action_create_po(self):
        """Tạo đơn mua hàng mới"""
        self.ensure_one()
        purchase = self.env['purchase.order'].create({
            'partner_id': self.partner_id.id,
            'sale_reference_id': self.id,
            'tag_ids': [(6, 0, self.tag_ids.ids)] if self.tag_ids else False,
            'buyer_id': self.user_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': purchase.id,
            'context': {
                'create': False,
                'edit': True
            }
        }

    def action_create_purchase_order(self):
        """
        Tạo hoặc cập nhật đơn mua hàng từ đơn bán:
        - Tạo mới nếu chưa có
        - Cập nhật nếu đã tồn tại
        - Liên kết với đơn bán
        - Cập nhật thông tin sản phẩm, số lượng, giá
        """
        self.ensure_one()
        _logger.info(f"=== Bắt đầu cập nhật đơn mua cho đơn bán {self.name} ===")
        _logger.info(f"Sale Order ID: {self.id}")
        _logger.info(f"Sale Order Name: {self.name}")
        _logger.info(f"Loại đơn bán: {self.sale_type}")
        _logger.info(f"Mã đơn mua tự động: {self.auto_purchase_order_id}")
        _logger.info(f"Company của sale order: {self.company_id.name if self.company_id else 'None'} (ID: {self.company_id.id if self.company_id else 'None'})")
        _logger.info(f"Warehouse của sale order: {self.warehouse_id.name if self.warehouse_id else 'None'} (ID: {self.warehouse_id.id if self.warehouse_id else 'None'})")
        
        # 1. Lọc các dòng sản phẩm hợp lệ trên đơn bán
        lines = self.order_line.filtered(lambda l: l.product_id and l.product_id != None)
        if not lines:
            _logger.warning("Không tìm thấy dòng sản phẩm hợp lệ")
            return False
        
        _logger.info(f"Tìm thấy {len(lines)} dòng sản phẩm hợp lệ")
        for line in lines:
            _logger.info(f"Dòng: {line.product_id.name}, Số lượng: {line.product_uom_qty}, Giá mua: {line.purchase_price}")
        
        # 2. Xác định công ty từ sale order (ưu tiên) hoặc từ context
        _logger.info(f"Xác định company:")
        _logger.info(f"  - self.company_id: {self.company_id.name if self.company_id else 'None'} (ID: {self.company_id.id if self.company_id else 'None'})")
        _logger.info(f"  - self.env.company: {self.env.company.name if self.env.company else 'None'} (ID: {self.env.company.id if self.env.company else 'None'})")
        _logger.info(f"  - self.env.user.company_id: {self.env.user.company_id.name if self.env.user.company_id else 'None'} (ID: {self.env.user.company_id.id if self.env.user.company_id else 'None'})")
        company = self.company_id or self.env.company or self.env.user.company_id
        _logger.info(f"→ Công ty được chọn: {company.name} (ID: {company.id})")
        
        # 3. Nếu đã có đơn mua tự động liên kết với đơn bán
        if self.auto_purchase_order_id:
            _logger.info(f"Tìm thấy đơn mua hiện có: {self.auto_purchase_order_id.name}")
            _logger.info(f"Trạng thái đơn mua: {self.auto_purchase_order_id.state}")
            
            # Chỉ cho phép cập nhật nếu đơn mua ở trạng thái nháp hoặc đã gửi báo giá
            if self.auto_purchase_order_id.state not in ['draft', 'sent']:
                _logger.error(f"Đơn mua {self.auto_purchase_order_id.name} không ở trạng thái nháp hoặc YCBG đã gửi, mới cập nhật được" % self.auto_purchase_order_id.name)
                raise UserError(u"Đơn mua hàng %s phải ở trạng thái nháp hoặc YCBG đã gửi, mới cập nhật được" % self.auto_purchase_order_id.name)
            
            _logger.info("Đang cập nhật đơn mua hiện có")
            _logger.info(f"Purchase Order ID: {self.auto_purchase_order_id.id}")
            _logger.info(f"Purchase Order Name: {self.auto_purchase_order_id.name}")
            _logger.info(f"Purchase Order Company: {self.auto_purchase_order_id.company_id.name if self.auto_purchase_order_id.company_id else 'None'} (ID: {self.auto_purchase_order_id.company_id.id if self.auto_purchase_order_id.company_id else 'None'})")
            # Cập nhật các trường thông tin chung của đơn mua
            update_vals = {
                'sale_id': self.id,
                'tag_ids': [(6, 0, self.tag_ids.ids)] if self.tag_ids else False,
                'date_planned': self.received_date,
            }
            _logger.info(f"Cập nhật purchase order với giá trị: {update_vals}")
            self.auto_purchase_order_id.write(update_vals)
            _logger.info(f"Đã cập nhật purchase order thành công")
            
            # Cập nhật từng dòng sản phẩm trên đơn mua dựa vào dòng đơn bán liên kết
            # Tạo mapping giữa dòng đơn mua và đơn bán để xử lý trường hợp nhiều dòng cùng sản phẩm
            remaining_so_lines = list(self.order_line.filtered(lambda l: l.product_id and l.product_id != None))
            _logger.info(f"Tổng số dòng đơn mua cần cập nhật: {len(self.auto_purchase_order_id.order_line)}")
            _logger.info(f"Số dòng đơn bán còn lại để map: {len(remaining_so_lines)}")
            
            for idx, line in enumerate(self.auto_purchase_order_id.order_line, 1):
                _logger.info(f"[{idx}/{len(self.auto_purchase_order_id.order_line)}] Đang xử lý dòng đơn mua:")
                _logger.info(f"  - Purchase Line ID: {line.id}")
                _logger.info(f"  - Product: {line.product_id.name} (ID: {line.product_id.id})")
                _logger.info(f"  - Product Code: {line.product_id.default_code}")
                if line.sale_line_id:
                    _logger.info(f"  - Có liên kết với sale line ID: {line.sale_line_id.id}")
                    _logger.info(f"  - Sale line product: {line.sale_line_id.product_id.name}")
                    val = self._prepare_purchase_order_line_data(line.sale_line_id, self.date_order, company)
                    val['price_unit'] = line.sale_line_id.purchase_price
                    val['product_qty'] = line.sale_line_id.purchase_uom_qty
                    # Đảm bảo copy các trường SL
                    val['quantity_another1'] = line.sale_line_id.quantity_another1
                    val['quantity_another2'] = line.sale_line_id.quantity_another2
                    val['quantity_another3'] = line.sale_line_id.quantity_another3
                    val['length'] = line.sale_line_id.length
                    val['supplier_delivery_type_id'] = line.sale_line_id.supplier_delivery_type_id.id if line.sale_line_id.supplier_delivery_type_id else False
                    val['discount_value'] = line.sale_line_id.discount_value
                    _logger.info(f"  - Giá trị cập nhật: price_unit={val.get('price_unit')}, product_qty={val.get('product_qty')}, quantity_another1={val.get('quantity_another1')}, quantity_another2={val.get('quantity_another2')}, quantity_another3={val.get('quantity_another3')}")
                    line.write(val)
                    _logger.info(f"  - Đã cập nhật dòng đơn mua thành công")
                else:
                    # Nếu không có liên kết, tìm dòng đơn bán tương ứng theo sản phẩm
                    _logger.info(f"  - Không có liên kết với sale line, đang tìm sản phẩm tương ứng")
                    so_lines = [l for l in remaining_so_lines if l.product_id.id == line.product_id.id]
                    _logger.info(f"  - Tìm thấy {len(so_lines)} dòng đơn bán có cùng sản phẩm")
                    
                    if so_lines:
                        # Lấy dòng đầu tiên trong danh sách còn lại và loại bỏ khỏi danh sách
                        so_line = so_lines[0]
                        remaining_so_lines.remove(so_line)
                        _logger.info(f"  - Tìm thấy dòng đơn bán tương ứng: Sale Line ID {so_line.id}")
                        _logger.info(f"  - Sale line product: {so_line.product_id.name}")
                        update_vals = {
                            'price_unit': so_line.purchase_price,
                            'product_qty': so_line.purchase_uom_qty,
                            'quantity_another1': so_line.quantity_another1,
                            'quantity_another2': so_line.quantity_another2,
                            'quantity_another3': so_line.quantity_another3,
                            'length': so_line.length,
                            'supplier_delivery_type_id': so_line.supplier_delivery_type_id.id if so_line.supplier_delivery_type_id else False,
                            'discount_value': so_line.discount_value
                        }
                        _logger.info(f"  - Giá trị cập nhật: {update_vals}")
                        line.write(update_vals)
                        _logger.info(f"  - Đã cập nhật dòng đơn mua thành công")
                    else:
                        _logger.warning(f"  - Không tìm thấy dòng đơn bán tương ứng cho sản phẩm {line.product_id.name} (ID: {line.product_id.id})")
        else:
            # 4. Nếu chưa có đơn mua, tạo mới đơn mua liên kết với đơn bán
            _logger.info("Không tìm thấy đơn mua, đang tạo mới")
            _logger.info(f"Company để tạo purchase order: {company.name} (ID: {company.id})")
            _logger.info(f"Intercompany user ID: {company.intercompany_user_id.id if company.intercompany_user_id else 'None'}")
            _logger.info(f"Đang gọi inter_company_create_purchase_order...")
            self.with_user(company.intercompany_user_id).with_context(default_company_id=company.id).with_company(
                company).inter_company_create_purchase_order(company)
            _logger.info(f"Đã gọi inter_company_create_purchase_order, đang tìm purchase order được tạo...")
            purchases = self.env['purchase.order'].search([('auto_sale_order_id', '=', self.id)])
            _logger.info(f"Đã tạo {len(purchases)} đơn mua mới")
            if purchases:
                for idx, po in enumerate(purchases, 1):
                    _logger.info(f"  Purchase Order [{idx}]: {po.name} (ID: {po.id}, Company: {po.company_id.name if po.company_id else 'None'})")
            
            # Cập nhật nhà cung cấp cho đơn mua dựa vào thông tin nhà cung cấp của sản phẩm
            _logger.info(f"Đang tìm nhà cung cấp cho {len(lines)} sản phẩm...")
            for idx, line in enumerate(lines, 1):
                _logger.info(f"[{idx}/{len(lines)}] Kiểm tra nhà cung cấp cho sản phẩm: {line.product_id.name} (ID: {line.product_id.id}, Code: {line.product_id.default_code})")
                supplierinfo = self.env['product.supplierinfo'].search(
                    [('product_id', '=', line.product_id.id), ('partner_id', '!=', None)])
                _logger.info(f"  - Tìm thấy {len(supplierinfo)} bản ghi supplierinfo")
                if supplierinfo:
                    for si in supplierinfo:
                        _logger.info(f"    + Supplier: {si.partner_id.name if si.partner_id else 'None'} (ID: {si.partner_id.id if si.partner_id else 'None'})")
                
                if purchases and supplierinfo:
                    supplier = supplierinfo[0].partner_id
                    _logger.info(f"  - Chọn nhà cung cấp: {supplier.name} (ID: {supplier.id})")
                    update_vals = {
                        'partner_id': supplier.id,
                        'tag_ids': [(6, 0, self.tag_ids.ids)] if self.tag_ids else False,
                        'date_planned': self.received_date,
                    }
                    _logger.info(f"  - Cập nhật purchase order với giá trị: {update_vals}")
                    purchases.write(update_vals)
                    _logger.info(f"  - Đã cập nhật purchase order với nhà cung cấp thành công")
                    break
                else:
                    if not purchases:
                        _logger.warning(f"  - Không có purchase order để cập nhật")
                    if not supplierinfo:
                        _logger.warning(f"  - Không tìm thấy thông tin nhà cung cấp cho sản phẩm {line.product_id.name}")
                    
            if purchases:
                purchase_id = purchases[0].id
                _logger.info(f"Gán purchase order ID {purchase_id} vào sale order {self.id}")
                self.auto_purchase_order_id = purchase_id
                self.auto_purchase_order_id.sale_id = self.id
                _logger.info(f"Đã gán mã đơn mua tự động: {purchase_id}")
                _logger.info(f"Purchase order name: {purchases[0].name}")
                _logger.info(f"Purchase order company: {purchases[0].company_id.name if purchases[0].company_id else 'None'}")
            else:
                _logger.error("Không tạo được đơn mua - purchases list rỗng")
            
        # 5. Cập nhật các thông tin cuối cùng cho đơn mua (người dùng, ngày, phương thức vận chuyển, ...)
        purchase = self.auto_purchase_order_id
        _logger.info(f"=== Bước 5: Cập nhật thông tin cuối cùng cho đơn mua ===")
        _logger.info(f"Purchase order: {purchase.name if purchase else 'Không có'}")
        if purchase:
            _logger.info(f"  - Purchase Order ID: {purchase.id}")
            _logger.info(f"  - Purchase Order Name: {purchase.name}")
            _logger.info(f"  - Purchase Order Company: {purchase.company_id.name if purchase.company_id else 'None'} (ID: {purchase.company_id.id if purchase.company_id else 'None'})")
        
        # Tìm phương thức vận chuyển của kho - support multi-company
        # Lấy warehouse từ company của purchase order (hoặc từ sale order's warehouse)
        _logger.info(f"Xác định company cho warehouse selection:")
        _logger.info(f"  - Purchase company: {purchase.company_id.name if purchase and purchase.company_id else 'None'} (ID: {purchase.company_id.id if purchase and purchase.company_id else 'None'})")
        _logger.info(f"  - Sale order company: {self.company_id.name if self.company_id else 'None'} (ID: {self.company_id.id if self.company_id else 'None'})")
        company = purchase.company_id if purchase else self.company_id
        _logger.info(f"→ Company được chọn: {company.name} (ID: {company.id})")
        warehouse = None
        picking_type_id = None
        
        # Ưu tiên 1: Lấy warehouse từ import.sale.order.config của company (theo yêu cầu)
        _logger.info(f"=== Tìm warehouse cho company {company.name} ===")
        _logger.info(f"Ưu tiên 1: Tìm warehouse từ import.sale.order.config...")
        import_config = self.env['import.sale.order.config'].search([
            ('company_id', '=', company.id)
        ], limit=1)
        if import_config:
            _logger.info(f"  - Tìm thấy import.sale.order.config ID: {import_config.id}")
            config_warehouse = import_config.sudo().warehouse_id
            if config_warehouse:
                _logger.info(f"  - Warehouse trong config: {config_warehouse.name} (ID: {config_warehouse.id}, Code: {config_warehouse.code})")
                _logger.info(f"  - Warehouse company: {config_warehouse.company_id.name if config_warehouse.company_id else 'None'} (ID: {config_warehouse.company_id.id if config_warehouse.company_id else 'None'})")
                if config_warehouse.company_id == company:
                    warehouse = config_warehouse
                    _logger.info(f"  → Sử dụng warehouse từ import.sale.order.config: {warehouse.name} (code: {warehouse.code})")
                else:
                    _logger.warning(f"  → Warehouse từ config ({config_warehouse.name}) không thuộc company {company.name}, sẽ tìm warehouse khác")
            else:
                _logger.info(f"  - Config không có warehouse được cấu hình")
        else:
            _logger.info(f"  - Không tìm thấy import.sale.order.config cho company {company.name}")
        # Ưu tiên 2: Lấy warehouse từ sale order nếu có và thuộc đúng company
        if not warehouse:
            _logger.info(f"Ưu tiên 2: Kiểm tra warehouse từ sale order...")
            if self.warehouse_id:
                _logger.info(f"  - Sale order có warehouse: {self.warehouse_id.name} (ID: {self.warehouse_id.id}, Code: {self.warehouse_id.code})")
                _logger.info(f"  - Warehouse company: {self.warehouse_id.company_id.name if self.warehouse_id.company_id else 'None'} (ID: {self.warehouse_id.company_id.id if self.warehouse_id.company_id else 'None'})")
                if self.warehouse_id.company_id == company:
                    warehouse = self.warehouse_id
                    _logger.info(f"  → Sử dụng warehouse từ sale order: {warehouse.name} (code: {warehouse.code})")
                else:
                    _logger.warning(f"  → Warehouse từ sale order ({self.warehouse_id.name}) không thuộc company {company.name}, sẽ tìm warehouse khác")
            else:
                _logger.info(f"  - Sale order không có warehouse")
        
        # Ưu tiên 3: Tìm warehouse đầu tiên của company (chỉ khi chưa có warehouse)
        if not warehouse:
            _logger.info(f"Ưu tiên 3: Tìm warehouse đầu tiên của company {company.name}...")
            warehouses = self.env['stock.warehouse'].search([
                ('company_id', '=', company.id)
            ], order='id')
            _logger.info(f"  - Tìm thấy {len(warehouses)} warehouse(s) cho company {company.name}")
            if warehouses:
                for wh in warehouses:
                    _logger.info(f"    + {wh.name} (ID: {wh.id}, Code: {wh.code})")
                warehouse = warehouses[0]
                _logger.info(f"  → Sử dụng warehouse đầu tiên: {warehouse.name} (code: {warehouse.code})")
            else:
                _logger.warning(f"  - Không tìm thấy warehouse nào cho company {company.name}")
                # Fallback: Tìm warehouse với code KHH (backward compatibility)
                _logger.info(f"  - Fallback: Tìm warehouse với code KHH...")
                warehouse = self.env['stock.warehouse'].search([
                    ('code', '=', 'KHH'),
                    ('company_id', '=', company.id)
                ], limit=1)
                if warehouse:
                    _logger.info(f"  → Sử dụng warehouse KHH (backward compatibility): {warehouse.name} (ID: {warehouse.id})")
                else:
                    _logger.error(f"  → Không tìm thấy warehouse KHH cho company {company.name}")
        
        if warehouse:
            _logger.info(f"=== Tìm picking type cho warehouse {warehouse.name} ===")
            _logger.info(f"Warehouse: {warehouse.name} (ID: {warehouse.id}, Code: {warehouse.code})")
            _logger.info(f"Company: {company.name} (ID: {company.id})")
            picking_types = self.env['stock.picking.type'].search([
                ('warehouse_id', '=', warehouse.id),
                ('sequence_code', '=', 'IN'),
                ('code', '=', 'incoming'),
                ('company_id', '=', company.id)
            ])
            _logger.info(f"Tìm thấy {len(picking_types)} picking type(s) phù hợp")
            if picking_types:
                for pt in picking_types:
                    _logger.info(f"  + {pt.name} (ID: {pt.id}, Code: {pt.code}, Sequence: {pt.sequence_code})")
                picking_type = picking_types[0]
                picking_type_id = picking_type.id
                _logger.info(f"→ Sử dụng picking type: {picking_type.name} (ID: {picking_type_id})")
            else:
                _logger.warning(f"Không tìm thấy phương thức vận chuyển cho warehouse {warehouse.name} (company: {company.name})")
                _logger.warning(f"Điều kiện tìm kiếm:")
                _logger.warning(f"  - warehouse_id = {warehouse.id}")
                _logger.warning(f"  - sequence_code = 'IN'")
                _logger.warning(f"  - code = 'incoming'")
                _logger.warning(f"  - company_id = {company.id}")
        else:
            _logger.error(f"Không tìm thấy warehouse cho company {company.name}")
        
        if not picking_type_id:
            _logger.error(f"=== LỖI: Không tìm thấy picking type ===")
            _logger.error(f"Company: {company.name} (ID: {company.id})")
            _logger.error(f"Warehouse: {warehouse.name if warehouse else 'None'} (ID: {warehouse.id if warehouse else 'None'})")
            raise UserError(u"Không tìm thấy phương thức vận chuyển (picking type) cho warehouse của công ty %s. Vui lòng kiểm tra cấu hình warehouse và picking type trong import.sale.order.config." % company.name)
        
        # Cập nhật các trường thông tin cuối cùng cho đơn mua
        _logger.info(f"=== Cập nhật thông tin cuối cùng cho purchase order ===")
        update_vals = {
            'user_id': self.user_id.id,
            'support_user_id': self.support_user_id.id,
            'date_order': self.date_order,
            'date_approve': self.date_order,
            'date_planned': self.received_date,
            'picking_type_id': picking_type_id,
            'tag_ids': [(6, 0, self.tag_ids.ids)] if self.tag_ids else False,
        }
        _logger.info(f"Giá trị cập nhật:")
        _logger.info(f"  - user_id: {update_vals['user_id']}")
        _logger.info(f"  - support_user_id: {update_vals['support_user_id']}")
        _logger.info(f"  - date_order: {update_vals['date_order']}")
        _logger.info(f"  - date_approve: {update_vals['date_approve']}")
        _logger.info(f"  - date_planned: {update_vals['date_planned']}")
        _logger.info(f"  - picking_type_id: {update_vals['picking_type_id']}")
        _logger.info(f"  - tag_ids: {len(self.tag_ids) if self.tag_ids else 0} tag(s)")
        purchase.write(update_vals)
        _logger.info(f"Đã cập nhật purchase order {purchase.name} thành công")
        
        # 6. Trả về action mở form đơn mua vừa cập nhật/tạo mới
        _logger.info(f"=== Hoàn thành cập nhật đơn mua ===")
        _logger.info(f"Purchase Order: {purchase.name} (ID: {purchase.id})")
        _logger.info(f"Company: {purchase.company_id.name if purchase.company_id else 'None'}")
        _logger.info(f"Warehouse: {warehouse.name if warehouse else 'None'}")
        _logger.info(f"Picking Type: {picking_type_id}")
        _logger.info(f"Trả về action để mở form purchase order")
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': purchase.id,
            'context': {
                'create': False,
                'edit': True
            }
        }

    def action_remove_include_extra_cost(self):
        """Xóa chi phí phát sinh khỏi đơn hàng"""
        for line in self.order_line:
            if line.base_price > 0:
                line.update({
                    'price_landing': 0,
                    'price_shipping': 0,
                })
            else:
                line.update({
                    'price_landing': 0,
                    'price_shipping': 0,
                })

    def get_purchase_and_sale_pricelist_rule(self, line):
        """Lấy quy tắc bảng giá mua và bán cho dòng đơn hàng"""
        self.ensure_one()
        sale_rule = None
        purchase_rule = None

        purchase_pricelist = None
        if not self.purchase_pricelist_id:
            purchase_pricelist = self.env['product.pricelist'].search([('type', '=', 'purchase')], limit=1)
            if purchase_pricelist:
                self.purchase_pricelist_id = purchase_pricelist.id

        purchase_pricelist_rules = self.purchase_pricelist_id.item_ids.filtered(
            lambda item: item.compute_price == 'fixed' and (
                    item.applied_on == '1_product' or item.applied_on == '0_product_variant') and (
                                 (item.product_id and item.product_id.id == line.product_id.id) or (
                                 item.product_tmpl_id and item.product_tmpl_id.id == line.product_id.product_tmpl_id.id)))
        if not purchase_pricelist_rules:
            purchase_pricelist_rules = self.purchase_pricelist_id.item_ids.filtered(
                lambda item: item.compute_price == 'fixed' and
                             item.applied_on == '2_product_category' and (
                                     item.categ_id and line.product_id.categ_id and item.categ_id.id == line.product_id.categ_id.id))
        if purchase_pricelist_rules:
            purchase_rule = purchase_pricelist_rules[0]

        sale_rules = self.pricelist_id.item_ids.filtered(
            lambda item: item.compute_price == 'formula' and (
                    item.applied_on == '1_product' or item.applied_on == '0_product_variant') and (
                                 (item.product_id and item.product_id.id == line.product_id.id) or (
                                 item.product_tmpl_id and item.product_tmpl_id.id == line.product_id.product_tmpl_id.id)))
        if not sale_rules:
            sale_rules = self.pricelist_id.item_ids.filtered(
                lambda item: item.compute_price == 'formula' and
                             item.applied_on == '2_product_category' and (
                                     item.categ_id and line.product_id.categ_id and item.categ_id.id == line.product_id.categ_id.id))
        if sale_rules:
            sale_rule = sale_rules[0]
        _logger.info('>>>>>>>>>> product id: %s have sale_rule %s and purchase_rule %s' % (
            line.product_id.id, sale_rule, purchase_rule))
        return {
            'sale_rule': sale_rule,
            'purchase_rule': purchase_rule,
        }

    def calculate_interest(self):
        """
        Tính toán lãi vay cho đơn hàng theo logic Google Sheets (Cách 2)
        
        Tham khảo: https://docs.google.com/spreadsheets/d/1LNc1qoGdk7KkFhj3kbg-UxUug-UgDtRE/edit?gid=846653463#gid=846653463
        
        Logic:
        - Số ngày tính lãi = (Ngày TT lần N) - (Ngày TT lần N-1) hoặc (Ngày TT lần 1) - (Ngày nhận hàng)
        - Số tiền tính lãi = Giá trị đơn - Tổng các lần trả trước đó
        - Lãi vay = Số ngày × Số tiền tính lãi × Lãi suất
        - Tính lãi cho TẤT CẢ các ngày từ lần thanh toán trước đến lần thanh toán hiện tại
        """
        for order in self:
            _logger.info(f"=== BẮT ĐẦU TÍNH LÃI VAY CHO ĐƠN HÀNG {order.name} ===")
            _logger.info(f"Khách hàng: {order.partner_id.name}")
            _logger.info(f"Tổng tiền đơn hàng (chưa VAT): {order.amount_untaxed:,.0f} VNĐ")
            _logger.info(f"Tổng khối lượng: {order.total_product_qty:,.0f} kg")
            
            # ========================================================================
            # KIỂM TRA ĐIỀU KIỆN BAN ĐẦU
            # ========================================================================
            if not order.invoice_ids:
                _logger.error("❌ Đơn hàng chưa có hoá đơn, không thể tính lãi vay")
                raise UserError("Đơn hàng chưa có hoá đơn, không thể tính lãi vay")
            
            if not order.payment_term_id:
                _logger.error("❌ Đơn hàng chưa có điều khoản thanh toán, không thể tính lãi vay")
                raise UserError("Đơn hàng chưa có điều khoản thanh toán, không thể tính lãi vay")
            
            if not hasattr(order.payment_term_id, 'lending_rate') or order.payment_term_id.lending_rate is None:
                _logger.error("❌ Điều khoản thanh toán chưa có lãi suất vay vốn")
                raise UserError("Điều khoản thanh toán chưa có lãi suất vay vốn")
            
            if order.payment_term_id.lending_rate <= 0:
                _logger.warning("⚠️ Lãi suất vay vốn bằng 0, không cần tính lãi vay")
                order.interest_amount = 0
                order.interest_per_kg = 0
                # Cập nhật price_landing = 0 cho tất cả các line
                for line in order.order_line:
                    line.price_landing = 0
                _logger.info("✅ Đã cập nhật lãi vay = 0 do lãi suất bằng 0")
                continue
            
            # Chuyển lãi suất từ % sang decimal (ví dụ: 0.02% → 0.0002)
            lending_rate = order.payment_term_id.lending_rate / 100
            _logger.info(f"Lãi suất vay vốn: {order.payment_term_id.lending_rate}%/ngày = {lending_rate}")
            
            # ========================================================================
            # XÁC ĐỊNH NGÀY BẮT ĐẦU TÍNH LÃI
            # ========================================================================
            # Ưu tiên: received_date, nếu không có thì lấy invoice_date sớm nhất
            posted_invoices = order.invoice_ids.filtered(lambda inv: inv.state == 'posted')
            _logger.info(f"Số hoá đơn đã vào sổ: {len(posted_invoices)}")
            
            invoice_date = None
            if posted_invoices:
                invoice_date = min(inv.invoice_date for inv in posted_invoices if inv.invoice_date)
            
            # Ngày bắt đầu tính lãi = ngày nhận hàng hoặc ngày hoá đơn sớm nhất
            start_date = order.received_date
            if not start_date and invoice_date:
                start_date = invoice_date
                _logger.info("📅 Sử dụng ngày hoá đơn làm ngày bắt đầu tính lãi")
            elif invoice_date and invoice_date < start_date:
                start_date = invoice_date
                _logger.info("📅 Sử dụng ngày hoá đơn (sớm hơn ngày nhận hàng) làm ngày bắt đầu tính lãi")
            else:
                _logger.info("📅 Sử dụng ngày nhận hàng làm ngày bắt đầu tính lãi")
            
            if not start_date:
                _logger.error("❌ Không thể xác định ngày bắt đầu tính lãi")
                raise UserError("Không thể xác định ngày bắt đầu tính lãi. Vui lòng kiểm tra ngày giao hàng hoặc ngày hoá đơn.")
            
            _logger.info(f"🚀 Ngày bắt đầu tính lãi: {start_date}")
            
            # ========================================================================
            # THU THẬP TẤT CẢ CÁC LẦN THANH TOÁN TỪ TẤT CẢ CÁC INVOICE
            # ========================================================================
            # Theo Google Sheets: Cần sắp xếp tất cả thanh toán theo ngày để xử lý tuần tự
            all_payments = []
            for invoice in posted_invoices:
                payment_info = invoice.invoice_payments_widget
                
                if not payment_info or not isinstance(payment_info, dict):
                    continue
                
                if not payment_info.get('content'):
                    continue
                
                # Thêm tất cả các lần thanh toán vào danh sách chung
                for payment in payment_info['content']:
                    all_payments.append(payment)
            
            # Sắp xếp tất cả các lần thanh toán theo ngày (theo logic Google Sheets)
            all_payments = sorted(all_payments, key=lambda x: x.get('date') or '')
            _logger.info(f"📊 Tổng số lần thanh toán từ tất cả các hoá đơn: {len(all_payments)}")
            
            # ========================================================================
            # TÍNH LÃI VAY THEO GOOGLE SHEETS (CÁCH 2)
            # ========================================================================
            # Logic:
            # - Số ngày tính lãi = (Ngày TT lần N) - (Ngày TT lần N-1) hoặc (Ngày TT lần 1) - (Ngày nhận hàng)
            # - Số tiền tính lãi = Giá trị đơn - Tổng các lần trả trước đó
            # - Lãi vay = Số ngày × Số tiền tính lãi × Lãi suất
            # ========================================================================
            
            total_interest = 0
            remaining_amount = order.amount_untaxed  # Số tiền còn nợ ban đầu (trước VAT)
            last_payment_date = start_date  # Ngày thanh toán cuối cùng (bắt đầu = ngày bắt đầu tính lãi)
            
            _logger.info(f"💰 Số tiền ban đầu cần tính lãi: {remaining_amount:,.0f} VNĐ")
            
            payment_count = 1
            
            for payment in all_payments:
                payment_date_str = payment.get('date')
                payment_amount = payment.get('amount', 0.0)  # Số tiền thanh toán có VAT
                
                if not payment_date_str:
                    _logger.warning(f"⚠️ Lần thanh toán {payment_count} không có ngày thanh toán, bỏ qua")
                    continue
                
                # Convert payment_date từ string sang date object
                # BỎ TRY-CATCH ĐỂ LỖI BUNG RA, KHÔNG GIẤU LỖI
                if isinstance(payment_date_str, str):
                    # Thử dùng fields.Date.from_string trước (chuẩn Odoo)
                    payment_date = fields.Date.from_string(payment_date_str)
                elif isinstance(payment_date_str, datetime):
                    payment_date = payment_date_str.date()
                elif hasattr(payment_date_str, 'date'):
                    payment_date = payment_date_str.date()
                else:
                    payment_date = payment_date_str
                
                # Kiểm tra kiểu dữ liệu - nếu không đúng sẽ raise lỗi
                if not isinstance(payment_date, type(start_date)):
                    raise ValueError(
                        f"Kiểu dữ liệu ngày thanh toán không hợp lệ: {type(payment_date)} "
                        f"(cần {type(start_date)}). Giá trị: {payment_date_str}"
                    )
                
                # ========================================================================
                # TÍNH SỐ NGÀY TÍNH LÃI
                # ========================================================================
                # Công thức: Số ngày = (Ngày TT lần N) - (Ngày TT lần N-1)
                #            hoặc (Ngày TT lần 1) - (Ngày nhận hàng)
                # LƯU Ý: Nếu thanh toán trước hạn, days_diff sẽ ÂM → lãi vay sẽ ÂM
                # ========================================================================
                days_diff = (payment_date - last_payment_date).days
                
                # Nếu thanh toán trước start_date, vẫn tính lãi (sẽ âm)
                if payment_date < start_date:
                    _logger.warning(f"⚠️ Thanh toán ngày {payment_date} trước ngày bắt đầu tính lãi {start_date}, lãi vay sẽ ÂM")
                
                # Áp dụng interest_calculation_extra_days (nếu có)
                if order.company_id.interest_calculation_extra_days:
                    days_diff = days_diff + order.company_id.interest_calculation_extra_days
                
                # ========================================================================
                # TÍNH LÃI VAY
                # ========================================================================
                # Công thức: Lãi vay = Số ngày × Số tiền tính lãi × Lãi suất
                # Số tiền tính lãi = Giá trị đơn - Tổng các lần trả trước đó
                # ========================================================================
                interest_so = days_diff * remaining_amount * lending_rate
                        # Log chi tiết từng lần tính
                _logger.info(f"\n💸 === THANH TOÁN LẦN {payment_count} ===")
                _logger.info(f"📅 Từ ngày: {last_payment_date} đến {payment_date}")
                _logger.info(f"📆 Số ngày tính lãi: {days_diff}")
                _logger.info(f"💵 Số tiền thanh toán (có VAT): {payment_amount:,.0f} VNĐ")
                _logger.info(f"💵 Số tiền thanh toán (trước VAT): {payment_amount/1.1:,.0f} VNĐ")
                _logger.info(f"💰 Số tiền tính lãi (dư nợ): {remaining_amount:,.0f} VNĐ")
                
                if days_diff > 0:
                    _logger.info(f"🧮 Công thức: {days_diff} ngày × {remaining_amount:,.0f} VNĐ × {lending_rate:.6f} = {interest_so:,.0f} VNĐ")
                    _logger.info(f"📈 Lãi SO phát sinh: {interest_so:,.0f} VNĐ")
                elif days_diff < 0:
                    _logger.info(f"🧮 Công thức: {days_diff} ngày (thanh toán trước hạn) × {remaining_amount:,.0f} VNĐ × {lending_rate:.6f} = {interest_so:,.0f} VNĐ")
                    _logger.info(f"📉 Lãi SO phát sinh (ÂM - thanh toán trước hạn): {interest_so:,.0f} VNĐ")
                else:
                    _logger.info(f"✅ Không tính lãi vay (số ngày = 0)")
                
                total_interest += interest_so
                _logger.info(f"📊 Tổng lãi lũy kế: {total_interest:,.0f} VNĐ")
                
                # ========================================================================
                # CẬP NHẬT SAU MỖI LẦN THANH TOÁN
                # ========================================================================
                # - Trừ số tiền đã thanh toán (trước VAT) khỏi remaining_amount
                # - Cập nhật last_payment_date để dùng cho lần thanh toán tiếp theo
                # ========================================================================
                payment_amount_before_vat = payment_amount / 1.1
                remaining_amount = remaining_amount - payment_amount_before_vat
                
                
                _logger.info(f"💰 Số tiền còn lại sau thanh toán: {remaining_amount:,.0f} VNĐ")
                
                last_payment_date = payment_date
                payment_count += 1
            
            # ========================================================================
            # TÍNH LÃI VAY ĐƠN MUA (PO)
            # ========================================================================
            # Theo Google Sheets: Lãi vay đơn mua = lending_rate * remaining_amount_po * lending_days
            # Tham khảo: https://docs.google.com/spreadsheets/d/1LNc1qoGdk7KkFhj3kbg-UxUug-UgDtRE/edit?gid=998231976#gid=998231976
            # ========================================================================
            total_interest_po = 0
            
            if order.auto_purchase_order_id:
                purchase = order.auto_purchase_order_id
                _logger.info(f"\n📦 === TÍNH LÃI VAY ĐƠN MUA (PO): {purchase.name} ===")
                
                # Kiểm tra PO có payment_term_id và lending_days không
                if purchase.payment_term_id and hasattr(purchase.payment_term_id, 'lending_days') and purchase.payment_term_id.lending_days:
                    po_lending_days = purchase.payment_term_id.lending_days
                    po_amount_untaxed = purchase.amount_untaxed
                    
                    _logger.info(f"💰 Giá trị PO (trước VAT): {po_amount_untaxed:,.0f} VNĐ")
                    _logger.info(f"📅 Thời hạn thanh toán đơn mua: {po_lending_days} ngày")
                    _logger.info(f"📊 Lãi suất vay vốn: {order.payment_term_id.lending_rate}%/ngày = {lending_rate}")
                    
                    # Tính lãi vay đơn mua
                    # Công thức: lending_rate * remaining_amount_po * lending_days
                    # remaining_amount_po = giá trị PO (trước VAT)
                    remaining_amount_po = po_amount_untaxed
                    total_interest_po = lending_rate * remaining_amount_po * po_lending_days
                    
                    _logger.info(f"🧮 Công thức: {lending_rate:.6f} × {remaining_amount_po:,.0f} VNĐ × {po_lending_days} ngày = {total_interest_po:,.0f} VNĐ")
                    _logger.info(f"💰 Lãi vay đơn mua: {total_interest_po:,.0f} VNĐ")
                else:
                    _logger.info(f"⚠️ PO không có thời hạn thanh toán (lending_days), không tính lãi vay đơn mua")
            else:
                _logger.info(f"ℹ️ Đơn hàng không có đơn mua (auto_purchase_order_id), không tính lãi vay đơn mua")
            
            # ========================================================================
            # TÍNH LÃI VAY CUỐI CÙNG (LÃI VAY ĐƠN BÁN - LÃI VAY ĐƠN MUA)
            # ========================================================================
            # Theo Google Sheets: Lãi vay cuối cùng = Lãi vay đơn bán - Lãi vay đơn mua
            # ========================================================================
            _logger.info(f"\n📊 === TÍNH LÃI VAY CUỐI CÙNG ===")
            _logger.info(f"💰 Lãi vay đơn bán: {total_interest:,.0f} VNĐ")
            _logger.info(f"💰 Lãi vay đơn mua: {total_interest_po:,.0f} VNĐ")
            
            # Lãi vay cuối cùng = Lãi vay đơn bán - Lãi vay đơn mua
            final_interest = total_interest - total_interest_po
            
            # Đảm bảo lãi vay cuối cùng không âm (theo logic nghiệp vụ)
            # if final_interest < 0:
            #     _logger.warning(f"⚠️ Lãi vay cuối cùng âm ({final_interest:,.0f}), đặt về 0")
            #     final_interest = 0
            
            _logger.info(f"🧮 Công thức: {total_interest:,.0f} - {total_interest_po:,.0f} = {final_interest:,.0f} VNĐ")
            _logger.info(f"💰 Lãi vay cuối cùng: {final_interest:,.0f} VNĐ")
            
            # ========================================================================
            # TÍNH LÃI VAY TRÊN MỖI KG
            # ========================================================================
            _logger.info(f"\n🧮 Tính lãi vay trên mỗi kg...")
            _logger.info(f"📊 Tổng lãi vay cuối cùng: {final_interest:,.0f} VNĐ")
            _logger.info(f"⚖️ Tổng khối lượng: {order.total_product_qty:,.0f} kg")
            
            if order.total_product_qty > 0:
                interest_per_kg = final_interest / order.total_product_qty
                _logger.info(f"🧮 Công thức lãi/kg: {final_interest:,.0f} ÷ {order.total_product_qty:,.0f} = {interest_per_kg:,.2f} VNĐ/kg")
            else:
                interest_per_kg = 0
                _logger.warning("⚠️ Tổng khối lượng bằng 0, không thể tính lãi trên mỗi kg")
            
            # ========================================================================
            # CẬP NHẬT KẾT QUẢ
            # ========================================================================
            old_interest_amount = order.interest_amount
            old_interest_per_kg = order.interest_per_kg
            
            order.interest_amount = final_interest
            order.interest_per_kg = interest_per_kg
            
            # Cập nhật price_landing cho từng line với giá trị đã làm tròn
            for line in order.order_line:
                # Làm tròn lãi vay theo quy tắc >=0.5 làm tròn lên, <0.5 làm tròn xuống
                decimal_part = interest_per_kg - int(interest_per_kg)
                if decimal_part >= 0.5:
                    rounded_price_landing = int(interest_per_kg) + 1
                else:
                    rounded_price_landing = int(interest_per_kg)
                line.price_landing = rounded_price_landing
                _logger.info(f"✅ Cập nhật price_landing cho line {line.name}: {line.price_landing}")
            
            # Log kết quả cuối cùng
            _logger.info(f"\n🎯 === KẾT QUẢ CUỐI CÙNG CHO ĐƠN HÀNG {order.name} ===")
            _logger.info(f"💰 Lãi vay đơn bán: {total_interest:,.0f} VNĐ")
            _logger.info(f"💰 Lãi vay đơn mua: {total_interest_po:,.0f} VNĐ")
            _logger.info(f"💰 Lãi vay cuối cùng: {final_interest:,.0f} VNĐ (cũ: {old_interest_amount:,.0f} VNĐ)")
            _logger.info(f"⚖️ Tổng khối lượng bán: {order.total_product_qty:,.0f} kg")
            _logger.info(f"📊 Lãi vay/kg: {interest_per_kg:,.2f} VNĐ/kg (cũ: {old_interest_per_kg:,.2f} VNĐ/kg)")
            
            if final_interest > 0:
                _logger.info(f"📈 Lãi vay đã được tính toán thành công!")
            else:
                _logger.info(f"ℹ️ Không có lãi vay phát sinh (hoặc lãi vay đơn mua >= lãi vay đơn bán)")
            
            _logger.info(f"✅ === HOÀN THÀNH TÍNH LÃI VAY CHO ĐƠN HÀNG {order.name} ===\n")
            return True

    def action_update_prices(self):
        """Cập nhật giá bán cho đơn hàng theo bảng giá"""
        _logger.info('begin action_update_prices()')
        self.ensure_one()

        total_qty = sum(line.product_uom_qty for line in self.order_line)
        res = super(SaleOrder, self).action_update_prices()
        if not self.purchase_pricelist_id:
            purchase_pricelist = self.env['product.pricelist'].search([('type', '=', 'purchase')], limit=1)
            if purchase_pricelist:
                self.purchase_pricelist_id = purchase_pricelist.id
        if not self.purchase_pricelist_id or not self.pricelist_id:
            return res
        for line in self.order_line:
            if not line.product_id or line.product_uom_qty <= 0:
                continue
            landing_cost = landing_cost_each_unit = price_shipping = 0
            rules = self.get_purchase_and_sale_pricelist_rule(line)
            purchase_pricelist_rule = rules.get('purchase_rule')
            pricelist_rule = rules.get('sale_rule')
            if not purchase_pricelist_rule:
                raise UserError(u"Sản phẩm %s không tìm thấy giá mua" % line.name)
            if not pricelist_rule:
                raise UserError(u"Sản phẩm %s không tìm thấy giá bán" % line.name)
            line.write({
                'purchase_price': purchase_pricelist_rule.fixed_price,
                'pricelist_item_id': purchase_pricelist_rule.id,
                'discount_value': pricelist_rule.discount_value
            })
            vals = {}
            if pricelist_rule.discount_value != 0 and purchase_pricelist_rule.fixed_price != 0:
                _logger.info('down purchase_price because have rule set discount_value')
                vals['purchase_price'] = purchase_pricelist_rule.fixed_price - pricelist_rule.discount_value
                vals['discount_value'] = pricelist_rule.discount_value
            else:
                vals['purchase_price'] = purchase_pricelist_rule.fixed_price
            if not line.product_id.quantity_supplier:
                line.product_id.quantity_supplier = 1
            if not line.product_id.quantity_tcvn:
                line.product_id.quantity_tcvn = 1
            if purchase_pricelist_rule and purchase_pricelist_rule.fixed_price:
                kl_ban = line.quantity_another1 * line.product_id.quantity_tcvn
                kl_mua = line.quantity_another1 * line.product_id.quantity_supplier
                if self.sale_type not in ['0_2', '0_4']:
                    kl_ban = kl_mua
                gia_mua = purchase_pricelist_rule.fixed_price - pricelist_rule.discount_value
                giamua_quydoi = gia_mua * kl_mua / kl_ban
                gia_goc = giamua_quydoi + pricelist_rule.price_min_margin
                # cost_price = line.price_shipping
                quantity_extra = 0
                product_uom_qty = 0
                if self.sale_type in ['0_1', '0_3', '0_5']:
                    product_uom_qty = line.quantity_another1 * line.product_id.quantity_supplier
                    quantity_extra = 0
                else:
                    quantity_extra = line.quantity_another1 * (
                            line.product_id.quantity_tcvn - line.product_id.quantity_supplier)
                    product_uom_qty = line.quantity_another1 * line.product_id.quantity_tcvn
                price_shipping = self.shipping_cost / total_qty
                price_unit = giamua_quydoi + line.cost_price + line.price_landing + pricelist_rule.price_min_margin
                vals.update({
                    'price_shipping': price_shipping,
                    'quantity_extra': quantity_extra,
                    'product_uom_qty': product_uom_qty,
                    'discount_value': pricelist_rule.discount_value,
                    # 'cost_price': cost_price,
                    'base_price': gia_goc,
                    'purchase_price': purchase_pricelist_rule.fixed_price,
                    'price_unit': price_unit,
                })
                line.update(vals)
                _logger.info(u"Tinh giá bán cho đơn hàng theo barem")
            else:
                raise UserError("Không tìm thấy bảng giá mua của sản phẩm %s" % line.product_id.name)
        self.show_update_pricelist = True
        self._onchange_payment_term_id()
        return res

    def update_margin(self):
        """Cập nhật lợi nhuận cho tất cả dòng đơn hàng"""
        for order in self:
            for line in order.order_line:
                line._compute_margin()
        return True

    def _prepare_invoice(self):
        """Chuẩn bị dữ liệu cho hóa đơn"""
        invoice_vals = super()._prepare_invoice()
        if self.tag_ids:
            invoice_vals['tag_ids'] = [(6, 0, self.tag_ids.ids)]
        return invoice_vals

    @api.depends('order_line.product_uom_qty')
    def _compute_total_product_qty(self):
        """Tính tổng số lượng sản phẩm của đơn hàng"""
        for order in self:
            order.total_product_qty = sum(line.product_uom_qty for line in order.order_line)

    @api.depends('order_line.difference_qty')
    def _compute_total_difference_qty(self):
        """Tính tổng khối lượng chênh lệch từ tất cả các dòng đơn hàng"""
        for order in self:
            order.total_difference_qty = sum(line.difference_qty for line in order.order_line)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    discount_value = fields.Float(u'CK', digits='Product Price', default=0.0)
    price_landing = fields.Integer(u'Lãi vay')
    price_shipping = fields.Integer(u'Vận chuyển(đ/kg)')
    quantity_extra = fields.Float(u'KL chênh')
    base_price = fields.Float(
        string=u'Giá gốc (mua vào)',
        help=u'Là giá mua quy đổi + lợi nhuận tối thiểu từ bảng giá bán. \n'
             u'Giá này được đưa về standard_price của sản phẩm khi xác nhận đơn hàng \n'
             u'Và làm giá mua sản phẩm khi tạo đơn mua',
        digits='Product Price'
    )
    quantity_another1 = fields.Integer(u'SL', default=1)
    quantity_another2 = fields.Integer(u'SL cây/bó')
    quantity_another3 = fields.Float(u'SL bó', digits='Product Price')
    cost_price = fields.Float('Chi Phí', help='Chi phí khác, không bao gồm lãi vay')
    purchase_amount = fields.Float(
        string=u'Tiền mua',
        compute='_compute_purchase_amount',
        store=True,
        help='Tiền mua = KL Mua * Giá vốn'
    )

    length = fields.Float(u'L(m)')
    purchase_price_each_unit = fields.Float(u'LN (đ/kg)', compute='_compute_margin', store=True, precompute=True)
    amount_costing = fields.Float(u'Tổng vốn', compute='_compute_amount_costing', store=True)
    price_unit = fields.Integer(
        string=u"Đơn giá",
        compute='_compute_price_unit',
        store=True, readonly=False, required=True, precompute=True)
    product_uom_qty = fields.Float(
        string=u"KL (kg)",
        compute='_compute_product_uom_qty',
        digits='Product Unit of Measure', default=1.0,
        store=True, readonly=False, required=True, precompute=True)
    purchase_uom_qty = fields.Float(
        string=u"KL (mua)",
        digits='Product Unit of Measure', default=1.0)
    difference_qty = fields.Float(compute='_compute_difference_qty', string='KL Chênh Lệch', store=True)
    supplier_ids = fields.Many2many(
        'res.partner',
        string=u'Các Nhà cung cấp',
        store=True,
        compute='_get_supplier_ids'
    )
    supplier_id = fields.Many2one(
        'res.partner',
        domain="[('id', 'in', supplier_ids)]",
        string=u'Nhà cung cấp')
    supplier_product_code = fields.Char(
        u'Mã NSX',
        compute='_compute_supplier_product_code',
        store=True
    )
    supplier_delivery_type_id = fields.Many2one('supplier.delivery.type', u'Quy cách')
    # todo: purchase_price will include 3 fields bellow
    supplier_discount_peer_month = fields.Float(
        u'Chiết khấu tháng',
        help=u'Chiết khấu sản lượng tháng của tháng theo doanh số bán')
    supplier_discount_peer_quarter = fields.Float(
        u'Chiết khấu quý', help=u'Chiết khấu sản lượng quý theo doanh số bán')
    supplier_commission_person = fields.Float(u'Hoa hồng bên mua')
    sale_commission_person = fields.Float(u'Hoa hồng bên bán')
    product_uom = fields.Many2one(
        comodel_name='uom.uom',
        string="ĐVT",
        compute='_compute_product_uom',
        store=True, readonly=False, precompute=True, ondelete='restrict',
        domain="[('category_id', '=', product_uom_category_id)]")

    @api.model
    def default_get(self, fields):
        result = super(SaleOrderLine, self).default_get(fields)
        delivery_types = self.env['supplier.delivery.type'].search([
            ('is_default', '=', True)
        ])
        if delivery_types:
            result['supplier_delivery_type_id'] = delivery_types[0].id
        result['length'] = 11.7
        return result

    @api.depends('quantity_another1', 'product_id', 'purchase_price', 'base_price')
    def _compute_amount_costing(self):
        for line in self:
            if line.quantity_another1 == 0:
                kl_mua = line.product_uom_qty
            else:
                kl_mua = line.quantity_another1 * line.product_id.quantity_supplier
            if not line.purchase_price:
                line.amount_costing = line.base_price * kl_mua
            else:
                line.amount_costing = line.purchase_price * kl_mua

    @api.depends('product_id')
    def _get_supplier_ids(self):
        for line in self:
            if line.product_id:
                line.supplier_ids = [seller.partner_id.id for seller in line.product_id.seller_ids]

    @api.depends('product_uom_qty', 'purchase_uom_qty')
    def _compute_difference_qty(self):
        for line in self:
            line.difference_qty = line.product_uom_qty - line.purchase_uom_qty

    @api.depends('product_id')
    def _compute_supplier_product_code(self):
        for line in self:
            if line.product_id and line.product_id.seller_ids:
                seller = line.product_id.seller_ids[0]
                line.supplier_product_code = seller.product_code
            else:
                continue

    def compute_margin_all(self):
        lines = self.search([])
        lines._compute_margin()
        return True

    @api.depends(
        'price_subtotal',
        'product_uom_qty',
        'purchase_price',
        'quantity_extra',
        'cost_price',
        'price_landing',
        'discount_value',
        'price_unit',
        'order_id.sale_type',
        'supplier_discount_peer_month',
        'supplier_discount_peer_quarter',
        'supplier_commission_person',
        'sale_commission_person')
    def _compute_margin(self):
        for line in self:
            line.purchase_price_each_unit = 0
            if line.order_id.sale_type == '0_0' or not line.product_id or not line.price_subtotal:
                return super(SaleOrderLine, self)._compute_margin()
            else:
                _logger.info('==> compute margin for sale line id {0}'.format(line.id))
                line._compute_amount_costing()
                kl_ban = line.product_uom_qty
                kl_mua = kl_ban - line.quantity_extra
                # if line.order_id.sale_type not in ['0_2', '0_4']:
                #     kl_ban = kl_mua
                giavon_da_ck = line.purchase_price - line.discount_value
                total_cost = line.cost_price
                loi_nhuan = kl_ban * line.price_unit - kl_mua * giavon_da_ck - total_cost * kl_ban - line.price_landing * kl_ban
                loi_nhuan_phan_tram = loi_nhuan / line.price_subtotal
                loi_nhuan_dong_tren_kg = loi_nhuan / kl_ban
                if line.supplier_discount_peer_month:
                    loi_nhuan += line.supplier_discount_peer_month * line.product_uom_qty
                if line.supplier_discount_peer_quarter:
                    loi_nhuan += line.supplier_discount_peer_quarter * line.product_uom_qty
                if line.supplier_commission_person:
                    loi_nhuan -= line.supplier_commission_person * line.product_uom_qty
                if line.sale_commission_person:
                    loi_nhuan -= line.sale_commission_person * line.product_uom_qty
                line.margin = loi_nhuan
                line.margin_percent = loi_nhuan_phan_tram
                line.purchase_price_each_unit = loi_nhuan_dong_tren_kg
                _logger.info('Loi nhuan [ %s ], Loi nhuan phan tram [ %s ] , Loi nhuan d/kg [ %s ]' % (
                    loi_nhuan, loi_nhuan_phan_tram, loi_nhuan_dong_tren_kg))

    @api.depends('product_id', 'company_id', 'currency_id', 'product_uom')
    def _compute_purchase_price(self):
        for line in self:
            if line.order_id.purchase_pricelist_id:
                _logger.info("Stop compute purchase_price if order have purchase pricelist")
                return True
        return super(SaleOrderLine, self)._compute_purchase_price()

    @api.onchange('product_id')
    def _onchange_product_id_change_quantity_another2(self):
        if self.product_id and self.product_id.quantity_another:
            self.quantity_another2 = self.product_id.quantity_another
        if self.quantity_another1 and self.product_id:
            self._onchange_quantity_another1()
        if self.product_id and self.product_id.seller_ids:
            for seller in self.product_id.seller_ids:
                self.supplier_id = seller.partner_id.id
                break

    @api.onchange('product_uom_qty', 'purchase_uom_qty')
    def _onchange_product_uom_qty_or_purchase_uom_qty(self):
        if self.product_uom_qty > 0 and self.purchase_uom_qty > 0:
            self.quantity_extra = self.product_uom_qty - self.purchase_uom_qty

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty(self):
        self.purchase_uom_qty = self.product_uom_qty

    @api.onchange('quantity_another1')
    def _onchange_quantity_another1(self):
        if self.quantity_another2 != 0:
            self.quantity_another3 = self.quantity_another1 / self.quantity_another2
        if self.quantity_another1 != 0 and self.product_id and self.product_id.quantity_supplier != 0 and self.product_id.quantity_tcvn != 0:
            if self.order_id.sale_type in [
                '0_2', '0_4']:
                self.quantity_extra = self.quantity_another1 * (
                        self.product_id.quantity_tcvn - self.product_id.quantity_supplier)
            else:
                self.quantity_extra = 0
            product_uom_qty = 0
            if self.order_id.sale_type in [
                '0_1', '0_3', '0_5']:
                product_uom_qty = self.quantity_another1 * self.product_id.quantity_supplier
            else:
                product_uom_qty = self.quantity_another1 * self.product_id.quantity_tcvn
            import math
            self.product_uom_qty = math.ceil(product_uom_qty)
            self._onchange_product_uom_qty()

    @api.onchange('quantity_another2')
    def _onchange_quantity_another2(self):
        if self.quantity_another1 != 0 and self.quantity_another2 != 0:
            self.quantity_another3 = self.quantity_another1 / self.quantity_another2

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            if line.order_id.sale_type == '0_0':
                return super(SaleOrderLine, self)._compute_price_unit()
            else:
                continue

    @api.depends('purchase_uom_qty', 'purchase_price')
    def _compute_purchase_amount(self):
        for line in self:
            line.purchase_amount = line.purchase_uom_qty * line.purchase_price
