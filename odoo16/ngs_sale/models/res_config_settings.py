from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_term_calculation = fields.Selection([
        ('invoice_date', 'Tính từ ngày hóa đơn'),
        ('receipt_date', 'Tính từ ngày nhận hàng')
    ], string='Cách tính thời hạn thanh toán',
        config_parameter='nsgerp.payment_term_calculation',
        default='invoice_date',
        help='Chọn cách tính thời hạn thanh toán cho hóa đơn')

    delivery_receipt_quality_note = fields.Char(
        string='Ghi chú chất lượng hàng hóa',
        config_parameter='nsgerp.delivery_receipt_quality_note',
        default='Hàng mới, không rỉ séc, không dính nước.',
        help='Ghi chú về chất lượng hàng hóa trong biên bản giao nhận'
    )

    delivery_receipt_responsibility_note = fields.Char(
        string='Ghi chú trách nhiệm giao nhận',
        config_parameter='nsgerp.delivery_receipt_responsibility_note',
        default='Việc giao nhận đã hoàn tất, và kể từ đây Bên giao không còn chịu trách nhiệm giải quyết sự thiếu hụt về số lượng này nữa, việc quản lý hàng hóa đã thuộc bên nhận hàng.',
        help='Ghi chú về trách nhiệm sau khi giao nhận'
    )

    delivery_receipt_documents_note = fields.Char(
        string='Ghi chú chứng từ kèm theo',
        config_parameter='nsgerp.delivery_receipt_documents_note',
        default='Bên giao hàng gửi kèm theo các chứng từ sau:\n+Biên bản giao nhận hàng hoá: 02 bản (NSG giữ 01 bản)\n+Chứng chỉ chất lượng và/ chứng chỉ xuất xưởng: 1 bộ bản cứng hoặc bản điện tử.',
        help='Ghi chú về các chứng từ kèm theo'
    ) 