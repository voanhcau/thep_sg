#!/usr/bin/env python3
"""
Script kiểm tra lại các đơn hàng sau khi sửa code:
- S09194: Quá hạn nhưng lãi vay = 0
- S09473, S09168, S09140, S09005, S08950: Có lãi vay nhưng thanh toán sớm hạn
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

# Danh sách đơn cần kiểm tra
ORDERS_TO_CHECK = ['S09194', 'S09473', 'S09168', 'S09140', 'S09005', 'S08950']

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
        print("KIỂM TRA LẠI CÁC ĐƠN HÀNG SAU KHI SỬA CODE")
        print("=" * 80)
        print()

        # Tìm các đơn hàng
        orders = models.execute_kw(
            DB, uid, PASSWORD,
            'sale.order', 'search_read',
            [[('name', 'in', ORDERS_TO_CHECK)]],
            {
                'fields': [
                    'name', 'partner_id', 'payment_term_id', 'received_date',
                    'date_order', 'amount_untaxed', 'total_product_qty',
                    'auto_purchase_order_id', 'invoice_ids', 
                    'interest_amount', 'interest_per_kg',
                    'invoice_state', 'invoice_posted_date'
                ]
            }
        )

        print(f"📊 Tìm thấy {len(orders)} đơn hàng cần kiểm tra\n")

        for order in orders:
            order_name = order['name']
            print("=" * 80)
            print(f"ĐƠN HÀNG: {order_name}")
            print("=" * 80)
            print(f"Khách hàng: {order['partner_id'][1]}")
            print(f"Tổng tiền (chưa VAT): {order.get('amount_untaxed', 0):,.0f} VNĐ")
            print(f"Tổng khối lượng: {order.get('total_product_qty', 0):,.0f} kg")
            print(f"Lãi vay hiện tại: {order.get('interest_amount', 0):,.0f} VNĐ")
            print(f"Lãi vay/kg hiện tại: {order.get('interest_per_kg', 0):,.2f} VNĐ/kg")
            print()

            # Lấy thông tin điều khoản TT
            if order['payment_term_id']:
                payment_term = models.execute_kw(
                    DB, uid, PASSWORD,
                    'account.payment.term', 'read',
                    [[order['payment_term_id'][0]]],
                    {'fields': ['name', 'lending_days', 'lending_rate']}
                )
                if payment_term:
                    pt = payment_term[0]
                    print(f"Điều khoản TT: {pt['name']}")
                    print(f"  - Thời hạn TT: {pt.get('lending_days', 0)} ngày")
                    print(f"  - Lãi suất: {pt.get('lending_rate', 0)}%/ngày")
                    lending_rate = pt.get('lending_rate', 0) / 100
                    so_payment_term_days = pt.get('lending_days', 0)
                else:
                    print("⚠️  Không tìm thấy thông tin điều khoản TT")
                    continue
            else:
                print("⚠️  Không có điều khoản TT")
                continue

            # Lấy thông tin PO
            if order['auto_purchase_order_id']:
                po = models.execute_kw(
                    DB, uid, PASSWORD,
                    'purchase.order', 'read',
                    [[order['auto_purchase_order_id'][0]]],
                    {'fields': ['name', 'payment_term_id']}
                )
                if po and po[0].get('payment_term_id'):
                    po_pt = models.execute_kw(
                        DB, uid, PASSWORD,
                        'account.payment.term', 'read',
                        [[po[0]['payment_term_id'][0]]],
                        {'fields': ['name', 'lending_days']}
                    )
                    if po_pt:
                        print(f"PO liên kết: {po[0]['name']}")
                        print(f"  - Điều khoản TT PO: {po_pt[0]['name']} ({po_pt[0].get('lending_days', 0)} ngày)")

            # Lấy thông tin hóa đơn
            if not order['invoice_ids']:
                print("⚠️  Không có hóa đơn")
                print()
                continue

            invoices = models.execute_kw(
                DB, uid, PASSWORD,
                'account.move', 'read',
                [order['invoice_ids']],
                {'fields': ['name', 'invoice_date', 'state', 'payment_state', 'invoice_payments_widget']}
            )

            posted_invoices = [inv for inv in invoices if inv['state'] == 'posted']
            paid_invoices = [inv for inv in posted_invoices if inv['payment_state'] == 'paid']

            if not paid_invoices:
                print("⚠️  Chưa có hóa đơn đã thanh toán")
                print()
                continue

            print(f"\n📋 THÔNG TIN HÓA ĐƠN VÀ THANH TOÁN:")
            for inv in paid_invoices:
                print(f"  - {inv['name']}: Ngày {inv['invoice_date']}, Trạng thái: {inv['payment_state']}")

            # Xác định ngày bắt đầu tính lãi
            received_date = order.get('received_date')
            invoice_dates = [inv['invoice_date'] for inv in posted_invoices if inv.get('invoice_date')]
            invoice_date = min(invoice_dates) if invoice_dates else None

            start_date = received_date
            if not start_date and invoice_date:
                start_date = invoice_date
            elif invoice_date and invoice_date <= (start_date or '9999-12-31'):
                start_date = invoice_date

            print(f"\n📅 NGÀY BẮT ĐẦU TÍNH LÃI: {start_date}")

            # Lấy thông tin thanh toán
            print(f"\n💳 CHI TIẾT THANH TOÁN:")
            all_payments = []
            for inv in paid_invoices:
                widget = inv.get('invoice_payments_widget')
                if widget:
                    if isinstance(widget, str):
                        import json
                        widget = json.loads(widget)
                    if isinstance(widget, dict) and widget.get('content'):
                        for payment in widget['content']:
                            all_payments.append({
                                'invoice': inv['name'],
                                'date': payment.get('date'),
                                'amount': payment.get('amount', 0)
                            })

            # Sắp xếp theo ngày
            all_payments.sort(key=lambda x: x.get('date', ''))

            for idx, payment in enumerate(all_payments, 1):
                print(f"  Lần {idx}: Ngày {payment['date']}, Số tiền: {payment['amount']:,.0f} VNĐ")

            if not all_payments:
                print("  ⚠️  Không có thông tin thanh toán")
                print()
                continue

            # Tính toán thủ công
            print(f"\n🧮 TÍNH TOÁN THỦ CÔNG:")
            due_date = datetime.strptime(start_date, '%Y-%m-%d').date() + timedelta(days=so_payment_term_days)
            print(f"  Ngày đến hạn = {start_date} + {so_payment_term_days} ngày = {due_date}")

            total_interest_manual = 0
            remaining_amount = order.get('amount_untaxed', 0)

            for idx, payment in enumerate(all_payments, 1):
                payment_date_str = payment['date']
                payment_amount = payment['amount']

                # Convert payment_date
                if isinstance(payment_date_str, str):
                    payment_date_obj = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                else:
                    payment_date_obj = payment_date_str

                overdue_days = (payment_date_obj - due_date).days

                print(f"\n  💸 Thanh toán lần {idx}:")
                print(f"     Ngày thanh toán: {payment_date_obj}")
                print(f"     Số ngày quá hạn: {overdue_days} ngày")

                if overdue_days > 0:
                    days_diff = overdue_days
                    interest = days_diff * remaining_amount * lending_rate
                    total_interest_manual += interest
                    print(f"     ✅ Tính lãi: {days_diff} ngày × {remaining_amount:,.0f} × {lending_rate:.6f} = {interest:,.0f} VNĐ")
                else:
                    print(f"     ✅ Thanh toán đúng hạn hoặc sớm hạn → Không tính lãi")

                # Cập nhật số tiền còn lại
                payment_amount_before_vat = payment_amount / 1.1
                remaining_amount = remaining_amount - payment_amount_before_vat
                print(f"     Số tiền còn lại: {remaining_amount:,.0f} VNĐ")

            # Tính lãi/kg
            total_qty = order.get('total_product_qty', 0)
            if total_qty > 0:
                interest_per_kg_manual = total_interest_manual / total_qty
            else:
                interest_per_kg_manual = 0

            print(f"\n📊 KẾT QUẢ TÍNH TOÁN THỦ CÔNG:")
            print(f"  Tổng lãi vay: {total_interest_manual:,.0f} VNĐ")
            print(f"  Lãi vay/kg: {interest_per_kg_manual:,.2f} VNĐ/kg")

            # So sánh với giá trị hiện tại
            current_interest = order.get('interest_amount', 0) or 0
            current_interest_per_kg = order.get('interest_per_kg', 0) or 0

            print(f"\n🔍 SO SÁNH:")
            print(f"  Lãi vay hiện tại: {current_interest:,.0f} VNĐ")
            print(f"  Lãi vay tính thủ công: {total_interest_manual:,.0f} VNĐ")
            print(f"  Lãi vay/kg hiện tại: {current_interest_per_kg:,.2f} VNĐ/kg")
            print(f"  Lãi vay/kg tính thủ công: {interest_per_kg_manual:,.2f} VNĐ/kg")

            if abs(current_interest - total_interest_manual) < 1:
                print(f"  ✅ KHỚP - Lãi vay đã được tính đúng!")
            else:
                diff = total_interest_manual - current_interest
                print(f"  ❌ KHÔNG KHỚP - Chênh lệch: {diff:,.0f} VNĐ")
                print(f"  → Cần chạy lại calculate_interest() để cập nhật")

            print()

        # Gợi ý chạy lại calculate_interest
        print("=" * 80)
        print("KHUYẾN NGHỊ:")
        print("=" * 80)
        print("Nếu có đơn không khớp, chạy lệnh sau để tính lại lãi vay:")
        print()
        for order_name in ORDERS_TO_CHECK:
            print(f"  - {order_name}")
        print()

        return 0
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

