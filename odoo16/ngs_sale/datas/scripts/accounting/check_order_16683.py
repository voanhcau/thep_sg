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
Script kiểm tra tính lãi vay cho đơn hàng ID 16683
Kiểm tra xem có tính đúng số ngày quá hạn (trừ thời hạn TT) hay không
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
        logging.FileHandler('check_order_16683.log'),
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

def check_order_16683():
    """Kiểm tra đơn hàng ID 16683"""
    logging.info(f"\n{'='*60}")
    logging.info(f"KIỂM TRA ĐƠN HÀNG ID: 16683")
    logging.info(f"{'='*60}")
    
    order_id = 16683
    
    try:
        # Đọc thông tin đơn hàng
        orders = models.execute_kw(
            db, uid, password,
            'sale.order', 'read',
            [order_id],
            {'fields': [
                'name', 'partner_id', 'date_order', 'amount_untaxed', 
                'total_product_qty', 'payment_term_id', 'received_date',
                'invoice_ids', 'interest_amount', 'interest_per_kg',
                'company_id', 'auto_purchase_order_id'
            ]}
        )
        if not orders:
            logging.error(f"❌ Không tìm thấy đơn hàng ID {order_id}")
            return
        order = orders[0]
    except Exception as e:
        logging.error(f"Lỗi đọc thông tin đơn hàng: {e}")
        import traceback
        traceback.print_exc()
        return
    
    logging.info(f"📋 Thông tin đơn hàng:")
    logging.info(f"   - Tên: {order['name']}")
    logging.info(f"   - Khách hàng: {order['partner_id'][1] if order['partner_id'] else 'N/A'}")
    logging.info(f"   - Ngày đặt hàng: {order['date_order']}")
    logging.info(f"   - Số tiền (chưa VAT): {order['amount_untaxed']:,.0f} VNĐ")
    logging.info(f"   - Tổng khối lượng: {order['total_product_qty']:,.0f} kg")
    logging.info(f"   - Ngày nhận hàng: {order['received_date']}")
    logging.info(f"   - Lãi vay hiện tại: {order.get('interest_amount', 0):,.0f} VNĐ")
    logging.info(f"   - Lãi vay/kg hiện tại: {order.get('interest_per_kg', 0):,.0f} VNĐ/kg")
    
    # Đọc thông tin Purchase Order (PO)
    if order.get('auto_purchase_order_id'):
        po_id = order['auto_purchase_order_id'][0]
        po = models.execute_kw(
            db, uid, password,
            'purchase.order', 'read',
            [po_id],
            {'fields': ['name', 'payment_term_id']}
        )[0]
        
        logging.info(f"\n📦 Thông tin Purchase Order (PO):")
        logging.info(f"   - Tên PO: {po['name']}")
        
        if po['payment_term_id']:
            po_payment_term = models.execute_kw(
                db, uid, password,
                'account.payment.term', 'read',
                [po['payment_term_id'][0]],
                {'fields': ['name', 'lending_days']}
            )[0]
            
            logging.info(f"   - Điều khoản thanh toán PO: {po_payment_term['name']}")
            logging.info(f"   - PO lending_days: {po_payment_term.get('lending_days', 0)} ngày")
        else:
            logging.info(f"   - PO không có điều khoản thanh toán")
    else:
        logging.info(f"\n📦 Không có Purchase Order (PO) liên quan")
    
    # Đọc thông tin điều khoản thanh toán
    if order['payment_term_id']:
        payment_term = models.execute_kw(
            db, uid, password,
            'account.payment.term', 'read',
            [order['payment_term_id'][0]],
            {'fields': ['name', 'lending_days', 'lending_rate']}
        )[0]
        
        logging.info(f"\n💳 Điều khoản thanh toán:")
        logging.info(f"   - Tên: {payment_term['name']}")
        logging.info(f"   - Số ngày cho vay (lending_days): {payment_term.get('lending_days', 0)}")
        logging.info(f"   - Lãi suất: {payment_term.get('lending_rate', 0)}%/ngày")
        
        lending_days = payment_term.get('lending_days', 0)
        lending_rate = payment_term.get('lending_rate', 0) / 100
    else:
        logging.warning("⚠️ Không có điều khoản thanh toán")
        return
    
    # Đọc thông tin hóa đơn và thanh toán
    if order['invoice_ids']:
        invoices = models.execute_kw(
            db, uid, password,
            'account.move', 'read',
            [order['invoice_ids']],
            {'fields': ['name', 'invoice_date', 'payment_state', 'amount_residual', 'invoice_payments_widget', 'order_received_date']}
        )
        
        logging.info(f"\n🧾 Thông tin hóa đơn:")
        for inv in invoices:
            logging.info(f"   - Hóa đơn: {inv['name']}")
            logging.info(f"   - Ngày hóa đơn: {inv['invoice_date']}")
            logging.info(f"   - Ngày nhận hàng (order_received_date): {inv.get('order_received_date')}")
            logging.info(f"   - Trạng thái thanh toán: {inv['payment_state']}")
            logging.info(f"   - Số tiền còn nợ: {inv['amount_residual']:,.0f} VNĐ")
            
            # Phân tích thanh toán
            if inv['invoice_payments_widget']:
                payments_data = inv['invoice_payments_widget']
                if isinstance(payments_data, str):
                    import json
                    payments_data = json.loads(payments_data)
                
                if 'content' in payments_data:
                    payments = payments_data['content']
                    logging.info(f"   - Số lần thanh toán: {len(payments)}")
                    for i, payment in enumerate(payments, 1):
                        payment_date = payment.get('date', 'N/A')
                        payment_amount = payment.get('amount', 0)
                        logging.info(f"     Lần {i}: {payment_date} - {payment_amount:,.0f} VNĐ")
    
    # Tính toán thủ công để so sánh
    logging.info(f"\n🧮 TÍNH TOÁN THỦ CÔNG:")
    
    # Xác định ngày bắt đầu tính lãi
    received_date = order['received_date']
    invoice_date = None
    if invoices:
        invoice_date = min(inv['invoice_date'] for inv in invoices if inv.get('invoice_date'))
    
    start_date = received_date or (invoice_date[:10] if invoice_date else None)
    if not start_date:
        logging.error("❌ Không có ngày nhận hàng hoặc ngày hóa đơn")
        return
    
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    logging.info(f"   - Ngày bắt đầu tính lãi: {start_date}")
    
    # Ngày đến hạn
    if lending_days > 0:
        due_date = start_date + timedelta(days=lending_days)
        logging.info(f"   - Thời hạn thanh toán: {lending_days} ngày")
        logging.info(f"   - Ngày đến hạn: {due_date}")
    else:
        logging.warning("⚠️ Không có thời hạn thanh toán (lending_days = 0)")
        due_date = None
    
    # Lấy ngày thanh toán cuối cùng
    last_payment_date = None
    if invoices:
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
    
    if last_payment_date:
        logging.info(f"   - Ngày thanh toán cuối: {last_payment_date}")
        
        if due_date:
            # Tính số ngày quá hạn
            overdue_days = (last_payment_date - due_date).days
            logging.info(f"   - Số ngày quá hạn: {overdue_days} ngày")
            
            if overdue_days > 0:
                # Tính lãi vay theo công thức đúng: chỉ tính cho ngày quá hạn
                interest_amount_correct = overdue_days * order['amount_untaxed'] * lending_rate
                interest_per_kg_correct = interest_amount_correct / order['total_product_qty'] if order['total_product_qty'] > 0 else 0
                
                logging.info(f"\n✅ CÁCH TÍNH ĐÚNG (chỉ tính ngày quá hạn):")
                logging.info(f"   - Số ngày quá hạn: {overdue_days} ngày")
                logging.info(f"   - Công thức: {overdue_days} ngày × {order['amount_untaxed']:,.0f} VNĐ × {lending_rate:.6f} = {interest_amount_correct:,.0f} VNĐ")
                logging.info(f"   - Lãi vay đúng: {interest_amount_correct:,.0f} VNĐ")
                logging.info(f"   - Lãi vay/kg đúng: {interest_per_kg_correct:,.0f} VNĐ/kg")
                
                # Tính lãi vay theo cách sai (tính từ ngày bắt đầu, không trừ thời hạn TT)
                total_days = (last_payment_date - start_date).days + 1
                interest_amount_wrong = total_days * order['amount_untaxed'] * lending_rate
                interest_per_kg_wrong = interest_amount_wrong / order['total_product_qty'] if order['total_product_qty'] > 0 else 0
                
                logging.info(f"\n❌ CÁCH TÍNH SAI (tính từ ngày bắt đầu, không trừ thời hạn TT):")
                logging.info(f"   - Tổng số ngày từ ngày bắt đầu đến ngày TT: {total_days} ngày")
                logging.info(f"   - Công thức SAI: {total_days} ngày × {order['amount_untaxed']:,.0f} VNĐ × {lending_rate:.6f} = {interest_amount_wrong:,.0f} VNĐ")
                logging.info(f"   - Lãi vay SAI: {interest_amount_wrong:,.0f} VNĐ")
                logging.info(f"   - Lãi vay/kg SAI: {interest_per_kg_wrong:,.0f} VNĐ/kg")
                
                # So sánh với giá trị hiện tại
                current_interest = order.get('interest_amount', 0)
                current_interest_per_kg = order.get('interest_per_kg', 0)
                
                logging.info(f"\n📊 SO SÁNH KẾT QUẢ:")
                logging.info(f"   - Lãi vay hiện tại trong DB: {current_interest:,.0f} VNĐ")
                logging.info(f"   - Lãi vay tính đúng (chỉ ngày quá hạn): {interest_amount_correct:,.0f} VNĐ")
                logging.info(f"   - Lãi vay tính sai (không trừ thời hạn TT): {interest_amount_wrong:,.0f} VNĐ")
                logging.info(f"   - Chênh lệch so với cách đúng: {abs(current_interest - interest_amount_correct):,.0f} VNĐ")
                logging.info(f"   - Chênh lệch so với cách sai: {abs(current_interest - interest_amount_wrong):,.0f} VNĐ")
                
                # Xác định xem đang tính đúng hay sai
                diff_correct = abs(current_interest - interest_amount_correct)
                diff_wrong = abs(current_interest - interest_amount_wrong)
                
                if diff_correct < diff_wrong:
                    logging.info(f"\n✅ KẾT LUẬN: Hệ thống đang tính ĐÚNG (chỉ tính ngày quá hạn)")
                else:
                    logging.warning(f"\n❌ KẾT LUẬN: Hệ thống đang tính SAI (tính từ ngày bắt đầu, không trừ thời hạn TT)")
                    logging.warning(f"   Cần kiểm tra lại code calculate_interest()")
            else:
                logging.info(f"   ✅ Thanh toán đúng hạn hoặc sớm hạn, không có lãi vay")
        else:
            logging.warning("⚠️ Không có thời hạn thanh toán, không thể tính số ngày quá hạn")
    else:
        logging.warning("   ⚠️ Không tìm thấy thông tin thanh toán")

def main():
    """Hàm chính"""
    logging.info("BẮT ĐẦU KIỂM TRA ĐƠN HÀNG ID 16683")
    logging.info(f"Database: {db}")
    logging.info(f"Thời gian: {datetime.now()}")
    
    try:
        # Test kết nối
        version = common.version()
        logging.info(f"Odoo version: {version}")
        
        # Kiểm tra đơn hàng 16683
        check_order_16683()
            
    except Exception as e:
        logging.error(f"Lỗi trong quá trình kiểm tra: {e}")
        import traceback
        traceback.print_exc()
    
    logging.info(f"\n{'='*60}")
    logging.info("HOÀN THÀNH KIỂM TRA")
    logging.info(f"{'='*60}")

if __name__ == "__main__":
    main()

