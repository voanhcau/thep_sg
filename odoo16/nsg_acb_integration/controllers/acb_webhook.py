# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime
from werkzeug.exceptions import BadRequest

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class ACBWebhookController(http.Controller):
    """Controller xử lý webhook từ ACB"""

    @http.route('/acb/webhook/transaction', type='json', auth='none', methods=['POST'], csrf=False)
    def handle_transaction_webhook(self):
        """
        Xử lý webhook thông báo giao dịch từ ACB
        
        BƯỚC 1: Chỉ đón và logger ra data mà ACB gửi sang
        
        Endpoint: POST /acb/webhook/transaction
        Content-Type: application/json
        
        Returns:
            dict: Response theo format ACB yêu cầu
        """
        start_time = datetime.now()
        _logger.info("=" * 80)
        _logger.info("=== ACB WEBHOOK - BƯỚC 1: NHẬN VÀ LOG DATA ===")
        _logger.info(f"Timestamp: {start_time}")
        _logger.info(f"Request IP: {request.httprequest.environ.get('REMOTE_ADDR', 'Unknown')}")
        _logger.info(f"User Agent: {request.httprequest.headers.get('User-Agent', 'Unknown')}")
        _logger.info("=" * 80)
        
        try:
            # Log request headers
            headers_dict = dict(request.httprequest.headers)
            _logger.info("=== REQUEST HEADERS ===")
            _logger.info(json.dumps(headers_dict, indent=2))
            
            # Lấy dữ liệu JSON từ request (theo cách Odoo chuẩn như Adyen webhook)
            webhook_data = request.dispatcher.jsonrequest
            if not webhook_data:
                _logger.error("❌ ERROR: No JSON data received in request")
                return self._create_error_response("400", "Không nhận được dữ liệu JSON")
            
            _logger.info("=== RAW WEBHOOK DATA FROM ACB ===")
            _logger.info(json.dumps(webhook_data, ensure_ascii=False, indent=2))
            
            # BƯỚC 2: Phân tích dữ liệu (chỉ log, không xử lý)
            self._analyze_webhook_data(webhook_data)
            
            # Tạm thời bỏ qua validate và processing
            _logger.info("=== SKIPPING VALIDATION AND PROCESSING (TESTING MODE) ===")
            
            # Log processing time
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            _logger.info(f"✅ Webhook data received and logged successfully in {processing_time:.2f} seconds")
            
            # Return success response
            response = self._create_success_response()
            
            # Log response
            _logger.info("=== RESPONSE TO ACB ===")
            _logger.info(json.dumps(response, ensure_ascii=False, indent=2))
            _logger.info("=" * 80)
            
            return response
                
        except Exception as e:
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            _logger.error(f"❌ CRITICAL ERROR processing webhook after {processing_time:.2f}s: {str(e)}")
            _logger.exception("Full exception traceback:")
            _logger.info("=" * 80)
            return self._create_error_response("500", f"Lỗi xử lý webhook: {str(e)}")

    def _analyze_webhook_data(self, webhook_data):
        """
        BƯỚC 2: Phân tích dữ liệu từ body JSON mà ACB gửi sang
        Chỉ logger ra, chưa xử lý gì cả
        
        Args:
            webhook_data (dict): Dữ liệu webhook từ ACB
        """
        _logger.info("🔍 === BƯỚC 2: PHÂN TÍCH DỮ LIỆU ACB ===")
        
        try:
            # 1. Phân tích masterMeta
            master_meta = webhook_data.get('masterMeta', {})
            _logger.info("📋 MASTER META ANALYSIS:")
            _logger.info(f"   - Client ID: {master_meta.get('clientId', 'NOT_PROVIDED')}")
            _logger.info(f"   - Client Request ID: {master_meta.get('clientRequestId', 'NOT_PROVIDED')}")
            
            # 2. Phân tích requests array
            requests_data = webhook_data.get('requests', [])
            _logger.info(f"📦 REQUESTS ANALYSIS:")
            _logger.info(f"   - Total requests: {len(requests_data)}")
            
            for idx, req_data in enumerate(requests_data):
                _logger.info(f"   🔸 Request {idx + 1}:")
                
                # Request meta
                request_meta = req_data.get('requestMeta', {})
                _logger.info(f"      - Type: {request_meta.get('requestType', 'NOT_PROVIDED')}")
                _logger.info(f"      - Code: {request_meta.get('requestCode', 'NOT_PROVIDED')}")
                
                # Request params
                request_params = req_data.get('requestParams', {})
                
                # Pagination
                pagination = request_params.get('pagination', {})
                _logger.info(f"      - Pagination: Page {pagination.get('page', 'N/A')}/{pagination.get('totalPage', 'N/A')}, Size: {pagination.get('pageSize', 'N/A')}")
                
                # Transactions
                transactions = request_params.get('transactions', [])
                _logger.info(f"      - Transactions count: {len(transactions)}")
                
                # Phân tích từng transaction
                for trans_idx, trans in enumerate(transactions):
                    _logger.info(f"         💳 Transaction {trans_idx + 1}:")
                    _logger.info(f"            - Status: {trans.get('transactionStatus', 'N/A')}")
                    _logger.info(f"            - Channel: {trans.get('transactionChannel', 'N/A')}")
                    _logger.info(f"            - Code: {trans.get('transactionCode', 'N/A')}")
                    _logger.info(f"            - Account: {trans.get('accountNumber', 'N/A')}")
                    _logger.info(f"            - Date: {trans.get('transactionDate', 'N/A')}")
                    _logger.info(f"            - Effective Date: {trans.get('effectiveDate', 'N/A')}")
                    _logger.info(f"            - Type: {trans.get('debitOrCredit', 'N/A')}")
                    _logger.info(f"            - Amount: {trans.get('amount', 'N/A')}")
                    _logger.info(f"            - Content: '{trans.get('transactionContent', 'N/A')}'")
                    _logger.info(f"            - Virtual Account Info: {trans.get('virtualAccountInfo', 'N/A')}")
                    _logger.info(f"            - Entity Attributes: {trans.get('transactionEntityAttribute', 'N/A')}")
                    
                    # Phân tích transaction content chi tiết
                    transaction_content = trans.get('transactionContent', '')
                    if transaction_content:
                        _logger.info(f"            🔍 PARSING TRANSACTION CONTENT:")
                        parsed_info = self._parse_transaction_content(transaction_content)
                        _logger.info(f"            - Raw: '{parsed_info['raw_content']}'")
                        _logger.info(f"            - Order Code: {parsed_info['order_code']}")
                        _logger.info(f"            - Customer Code: {parsed_info['customer_code']}")
                        _logger.info(f"            - All Parts: {parsed_info['parsed_parts']}")
            
            # 3. Tổng kết
            total_transactions = sum(len(req.get('requestParams', {}).get('transactions', [])) for req in requests_data)
            _logger.info(f"📊 SUMMARY:")
            _logger.info(f"   - Total transactions to process: {total_transactions}")
            _logger.info(f"   - Data structure: ✅ Valid ACB format")
            _logger.info("✅ Data analysis completed successfully")
            
        except Exception as e:
            _logger.error(f"❌ Error analyzing webhook data: {str(e)}")
            _logger.exception("Analysis error details:")
        
        _logger.info("🔍 === END OF DATA ANALYSIS ===")

    def _log_webhook_parameters(self, webhook_data):
        """DEPRECATED: Replaced by _analyze_webhook_data"""
        pass

    @http.route('/acb/webhook/test', type='http', auth='none', methods=['GET'], csrf=False)
    def test_webhook(self):
        """Test endpoint webhook"""
        _logger.info("=== ACB WEBHOOK TEST ENDPOINT ACCESSED ===")
        _logger.info(f"Timestamp: {datetime.now()}")
        _logger.info(f"Request IP: {request.httprequest.environ.get('REMOTE_ADDR', 'Unknown')}")
        
        response_data = {
            'status': 'success',
            'message': 'ACB Webhook endpoint is working',
            'timestamp': datetime.now().isoformat(),
            'endpoint': '/acb/webhook/test',
            'version': '1.0.0'
        }
        
        _logger.info(f"Test response: {json.dumps(response_data, indent=2)}")
        return json.dumps(response_data)

    @http.route('/acb/webhook/simulate', type='json', auth='user', methods=['POST'], csrf=False)
    def simulate_acb_webhook(self):
        """Simulate ACB webhook call với format mới - CHỈ ĐỂ TEST"""
        _logger.info("=== SIMULATING ACB WEBHOOK CALL FOR TESTING ===")
        _logger.info(f"User: {request.env.user.name}")
        _logger.info(f"Timestamp: {datetime.now()}")
        
        try:
            # Tạo sample webhook data theo format ACB thực tế
            sample_webhook_data = {
                "masterMeta": {
                    "clientId": "bec6e2dab04eaccb2d3cef544c59731d",
                    "clientRequestId": f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                },
                "requests": [
                    {
                        "requestMeta": {
                            "requestType": "NOTIFICATION",
                            "requestCode": "TRANSACTION_UPDATE"
                        },
                        "requestParams": {
                            "transactions": [
                                {
                                    "transactionStatus": "COMPLETED",
                                    "transactionChannel": "SOBA",
                                    "transactionCode": 11053,
                                    "accountNumber": 5168389,
                                    "transactionDate": "2023-09-20T09:51:50.000Z",
                                    "effectiveDate": "2023-09-19T17:00:00.000Z",
                                    "debitOrCredit": "credit",
                                    "virtualAccountInfo": None,
                                    "amount": 50000,
                                    "transactionEntityAttribute": {},
                                    "transactionContent": "DH123456-959413224"
                                }
                            ],
                            "pagination": {
                                "page": 1,
                                "pageSize": 1,
                                "totalPage": 1
                            }
                        }
                    }
                ]
            }
            
            _logger.info(f"Sample webhook data: {json.dumps(sample_webhook_data, indent=2)}")
            
            # Simulate calling webhook handler
            original_request = request.dispatcher.jsonrequest
            request.dispatcher.jsonrequest = sample_webhook_data
            
            try:
                result = self.handle_transaction_webhook()
                _logger.info(f"Webhook simulation result: {result}")
                
                return {
                    'success': True,
                    'message': 'Webhook simulation completed successfully',
                    'webhook_data': sample_webhook_data,
                    'result': result
                }
            finally:
                request.dispatcher.jsonrequest = original_request
            
        except Exception as e:
            _logger.error(f"Error simulating webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/acb/api/test', type='json', auth='user', methods=['POST'], csrf=False)
    def test_acb_api_call(self):
        """Test endpoint để gọi ACB API từ UI"""
        _logger.info("=== ACB API TEST CALL ===")
        _logger.info(f"User: {request.env.user.name}")
        _logger.info(f"Timestamp: {datetime.now()}")
        
        try:
            # Lấy cấu hình ACB đang active
            acb_config = request.env['acb.config'].search([
                ('active', '=', True)
            ], limit=1)
            
            if not acb_config:
                return {
                    'success': False,
                    'error': 'Không tìm thấy cấu hình ACB active'
                }
            
            _logger.info(f"Using ACB config: {acb_config.name}")
            
            # Gọi API test
            result = acb_config.test_api_connection()
            
            _logger.info(f"API test result: {result}")
            return {
                'success': True,
                'result': result
            }
            
        except Exception as e:
            _logger.error(f"Error in API test: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    @http.route('/acb/api/fetch-transactions', type='json', auth='user', methods=['POST'], csrf=False)
    def fetch_transactions_from_api(self):
        """Endpoint để lấy giao dịch từ ACB API"""
        _logger.info("=== MANUAL FETCH TRANSACTIONS FROM ACB API ===")
        _logger.info(f"User: {request.env.user.name}")
        _logger.info(f"Timestamp: {datetime.now()}")
        
        try:
            # Lấy parameters từ request
            params = request.dispatcher.jsonrequest or {}
            from_date = params.get('from_date')
            to_date = params.get('to_date')
            
            _logger.info(f"Parameters: from_date={from_date}, to_date={to_date}")
            
            # Lấy cấu hình ACB đang active
            acb_config = request.env['acb.config'].search([
                ('active', '=', True)
            ], limit=1)
            
            if not acb_config:
                return {
                    'success': False,
                    'error': 'Không tìm thấy cấu hình ACB active'
                }
            
            _logger.info(f"Using ACB config: {acb_config.name}")
            
            # Parse dates if provided
            from_date_obj = None
            to_date_obj = None
            
            if from_date:
                from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
            if to_date:
                to_date_obj = datetime.strptime(to_date, '%Y-%m-%d')
            
            # Gọi API lấy giao dịch
            result = acb_config.fetch_transactions(from_date_obj, to_date_obj)
            
            _logger.info(f"Fetch result: success={result.get('success')}, transactions={result.get('transactions_count', 0)}")
            
            return result
            
        except Exception as e:
            _logger.error(f"Error fetching transactions: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _validate_webhook_data(self, data):
        """
        Validate dữ liệu webhook cơ bản
        
        Args:
            data (dict): Dữ liệu webhook
            
        Returns:
            dict: {'valid': bool, 'message': str}
        """
        _logger.info("=== VALIDATING WEBHOOK DATA ===")
        
        # Kiểm tra masterMeta
        master_meta = data.get('masterMeta', {})
        if not master_meta:
            error_msg = "Missing masterMeta object"
            _logger.error(error_msg)
            return {'valid': False, 'message': "Thiếu thông tin masterMeta"}
        
        # Kiểm tra required fields trong masterMeta
        required_meta_fields = ['clientId', 'clientRequestId']
        for field in required_meta_fields:
            if field not in master_meta or not master_meta[field]:
                error_msg = f"Missing required field in masterMeta: {field}"
                _logger.error(error_msg)
                return {'valid': False, 'message': f"Thiếu trường bắt buộc trong masterMeta: {field}"}
        
        # Validate client_id format
        client_id = master_meta.get('clientId', '')
        if not client_id or len(client_id) < 10:
            error_msg = f"Invalid client_id format: {client_id}"
            _logger.error(error_msg)
            return {'valid': False, 'message': f"Client ID không hợp lệ: {client_id}"}
        
        # Validate client_request_id format
        client_request_id = master_meta.get('clientRequestId', '')
        if not client_request_id or len(client_request_id) < 10:
            error_msg = f"Invalid client_request_id format: {client_request_id}"
            _logger.error(error_msg)
            return {'valid': False, 'message': f"Client Request ID không hợp lệ: {client_request_id}"}
        
        # Validate requests structure
        requests_data = data.get('requests', [])
        if not isinstance(requests_data, list):
            error_msg = "Requests field must be a list"
            _logger.error(error_msg)
            return {'valid': False, 'message': "Trường requests phải là mảng"}
        
        if not requests_data:
            error_msg = "Empty requests array"
            _logger.error(error_msg)
            return {'valid': False, 'message': "Mảng requests trống"}
        
        # Validate request structure
        for idx, req_data in enumerate(requests_data):
            request_params = req_data.get('requestParams', {})
            if not request_params:
                error_msg = f"Missing requestParams in request {idx}"
                _logger.error(error_msg)
                return {'valid': False, 'message': f"Thiếu requestParams trong request {idx}"}
            
            transactions = request_params.get('transactions', [])
            if not isinstance(transactions, list):
                error_msg = f"Transactions must be a list in request {idx}"
                _logger.error(error_msg)
                return {'valid': False, 'message': f"Transactions phải là mảng trong request {idx}"}
        
        _logger.info(f"Validation passed for {len(requests_data)} request(s)")
        return {'valid': True, 'message': 'Valid'}

    def _process_transaction(self, webhook_data):
        """
        Xử lý giao dịch từ webhook
        
        Args:
            webhook_data (dict): Dữ liệu webhook
            
        Returns:
            dict: {'success': bool, 'message': str, 'transactions_count': int}
        """
        _logger.info("=== PROCESSING WEBHOOK TRANSACTIONS ===")
        
        try:
            # Tạo giao dịch từ webhook data
            transaction_model = request.env['acb.transaction'].sudo()
            transactions = transaction_model.create_from_webhook(webhook_data)
            
            if not transactions:
                error_msg = "No transactions created from webhook data"
                _logger.warning(error_msg)
                return {
                    'success': False,
                    'message': "Không tạo được giao dịch từ dữ liệu webhook",
                    'transactions_count': 0
                }
            
            transactions_count = len(transactions)
            _logger.info(f"Created {transactions_count} transaction(s)")
            
            # Tự động xử lý giao dịch nếu cần
            auto_process_param = request.env['ir.config_parameter'].sudo().get_param('acb.auto_process', 'True')
            auto_process = auto_process_param.lower() == 'true'
            
            if auto_process:
                _logger.info("Auto-processing transactions...")
                processed_count = 0
                error_count = 0
                
                for transaction in transactions:
                    if transaction.state == 'draft':
                        try:
                            transaction.action_process()
                            processed_count += 1
                            _logger.debug(f"Auto-processed transaction: {transaction.transaction_code}")
                        except Exception as e:
                            error_count += 1
                            _logger.warning(f"Failed to auto-process transaction {transaction.transaction_code}: {str(e)}")
                            # Không fail cả request, chỉ log warning
                
                _logger.info(f"Auto-processing completed: {processed_count} processed, {error_count} errors")
            
            return {
                'success': True,
                'message': "Thành công",
                'transactions_count': transactions_count
            }
            
        except Exception as e:
            error_msg = f"Error processing transactions: {str(e)}"
            _logger.error(error_msg)
            _logger.exception("Full exception traceback:")
            return {
                'success': False,
                'message': str(e),
                'transactions_count': 0
            }

    def _create_success_response(self):
        """
        Tạo response thành công theo format ACB
        
        Returns:
            dict: Response data
        """
        response = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "responseCode": "00000000",
            "message": "Success",
            "responseBody": {
                "index": 1,
                "referenceCode": "123456"
            }
        }
        
        _logger.debug(f"Success response created: {response}")
        return response

    def _create_error_response(self, error_code, message):
        """
        Tạo response lỗi theo format ACB
        
        Args:
            error_code (str): Mã lỗi
            message (str): Thông báo lỗi
            
        Returns:
            dict: Response data
        """
        response = {
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "responseCode": error_code.zfill(8),  # Pad to 8 digits
            "message": message,
            "responseBody": {
                "index": 1,
                "referenceCode": "000000"
            }
        }
        
        _logger.debug(f"Error response created: {response}")
        return response

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
            if any(prefix in part_upper for prefix in ['DH', 'ORDER', 'SO', 'SALE']):
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

    @http.route('/acb/webhook/status', type='json', auth='user', methods=['POST'])
    def check_webhook_status(self):
        """
        Kiểm tra trạng thái webhook (cho admin)
        
        Returns:
            dict: Thông tin trạng thái
        """
        _logger.info("=== WEBHOOK STATUS CHECK ===")
        _logger.info(f"User: {request.env.user.name}")
        
        try:
            # Kiểm tra quyền truy cập
            if not request.env.user.has_group('base.group_system'):
                _logger.warning(f"Access denied for user: {request.env.user.name}")
                return {'error': 'Không có quyền truy cập'}
            
            # Thống kê giao dịch
            transaction_model = request.env['acb.transaction']
            
            total_transactions = transaction_model.search_count([])
            today_transactions = transaction_model.search_count([
                ('create_date', '>=', datetime.now().strftime('%Y-%m-%d 00:00:00')),
                ('create_date', '<=', datetime.now().strftime('%Y-%m-%d 23:59:59'))
            ])
            
            processed_transactions = transaction_model.search_count([
                ('state', '=', 'processed')
            ])
            
            error_transactions = transaction_model.search_count([
                ('state', '=', 'error')
            ])
            
            webhook_transactions = transaction_model.search_count([
                ('source_type', '=', 'webhook')
            ])
            
            api_transactions = transaction_model.search_count([
                ('source_type', '=', 'api_call')
            ])
            
            # Cấu hình ACB
            acb_configs = request.env['acb.config'].search_count([
                ('active', '=', True)
            ])
            
            # Lấy API call statistics
            configs = request.env['acb.config'].search([('active', '=', True)])
            total_api_calls = sum(config.api_call_count for config in configs)
            last_api_call = max([config.last_api_call for config in configs if config.last_api_call], default=False)
            
            status_data = {
                'total_transactions': total_transactions,
                'today_transactions': today_transactions,
                'processed_transactions': processed_transactions,
                'error_transactions': error_transactions,
                'webhook_transactions': webhook_transactions,
                'api_call_transactions': api_transactions,
                'active_configs': acb_configs,
                'total_api_calls': total_api_calls,
                'last_api_call': last_api_call.isoformat() if last_api_call else None,
                'last_check': datetime.now().isoformat()
            }
            
            _logger.info(f"Status data: {status_data}")
            
            return {
                'status': 'success',
                'data': status_data
            }
            
        except Exception as e:
            _logger.error(f"Error checking webhook status: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            } 