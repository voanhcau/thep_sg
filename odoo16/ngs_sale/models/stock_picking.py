# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    received_date = fields.Date(string="Ngày nhận hàng")
    delivery_receipt_construction_site = fields.Html(
        string="Biên bản giao nhận",
        default=lambda self: self.env.company.delivery_receipt_construction_site,
        help="Phần mở đầu biên bản giao nhận (HTML). Mặc định lấy theo công ty, có thể chỉnh trực tiếp trên phiếu."
    )

    def _get_user_id_from_origin(self, origin):
        """Lấy user_id từ origin (sale order hoặc purchase order)"""
        if not origin:
            return False
        
        origin = origin.strip()
        # Parse origin để xác định loại order
        # Format: "S00015" (sale order) hoặc "P00021" (purchase order)
        if origin.startswith('S'):
            # Tìm sale order theo name
            sale_order = self.env['sale.order'].search([('name', '=', origin)], limit=1)
            if sale_order and sale_order.user_id:
                return sale_order.user_id.id
        elif origin.startswith('P'):
            # Tìm purchase order theo name
            purchase_order = self.env['purchase.order'].search([('name', '=', origin)], limit=1)
            if purchase_order and purchase_order.user_id:
                return purchase_order.user_id.id
        
        return False

    @api.model
    def create(self, vals):
        """Tự động điền user_id từ origin (sale.order hoặc purchase.order)"""
        # Nếu chưa có user_id và có origin trong vals, thử lấy user_id trước khi create
        if not vals.get('user_id') and vals.get('origin'):
            user_id = self._get_user_id_from_origin(vals['origin'])
            if user_id:
                vals['user_id'] = user_id
        
        picking = super(StockPicking, self).create(vals)
        
        # Sau khi create, kiểm tra lại nếu chưa có user_id (trường hợp origin được set sau)
        if not picking.user_id and picking.origin:
            user_id = picking._get_user_id_from_origin(picking.origin)
            if user_id:
                picking.user_id = user_id
        
        return picking

    def write(self, vals):
        """Cập nhật user_id khi thay đổi origin"""
        for picking in self:
            # Cập nhật user_id nếu thay đổi origin hoặc chưa có user_id
            # Chỉ cập nhật nếu user_id chưa được set trong vals và picking chưa có user_id
            if not vals.get('user_id') and not picking.user_id:
                # Kiểm tra origin trong vals hoặc picking hiện tại
                origin = vals.get('origin') or picking.origin
                if origin:
                    user_id = picking._get_user_id_from_origin(origin)
                    if user_id:
                        vals['user_id'] = user_id
            
            # Logic cũ: kiểm tra received_date
            if vals.get('state') == 'done' and not vals.get('received_date') and not picking.received_date:
                raise UserError("Vui lòng nhập 'Ngày nhận hàng' trước khi chuyển trạng thái sang 'Done'.")
            if vals.get('state') == 'done' and picking.sale_id:
                received_date = vals.get('received_date', None)
                if not received_date:
                    received_date = picking.received_date
                picking.sale_id.write({'received_date': received_date})
        return super(StockPicking, self).write(vals)
