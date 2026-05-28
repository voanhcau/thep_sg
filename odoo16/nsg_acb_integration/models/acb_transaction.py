# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class ACBTransaction(models.Model):
    _name = 'acb.transaction'
    _description = 'Giao dịch ACB'
    _order = 'transaction_date desc, id desc'
    _rec_name = 'transaction_code'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']

    # Thông tin định danh
    client_id = fields.Char(
        string='Client ID',
        required=True,
        help='Mã định danh khách hàng do khách hàng cung cấp cho ACB',
        index=True
    )
    
    client_request_id = fields.Char(
        string='Client Request ID',
        required=True,
        help='Mã định danh duy nhất cho mỗi yêu cầu do khách hàng tạo ra để truy vấn',
        index=True
    )
    
    checksum = fields.Char(
        string='Checksum',
        required=True,
        help='Mã hash dùng để kiểm tra tính chính xác của giao dịch'
    )
    
    # Thông tin phân trang
    page = fields.Integer(
        string='Trang hiện tại',
        default=1,
        help='Số trang hiện tại'
    )
    
    page_size = fields.Integer(
        string='Kích thước trang',
        default=100,
        help='Tổng số dòng dữ liệu trong 1 trang'
    )
    
    total_page = fields.Integer(
        string='Tổng số trang',
        help='Tổng số trang'
    )
    
    # Thông tin giao dịch
    transaction_status = fields.Selection([
        ('COMPLETED', 'Giao dịch thành công'),
        ('ERRORCORRECTED', 'Giao dịch bị hủy'),
    ], string='Trạng thái giao dịch', required=True, index=True)
    
    transaction_channel = fields.Selection([
        ('BAT', 'BAT'),
        ('VRU', 'VRU'),
        ('WWW', 'WWW'),
        ('ATM', 'ATM'),
        ('ONLI', 'ONLI'),
        ('ACH', 'ACH'),
        ('FSC', 'FSC'),
        ('CCM', 'CCM'),
        ('API', 'API'),
        ('MG', 'MG'),
        ('SECU', 'SECU'),
        ('MAPP', 'MAPP'),
        ('SMS', 'SMS'),
        ('ACHS', 'ACHS'),
        ('CCAT', 'CCAT'),
        ('AAP', 'AAP'),
        ('IBFT', 'IBFT'),
        ('CLMS', 'CLMS'),
        ('REMI', 'REMI'),
        ('TB', 'TB'),
        ('SOBA', 'SOBA'),
        ('BIZ', 'BIZ'),
    ], string='Kênh thực hiện giao dịch', required=True)
    
    transaction_code = fields.Char(
        string='Mã giao dịch',
        required=True,
        help='Mã giao dịch do ACB tạo ra khi hoàn tất giao dịch',
        index=True
    )
    
    account_number = fields.Char(
        string='Số tài khoản',
        required=True,
        help='Số tài khoản đã đăng ký nhận thông báo ghi có hoặc ghi nợ',
        index=True
    )
    
    transaction_date = fields.Datetime(
        string='Thời gian giao dịch',
        required=True,
        help='Thời gian thực hiện giao dịch, được ghi nhận theo giờ trên hệ thống của ACB',
        index=True
    )
    
    effective_date = fields.Datetime(
        string='Thời gian hiệu lực',
        required=True,
        help='Thời gian hiệu lực của giao dịch'
    )
    
    debit_or_credit = fields.Selection([
        ('debit', 'Ghi nợ'),
        ('credit', 'Ghi có'),
    ], string='Loại giao dịch', required=True, index=True)
    
    amount = fields.Float(
        string='Số tiền giao dịch',
        required=True,
        help='Số tiền giao dịch',
        index=True
    )
    
    # Thông tin tài khoản ảo
    virtual_account_id = fields.Char(
        string='Virtual Account ID',
        help='Mã tài khoản ảo, thông tin này chỉ hiển thị khi có giao dịch nộp tiền vào tài khoản ảo của khách hàng'
    )
    
    virtual_account_prefix = fields.Char(
        string='Virtual Account Prefix',
        help='Tiền tố tài khoản ảo'
    )
    
    virtual_account_number = fields.Char(
        string='Virtual Account Number',
        help='Số tài khoản ảo, thông tin này chỉ hiển thị khi có giao dịch nộp tiền vào tài khoản ảo của khách hàng'
    )
    
    # Thông tin chi tiết giao dịch
    transaction_content = fields.Text(
        string='Nội dung giao dịch',
        required=True,
        help='Nội dung của giao dịch'
    )
    
    # Thông tin bên giao dịch
    issue_bank_name = fields.Char(
        string='Tên ngân hàng chuyển tiền',
        help='Tên ngân hàng chuyển tiền'
    )
    
    virtual_account = fields.Char(
        string='Tài khoản ảo',
        help='Tài khoản ảo'
    )
    
    reference_number = fields.Char(
        string='Reference Number',
        help='Mã tham chiếu của giao dịch do hệ thống của khách hàng tạo ra'
    )
    
    partner_customer_code = fields.Char(
        string='Partner Customer Code',
        help='Mã định danh người dùng trên hệ thống của khách hàng'
    )
    
    partner_customer_name = fields.Char(
        string='Partner Customer Name',
        help='Tên người dùng trên hệ thống của khách hàng'
    )
    
    partner_customer_type = fields.Char(
        string='Partner Customer Type',
        help='Phân loại người dùng trên hệ thống của khách hàng để nhận diện KHCN, KHDN,...'
    )
    
    # Thông tin thêm
    custom1 = fields.Char(string='Thông tin mở rộng 1')
    custom2 = fields.Char(string='Thông tin mở rộng 2')
    custom3 = fields.Char(string='Thông tin mở rộng 3')
    custom4 = fields.Char(string='Thông tin mở rộng 4')
    custom5 = fields.Char(string='Thông tin mở rộng 5')
    custom6 = fields.Char(string='Thông tin mở rộng 6')
    custom7 = fields.Char(string='Thông tin mở rộng 7')
    custom8 = fields.Char(string='Thông tin mở rộng 8')
    custom9 = fields.Char(string='Thông tin mở rộng 9')
    custom10 = fields.Char(string='Thông tin mở rộng 10')
    
    # Thông tin hệ thống
    raw_data = fields.Text(
        string='Dữ liệu thô',
        help='Dữ liệu JSON gốc từ ACB'
    )
    
    response_timestamp = fields.Datetime(
        string='Thời gian phản hồi',
        help='Thời gian gửi phản hồi'
    )
    
    response_code = fields.Char(
        string='Mã phản hồi',
        help='Mã phản hồi gửi 8 ký tự số do ACB quy định'
    )
    
    response_message = fields.Char(
        string='Nội dung phản hồi',
        help='Nội dung chi tiết phản hồi'
    )
    
    # Trạng thái xử lý
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('processed', 'Đã xử lý'),
        ('error', 'Lỗi'),
        ('cancelled', 'Hủy bỏ'),
    ], string='Trạng thái', default='draft', index=True)
    
    error_message = fields.Text(
        string='Thông báo lỗi',
        help='Thông báo lỗi khi xử lý giao dịch'
    )
    
    # API source tracking
    source_type = fields.Selection([
        ('webhook', 'Webhook'),
        ('api_call', 'API Call'),
        ('manual', 'Manual'),
    ], string='Nguồn dữ liệu', default='webhook')
    
    api_call_time = fields.Datetime(
        string='Thời gian gọi API',
        help='Thời gian thực hiện API call'
    )
    
    # Liên kết với các record khác
    company_id = fields.Many2one(
        'res.company',
        string='Công ty',
        default=lambda self: self.env.company
    )
    
    partner_id = fields.Many2one(
        'res.partner',
        string='Khách hàng',
        help='Khách hàng liên quan đến giao dịch'
    )
    
    invoice_id = fields.Many2one(
        'account.move',
        string='Hóa đơn',
        help='Hóa đơn liên quan đến giao dịch'
    )
    
    payment_id = fields.Many2one(
        'account.payment',
        string='Thanh toán',
        help='Thanh toán liên quan đến giao dịch'
    )
    
    # Thông tin tính toán
    currency_id = fields.Many2one(
        'res.currency',
        string='Tiền tệ',
        default=lambda self: self.env.company.currency_id
    )
    
    amount_in_currency = fields.Monetary(
        string='Số tiền',
        currency_field='currency_id',
        help='Số tiền giao dịch theo tiền tệ'
    )

    @api.model
    def create_from_webhook(self, webhook_data):
        """
        Tạo giao dịch từ dữ liệu webhook
        
        Args:
            webhook_data (dict): Dữ liệu từ webhook ACB
            
        Returns:
            acb.transaction: Bản ghi giao dịch được tạo
        """
        _logger.info("=== Creating transaction from webhook ===")
        _logger.info(f"Webhook data: {json.dumps(webhook_data, ensure_ascii=False, indent=2)}")
        
        try:
            # Lấy thông tin cơ bản từ masterMeta
            master_meta = webhook_data.get('masterMeta', {})
            client_id = master_meta.get('clientId', '')
            client_request_id = master_meta.get('clientRequestId', '')
            checksum = webhook_data.get('checksum', '')  # Checksum có thể không có
            
            _logger.info(f"Client ID: {client_id}, Request ID: {client_request_id}")
            
            # Kiểm tra xem giao dịch đã tồn tại chưa
            existing_filter = [
                ('client_id', '=', client_id),
                ('client_request_id', '=', client_request_id)
            ]
            
            # Chỉ thêm checksum filter nếu có checksum
            if checksum:
                existing_filter.append(('checksum', '=', checksum))
            
            existing = self.search(existing_filter)
            
            if existing:
                _logger.warning(f"Transaction already exists: {client_request_id}")
                return existing
            
            # Xử lý danh sách requests
            requests_data = webhook_data.get('requests', [])
            if not requests_data:
                _logger.error("No requests data found in webhook")
                return self.env['acb.transaction']
            
            created_transactions = self.env['acb.transaction']
            
            for request_data in requests_data:
                # Lấy requestParams
                request_params = request_data.get('requestParams', {})
                
                # Lấy pagination info
                pagination = request_params.get('pagination', {})
                
                # Lấy thông tin giao dịch
                transactions = request_params.get('transactions', [])
                
                for trans in transactions:
                    _logger.info(f"Processing transaction: {trans.get('transactionCode', 'N/A')}")
                    
                    # Parse datetime
                    transaction_date = self._parse_datetime(trans.get('transactionDate'))
                    effective_date = self._parse_datetime(trans.get('effectiveDate'))
                    
                    # Tạo bản ghi giao dịch
                    transaction_vals = {
                        'client_id': client_id,
                        'client_request_id': client_request_id,
                        'checksum': checksum,
                        'page': pagination.get('page', 1),
                        'page_size': pagination.get('pageSize', 100),
                        'total_page': pagination.get('totalPage', 1),
                        'transaction_status': trans.get('transactionStatus', 'COMPLETED'),
                        'transaction_channel': trans.get('transactionChannel', 'API'),
                        'transaction_code': trans.get('transactionCode', ''),
                        'account_number': trans.get('accountNumber', ''),
                        'transaction_date': transaction_date,
                        'effective_date': effective_date,
                        'debit_or_credit': trans.get('debitOrCredit', 'credit'),
                        'amount': float(trans.get('amount', 0)),
                        'amount_in_currency': float(trans.get('amount', 0)),
                        'transaction_content': trans.get('transactionContent', ''),
                        'virtual_account_id': trans.get('virtualAccountInfo', {}).get('vaPrefiexId', ''),
                        'virtual_account_prefix': trans.get('virtualAccountInfo', {}).get('vaNbr', ''),
                        'virtual_account_number': trans.get('virtualAccountInfo', {}).get('vaNumber', ''),
                        'issue_bank_name': trans.get('issueBankName', ''),
                        'virtual_account': trans.get('virtualAccount', ''),
                        'reference_number': trans.get('referenceNumber', ''),
                        'partner_customer_code': trans.get('partnerCustomerCode', ''),
                        'partner_customer_name': trans.get('partnerCustomerName', ''),
                        'partner_customer_type': trans.get('partnerCustomerType', ''),
                        'custom1': trans.get('custom1', ''),
                        'custom2': trans.get('custom2', ''),
                        'custom3': trans.get('custom3', ''),
                        'custom4': trans.get('custom4', ''),
                        'custom5': trans.get('custom5', ''),
                        'custom6': trans.get('custom6', ''),
                        'custom7': trans.get('custom7', ''),
                        'custom8': trans.get('custom8', ''),
                        'custom9': trans.get('custom9', ''),
                        'custom10': trans.get('custom10', ''),
                        'raw_data': json.dumps(webhook_data, ensure_ascii=False),
                        'source_type': 'webhook',
                        'state': 'draft',
                    }
                    
                    transaction = self.create(transaction_vals)
                    created_transactions |= transaction
                    
                    _logger.info(f"Created transaction: {transaction.transaction_code} (ID: {transaction.id})")
            
            _logger.info(f"Total transactions created: {len(created_transactions)}")
            return created_transactions
            
        except Exception as e:
            _logger.error(f"Error creating transaction from webhook: {str(e)}")
            raise ValidationError(f"Lỗi tạo giao dịch: {str(e)}")

    @api.model
    def create_from_api_data(self, transaction_data, api_response_data):
        """
        Tạo giao dịch từ dữ liệu API call
        
        Args:
            transaction_data (dict): Dữ liệu giao dịch cụ thể
            api_response_data (dict): Dữ liệu response đầy đủ từ API
            
        Returns:
            acb.transaction: Bản ghi giao dịch được tạo
        """
        _logger.info("=== Creating transaction from API data ===")
        _logger.info(f"Transaction data: {json.dumps(transaction_data, ensure_ascii=False, indent=2)}")
        
        try:
            # Lấy thông tin từ API response
            client_id = api_response_data.get('clientId', '')
            client_request_id = api_response_data.get('clientRequestId', '')
            checksum = api_response_data.get('checksum', '')
            
            # Kiểm tra xem giao dịch đã tồn tại chưa (dựa trên transaction_code)
            transaction_code = transaction_data.get('transactionCode', '')
            if transaction_code:
                existing = self.search([
                    ('transaction_code', '=', transaction_code),
                    ('client_id', '=', client_id)
                ])
                
                if existing:
                    _logger.warning(f"Transaction with code {transaction_code} already exists")
                    return existing
            
            # Parse datetime
            transaction_date = self._parse_datetime(transaction_data.get('transactionDate'))
            effective_date = self._parse_datetime(transaction_data.get('effectiveDate'))
            
            # Tạo bản ghi giao dịch
            transaction_vals = {
                'client_id': client_id,
                'client_request_id': client_request_id,
                'checksum': checksum,
                'page': api_response_data.get('pagination', {}).get('page', 1),
                'page_size': api_response_data.get('pagination', {}).get('pageSize', 100),
                'total_page': api_response_data.get('pagination', {}).get('totalPage', 1),
                'transaction_status': transaction_data.get('transactionStatus', 'COMPLETED'),
                'transaction_channel': transaction_data.get('transactionChannel', 'API'),
                'transaction_code': transaction_code,
                'account_number': transaction_data.get('accountNumber', ''),
                'transaction_date': transaction_date,
                'effective_date': effective_date,
                'debit_or_credit': transaction_data.get('debitOrCredit', 'credit'),
                'amount': float(transaction_data.get('amount', 0)),
                'amount_in_currency': float(transaction_data.get('amount', 0)),
                'transaction_content': transaction_data.get('transactionContent', ''),
                'virtual_account_id': transaction_data.get('virtualAccountInfo', {}).get('vaPrefiexId', ''),
                'virtual_account_prefix': transaction_data.get('virtualAccountInfo', {}).get('vaNbr', ''),
                'issue_bank_name': transaction_data.get('issueBankName', ''),
                'virtual_account': transaction_data.get('virtualAccount', ''),
                'reference_number': transaction_data.get('referenceNumber', ''),
                'partner_customer_code': transaction_data.get('partnerCustomerCode', ''),
                'partner_customer_name': transaction_data.get('partnerCustomerName', ''),
                'partner_customer_type': transaction_data.get('partnerCustomerType', ''),
                'custom1': transaction_data.get('custom1', ''),
                'custom2': transaction_data.get('custom2', ''),
                'custom3': transaction_data.get('custom3', ''),
                'custom4': transaction_data.get('custom4', ''),
                'custom5': transaction_data.get('custom5', ''),
                'custom6': transaction_data.get('custom6', ''),
                'custom7': transaction_data.get('custom7', ''),
                'custom8': transaction_data.get('custom8', ''),
                'custom9': transaction_data.get('custom9', ''),
                'custom10': transaction_data.get('custom10', ''),
                'raw_data': json.dumps(api_response_data, ensure_ascii=False),
                'source_type': 'api_call',
                'api_call_time': datetime.now(),
                'state': 'draft',
            }
            
            transaction = self.create(transaction_vals)
            _logger.info(f"Created transaction from API: {transaction.transaction_code} (ID: {transaction.id})")
            
            return transaction
            
        except Exception as e:
            _logger.error(f"Error creating transaction from API data: {str(e)}")
            return False

    @api.model
    def _parse_datetime(self, datetime_str):
        """Parse datetime string từ ACB"""
        if not datetime_str:
            return False
        
        _logger.debug(f"Parsing datetime: {datetime_str}")
        
        try:
            # Format: 2021-04-20T08:48:27Z
            if 'T' in datetime_str and 'Z' in datetime_str:
                return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%SZ')
            # Format: 2022-09-19T03:28:51.000Z
            elif 'T' in datetime_str and '.000Z' in datetime_str:
                return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')
            # Format: 2022-09-18T17:00:00.000Z
            else:
                return datetime.strptime(datetime_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        except ValueError as e:
            _logger.error(f"Cannot parse datetime: {datetime_str}, error: {str(e)}")
            return False

    def action_process(self):
        """Xử lý giao dịch"""
        _logger.info(f"=== Processing {len(self)} transactions ===")
        
        for transaction in self:
            _logger.info(f"Processing transaction: {transaction.transaction_code}")
            try:
                # Thực hiện xử lý giao dịch
                # Tìm khách hàng dựa trên virtual account hoặc reference number
                partner = transaction._find_partner()
                if partner:
                    transaction.partner_id = partner.id
                    _logger.info(f"Found partner: {partner.name}")
                
                # Tự động tạo payment nếu cần
                if transaction.debit_or_credit == 'credit' and transaction.amount > 0:
                    payment = transaction._create_payment()
                    if payment:
                        _logger.info(f"Created payment: {payment.name}")
                        
                        # Thử tự động reconcile với invoice nếu có
                        if transaction.partner_id:
                            transaction._try_auto_reconcile_payment(payment)
                
                transaction.state = 'processed'
                _logger.info(f"Successfully processed transaction: {transaction.transaction_code}")
                
            except Exception as e:
                transaction.state = 'error'
                transaction.error_message = str(e)
                _logger.error(f"Error processing transaction {transaction.transaction_code}: {str(e)}")

    def _find_partner(self):
        """Tìm khách hàng dựa trên thông tin giao dịch"""
        self.ensure_one()
        _logger.info(f"Finding partner for transaction: {self.transaction_code}")
        _logger.info(f"Transaction content: '{self.transaction_content}'")
        
        partner = False
        
        # 1. Tìm theo transaction content (ưu tiên cao nhất)
        if self.transaction_content:
            partner = self._find_partner_by_transaction_content()
            if partner:
                _logger.info(f"Found partner by transaction content: {partner.name}")
                return partner
        
        # 2. Tìm theo reference number
        if self.reference_number:
            partner = self.env['res.partner'].search([
                ('ref', '=', self.reference_number)
            ], limit=1)
            if partner:
                _logger.info(f"Found partner by reference number: {partner.name}")
                return partner
        
        # 3. Tìm theo virtual account
        if self.virtual_account_number:
            partner = self.env['res.partner'].search([
                ('bank_account_number', '=', self.virtual_account_number)
            ], limit=1)
            if partner:
                _logger.info(f"Found partner by virtual account: {partner.name}")
                return partner
        
        # 4. Tìm theo partner customer code
        if self.partner_customer_code:
            partner = self.env['res.partner'].search([
                ('ref', '=', self.partner_customer_code)
            ], limit=1)
            if partner:
                _logger.info(f"Found partner by customer code: {partner.name}")
                return partner
        
        _logger.warning(f"No partner found for transaction: {self.transaction_code}")
        return False

    def _find_partner_by_transaction_content(self):
        """Tìm partner dựa trên transaction content"""
        self.ensure_one()
        _logger.info(f"Parsing transaction content: '{self.transaction_content}'")
        
        # Parse transaction content
        parsed_info = self._parse_transaction_content(self.transaction_content)
        _logger.info(f"Parsed info: {parsed_info}")
        
        partner = False
        
        # 1. Tìm theo order code (tìm từ sale.order hoặc account.move)
        if parsed_info.get('order_code'):
            partner = self._find_partner_by_order_code(parsed_info['order_code'])
            if partner:
                _logger.info(f"Found partner by order code '{parsed_info['order_code']}': {partner.name}")
                return partner
        
        # 2. Tìm theo customer code
        if parsed_info.get('customer_code'):
            partner = self._find_partner_by_customer_code(parsed_info['customer_code'])
            if partner:
                _logger.info(f"Found partner by customer code '{parsed_info['customer_code']}': {partner.name}")
                return partner
        
        # 3. Tìm theo từng part trong parsed_parts
        for part in parsed_info.get('parsed_parts', []):
            if len(part) >= 3:  # Chỉ tìm parts đủ dài
                # Try as customer ref
                partner = self.env['res.partner'].search([
                    ('ref', '=', part)
                ], limit=1)
                if partner:
                    _logger.info(f"Found partner by part ref '{part}': {partner.name}")
                    return partner
                
                # Try as order/invoice name
                partner = self._find_partner_by_order_code(part)
                if partner:
                    _logger.info(f"Found partner by part as order '{part}': {partner.name}")
                    return partner
        
        return False

    def _find_partner_by_order_code(self, order_code):
        """Tìm partner thông qua order code"""
        if not order_code:
            return False
        
        _logger.debug(f"Searching for partner by order code: {order_code}")
        
        # Tìm trong sale.order
        sale_order = self.env['sale.order'].search([
            ('name', '=', order_code)
        ], limit=1)
        
        if sale_order:
            _logger.debug(f"Found sale order: {sale_order.name}")
            return sale_order.partner_id
        
        # Tìm trong account.move (invoice)
        invoice = self.env['account.move'].search([
            ('name', '=', order_code),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ], limit=1)
        
        if invoice:
            _logger.debug(f"Found invoice: {invoice.name}")
            return invoice.partner_id
        
        # Tìm trong account.move với ref field
        invoice_by_ref = self.env['account.move'].search([
            ('ref', '=', order_code),
            ('move_type', 'in', ['out_invoice', 'out_refund'])
        ], limit=1)
        
        if invoice_by_ref:
            _logger.debug(f"Found invoice by ref: {invoice_by_ref.name}")
            return invoice_by_ref.partner_id
        
        return False

    def _find_partner_by_customer_code(self, customer_code):
        """Tìm partner thông qua customer code"""
        if not customer_code:
            return False
        
        _logger.debug(f"Searching for partner by customer code: {customer_code}")
        
        # Tìm theo ref
        partner = self.env['res.partner'].search([
            ('ref', '=', customer_code)
        ], limit=1)
        
        if partner:
            _logger.debug(f"Found partner by ref: {partner.name}")
            return partner
        
        # Tìm theo vat (nếu là số thuế)
        if customer_code.isdigit() and len(customer_code) >= 8:
            partner = self.env['res.partner'].search([
                ('vat', '=', customer_code)
            ], limit=1)
            if partner:
                _logger.debug(f"Found partner by vat: {partner.name}")
                return partner
        
        # Tìm theo phone (nếu là số điện thoại)
        if customer_code.isdigit() and len(customer_code) >= 9:
            partner = self.env['res.partner'].search([
                ('phone', '=', customer_code)
            ], limit=1)
            if partner:
                _logger.debug(f"Found partner by phone: {partner.name}")
                return partner
        
        return False

    def _parse_transaction_content(self, transaction_content):
        """
        Parse transaction content để extract thông tin đơn hàng và khách hàng
        
        Format thường gặp: "DH123456-959413224" hoặc "ORDER123-CUSTOMER456"
        
        Args:
            transaction_content (str): Nội dung giao dịch
            
        Returns:
            dict: Parsed info
        """
        if not transaction_content:
            return {
                'raw_content': transaction_content,
                'order_code': None,
                'customer_code': None,
                'parsed_parts': []
            }
        
        # Try to split by common separators
        separators = ['-', '_', '|', ':', ';', ' ']
        parts = []
        
        for sep in separators:
            if sep in transaction_content:
                parts = transaction_content.split(sep)
                break
        
        if not parts:
            parts = [transaction_content]
        
        # Clean up parts
        parts = [part.strip() for part in parts if part.strip()]
        
        result = {
            'raw_content': transaction_content,
            'order_code': None,
            'customer_code': None,
            'parsed_parts': parts
        }
        
        # Try to identify order code and customer code
        for part in parts:
            part_upper = part.upper()
            
            # Check for order code patterns
            if any(prefix in part_upper for prefix in ['DH', 'ORDER', 'SO', 'SALE', 'INV']):
                result['order_code'] = part
                
            # Check for customer code patterns (numeric or specific patterns)
            elif part.isdigit() and len(part) >= 6:
                result['customer_code'] = part
                
            # If starts with common customer prefixes
            elif any(prefix in part_upper for prefix in ['KH', 'CUST', 'CUSTOMER', 'CUS']):
                result['customer_code'] = part
        
        # If we have parts but no specific patterns, make reasonable assumptions
        if len(parts) >= 2 and not result['order_code'] and not result['customer_code']:
            # First part might be order, second might be customer
            result['order_code'] = parts[0]
            result['customer_code'] = parts[1]
        elif len(parts) == 1 and not result['order_code']:
            # Single part might be order code
            result['order_code'] = parts[0]
        
        return result

    def _create_payment(self):
        """Tạo payment record từ giao dịch"""
        self.ensure_one()
        _logger.info(f"Creating payment for transaction: {self.transaction_code}")
        
        if not self.partner_id:
            _logger.warning("No partner found, cannot create payment")
            return False
        
        try:
            # Tạo payment
            payment_vals = {
                'payment_type': 'inbound',
                'partner_type': 'customer',
                'partner_id': self.partner_id.id,
                'amount': self.amount,
                'currency_id': self.currency_id.id,
                'payment_date': self.transaction_date.date(),
                'payment_method_id': self.env.ref('account.account_payment_method_manual_in').id,
                'journal_id': self._get_bank_journal().id,
                'ref': f"ACB-{self.transaction_code}",
                'memo': self.transaction_content,
            }
            
            payment = self.env['account.payment'].create(payment_vals)
            self.payment_id = payment.id
            
            _logger.info(f"Created payment: {payment.name} for amount: {self.amount}")
            return payment
            
        except Exception as e:
            _logger.error(f"Error creating payment: {str(e)}")
            return False

    def _get_bank_journal(self):
        """Lấy journal ngân hàng"""
        bank_journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.company_id.id),
        ], limit=1)
        
        if not bank_journal:
            bank_journal = self.env['account.journal'].search([
                ('type', '=', 'bank'),
            ], limit=1)
        
        _logger.debug(f"Using bank journal: {bank_journal.name if bank_journal else 'None'}")
        return bank_journal

    def _try_auto_reconcile_payment(self, payment):
        """Thử tự động reconcile payment với invoice"""
        self.ensure_one()
        if not payment or not self.partner_id:
            return False
        
        _logger.info(f"Trying to auto-reconcile payment {payment.name} for partner {self.partner_id.name}")
        
        # Parse transaction content để tìm order code
        parsed_info = self._parse_transaction_content(self.transaction_content)
        order_code = parsed_info.get('order_code')
        
        if not order_code:
            _logger.info("No order code found in transaction content, skipping auto-reconcile")
            return False
        
        # Tìm invoice theo order code
        invoice = None
        
        # Tìm trong sale.order rồi lấy invoice
        sale_order = self.env['sale.order'].search([
            ('name', '=', order_code),
            ('partner_id', '=', self.partner_id.id)
        ], limit=1)
        
        if sale_order:
            # Lấy invoice từ sale order
            invoice = self.env['account.move'].search([
                ('invoice_origin', '=', sale_order.name),
                ('partner_id', '=', self.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ], limit=1, order='date desc')
            
            if invoice:
                _logger.info(f"Found invoice from sale order: {invoice.name}")
        
        # Tìm trực tiếp trong invoice
        if not invoice:
            invoice = self.env['account.move'].search([
                ('name', '=', order_code),
                ('partner_id', '=', self.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ], limit=1)
            
            if invoice:
                _logger.info(f"Found invoice directly: {invoice.name}")
        
        # Tìm theo ref
        if not invoice:
            invoice = self.env['account.move'].search([
                ('ref', '=', order_code),
                ('partner_id', '=', self.partner_id.id),
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('payment_state', 'in', ['not_paid', 'partial'])
            ], limit=1)
            
            if invoice:
                _logger.info(f"Found invoice by ref: {invoice.name}")
        
        if not invoice:
            _logger.info(f"No unpaid invoice found for order code: {order_code}")
            return False
        
        # Kiểm tra số tiền
        if abs(invoice.amount_residual - payment.amount) > 0.01:
            _logger.warning(f"Payment amount ({payment.amount}) doesn't match invoice residual ({invoice.amount_residual})")
            # Vẫn thử reconcile partial
        
        try:
            # Tạo reconcile
            _logger.info(f"Attempting to reconcile payment {payment.name} with invoice {invoice.name}")
            
            # Lấy receivable line từ invoice
            receivable_line = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'receivable')
            
            # Lấy liquidity line từ payment
            liquidity_line = payment.move_id.line_ids.filtered(lambda l: l.account_id.user_type_id.type in ['liquidity'])
            
            if receivable_line and liquidity_line:
                # Reconcile lines
                lines_to_reconcile = receivable_line + liquidity_line
                lines_to_reconcile.reconcile()
                
                _logger.info(f"Successfully reconciled payment {payment.name} with invoice {invoice.name}")
                return True
            else:
                _logger.warning("Could not find appropriate lines for reconciliation")
                
        except Exception as e:
            _logger.error(f"Error during auto-reconciliation: {str(e)}")
            
        return False

    def action_view_api_call_log(self):
        """Xem log API call cho giao dịch này"""
        self.ensure_one()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': f'API Call Log - {self.transaction_code}',
                'message': f'Source: {self.source_type}\nAPI Call Time: {self.api_call_time}\nRaw Data:\n{self.raw_data}',
                'type': 'info',
                'sticky': True
            }
        } 