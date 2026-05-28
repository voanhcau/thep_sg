#!/usr/bin/env python3
import sys
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False
# -*- coding: utf-8 -*-
"""
Script kiểm tra tính lãi vay cho 100 đơn hàng
So sánh kết quả với công thức: (Ngày TT - Ngày bắt đầu - SO TT) nếu > 0
"""

import os
import xmlrpc.client
import logging
from datetime import datetime, timedelta
import sys

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_interest_100_orders.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Thông tin kết nối
# Get connection với hỗ trợ 3 môi trường
env_type = sys.argv[1] if len(sys.argv) > 1 else None

if USE_ENV_LOADER:
    try:
        url, db, username, password, models, uid = setup_odoo_connection(env_type)
        print(f"✅ Connected to {env_type or 'default'} environment")
        # Tạo common để dùng cho version check
        import xmlrpc.client
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        sys.exit(1)
else:
    # Fallback: dùng environment variables trực tiếp
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USERNAME")
    password = os.getenv("ODOO_PASSWORD")
    
    if not all([url, db, username, password]):
        print("❌ Missing environment variables. Please:")
        print("   1. Run: source load_env.sh [prod|staging|local]")
        print("   2. Or set: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD")
        sys.exit(1)
    
    import xmlrpc.client
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Authentication failed")
        sys.exit(1)
logging.info("Authentication successful")

def calculate_interest_manually(order_data):
    """
    Tính lãi vay thủ công theo công thức:
    - Ngày đến hạn = Ngày bắt đầu + SO.lending_days
    - Quá hạn = (Ngày thanh toán - Ngày đến hạn)
    - Chỉ tính lãi nếu quá hạn > 0
    """
    start_date_str = order_data.get('received_date') or order_data.get('date_order', '')[:10]
    if not start_date_str:
        return None
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    so_lending_days = order_data.get('so_lending_days', 0)
    payment_date_str = order_data.get('payment_date')
    
    if not payment_date_str or so_lending_days <= 0:
        return None
    
    payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
    lending_rate = order_data.get('lending_rate', 0) / 100
    amount_untaxed = order_data.get('amount_untaxed', 0)
    
    # Tính ngày đến hạn
    due_date = start_date + timedelta(days=so_lending_days)
    
    # Tính số ngày quá hạn
    overdue_days = (payment_date - due_date).days
    
    if overdue_days > 0:
        # Tính lãi vay
        interest_amount = overdue_days * amount_untaxed * lending_rate
        return {
            'due_date': due_date.strftime('%Y-%m-%d'),
            'overdue_days': overdue_days,
            'interest_amount': interest_amount,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'payment_date': payment_date.strftime('%Y-%m-%d'),
            'so_lending_days': so_lending_days
        }
    else:
        return {
            'due_date': due_date.strftime('%Y-%m-%d'),
            'overdue_days': 0,
            'interest_amount': 0,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'payment_date': payment_date.strftime('%Y-%m-%d'),
            'so_lending_days': so_lending_days
        }

