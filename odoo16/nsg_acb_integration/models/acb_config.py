# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
import hashlib
import hmac
import logging
import requests
import json
from datetime import datetime, timedelta

_logger = logging.getLogger(__name__)


class ACBConfig(models.Model):
    _name = 'acb.config'
    _description = 'Cấu hình kết nối ACB'
    _rec_name = 'name'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    name = fields.Char(
        string='Tên cấu hình',
        required=True,
        default='ACB Configuration'
    )
    
    # Thông tin kết nối API
    api_base_url = fields.Char(
        string='API Base URL',
        required=True,
        default='https://sandbox.acb.com.vn/acb/open/transactions/notification-api-adapter/v1',
        help='URL gốc của API ACB'
    )
    
    api_notification_url = fields.Char(
        string='API Notification URL',
        required=True,
        default='https://sandbox.acb.com.vn/acb/open/transactions/notification-api-adapter/v1/rtxn-notification',
        help='URL đầy đủ của API notification ACB'
    )
    
    client_id = fields.Char(
        string='Client ID',
        required=True,
        default='30735a42d5313ce3a29284d3cbfd1d8f',
        help='Mã định danh khách hàng do khách hàng cung cấp cho ACB'
    )
    
    secret_key = fields.Char(
        string='Secret Key',
        required=True,
        default='c3a571706fe79e816e918d6386d23a4f',
        help='Khóa bí mật để xác thực checksum'
    )
    
    # Thông tin tài khoản ảo
    virtual_account_id = fields.Char(
        string='Virtual Account ID',
        help='Mã tài khoản ảo để nhận thông báo giao dịch'
    )
    
    virtual_account_prefix = fields.Char(
        string='Virtual Account Prefix',
        help='Tiền tố tài khoản ảo'
    )
    
    # Cấu hình webhook
    webhook_url = fields.Char(
        string='Webhook URL',
        help='URL webhook để ACB gửi thông báo giao dịch đến'
    )
    
    # Cấu hình khác
    active = fields.Boolean(
        string='Kích hoạt',
        default=True
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    
    # Logging
    enable_logging = fields.Boolean(
        string='Bật logging',
        default=True,
        help='Ghi log các giao dịch từ ACB'
    )
    
    # API Testing
    last_api_call = fields.Datetime(
        string='Lần gọi API cuối',
        readonly=True
    )
    
    last_api_response = fields.Text(
        string='Response API cuối',
        readonly=True
    )
    
    api_call_count = fields.Integer(
        string='Số lần gọi API',
        default=0,
        readonly=True
    )
    
    # Thống kê
    total_transactions = fields.Integer(
        string='Tổng số giao dịch',
        compute='_compute_statistics',
        store=True
    )
    
    last_transaction_date = fields.Datetime(
        string='Giao dịch cuối cùng',
        compute='_compute_statistics',
        store=True
    )

    @api.depends('client_id')
    def _compute_statistics(self):
        """Tính toán thống kê giao dịch"""
        _logger.info("=== Computing ACB statistics ===")
        for config in self:
            transactions = self.env['acb.transaction'].search([
                ('client_id', '=', config.client_id)
            ])
            config.total_transactions = len(transactions)
            if transactions:
                config.last_transaction_date = max(transactions.mapped('transaction_date'))
                _logger.info(f"Config {config.name}: {len(transactions)} transactions, last: {config.last_transaction_date}")
            else:
                config.last_transaction_date = False
                _logger.info(f"Config {config.name}: No transactions found")

    def _create_checksum(self, data):
        """
        Tạo checksum cho request gửi đến ACB
        
        Args:
            data (dict): Dữ liệu request
            
        Returns:
            str: Checksum đã tạo
        """
        self.ensure_one()
        _logger.info(f"=== Creating checksum for data: {data} ===")
        
        if not self.secret_key:
            _logger.error("Secret key chưa được cấu hình")
            raise ValidationError("Secret key chưa được cấu hình")
            
        try:
            # Tạo chuỗi để hash theo format của ACB
            # clientId + clientRequestId + amount + transactionDate
            message = f"{data.get('clientId', '')}{data.get('clientRequestId', '')}"
            
            # Thêm amount nếu có
            if 'amount' in data:
                message += str(data['amount'])
            
            # Thêm transactionDate nếu có
            if 'transactionDate' in data:
                message += str(data['transactionDate'])
            
            _logger.info(f"Message to hash: {message}")
            
            # Tạo HMAC SHA256
            calculated_checksum = hmac.new(
                self.secret_key.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            _logger.info(f"Generated checksum: {calculated_checksum}")
            return calculated_checksum
            
        except Exception as e:
            _logger.error(f"Lỗi tạo checksum: {str(e)}")
            raise ValidationError(f"Lỗi tạo checksum: {str(e)}")

    def validate_checksum(self, data, received_checksum):
        """
        Xác thực checksum từ ACB
        
        Args:
            data (dict): Dữ liệu giao dịch
            received_checksum (str): Checksum nhận từ ACB
            
        Returns:
            bool: True nếu checksum hợp lệ
        """
        self.ensure_one()
        _logger.info(f"=== Validating checksum ===")
        _logger.info(f"Received checksum: {received_checksum}")
        _logger.info(f"Data: {data}")
        
        if not self.secret_key:
            _logger.error("Secret key chưa được cấu hình")
            return False
            
        try:
            # Tạo checksum từ data
            calculated_checksum = self._create_checksum(data)
            
            _logger.info(f"Calculated checksum: {calculated_checksum}")
            _logger.info(f"Received checksum: {received_checksum}")
            
            is_valid = hmac.compare_digest(calculated_checksum, received_checksum)
            _logger.info(f"Checksum validation result: {is_valid}")
            
            return is_valid
            
        except Exception as e:
            _logger.error(f"Lỗi xác thực checksum: {str(e)}")
            return False

    def call_acb_api(self, request_data=None):
        """
        Gọi API ACB để lấy thông báo giao dịch
        
        Args:
            request_data (dict): Dữ liệu request tùy chỉnh
            
        Returns:
            dict: Response từ ACB API
        """
        self.ensure_one()
        _logger.info("=== Calling ACB API ===")
        _logger.info(f"API URL: {self.api_notification_url}")
        _logger.info(f"Client ID: {self.client_id}")
        
        try:
            # Chuẩn bị dữ liệu request
            if not request_data:
                # Tạo request mặc định để test
                request_data = {
                    "clientId": self.client_id,
                    "clientRequestId": f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "requestMeta": {
                        "requestType": "NOTIFICATION"
                    },
                    "requestParams": {
                        "pagination": {
                            "page": 1,
                            "pageSize": 100,
                            "totalPage": 1
                        },
                        "transactions": []
                    }
                }
            
            # Tạo checksum
            checksum = self._create_checksum(request_data)
            request_data['checksum'] = checksum
            
            _logger.info(f"Request data: {json.dumps(request_data, ensure_ascii=False, indent=2)}")
            
            # Chuẩn bị headers
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            _logger.info(f"Request headers: {headers}")
            
            # Gọi API
            response = requests.post(
                self.api_notification_url,
                json=request_data,
                headers=headers,
                timeout=30
            )
            
            _logger.info(f"Response status code: {response.status_code}")
            _logger.info(f"Response headers: {dict(response.headers)}")
            
            # Xử lý response
            response_data = {}
            try:
                response_data = response.json()
                _logger.info(f"Response JSON: {json.dumps(response_data, ensure_ascii=False, indent=2)}")
            except:
                response_data = {
                    'error': 'Invalid JSON response',
                    'text': response.text
                }
                _logger.error(f"Response text: {response.text}")
            
            # Cập nhật thống kê
            self.write({
                'last_api_call': datetime.now(),
                'last_api_response': json.dumps(response_data, ensure_ascii=False, indent=2),
                'api_call_count': self.api_call_count + 1
            })
            
            return {
                'success': response.status_code == 200,
                'status_code': response.status_code,
                'data': response_data,
                'request': request_data
            }
            
        except requests.exceptions.Timeout:
            error_msg = "Timeout khi gọi API ACB"
            _logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except requests.exceptions.ConnectionError:
            error_msg = "Không thể kết nối đến API ACB"
            _logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f"Lỗi gọi API ACB: {str(e)}"
            _logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def test_api_connection(self):
        """Test kết nối API và hiển thị kết quả"""
        self.ensure_one()
        _logger.info("=== Testing ACB API connection ===")
        
        # Gọi API
        result = self.call_acb_api()
        
        if result['success']:
            message = f"Kết nối thành công!\nStatus: {result['status_code']}\nResponse: {json.dumps(result['data'], ensure_ascii=False, indent=2)}"
            msg_type = 'success'
            _logger.info("API connection test successful")
        else:
            message = f"Kết nối thất bại!\nLỗi: {result.get('error', 'Unknown error')}"
            msg_type = 'danger'
            _logger.error(f"API connection test failed: {result.get('error')}")
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Test API ACB',
                'message': message,
                'type': msg_type,
                'sticky': True
            }
        }

    def get_webhook_endpoint(self):
        """Lấy endpoint webhook đầy đủ"""
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/acb/webhook/transaction"

    @api.constrains('client_id')
    def _check_unique_client_id(self):
        """Đảm bảo client_id là duy nhất"""
        for record in self:
            if record.client_id:
                existing = self.search([
                    ('client_id', '=', record.client_id),
                    ('id', '!=', record.id)
                ])
                if existing:
                    raise ValidationError(f"Client ID {record.client_id} đã tồn tại!")

    def test_connection(self):
        """Test kết nối đến ACB API (method cũ, giữ lại để tương thích)"""
        return self.test_api_connection()

    def fetch_transactions(self, from_date=None, to_date=None):
        """
        Lấy giao dịch từ ACB trong khoảng thời gian
        
        Args:
            from_date (datetime): Từ ngày
            to_date (datetime): Đến ngày
            
        Returns:
            dict: Kết quả và danh sách giao dịch
        """
        self.ensure_one()
        _logger.info(f"=== Fetching transactions from {from_date} to {to_date} ===")
        
        try:
            # Chuẩn bị request data
            if not from_date:
                from_date = datetime.now() - timedelta(days=1)
            if not to_date:
                to_date = datetime.now()
            
            request_data = {
                "clientId": self.client_id,
                "clientRequestId": f"fetch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "requestMeta": {
                    "requestType": "NOTIFICATION"
                },
                "requestParams": {
                    "fromDate": from_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "toDate": to_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    "pagination": {
                        "page": 1,
                        "pageSize": 100,
                        "totalPage": 1
                    }
                }
            }
            
            # Gọi API
            result = self.call_acb_api(request_data)
            
            if result['success']:
                # Xử lý response và tạo giao dịch
                response_data = result['data']
                transactions_created = []
                
                # Kiểm tra nếu có giao dịch trong response
                if 'requests' in response_data:
                    for req_data in response_data['requests']:
                        if 'transactions' in req_data:
                            for trans_data in req_data['transactions']:
                                # Tạo giao dịch từ dữ liệu
                                transaction = self.env['acb.transaction'].create_from_api_data(
                                    trans_data, response_data
                                )
                                if transaction:
                                    transactions_created.append(transaction)
                
                _logger.info(f"Created {len(transactions_created)} transactions")
                return {
                    'success': True,
                    'transactions_count': len(transactions_created),
                    'transactions': transactions_created
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Lỗi lấy giao dịch: {str(e)}"
            _logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }

    def action_fetch_transactions(self):
        """Action để lấy giao dịch từ ACB"""
        self.ensure_one()
        _logger.info("=== Manual fetch transactions action ===")
        
        result = self.fetch_transactions()
        
        if result['success']:
            message = f"Đã lấy thành công {result['transactions_count']} giao dịch!"
            msg_type = 'success'
        else:
            message = f"Lấy giao dịch thất bại: {result.get('error', 'Unknown error')}"
            msg_type = 'danger'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Lấy giao dịch ACB',
                'message': message,
                'type': msg_type,
                'sticky': False
            }
        } 