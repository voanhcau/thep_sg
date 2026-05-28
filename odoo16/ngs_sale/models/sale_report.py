# -*- coding: utf-8 -*-

from odoo import fields, models


class SaleReport(models.Model):
    _inherit = 'sale.report'

    type_id = fields.Many2one(
        'res.partner.type',
        string='Loại KH (SO)',
        readonly=True,
        help='Loại khách hàng được chọn trực tiếp trên đơn hàng bán (sale.order.type_id)'
    )
    type_partner_id = fields.Many2one(
        'res.partner.type',
        string='Loại KH (KH)',
        readonly=True,
        help='Loại khách hàng lấy từ thông tin khách hàng (res.partner.type_id)'
    )

    def _select_additional_fields(self):
        """Thêm type_id và type_partner_id vào SELECT - sử dụng hook method để tương thích với các module khác
        
        Theo pattern của Odoo core (sale/report/sale_report.py):
        - type_id: Lấy từ sale_order (s.type_id) - field trực tiếp trên SO
        - type_partner_id: Lấy từ res_partner (partner.type_id) - field từ khách hàng
        
        Returns:
            dict: Mapping field name -> SQL expression
        """
        res = super()._select_additional_fields()
        # type_id: Lấy từ sale_order (s) - field trực tiếp trên đơn hàng bán
        res['type_id'] = "s.type_id"
        # type_partner_id: Lấy từ res_partner (partner) - field từ thông tin khách hàng
        res['type_partner_id'] = "partner.type_id"
        return res

    def _group_by_sale(self):
        """Thêm type_id và type_partner_id vào GROUP BY
        
        Theo pattern của Odoo core, các field được thêm vào SELECT cũng phải được thêm vào GROUP BY
        để đảm bảo SQL query hợp lệ.
        """
        group_by = super(SaleReport, self)._group_by_sale()
        group_by += """,
            s.type_id,
            partner.type_id"""
        return group_by
