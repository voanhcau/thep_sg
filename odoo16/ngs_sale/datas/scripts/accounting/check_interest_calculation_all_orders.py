#!/usr/bin/env python3
"""
Script rà soát tất cả đơn hàng để tìm các đơn có lãi vay tính sai
Kiểm tra các đơn hàng:
- Đã thanh toán (invoice_state = 'paid')
- Có điều khoản TT với lending_rate > 0
- Có invoice đã thanh toán
- Nhưng interest_amount = 0 hoặc price_landing = 0
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
        print("RÀ SOÁT ĐƠN HÀNG CÓ LÃI VAY TÍNH SAI")
        print("=" * 80)
        print()

        # Tìm tất cả đơn hàng đã thanh toán và có điều khoản TT với lãi suất > 0
        print("🔍 Đang tìm các đơn hàng đã thanh toán...")
        
        # Tìm đơn hàng có:
        # - state in ['sale', 'done']
        # - invoice_ids (có hóa đơn)
        # - payment_term_id (có điều khoản TT)
        orders = models.execute_kw(
            DB, uid, PASSWORD,
            'sale.order', 'search_read',
            [[
                ('state', 'in', ['sale', 'done']),
                ('invoice_ids', '!=', False),
                ('payment_term_id', '!=', False),
            ]],
            {
                'fields': [
                    'name', 'partner_id', 'payment_term_id', 'received_date',
                    'date_order', 'amount_untaxed', 'total_product_qty',
                    'auto_purchase_order_id', 'invoice_ids', 
                    'interest_amount', 'interest_per_kg',
                    'invoice_state', 'invoice_posted_date'
                ],
                'limit': 1000  # Giới hạn 1000 đơn để tránh quá tải
            }
        )

        print(f"📊 Tìm thấy {len(orders)} đơn hàng cần kiểm tra\n")

        # Lọc các đơn hàng có điều khoản TT với lending_rate > 0
        orders_with_interest = []
        for order in orders:
            if order['payment_term_id']:
                payment_term = models.execute_kw(
                    DB, uid, PASSWORD,
                    'account.payment.term', 'read',
                    [[order['payment_term_id'][0]]],
                    {'fields': ['name', 'lending_days', 'lending_rate']}
                )
                if payment_term and payment_term[0].get('lending_rate', 0) > 0:
                    order['payment_term_info'] = payment_term[0]
                    orders_with_interest.append(order)

        print(f"📊 Có {len(orders_with_interest)} đơn hàng có điều khoản TT với lãi suất > 0\n")

        # Kiểm tra từng đơn hàng
        suspicious_orders = []
        for idx, order in enumerate(orders_with_interest, 1):
            order_name = order['name']
            print(f"[{idx}/{len(orders_with_interest)}] Kiểm tra {order_name}...", end=" ")

            # Kiểm tra có invoice đã thanh toán không
            if not order['invoice_ids']:
                print("⏭️  Không có hóa đơn")
                continue

            invoices = models.execute_kw(
                DB, uid, PASSWORD,
                'account.move', 'read',
                [order['invoice_ids']],
                {'fields': ['name', 'invoice_date', 'state', 'payment_state', 'invoice_payments_widget']}
            )

            # Lọc invoice đã vào sổ và đã thanh toán
            paid_invoices = [
                inv for inv in invoices 
                if inv['state'] == 'posted' and inv['payment_state'] == 'paid'
            ]

            if not paid_invoices:
                print("⏭️  Chưa thanh toán")
                continue

            # Kiểm tra có payment date không
            has_payment = False
            payment_date = None
            for inv in paid_invoices:
                widget = inv.get('invoice_payments_widget')
                if widget:
                    if isinstance(widget, str):
                        import json
                        widget = json.loads(widget)
                    if isinstance(widget, dict) and widget.get('content'):
                        has_payment = True
                        # Lấy ngày thanh toán cuối cùng
                        payments = sorted(widget['content'], key=lambda x: x.get('date', ''))
                        if payments:
                            payment_date = payments[-1].get('date')
                        break

            if not has_payment:
                print("⏭️  Không có thông tin thanh toán")
                continue

            # Tính toán thủ công để so sánh
            received_date = order.get('received_date')
            invoice_date = min([inv['invoice_date'] for inv in paid_invoices if inv.get('invoice_date')])
            
            # Xác định ngày bắt đầu tính lãi
            start_date = received_date or invoice_date
            if invoice_date and (not start_date or invoice_date <= start_date):
                start_date = invoice_date

            if not start_date:
                print("⏭️  Không có ngày bắt đầu tính lãi")
                continue

            # Tính ngày đến hạn
            so_payment_term_days = order['payment_term_info'].get('lending_days', 0)
            if so_payment_term_days <= 0:
                print("⏭️  Không có thời hạn TT")
                continue

            due_date = datetime.strptime(start_date, '%Y-%m-%d').date() + timedelta(days=so_payment_term_days)
            
            # Convert payment_date
            if isinstance(payment_date, str):
                payment_date_obj = datetime.strptime(payment_date, '%Y-%m-%d').date()
            else:
                payment_date_obj = payment_date

            # Tính số ngày quá hạn
            overdue_days = (payment_date_obj - due_date).days

            # Kiểm tra nếu quá hạn nhưng lãi vay = 0
            current_interest = order.get('interest_amount', 0) or 0
            lending_rate = order['payment_term_info'].get('lending_rate', 0) / 100

            if overdue_days > 0 and current_interest == 0:
                suspicious_orders.append({
                    'order': order,
                    'overdue_days': overdue_days,
                    'due_date': due_date,
                    'payment_date': payment_date_obj,
                    'start_date': start_date,
                    'so_payment_term_days': so_payment_term_days,
                    'lending_rate': lending_rate,
                    'amount_untaxed': order.get('amount_untaxed', 0),
                })
                print(f"❌ SAI: Quá hạn {overdue_days} ngày nhưng lãi vay = 0")
            elif overdue_days <= 0 and current_interest > 0:
                suspicious_orders.append({
                    'order': order,
                    'overdue_days': overdue_days,
                    'due_date': due_date,
                    'payment_date': payment_date_obj,
                    'start_date': start_date,
                    'so_payment_term_days': so_payment_term_days,
                    'lending_rate': lending_rate,
                    'amount_untaxed': order.get('amount_untaxed', 0),
                    'issue': 'Có lãi vay nhưng không quá hạn'
                })
                print(f"⚠️  NGHI VẤN: Không quá hạn nhưng có lãi vay = {current_interest:,.0f}")
            else:
                print("✅ OK")

        print()
        print("=" * 80)
        print(f"KẾT QUẢ: Tìm thấy {len(suspicious_orders)} đơn hàng có vấn đề")
        print("=" * 80)
        print()

        if suspicious_orders:
            print("📋 CHI TIẾT CÁC ĐƠN HÀNG CÓ VẤN ĐỀ:\n")
            for idx, item in enumerate(suspicious_orders, 1):
                order = item['order']
                print(f"{idx}. {order['name']}")
                print(f"   Khách hàng: {order['partner_id'][1]}")
                print(f"   Điều khoản TT: {order['payment_term_info']['name']} ({item['so_payment_term_days']} ngày)")
                print(f"   Lãi suất: {order['payment_term_info'].get('lending_rate', 0)}%/ngày")
                print(f"   Ngày bắt đầu: {item['start_date']}")
                print(f"   Ngày đến hạn: {item['due_date']}")
                print(f"   Ngày thanh toán: {item['payment_date']}")
                print(f"   Số ngày quá hạn: {item['overdue_days']} ngày")
                print(f"   Tổng tiền (chưa VAT): {item['amount_untaxed']:,.0f} VNĐ")
                print(f"   Lãi vay hiện tại: {order.get('interest_amount', 0):,.0f} VNĐ")
                
                # Tính lãi vay đúng
                if item['overdue_days'] > 0:
                    correct_interest = item['overdue_days'] * item['amount_untaxed'] * item['lending_rate']
                    print(f"   Lãi vay đúng (ước tính): {correct_interest:,.0f} VNĐ")
                
                if 'issue' in item:
                    print(f"   ⚠️  Vấn đề: {item['issue']}")
                
                print()

        return 0
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

