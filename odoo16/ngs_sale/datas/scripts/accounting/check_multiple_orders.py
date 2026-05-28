#!/usr/bin/env python3
"""
Script kiểm tra nhiều đơn hàng và so sánh với Google Sheets
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

# Danh sách đơn hàng cần kiểm tra
ORDERS_TO_CHECK = [
    ("S00254", "https://docs.google.com/spreadsheets/d/1LNc1qoGdk7KkFhj3kbg-UxUug-UgDtRE/edit?gid=998231976#gid=998231976"),
    ("S00255", "https://docs.google.com/spreadsheets/d/1LNc1qoGdk7KkFhj3kbg-UxUug-UgDtRE/edit?gid=995670883#gid=995670883"),
    ("S00632", "https://docs.google.com/spreadsheets/d/1LNc1qoGdk7KkFhj3kbg-UxUug-UgDtRE/edit?gid=445959012#gid=445959012"),
    ("S01592", "https://docs.google.com/spreadsheets/d/1LNc1qoGdk7KkFhj3kbg-UxUug-UgDtRE/edit?gid=985276392#gid=985276392"),
    ("S09471", "https://docs.google.com/spreadsheets/d/1LNc1qoGdk7KkFhj3kbg-UxUug-UgDtRE/edit?gid=445074174#gid=445074174"),
    ("S08193", "https://docs.google.com/spreadsheets/d/1LNc1qoGdk7KkFhj3kbg-UxUug-UgDtRE/edit?gid=1562520083#gid=1562520083"),
]

def parse_date(date_str):
    """Parse date string to date object"""
    if date_str is None:
        return None
    if isinstance(date_str, str):
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        raise ValueError(f"Không thể parse ngày: {date_str}")
    if hasattr(date_str, 'date'):
        return date_str.date()
    return date_str

def calculate_interest_manual(order_data, payments_list, start_date, lending_rate):
    """Tính lãi vay thủ công theo công thức Google Sheets (Cách 2)"""
    start_date = parse_date(start_date) if isinstance(start_date, str) else start_date
    
    total_interest = 0
    remaining_amount = order_data['amount_untaxed']
    last_payment_date = start_date
    
    for idx, payment in enumerate(payments_list, 1):
        payment_date = parse_date(payment['date'])
        payment_amount = payment['amount'] / 1.1  # Trước VAT
        
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
        
        total_interest += interest
        remaining_amount = remaining_amount - payment_amount
        last_payment_date = payment_date
        
        if remaining_amount < 0:
            remaining_amount = 0
    
    if total_interest < 0:
        total_interest = 0
    
    return total_interest

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
        print("KIỂM TRA NHIỀU ĐƠN HÀNG VÀ SO SÁNH VỚI GOOGLE SHEETS")
        print("=" * 80)
        print()

        results = []
        
        for order_name, sheet_url in ORDERS_TO_CHECK:
            print(f"\n{'='*80}")
            print(f"KIỂM TRA ĐƠN HÀNG: {order_name}")
            print(f"Google Sheets: {sheet_url}")
            print(f"{'='*80}\n")
            
            try:
                # Tìm đơn hàng
                order_ids = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'search',
                    [[('name', '=', order_name)]]
                )
                
                if not order_ids:
                    print(f"❌ Không tìm thấy đơn hàng {order_name}")
                    results.append({
                        'order': order_name,
                        'status': 'NOT_FOUND',
                        'error': 'Không tìm thấy đơn hàng'
                    })
                    continue
                
                order_id = order_ids[0]
                
                # Đọc thông tin đơn hàng
                order = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'read',
                    [[order_id]],
                    {'fields': [
                        'name', 'partner_id', 'amount_untaxed', 'total_product_qty',
                        'received_date', 'payment_term_id', 'interest_amount', 'interest_per_kg',
                        'invoice_ids', 'company_id'
                    ]}
                )[0]
                
                print(f"📋 Thông tin đơn hàng:")
                print(f"   Tên: {order['name']}")
                print(f"   Giá trị SO (trước VAT): {order['amount_untaxed']:,.0f} VNĐ")
                print(f"   Tổng KL bán: {order['total_product_qty']:,.0f} kg")
                print(f"   Ngày nhận hàng: {order.get('received_date', 'N/A')}")
                print(f"   Lãi vay hiện tại: {order.get('interest_amount', 0):,.0f} VNĐ")
                print(f"   Lãi vay/kg hiện tại: {order.get('interest_per_kg', 0):,.2f} VNĐ/kg")
                
                # Đọc thông tin điều khoản thanh toán
                if not order['payment_term_id']:
                    print(f"⚠️ Đơn hàng không có điều khoản thanh toán")
                    results.append({
                        'order': order_name,
                        'status': 'NO_PAYMENT_TERM',
                        'error': 'Không có điều khoản thanh toán'
                    })
                    continue
                
                payment_term = models.execute_kw(
                    DB, uid, PASSWORD,
                    'account.payment.term', 'read',
                    [[order['payment_term_id'][0]]],
                    {'fields': ['name', 'lending_days', 'lending_rate']}
                )[0]
                
                lending_rate = payment_term.get('lending_rate', 0)
                if lending_rate <= 0:
                    print(f"⚠️ Đơn hàng không có lãi suất vay vốn")
                    results.append({
                        'order': order_name,
                        'status': 'NO_LENDING_RATE',
                        'error': 'Không có lãi suất vay vốn'
                    })
                    continue
                
                print(f"   Điều khoản TT: {payment_term['name']}")
                print(f"   Lãi suất: {lending_rate}%/ngày")
                
                # Đọc thông tin invoice và payments
                if not order['invoice_ids']:
                    print(f"⚠️ Đơn hàng chưa có hoá đơn")
                    results.append({
                        'order': order_name,
                        'status': 'NO_INVOICE',
                        'error': 'Chưa có hoá đơn'
                    })
                    continue
                
                invoices = models.execute_kw(
                    DB, uid, PASSWORD,
                    'account.move', 'search_read',
                    [[('id', 'in', order['invoice_ids'])]],
                    {'fields': ['name', 'state', 'invoice_date', 'invoice_payments_widget']}
                )
                
                all_payments = []
                for inv in invoices:
                    if inv['state'] != 'posted':
                        continue
                    payment_info = inv.get('invoice_payments_widget')
                    if payment_info and isinstance(payment_info, dict) and payment_info.get('content'):
                        for payment in payment_info['content']:
                            all_payments.append(payment)
                
                if not all_payments:
                    print(f"⚠️ Đơn hàng chưa có thanh toán")
                    results.append({
                        'order': order_name,
                        'status': 'NO_PAYMENTS',
                        'error': 'Chưa có thanh toán'
                    })
                    continue
                
                # Sắp xếp payments theo ngày
                all_payments = sorted(all_payments, key=lambda x: x.get('date') or '')
                
                # Xác định ngày bắt đầu (theo logic trong code: ưu tiên received_date, nếu invoice_date < received_date thì dùng invoice_date)
                received_date = order.get('received_date')
                if received_date:
                    received_date = parse_date(received_date)
                
                invoice_dates = [parse_date(inv.get('invoice_date')) for inv in invoices if inv.get('invoice_date')]
                invoice_date = min(invoice_dates) if invoice_dates else None
                
                start_date = received_date
                if not start_date and invoice_date:
                    start_date = invoice_date
                elif invoice_date and received_date and invoice_date < received_date:
                    start_date = invoice_date
                
                if not start_date:
                    print(f"⚠️ Không có ngày bắt đầu tính lãi")
                    results.append({
                        'order': order_name,
                        'status': 'NO_START_DATE',
                        'error': 'Không có ngày bắt đầu tính lãi'
                    })
                    continue
                
                print(f"\n📋 Thông tin thanh toán:")
                for idx, payment in enumerate(all_payments, 1):
                    payment_date = payment.get('date', 'N/A')
                    payment_amount = payment.get('amount', 0)
                    print(f"   Lần {idx}: {payment_date} - {payment_amount:,.0f} VNĐ (có VAT)")
                
                # Tính lãi vay thủ công
                lending_rate_decimal = lending_rate / 100
                manual_interest = calculate_interest_manual(order, all_payments, start_date, lending_rate_decimal)
                manual_interest_per_kg = manual_interest / order['total_product_qty'] if order['total_product_qty'] > 0 else 0
                
                # So sánh
                system_interest = order.get('interest_amount', 0)
                system_interest_per_kg = order.get('interest_per_kg', 0)
                
                diff_interest = abs(system_interest - manual_interest)
                diff_per_kg = abs(system_interest_per_kg - manual_interest_per_kg)
                
                print(f"\n📊 KẾT QUẢ SO SÁNH:")
                print(f"   Hệ thống: {system_interest:,.0f} VNĐ ({system_interest_per_kg:,.2f} VNĐ/kg)")
                print(f"   Tính thủ công: {manual_interest:,.0f} VNĐ ({manual_interest_per_kg:,.2f} VNĐ/kg)")
                
                if diff_interest <= 0.01 and diff_per_kg <= 0.01:
                    print(f"   ✅ KHỚP HOÀN TOÀN")
                    status = 'OK'
                else:
                    print(f"   ❌ CHÊNH LỆCH: {diff_interest:,.0f} VNĐ ({diff_per_kg:,.2f} VNĐ/kg)")
                    status = 'MISMATCH'
                
                results.append({
                    'order': order_name,
                    'status': status,
                    'system_interest': system_interest,
                    'system_interest_per_kg': system_interest_per_kg,
                    'manual_interest': manual_interest,
                    'manual_interest_per_kg': manual_interest_per_kg,
                    'diff_interest': diff_interest,
                    'diff_per_kg': diff_per_kg
                })
                
            except Exception as e:
                print(f"❌ Lỗi khi xử lý {order_name}: {e}")
                import traceback
                traceback.print_exc()
                results.append({
                    'order': order_name,
                    'status': 'ERROR',
                    'error': str(e)
                })
        
        # Tổng kết
        print("\n" + "=" * 80)
        print("TỔNG KẾT")
        print("=" * 80)
        print()
        
        ok_count = sum(1 for r in results if r['status'] == 'OK')
        mismatch_count = sum(1 for r in results if r['status'] == 'MISMATCH')
        error_count = sum(1 for r in results if r['status'] not in ['OK', 'MISMATCH'])
        
        print(f"✅ Khớp: {ok_count}/{len(ORDERS_TO_CHECK)}")
        print(f"❌ Không khớp: {mismatch_count}/{len(ORDERS_TO_CHECK)}")
        print(f"⚠️ Lỗi/Không tìm thấy: {error_count}/{len(ORDERS_TO_CHECK)}")
        print()
        
        if mismatch_count > 0:
            print("📋 CÁC ĐƠN HÀNG KHÔNG KHỚP:")
            for r in results:
                if r['status'] == 'MISMATCH':
                    print(f"   - {r['order']}: Hệ thống={r['system_interest']:,.0f}, Thủ công={r['manual_interest']:,.0f}, Chênh lệch={r['diff_interest']:,.0f}")
        
        return 0
    except Exception as e:
        print(f"❌ Lỗi tổng quát: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

