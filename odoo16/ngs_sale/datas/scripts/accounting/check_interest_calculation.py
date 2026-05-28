#!/usr/bin/env python3
"""
Script kiểm tra tính lãi vay theo công thức Google Sheets (Cách 2)
Tham khảo: https://docs.google.com/spreadsheets/d/1LNc1qoGdk7KkFhj3kbg-UxUug-UgDtRE/edit?gid=846653463#gid=846653463

Logic Google Sheets (Cách 2):
- Số ngày tính lãi = (Ngày TT lần N) - (Ngày TT lần N-1) hoặc (Ngày TT lần 1) - (Ngày nhận hàng)
- Số tiền tính lãi = Giá trị đơn - Tổng các lần trả trước đó
- Lãi vay = Số ngày × Số tiền tính lãi × Lãi suất
"""
import os
import sys
import xmlrpc.client
from datetime import datetime, timedelta
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False

def parse_date(date_str):
    """Parse date string to date object"""
    if date_str is None:
        return None
    if isinstance(date_str, str):
        # Thử các format khác nhau
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        raise ValueError(f"Không thể parse ngày: {date_str}")
    # Nếu đã là date object thì trả về
    if hasattr(date_str, 'date'):
        return date_str.date()
    return date_str

def calculate_interest_manual(order_data, payments_list, start_date, lending_rate, verbose=False):
    """
    Tính lãi vay thủ công theo công thức Google Sheets (Cách 2)
    """
    # Parse start_date nếu là string
    start_date = parse_date(start_date) if isinstance(start_date, str) else start_date
    
    total_interest = 0
    remaining_amount = order_data['amount_untaxed']
    last_payment_date = start_date
    
    if verbose:
        print(f"\n  📋 Tính toán thủ công theo Google Sheets:")
        print(f"     Ngày bắt đầu: {start_date}")
        print(f"     Số tiền ban đầu: {remaining_amount:,.0f} VNĐ")
        print(f"     Lãi suất: {lending_rate * 100}%/ngày")
    
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
        
        # Đảm bảo days_diff không âm
        if days_diff < 0:
            days_diff = 0
        
        # Đảm bảo remaining_amount không âm
        if remaining_amount < 0:
            remaining_amount = 0
        
        # Tính lãi vay
        interest = days_diff * remaining_amount * lending_rate
        
        # Đảm bảo interest không âm
        if interest < 0:
            interest = 0
        
        if verbose:
            print(f"\n     Lần {idx}:")
            print(f"       Ngày TT: {payment_date}")
            print(f"       Số ngày: {days_diff} (từ {last_payment_date} đến {payment_date})")
            print(f"       Số tiền tính lãi: {remaining_amount:,.0f} VNĐ")
            print(f"       Số tiền thanh toán: {payment_amount:,.0f} VNĐ")
            print(f"       Lãi vay: {days_diff} × {remaining_amount:,.0f} × {lending_rate:.6f} = {interest:,.0f} VNĐ")
        
        total_interest += interest
        remaining_amount = remaining_amount - payment_amount
                                    last_payment_date = payment_date
        
        if remaining_amount < 0:
            remaining_amount = 0
    
    # Đảm bảo total_interest không âm
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
        print("KIỂM TRA TÍNH LÃI VAY THEO CÔNG THỨC GOOGLE SHEETS (CÁCH 2)")
        print("=" * 80)
        print()

        # Tìm tất cả đơn hàng đã thanh toán và có điều khoản TT với lãi suất > 0
        print("🔍 Đang tìm các đơn hàng đã thanh toán...")
        
        orders = models.execute_kw(
            DB, uid, PASSWORD,
            'sale.order', 'search',
            [[
                ('state', 'in', ['sale', 'done']),
                ('invoice_ids', '!=', False),
                ('payment_term_id', '!=', False),
            ]],
            {'limit': 1000}
        )
        
        print(f"📊 Tìm thấy {len(orders)} đơn hàng\n")

        # Lọc các đơn hàng có điều khoản TT với lending_rate > 0
        orders_to_check = []
        for order_id in orders:
                order = models.execute_kw(
                DB, uid, PASSWORD,
                    'sale.order', 'read',
                [[order_id]],
                {'fields': ['name', 'payment_term_id', 'amount_untaxed', 'total_product_qty', 'received_date', 'interest_amount', 'interest_per_kg']}
                )[0]
            
            if order['payment_term_id']:
                payment_term = models.execute_kw(
                    DB, uid, PASSWORD,
                    'account.payment.term', 'read',
                    [[order['payment_term_id'][0]]],
                    {'fields': ['name', 'lending_rate']}
                )
                if payment_term and payment_term[0].get('lending_rate', 0) > 0:
                    order['payment_term_info'] = payment_term[0]
                    orders_to_check.append(order)

        print(f"📊 Có {len(orders_to_check)} đơn hàng cần kiểm tra\n")
        print("🔄 Đang kiểm tra...\n")

        issues = []
        correct = []
        
        for idx, order_data in enumerate(orders_to_check, 1):
            order_id = order_data['id']
            order_name = order_data['name']
            current_interest = order_data.get('interest_amount', 0)
            
            # Lấy thông tin invoice_ids
            order_full = models.execute_kw(
                DB, uid, PASSWORD,
                'sale.order', 'read',
                [[order_id]],
                {'fields': ['invoice_ids']}
            )[0]
            
            invoice_ids = order_full.get('invoice_ids', [])
            if not invoice_ids:
                continue
            
            # Lấy thông tin thanh toán
            invoices = models.execute_kw(
                DB, uid, PASSWORD,
                'account.move', 'search_read',
                [[('id', 'in', invoice_ids)]],
                {'fields': ['name', 'state', 'invoice_date', 'invoice_payments_widget']}
            )
            
            # Thu thập tất cả thanh toán
            all_payments = []
            for inv in invoices:
                if inv['state'] != 'posted':
                    continue
                payment_info = inv.get('invoice_payments_widget')
                if payment_info and isinstance(payment_info, dict) and payment_info.get('content'):
                    for payment in payment_info['content']:
                        all_payments.append(payment)
            
            if not all_payments:
                if idx <= 5:  # Chỉ hiển thị 5 đơn đầu tiên không có thanh toán
                    print(f"  ⚠️ {order_name}: Không có thanh toán")
                continue
            
            # Sắp xếp theo ngày
            all_payments = sorted(all_payments, key=lambda x: x.get('date') or '')
            
            # Xác định ngày bắt đầu
            start_date = order_data.get('received_date')
            if start_date:
                start_date = parse_date(start_date)
            else:
                # Lấy ngày invoice sớm nhất
                invoice_dates = [parse_date(inv.get('invoice_date')) for inv in invoices if inv.get('invoice_date')]
                if invoice_dates:
                    start_date = min(invoice_dates)
            
            if not start_date:
                if idx <= 5:
                    print(f"  ⚠️ {order_name}: Không có ngày bắt đầu tính lãi")
                continue
            
            # Lấy lãi suất
            lending_rate = order_data['payment_term_info']['lending_rate'] / 100
            
            # Tính lãi vay thủ công
            try:
                manual_interest = calculate_interest_manual(order_data, all_payments, start_date, lending_rate, verbose=False)
                
                # So sánh
                diff = abs(current_interest - manual_interest)
                if diff > 0.01:  # Cho phép sai số nhỏ do làm tròn
                    issues.append({
                        'order': order_name,
                        'current': current_interest,
                        'manual': manual_interest,
                        'diff': diff
                    })
                    print(f"  ❌ [{idx}/{len(orders_to_check)}] {order_name}: Hệ thống={current_interest:,.0f}, Thủ công={manual_interest:,.0f}, Chênh lệch={diff:,.0f}")
                    # Hiển thị chi tiết cho đơn có vấn đề
                    calculate_interest_manual(order_data, all_payments, start_date, lending_rate, verbose=True)
                else:
                    correct.append(order_name)
                    if idx <= 10:  # Chỉ hiển thị 10 đơn đầu tiên
                        print(f"  ✅ [{idx}/{len(orders_to_check)}] {order_name}: {current_interest:,.0f} VNĐ (đúng)")
            except Exception as e:
                print(f"  ❌ [{idx}/{len(orders_to_check)}] {order_name}: Lỗi khi tính toán - {e}")
                import traceback
                traceback.print_exc()
        
        print("\n" + "=" * 80)
        print("KẾT QUẢ KIỂM TRA:")
        print("=" * 80)
        print(f"  ✅ Đúng: {len(correct)}/{len(orders_to_check)}")
        print(f"  ❌ Sai: {len(issues)}/{len(orders_to_check)}")
        
        if issues:
            print("\n📋 CÁC ĐƠN HÀNG CÓ SỰ KHÁC BIỆT:")
            for issue in issues[:20]:  # Chỉ hiển thị 20 đơn đầu tiên
                print(f"  - {issue['order']}: Hệ thống={issue['current']:,.0f}, Thủ công={issue['manual']:,.0f}, Chênh lệch={issue['diff']:,.0f}")
        
        return 0
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
