#!/usr/bin/env python3
"""
Script kiểm tra tính lãi vay ÂM khi thanh toán trước hạn
Test case: Đơn S09623 - thanh toán trước hạn 4 ngày
"""

import os
import sys
import xmlrpc.client
from datetime import datetime, date
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

# Thêm đường dẫn để import từ Odoo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False

# Lấy environment type từ command line argument
env_type = sys.argv[1] if len(sys.argv) > 1 else None

print("=" * 80)
print("KIỂM TRA TÍNH LÃI VAY ÂM KHI THANH TOÁN TRƯỚC HẠN")
print("=" * 80)

if USE_ENV_LOADER:
    try:
        URL, DB, USERNAME, PASSWORD, models, uid = setup_odoo_connection(env_type)
        print(f"✅ Connected to {env_type or 'default'} environment")
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        sys.exit(1)
else:
    # Fallback: dùng environment variables
    URL = os.getenv('ODOO_URL')
    DB = os.getenv('ODOO_DB')
    USERNAME = os.getenv('ODOO_USERNAME')
    PASSWORD = os.getenv('ODOO_PASSWORD')
    
    if not all([URL, DB, USERNAME, PASSWORD]):
        print('❌ Missing environment variables')
        print('   Run: source load_env.sh [prod|staging|local]')
        sys.exit(1)

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common", allow_none=True)
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        print("❌ Authentication failed")
        sys.exit(1)
    
    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)
if not uid:
    print('❌ Authentication failed')
    sys.exit(1)

models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)

# Tìm đơn S09623
order_name = 'S09623'
so_ids = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'search', [[('name', '=', order_name)]])
if not so_ids:
    print(f'❌ Order {order_name} not found')
    sys.exit(1)

order_id = so_ids[0]
print(f"\n✅ Tìm thấy đơn hàng: {order_name} (ID: {order_id})")

# Đọc thông tin đơn hàng
order = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'read', [order_id], {
    'fields': [
        'name', 'payment_term_id', 'received_date', 
        'interest_amount', 'interest_per_kg', 'amount_untaxed',
        'auto_purchase_order_id', 'invoice_ids', 'total_product_qty'
    ]
})[0]

print(f"\n📋 THÔNG TIN ĐƠN HÀNG:")
print(f"   - interest_amount (hiện tại): {order.get('interest_amount', 0):,.0f} VNĐ")
print(f"   - interest_per_kg (hiện tại): {order.get('interest_per_kg', 0):,.2f} VNĐ/kg")
print(f"   - amount_untaxed: {order.get('amount_untaxed', 0):,.0f} VNĐ")
print(f"   - received_date: {order.get('received_date')}")
print(f"   - total_product_qty: {order.get('total_product_qty', 0):,.0f} kg")

# Lấy payment term
if order.get('payment_term_id'):
    pt_id = order['payment_term_id'][0] if isinstance(order['payment_term_id'], list) else order['payment_term_id']
    pt = models.execute_kw(DB, uid, PASSWORD, 'account.payment.term', 'read', [pt_id], {
        'fields': ['name', 'lending_rate', 'lending_days']
    })[0]
    print(f"\n💳 PAYMENT TERM:")
    print(f"   - name: {pt.get('name')}")
    print(f"   - lending_rate: {pt.get('lending_rate', 0)}%/ngày")
    print(f"   - lending_days: {pt.get('lending_days', 0)} ngày")

