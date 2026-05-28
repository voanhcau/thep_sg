# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class ACBFetchWizard(models.TransientModel):
    _name = 'acb.fetch.wizard'
    _description = 'Wizard lấy giao dịch ACB'

    config_id = fields.Many2one(
        'acb.config',
        string='Cấu hình ACB',
        required=True,
        default=lambda self: self.env['acb.config'].search([('active', '=', True)], limit=1)
    )
    
    date_range = fields.Selection([
        ('today', 'Hôm nay'),
        ('yesterday', 'Hôm qua'),
        ('this_week', 'Tuần này'),
        ('last_week', 'Tuần trước'),
        ('this_month', 'Tháng này'),
        ('last_month', 'Tháng trước'),
        ('custom', 'Tùy chỉnh')
    ], string='Khoảng thời gian', default='today', required=True)
    
    from_date = fields.Datetime(
        string='Từ ngày',
        default=fields.Datetime.now
    )
    
    to_date = fields.Datetime(
        string='Đến ngày',
        default=fields.Datetime.now
    )
    
    auto_process = fields.Boolean(
        string='Tự động xử lý giao dịch',
        default=True,
        help='Tự động xử lý giao dịch sau khi lấy về'
    )
    
    # Readonly fields to show results
    fetched_count = fields.Integer(
        string='Số giao dịch đã lấy',
        readonly=True
    )
    
    error_message = fields.Text(
        string='Thông báo lỗi',
        readonly=True
    )

    @api.onchange('date_range')
    def _onchange_date_range(self):
        """Cập nhật from_date và to_date khi thay đổi date_range"""
        if self.date_range == 'today':
            self.from_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            self.to_date = datetime.now()
        elif self.date_range == 'yesterday':
            yesterday = datetime.now() - timedelta(days=1)
            self.from_date = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            self.to_date = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif self.date_range == 'this_week':
            today = datetime.now()
            start_of_week = today - timedelta(days=today.weekday())
            self.from_date = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            self.to_date = datetime.now()
        elif self.date_range == 'last_week':
            today = datetime.now()
            start_of_last_week = today - timedelta(days=today.weekday() + 7)
            end_of_last_week = start_of_last_week + timedelta(days=6)
            self.from_date = start_of_last_week.replace(hour=0, minute=0, second=0, microsecond=0)
            self.to_date = end_of_last_week.replace(hour=23, minute=59, second=59, microsecond=999999)
        elif self.date_range == 'this_month':
            today = datetime.now()
            start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            self.from_date = start_of_month
            self.to_date = datetime.now()
        elif self.date_range == 'last_month':
            today = datetime.now()
            start_of_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            end_of_last_month = today.replace(day=1) - timedelta(days=1)
            self.from_date = start_of_last_month.replace(hour=0, minute=0, second=0, microsecond=0)
            self.to_date = end_of_last_month.replace(hour=23, minute=59, second=59, microsecond=999999)

    @api.constrains('from_date', 'to_date')
    def _check_date_range(self):
        """Kiểm tra khoảng thời gian hợp lệ"""
        for record in self:
            if record.from_date and record.to_date:
                if record.from_date > record.to_date:
                    raise ValidationError("Từ ngày phải nhỏ hơn đến ngày!")
                
                # Kiểm tra không quá 30 ngày
                if (record.to_date - record.from_date).days > 30:
                    raise ValidationError("Khoảng thời gian không được quá 30 ngày!")

    def action_fetch_transactions(self):
        """Thực hiện lấy giao dịch"""
        self.ensure_one()
        
        if not self.config_id:
            raise ValidationError("Vui lòng chọn cấu hình ACB!")
        
        _logger.info(f"=== Fetching transactions via wizard from {self.from_date} to {self.to_date} ===")
        
        try:
            # Gọi method fetch_transactions từ ACB config
            result = self.config_id.fetch_transactions(
                from_date=self.from_date,
                to_date=self.to_date
            )
            
            if result['success']:
                self.fetched_count = result['transactions_count']
                self.error_message = False
                
                # Tự động xử lý giao dịch nếu được chọn
                if self.auto_process and result['transactions']:
                    for transaction in result['transactions']:
                        try:
                            transaction.action_process()
                            _logger.info(f"Auto-processed transaction: {transaction.transaction_code}")
                        except Exception as e:
                            _logger.warning(f"Failed to auto-process transaction {transaction.transaction_code}: {str(e)}")
                
                # Hiển thị thông báo thành công
                message = f"Đã lấy thành công {self.fetched_count} giao dịch!"
                if self.auto_process:
                    message += " Các giao dịch đã được tự động xử lý."
                
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Lấy giao dịch ACB',
                        'message': message,
                        'type': 'success',
                        'sticky': False
                    }
                }
            else:
                self.error_message = result.get('error', 'Lỗi không xác định')
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Lấy giao dịch ACB',
                        'message': f"Lấy giao dịch thất bại: {self.error_message}",
                        'type': 'danger',
                        'sticky': True
                    }
                }
                
        except Exception as e:
            self.error_message = str(e)
            _logger.error(f"Error in wizard fetch: {str(e)}")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Lấy giao dịch ACB',
                    'message': f"Lỗi: {str(e)}",
                    'type': 'danger',
                    'sticky': True
                }
            }

    def action_view_transactions(self):
        """Xem danh sách giao dịch đã lấy"""
        self.ensure_one()
        
        domain = [
            ('transaction_date', '>=', self.from_date),
            ('transaction_date', '<=', self.to_date)
        ]
        
        if self.config_id:
            domain.append(('client_id', '=', self.config_id.client_id))
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Giao dịch ACB',
            'res_model': 'acb.transaction',
            'view_mode': 'tree,form',
            'domain': domain,
            'context': {
                'search_default_group_by_date': 1,
                'search_default_group_by_status': 1,
            }
        }

    def action_close(self):
        """Đóng wizard"""
        return {'type': 'ir.actions.act_window_close'} 