def test_100_orders():
    """Kiểm tra 100 đơn hàng"""
    logging.info(f"\n{'='*80}")
    logging.info(f"KIỂM TRA TÍNH LÃI VAY CHO 100 ĐƠN HÀNG")
    logging.info(f"{'='*80}")
    
    try:
        # Tìm tất cả đơn hàng có payment_term_id và interest_amount > 0 (đã tính lãi)
        order_ids = models.execute_kw(
            db, uid, password,
            'sale.order', 'search',
            [
                ('payment_term_id', '!=', False),
                ('interest_amount', '>', 0)
            ],
            {'limit': 100, 'order': 'id desc'}
        )
        
        logging.info(f"Tìm thấy {len(order_ids)} đơn hàng có lãi vay để kiểm tra")
        
        if not order_ids:
            logging.warning("Không tìm thấy đơn hàng nào có lãi vay, tìm đơn hàng có payment_term_id...")
            # Tìm đơn hàng có payment_term_id và có invoice
            order_ids = models.execute_kw(
                db, uid, password,
                'sale.order', 'search',
                [('payment_term_id', '!=', False)],
                {'limit': 100, 'order': 'id desc'}
            )
            logging.info(f"Tìm thấy {len(order_ids)} đơn hàng có payment_term_id")
        
        if not order_ids:
            logging.error("Không tìm thấy đơn hàng nào")
            return
        
        # Đọc thông tin đơn hàng
        orders = models.execute_kw(
            db, uid, password,
            'sale.order', 'read',
            [order_ids],
            {'fields': [
                'name', 'partner_id', 'date_order', 'amount_untaxed', 
                'total_product_qty', 'payment_term_id', 'received_date',
                'invoice_ids', 'interest_amount', 'interest_per_kg',
                'auto_purchase_order_id'
            ]}
        )
        
        correct_count = 0
        incorrect_count = 0
        no_interest_count = 0
        error_count = 0
        
        for idx, order in enumerate(orders, 1):
            try:
                order_name = order['name']
                logging.info(f"\n{'='*60}")
                logging.info(f"[{idx}/{len(orders)}] Đơn hàng: {order_name}")
                
                # Đọc thông tin payment term
                if not order['payment_term_id']:
                    logging.info(f"   ⚠️ Không có điều khoản thanh toán, bỏ qua")
                    continue
                
                payment_term = models.execute_kw(
                    db, uid, password,
                    'account.payment.term', 'read',
                    [order['payment_term_id'][0]],
                    {'fields': ['name', 'lending_days', 'lending_rate']}
                )[0]
                
                so_lending_days = payment_term.get('lending_days', 0)
                lending_rate = payment_term.get('lending_rate', 0)
                
                if so_lending_days <= 0 or lending_rate <= 0:
                    logging.info(f"   ⚠️ Không có lending_days hoặc lending_rate, bỏ qua")
                    continue
                
                # Đọc thông tin hóa đơn và thanh toán
                if not order['invoice_ids']:
                    logging.info(f"   ⚠️ Không có hóa đơn, bỏ qua")
                    continue
                
                invoices = models.execute_kw(
                    db, uid, password,
                    'account.move', 'read',
                    [order['invoice_ids']],
                    {'fields': ['name', 'invoice_date', 'payment_state', 'invoice_payments_widget']}
                )
                
                # Tìm ngày thanh toán cuối cùng
                last_payment_date = None
                for inv in invoices:
                    if inv.get('invoice_payments_widget'):
                        payments_data = inv['invoice_payments_widget']
                        if isinstance(payments_data, str):
                            import json
                            payments_data = json.loads(payments_data)
                        
                        if 'content' in payments_data:
                            payments = payments_data['content']
                            for payment in payments:
                                payment_date_str = payment.get('date')
                                if payment_date_str:
                                    payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                                    if not last_payment_date or payment_date > last_payment_date:
                                        last_payment_date = payment_date
                
                if not last_payment_date:
                    logging.info(f"   ⚠️ Không có thông tin thanh toán, bỏ qua")
                    continue
                
                # Chuẩn bị dữ liệu để tính thủ công
                order_data = {
                    'received_date': order.get('received_date'),
                    'date_order': order.get('date_order', ''),
                    'so_lending_days': so_lending_days,
                    'payment_date': last_payment_date.strftime('%Y-%m-%d'),
                    'lending_rate': lending_rate,
                    'amount_untaxed': order.get('amount_untaxed', 0)
                }
                
                # Tính lãi vay thủ công
                manual_result = calculate_interest_manually(order_data)
                
                if not manual_result:
                    logging.info(f"   ⚠️ Không thể tính lãi vay thủ công, bỏ qua")
                    continue
                
                # So sánh với giá trị trong DB
                db_interest = order.get('interest_amount', 0)
                manual_interest = manual_result['interest_amount']
                
                # Tính lãi/kg
                total_qty = order.get('total_product_qty', 0)
                if total_qty > 0:
                    manual_interest_per_kg = manual_interest / total_qty
                else:
                    manual_interest_per_kg = 0
                
                db_interest_per_kg = order.get('interest_per_kg', 0)
                
                # Log kết quả
                logging.info(f"   📅 Ngày bắt đầu: {manual_result['start_date']}")
                logging.info(f"   📅 SO thời hạn TT: {so_lending_days} ngày")
                logging.info(f"   📅 Ngày đến hạn: {manual_result['due_date']}")
                logging.info(f"   📅 Ngày thanh toán: {manual_result['payment_date']}")
                logging.info(f"   📆 Số ngày quá hạn: {manual_result['overdue_days']} ngày")
                logging.info(f"   💰 Lãi vay tính thủ công: {manual_interest:,.0f} VNĐ ({manual_interest_per_kg:,.2f} VNĐ/kg)")
                logging.info(f"   💰 Lãi vay trong DB: {db_interest:,.0f} VNĐ ({db_interest_per_kg:,.2f} VNĐ/kg)")
                
                # So sánh (cho phép sai lệch < 1000 VNĐ do làm tròn)
                diff = abs(db_interest - manual_interest)
                if diff < 1000:
                    correct_count += 1
                    logging.info(f"   ✅ ĐÚNG (chênh lệch: {diff:,.0f} VNĐ)")
                elif manual_interest == 0 and db_interest == 0:
                    no_interest_count += 1
                    logging.info(f"   ✅ ĐÚNG (không có lãi vay)")
                else:
                    incorrect_count += 1
                    logging.warning(f"   ❌ SAI! Chênh lệch: {diff:,.0f} VNĐ")
                    logging.warning(f"      Cần chạy lại calculate_interest() cho đơn hàng này")
                
            except Exception as e:
                error_count += 1
                logging.error(f"   ❌ Lỗi khi xử lý đơn hàng {order.get('name', 'N/A')}: {e}")
                import traceback
                traceback.print_exc()
        
        # Tổng kết
        logging.info(f"\n{'='*80}")
        logging.info(f"KẾT QUẢ TỔNG KẾT:")
        logging.info(f"{'='*80}")
        logging.info(f"Tổng số đơn hàng kiểm tra: {len(orders)}")
        logging.info(f"✅ Đúng: {correct_count + no_interest_count}")
        logging.info(f"   - Có lãi vay và tính đúng: {correct_count}")
        logging.info(f"   - Không có lãi vay (đúng): {no_interest_count}")
        logging.info(f"❌ Sai: {incorrect_count}")
        logging.info(f"⚠️ Lỗi: {error_count}")
        logging.info(f"{'='*80}")
        
        if incorrect_count > 0:
            logging.warning(f"\n⚠️ CÓ {incorrect_count} ĐƠN HÀNG TÍNH SAI LÃI VAY!")
            logging.warning(f"   Cần chạy lại calculate_interest() cho các đơn hàng này")
        else:
            logging.info(f"\n✅ TẤT CẢ ĐƠN HÀNG ĐỀU TÍNH ĐÚNG!")
            
    except Exception as e:
        logging.error(f"Lỗi trong quá trình kiểm tra: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Hàm chính"""
    logging.info("BẮT ĐẦU KIỂM TRA TÍNH LÃI VAY CHO 100 ĐƠN HÀNG")
    logging.info(f"Database: {db}")
    logging.info(f"Thời gian: {datetime.now()}")
    
    try:
        # Test kết nối
        version = common.version()
        logging.info(f"Odoo version: {version}")
        
        # Kiểm tra 100 đơn hàng
        test_100_orders()
            
    except Exception as e:
        logging.error(f"Lỗi trong quá trình kiểm tra: {e}")
        import traceback
        traceback.print_exc()
    
    logging.info(f"\n{'='*80}")
    logging.info("HOÀN THÀNH KIỂM TRA")
    logging.info(f"{'='*80}")

if __name__ == "__main__":
    main()

