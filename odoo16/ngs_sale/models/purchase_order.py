# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare, float_round
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, format_amount, format_date, formatLang, get_lang, groupby

import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_description = fields.Text(u'Nội dung và điều khoản mua hàng')
    default_location_dest_id = fields.Many2one('stock.location', string=u'Giao đến Kho', related='picking_type_id.default_location_dest_id', store=False)
    sale_id = fields.Many2one('sale.order', string=u'Đơn hàng')
    sale_type = fields.Selection(related="sale_id.sale_type", store=True, string=u'Kiểu mua bán')
    date_approve = fields.Datetime(u'Ngày xác nhận', readonly=False, index=True, copy=False)
    sale_reference_id = fields.Many2one('sale.order', string=u'Chi phí của')
    support_user_id = fields.Many2one('res.users', u'Nhân viên hỗ trợ')
    tag_ids = fields.Many2many('crm.tag', 'purchase_order_crm_tag_rel', 'purchase_id', 'crm_tag_id', string='Thẻ')
    buyer_id = fields.Many2one('res.users', string='Người mua')
    advance_state = fields.Selection([
        ('not_requested', 'Chưa yêu cầu tạm ứng'),
        ('requested', 'Đã đề xuất tạm ứng'),
        ('advanced', 'Đã tạm ứng')
    ], string='Trạng thái tạm ứng', default='not_requested', tracking=True)
    total_product_qty = fields.Float(
        string='KL (kg)',
        compute='_compute_total_product_qty',
        store=True
    )
    
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
    commission_tool_id = fields.Many2one('sale.commission.tool', string=u'Phiếu hoa hồng', copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        purchase_default = self.env['account.payment.term'].search([('purchase_default', '=', True)], limit=1)
        for val in vals_list:
            if val.get('type_id', None):
                types = self.env['res.partner.type'].search([('is_default', '=', True)])
                if types:
                    val.update({
                        'type_id': types[0].id
                    })
            if purchase_default and not val.get('payment_term_id'):
                val.update({
                    'payment_term_id': purchase_default.id
                })
        return super().create(vals_list)

    def force_cancel(self):
        self.state = 'cancel'
    
    def button_cancel(self):
        res = super().button_cancel()
        po_cancel = self.filtered(lambda p: p.state == 'cancel' and p.sale_reference_id)
        if po_cancel:
            for po in po_cancel:
                po.sale_reference_id._rebuild_cost()
        return res

    def button_approve(self, force=False):
        po_by_date_approve = {}
        for po in self:
            if po.date_approve:
                po_by_date_approve[po.id] = po.date_approve
        res = super().button_approve()
        for po in self:
            if po_by_date_approve.get(po.id, None):
                po.write({'date_approve': po_by_date_approve.get(po.id)})
        po_approved = self.filtered(lambda p: p.state == 'purchase' and p.sale_reference_id)
        if po_approved:
            for po in po_approved:
                po.sale_reference_id._rebuild_cost()
        return res

    @api.model
    def default_get(self, fields):
        result = super(PurchaseOrder, self).default_get(fields)
        result['purchase_description'] = self.env.user.company_id.purchase_description or ''
        return result

    def write(self, vals):
        for purchase in self:
            if not purchase.purchase_description and self.env.user.company_id and self.env.user.company_id.purchase_description:
                vals.update({
                    'purchase_description': self.env.user.company_id.purchase_description
                })
        return super(PurchaseOrder, self).write(vals)

    def _prepare_invoice(self):
        invoice_vals = super(PurchaseOrder, self)._prepare_invoice()
        # Copy tag_ids from purchase order to invoice
        invoice_vals['tag_ids'] = [(6, 0, self.tag_ids.ids)]
        return invoice_vals

    def button_propose_advance(self):
        self.advance_state = 'requested'

    def button_confirm_advance(self):
        self.advance_state = 'advanced'

    def button_cancel_advance(self):
        self.advance_state = 'not_requested'

    @api.depends('order_line.product_qty')
    def _compute_total_product_qty(self):
        for order in self:
            order.total_product_qty = sum(order.order_line.mapped('product_qty'))

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
        Odoo core chỉ quan tâm đến qty_to_invoice và invoice_ids,
        không quan tâm đến thanh toán. Logic này kết hợp cả 2 yếu tố.
        
        ===== TÁC ĐỘNG =====
        - Giải quyết vấn đề trong hình ảnh: PO P06906 và SO S07598
        - Trạng thái hiển thị chính xác theo nghiệp vụ thực tế
        - Nhất quán với Sale Order logic
        """
        for order in self:
            # ===== BƯỚC 1: KIỂM TRA CÓ HÓA ĐƠN KHÔNG =====
            if not order.invoice_ids:
                # Không có hóa đơn nào → Chưa tạo hóa đơn
                # Trường hợp: PO mới tạo, chưa có hóa đơn
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


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    quantity_another1 = fields.Float(u'SL', digits='Product Price')
    quantity_another2 = fields.Float(u'SL cây/bó', digits='Product Price')
    quantity_another3 = fields.Float(u'SL bó', digits='Product Price')
    length = fields.Float(u'L(m)')
    discount_value = fields.Float(u'CK')
    product_uom = fields.Many2one(
        'uom.uom', string='ĐVT',
        domain="[('category_id', '=', product_uom_category_id)]")
    report_id = fields.Many2one(
        'purchase.report.tool',
        string='Báo cáo sản lượng'
    )
    categ_id = fields.Many2one('product.category', related='product_id.categ_id', readonly=True)
    supplier_delivery_type_id = fields.Many2one('supplier.delivery.type', string='Quy cách')

    @api.onchange('product_id')
    def _onchange_product_id_change_quantity_another2(self):
        if self.product_id and self.product_id.quantity_another:
            self.quantity_another2 = self.product_id.quantity_another
        if self.quantity_another1 and self.product_id:
            self._onchange_quantity_another1()

    @api.onchange('quantity_another1')
    def _onchange_quantity_another1(self):
        if self.quantity_another2 != 0:
            self.quantity_another3 = self.quantity_another1 / self.quantity_another2
        if self.quantity_another1 != 0 and self.product_id and self.product_id.quantity_supplier != 0 and self.product_id.quantity_tcvn != 0:
            product_qty = 0
            if self.order_id.sale_type in [
                '0_1', '0_3', '0_5']:
                product_qty = self.quantity_another1 * self.product_id.quantity_supplier
            else:
                product_qty = self.quantity_another1 * self.product_id.quantity_tcvn
            self.product_qty = float_round(product_qty, precision_digits=0, rounding_method='HALF-UP')

    @api.onchange('quantity_another2')
    def _onchange_quantity_another2(self):
        if self.quantity_another1 != 0 and self.quantity_another2 != 0:
            self.quantity_another3 = self.quantity_another1 / self.quantity_another2

    @api.depends('product_qty', 'product_uom', 'company_id')
    def _prepare_purchase_order_line_data(self, so_line, date_order, company):
        # todo: no need on change quantity, change price unit of line
        quantity = so_line.product_id and so_line.product_uom._compute_quantity(
            so_line.product_uom_qty, so_line.product_id.uom_po_id) or so_line.product_uom_qty
        if so_line.purchase_uom_qty > 0:
            quantity = so_line.purchase_uom_qty
        return {
            'name': so_line.name,
            'product_qty': quantity,
            'product_id': so_line.product_id and so_line.product_id.id or False,
            'product_uom': so_line.product_id and so_line.product_id.uom_po_id.id or so_line.product_uom.id,
            'company_id': company.id,
            'date_planned': so_line.order_id.expected_date or date_order,
            'display_type': so_line.display_type,
        }

    @api.depends('product_qty', 'product_uom', 'company_id')
    def _compute_price_unit_and_date_planned_and_name(self):
        # todo: no need change product_qty change price unit
        for line in self:
            if not line.product_id or line.invoice_lines or not line.company_id:
                continue
            params = {'order_id': line.order_id}
            seller = line.product_id._select_seller(
                partner_id=line.partner_id,
                quantity=line.product_qty,
                date=line.order_id.date_order and line.order_id.date_order.date() or fields.Date.context_today(line),
                uom_id=line.product_uom,
                params=params)

            if seller or not line.date_planned:
                line.date_planned = line._get_date_planned(seller).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

            # If not seller, use the standard price. It needs a proper currency conversion.
            if not seller:
                unavailable_seller = line.product_id.seller_ids.filtered(
                    lambda s: s.partner_id == line.order_id.partner_id)
                if not unavailable_seller and line.price_unit and line.product_uom == line._origin.product_uom:
                    # Avoid to modify the price unit if there is no price list for this partner and
                    # the line has already one to avoid to override unit price set manually.
                    continue
                po_line_uom = line.product_uom or line.product_id.uom_po_id
                # price_unit = line.env['account.tax']._fix_tax_included_price_company(
                #     line.product_id.uom_id._compute_price(line.product_id.standard_price, po_line_uom),
                #     line.product_id.supplier_taxes_id,
                #     line.taxes_id,
                #     line.company_id,
                # )
                # price_unit = line.product_id.cost_currency_id._convert(
                #     price_unit,
                #     line.currency_id,
                #     line.company_id,
                #     line.date_order or fields.Date.context_today(line),
                #     False
                # )
                # line.price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places,
                #                                                                self.env[
                #                                                                    'decimal.precision'].precision_get(
                #                                                                    'Product Price')))
                continue

            price_unit = line.env['account.tax']._fix_tax_included_price_company(seller.price,
                                                                                 line.product_id.supplier_taxes_id,
                                                                                 line.taxes_id,
                                                                                 line.company_id) if seller else 0.0
            price_unit = seller.currency_id._convert(price_unit, line.currency_id, line.company_id,
                                                     line.date_order or fields.Date.context_today(line), False)
            price_unit = float_round(price_unit, precision_digits=max(line.currency_id.decimal_places,
                                                                      self.env['decimal.precision'].precision_get(
                                                                          'Product Price')))
            # line.price_unit = seller.product_uom._compute_price(price_unit, line.product_uom)

            # record product names to avoid resetting custom descriptions
            default_names = []
            vendors = line.product_id._prepare_sellers({})
            for vendor in vendors:
                product_ctx = {'seller_id': vendor.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                default_names.append(line._get_product_purchase_description(line.product_id.with_context(product_ctx)))
            if not line.name or line.name in default_names:
                product_ctx = {'seller_id': seller.id, 'lang': get_lang(line.env, line.partner_id.lang).code}
                line.name = line._get_product_purchase_description(line.product_id.with_context(product_ctx))