# Lấy invoices và payments
invoice_ids = order.get('invoice_ids', [])
if invoice_ids:
    invoices = models.execute_kw(DB, uid, PASSWORD, 'account.move', 'read', [invoice_ids], {
        'fields': ['name', 'invoice_date', 'state', 'amount_total', 'amount_residual', 'invoice_date_due', 'invoice_payments_widget']
    })
    print(f"\n📄 INVOICES ({len(invoices)}):")
    for inv in invoices:
        print(f"\n   Invoice: {inv.get('name')}")
        print(f"   - invoice_date: {inv.get('invoice_date')}")
        print(f"   - invoice_date_due: {inv.get('invoice_date_due')}")
        print(f"   - state: {inv.get('state')}")
        print(f"   - amount_total: {inv.get('amount_total', 0):,.0f} VNĐ")
        print(f"   - amount_residual: {inv.get('amount_residual', 0):,.0f} VNĐ")
        
        # Lấy payments từ invoice_payments_widget
        payment_widget = inv.get('invoice_payments_widget')
        if payment_widget and isinstance(payment_widget, dict):
            content = payment_widget.get('content', [])
            if content:
                print(f"   - Payments ({len(content)}):")
                for idx, p in enumerate(content, 1):
                    payment_date = p.get('date')
                    payment_amount = p.get('amount', 0)
                    print(f"     Payment {idx}:")
                    print(f"       - date: {payment_date}")
                    print(f"       - amount: {payment_amount:,.0f} VNĐ")
                    
                    # Tính toán thủ công
                    if payment_date and order.get('received_date'):
                        received_date = datetime.strptime(order.get('received_date'), '%Y-%m-%d').date()
                        payment_date_obj = datetime.strptime(payment_date, '%Y-%m-%d').date()
                        days_diff = (payment_date_obj - received_date).days
                        lending_rate = pt.get('lending_rate', 0) / 100
                        amount_untaxed = order.get('amount_untaxed', 0)
                        
                        print(f"       - days_diff (payment_date - received_date): {days_diff} ngày")
                        if days_diff < 0:
                            print(f"       ⚠️  Thanh toán TRƯỚC HẠN {abs(days_diff)} ngày")
                            expected_interest = days_diff * amount_untaxed * lending_rate
                            print(f"       - Expected interest (manual calc): {expected_interest:,.0f} VNĐ (ÂM)")
                        else:
                            print(f"       - Thanh toán SAU HẠN {days_diff} ngày")
                            expected_interest = days_diff * amount_untaxed * lending_rate
                            print(f"       - Expected interest (manual calc): {expected_interest:,.0f} VNĐ")

print("\n" + "=" * 80)
print("CHẠY LẠI TÍNH LÃI VAY...")
print("=" * 80)

# Gọi calculate_interest
try:
    result = models.execute_kw(
        DB, uid, PASSWORD,
        'sale.order', 'calculate_interest',
        [[order_id]]
    )
    print("✅ Đã chạy calculate_interest thành công")
except Exception as e:
    print(f"❌ Lỗi khi chạy calculate_interest: {e}")
    sys.exit(1)

# Đọc lại kết quả
order_after = models.execute_kw(DB, uid, PASSWORD, 'sale.order', 'read', [order_id], {
    'fields': ['name', 'interest_amount', 'interest_per_kg']
})[0]

print(f"\n📊 KẾT QUẢ SAU KHI TÍNH LẠI:")
print(f"   - interest_amount: {order_after.get('interest_amount', 0):,.0f} VNĐ")
print(f"   - interest_per_kg: {order_after.get('interest_per_kg', 0):,.2f} VNĐ/kg")

# So sánh
old_interest = order.get('interest_amount', 0)
new_interest = order_after.get('interest_amount', 0)

print(f"\n🔍 SO SÁNH:")
print(f"   - interest_amount (trước): {old_interest:,.0f} VNĐ")
print(f"   - interest_amount (sau): {new_interest:,.0f} VNĐ")

if new_interest < 0:
    print(f"\n✅ THÀNH CÔNG: Lãi vay đã được tính ÂM ({new_interest:,.0f} VNĐ) khi thanh toán trước hạn")
elif new_interest == 0:
    print(f"\n⚠️  CẢNH BÁO: Lãi vay vẫn = 0, có thể do logic chưa đúng hoặc có điều kiện khác")
else:
    print(f"\n❌ LỖI: Lãi vay vẫn dương ({new_interest:,.0f} VNĐ), logic chưa đúng")

print("\n" + "=" * 80)

