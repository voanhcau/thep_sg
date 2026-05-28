#!/usr/bin/env python3
"""
Script kiểm tra chi tiết đơn hàng S09471 và so sánh với Google Sheets
"""
import os
import sys
import xmlrpc.client
from datetime import datetime
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False

ORDER_ID = 17961
ORDER_NAME = "S09471"

def parse_date(date_str):
    """Parse date string to date object"""
    if date_str is None:
        return None
    if isinstance(date_str, str):
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        raise ValueError(f"Không thể parse ngày: {date_str}")
    if hasattr(date_str, 'date'):
        return date_str.date()
    return date_str

def main():
    # Lấy environment type từ command line argument
    env_type = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        if USE_ENV_LOADER:
            URL, DB, USERNAME, PASSWORD, models, uid = setup_odoo_connection(env_type)
            print(f"✅ Connected to {env_type or 'default'} environment")
        else:
            # Fallback: dùng environment variables
            URL = os.getenv("ODOO_URL")
            DB = os.getenv("ODOO_DB")
            USERNAME = os.getenv("ODOO_USERNAME")
            PASSWORD = os.getenv("ODOO_PASSWORD")
            
            if not all([URL, DB, USERNAME, PASSWORD]):
                print("❌ Error: Environment variables must be set")
                print("   Run: source load_env.sh [prod|staging|local]")
                return 1
            
            common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", allow_none=True)
            uid = common.authenticate(DB, USERNAME, PASSWORD, {})
            if not uid:
                print("❌ Authentication failed")
                return 1
            
            models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)

        print("=" * 80)
        print(f"KIỂM TRA CHI TIẾT ĐƠN HÀNG {ORDER_NAME} (ID: {ORDER_ID})")
        print("=" * 80)
        print()

        # Đọc thông tin đơn hàng
        order = models.execute_kw(
            DB, uid, PASSWORD,
            'sale.order', 'read',
            [[ORDER_ID]],
            {'fields': [
                'name', 'partner_id', 'amount_untaxed', 'total_product_qty',
                'received_date', 'payment_term_id', 'interest_amount', 'interest_per_kg',
                'invoice_ids', 'auto_purchase_order_id'
            ]}
        )[0]

        print(f"📋 Thông tin đơn hàng:")
        print(f"   Tên: {order['name']}")
        print(f"   Khách hàng: {order['partner_id'][1] if order['partner_id'] else 'N/A'}")
        print(f"   Giá trị SO (trước VAT): {order['amount_untaxed']:,.0f} VNĐ")
        print(f"   Tổng KL bán: {order['total_product_qty']:,.0f} kg")
        print(f"   Ngày nhận hàng: {order.get('received_date', 'N/A')}")
        print(f"   Lãi vay hiện tại: {order.get('interest_amount', 0):,.0f} VNĐ")
        print(f"   Lãi vay/kg hiện tại: {order.get('interest_per_kg', 0):,.2f} VNĐ/kg")
        print()

        # Đọc thông tin điều khoản thanh toán
        if order['payment_term_id']:
            payment_term = models.execute_kw(
                DB, uid, PASSWORD,
                'account.payment.term', 'read',
                [[order['payment_term_id'][0]]],
                {'fields': ['name', 'lending_days', 'lending_rate']}
            )[0]
            print(f"📋 Điều khoản thanh toán:")
            print(f"   Tên: {payment_term['name']}")
            print(f"   Thời hạn TT: {payment_term.get('lending_days', 0)} ngày")
            print(f"   Lãi suất: {payment_term.get('lending_rate', 0)}%/ngày")
            print()

        # Đọc thông tin invoice và payments
        if order['invoice_ids']:
            invoices = models.execute_kw(
                DB, uid, PASSWORD,
                'account.move', 'search_read',
                [[('id', 'in', order['invoice_ids'])]],
                {'fields': ['name', 'state', 'invoice_date', 'invoice_payments_widget']}
            )

            print(f"📋 Thông tin hoá đơn và thanh toán:")
            all_payments = []
            for inv in invoices:
                print(f"\n   Hoá đơn: {inv['name']}")
                print(f"   Trạng thái: {inv['state']}")
                print(f"   Ngày hoá đơn: {inv.get('invoice_date', 'N/A')}")
                
                if inv['state'] == 'posted':
                    payment_info = inv.get('invoice_payments_widget')
                    if payment_info and isinstance(payment_info, dict) and payment_info.get('content'):
                        print(f"   Số lần thanh toán: {len(payment_info['content'])}")
                        for idx, payment in enumerate(payment_info['content'], 1):
                            payment_date = payment.get('date', 'N/A')
                            payment_amount = payment.get('amount', 0)
                            print(f"      Lần {idx}: {payment_date} - {payment_amount:,.0f} VNĐ (có VAT)")
                            all_payments.append(payment)
                    else:
                        print(f"   ⚠️ Không có thông tin thanh toán")

            # Sắp xếp payments theo ngày
            all_payments = sorted(all_payments, key=lambda x: x.get('date') or '')
            
            print(f"\n📋 Tổng hợp thanh toán (đã sắp xếp):")
            total_payment = 0
            for idx, payment in enumerate(all_payments, 1):
                payment_date = payment.get('date', 'N/A')
                payment_amount = payment.get('amount', 0)
                payment_before_vat = payment_amount / 1.1
                total_payment += payment_before_vat
                print(f"   Lần {idx}: {payment_date} - {payment_amount:,.0f} VNĐ (có VAT) = {payment_before_vat:,.0f} VNĐ (trước VAT)")
            print(f"   Tổng thanh toán (trước VAT): {total_payment:,.0f} VNĐ")
            print()

        # Tính toán thủ công theo Google Sheets
        print("=" * 80)
        print("TÍNH TOÁN THỦ CÔNG THEO GOOGLE SHEETS:")
        print("=" * 80)
        print()
        
        # Theo Google Sheets:
        # - Ngày giao hàng: 11/17/2025
        # - Ngày TT lần 1: 11/21/2025
        # - Số ngày: 4 ngày (từ 11/17 đến 11/21)
        # - Số tiền tính lãi: 370,365,710 VNĐ
        # - Lãi suất: 0.017%/ngày
        # - Lãi vay: 4 × 370,365,710 × 0.00017 = 251,849 VNĐ
        # - Lãi vay/kg: 251,849 / 27,521 = 9.15 VNĐ/kg
        
        if order.get('received_date') and all_payments:
            start_date = parse_date(order['received_date'])
            lending_rate = payment_term.get('lending_rate', 0) / 100 if order['payment_term_id'] else 0
            
            print(f"📅 Ngày bắt đầu tính lãi: {start_date}")
            print(f"📊 Lãi suất: {payment_term.get('lending_rate', 0)}%/ngày = {lending_rate}")
            print()
            
            remaining_amount = order['amount_untaxed']
            last_payment_date = start_date
            total_interest = 0
            
            for idx, payment in enumerate(all_payments, 1):
                payment_date_str = payment.get('date')
                if not payment_date_str:
                    continue
                
                payment_date = parse_date(payment_date_str)
                payment_amount = payment.get('amount', 0) / 1.1  # Trước VAT
                
                # Bỏ qua thanh toán trước ngày bắt đầu
                if payment_date < start_date:
                    remaining_amount = remaining_amount - payment_amount
                    if remaining_amount < 0:
                        remaining_amount = 0
                    continue
                
                # Tính số ngày
                days_diff = (payment_date - last_payment_date).days
                if days_diff < 0:
                    days_diff = 0
                
                if remaining_amount < 0:
                    remaining_amount = 0
                
                # Tính lãi vay
                interest = days_diff * remaining_amount * lending_rate
                if interest < 0:
                    interest = 0
                
                print(f"💸 Lần thanh toán {idx}:")
                print(f"   Ngày TT: {payment_date}")
                print(f"   Số ngày tính lãi: {days_diff} (từ {last_payment_date} đến {payment_date})")
                print(f"   Số tiền tính lãi: {remaining_amount:,.0f} VNĐ")
                print(f"   Số tiền thanh toán: {payment_amount:,.0f} VNĐ (trước VAT)")
                print(f"   Lãi vay: {days_diff} × {remaining_amount:,.0f} × {lending_rate:.6f} = {interest:,.0f} VNĐ")
                print()
                
                total_interest += interest
                remaining_amount = remaining_amount - payment_amount
                last_payment_date = payment_date
                
                if remaining_amount < 0:
                    remaining_amount = 0
            
            if total_interest < 0:
                total_interest = 0
            
            interest_per_kg = total_interest / order['total_product_qty'] if order['total_product_qty'] > 0 else 0
            
            print("=" * 80)
            print("KẾT QUẢ TÍNH TOÁN:")
            print("=" * 80)
            print(f"   Tổng lãi vay (tính thủ công): {total_interest:,.0f} VNĐ")
            print(f"   Lãi vay/kg (tính thủ công): {interest_per_kg:,.2f} VNĐ/kg")
            print()
            print(f"   Tổng lãi vay (trong hệ thống): {order.get('interest_amount', 0):,.0f} VNĐ")
            print(f"   Lãi vay/kg (trong hệ thống): {order.get('interest_per_kg', 0):,.2f} VNĐ/kg")
            print()
            print(f"   Theo Google Sheets:")
            print(f"   - Tổng lãi vay: 251,849 VNĐ")
            print(f"   - Lãi vay/kg: 9.15 VNĐ/kg")
            print()
            
            diff_interest = abs(total_interest - order.get('interest_amount', 0))
            diff_per_kg = abs(interest_per_kg - order.get('interest_per_kg', 0))
            
            if diff_interest > 0.01:
                print(f"   ❌ CHÊNH LỆCH: {diff_interest:,.0f} VNĐ")
            else:
                print(f"   ✅ Khớp với hệ thống")
            
            if diff_per_kg > 0.01:
                print(f"   ❌ CHÊNH LỆCH/kg: {diff_per_kg:,.2f} VNĐ/kg")
            else:
                print(f"   ✅ Khớp với hệ thống")

        return 0
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

