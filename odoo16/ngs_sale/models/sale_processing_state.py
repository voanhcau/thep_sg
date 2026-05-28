from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SaleProcessingState(models.Model):
    _name = 'sale.processing.state'
    _description = 'Sale Processing State'
    _rec_name = 'name'

    name = fields.Char(string='Tên trạng thái', required=True)
    description = fields.Text(string='Mô tả')

    @api.constrains('name')
    def _check_unique_name(self):
        """Đảm bảo rằng tên trạng thái là duy nhất."""
        for state in self:
            if self.search([('name', '=', state.name), ('id', '!=', state.id)]):
                raise ValidationError("Tên trạng thái phải là duy nhất!")

    def unlink(self):
        """Không cho phép xóa trạng thái nếu đang được sử dụng."""
        sale_orders = self.env['sale.order'].search([('processing_state_id', 'in', self.ids)])
        if sale_orders:
            raise ValidationError("Bạn không thể xóa trạng thái đang được sử dụng trong các đơn bán hàng.")
        return super(SaleProcessingState, self).unlink()


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    processing_state_id = fields.Many2one(
        'sale.processing.state',
        string='Trạng thái xử lý',
        ondelete='restrict',
        help='Trạng thái xử lý cho đơn bán hàng'
    )