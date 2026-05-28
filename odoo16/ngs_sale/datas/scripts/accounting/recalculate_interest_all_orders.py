#!/usr/bin/env python3
"""
Script tính lại lãi vay cho tất cả các đơn hàng đã thanh toán
"""
import os
import sys
import xmlrpc.client
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
        print("TÍNH LẠI LÃI VAY CHO TẤT CẢ ĐƠN HÀNG ĐÃ THANH TOÁN")
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
            {'limit': 10000}
        )

        print(f"📊 Tìm thấy {len(orders)} đơn hàng\n")

        # Lọc các đơn hàng có điều khoản TT với lending_rate > 0 và đã thanh toán
        orders_to_recalculate = []
        for order_id in orders:
            order = models.execute_kw(
                DB, uid, PASSWORD,
                'sale.order', 'read',
                [[order_id]],
                {
                    'fields': [
                        'name', 'payment_term_id', 'invoice_ids',
                        'interest_amount', 'interest_per_kg'
                    ]
                }
            )[0]

            if not order['payment_term_id']:
                continue

            # Kiểm tra payment_term có lending_rate > 0
            payment_term = models.execute_kw(
                DB, uid, PASSWORD,
                'account.payment.term', 'read',
                [[order['payment_term_id'][0]]],
                {'fields': ['name', 'lending_rate', 'lending_days']}
            )
            if not payment_term or payment_term[0].get('lending_rate', 0) <= 0:
                continue

            # Kiểm tra có invoice đã thanh toán không
            if not order['invoice_ids']:
                continue

            invoices = models.execute_kw(
                DB, uid, PASSWORD,
                'account.move', 'read',
                [order['invoice_ids']],
                {'fields': ['state', 'payment_state']}
            )

            paid_invoices = [
                inv for inv in invoices 
                if inv['state'] == 'posted' and inv['payment_state'] == 'paid'
            ]

            if not paid_invoices:
                continue

            orders_to_recalculate.append({
                'id': order_id,
                'name': order['name'],
                'old_interest': order.get('interest_amount', 0) or 0,
                'old_interest_per_kg': order.get('interest_per_kg', 0) or 0,
            })

        print(f"📊 Có {len(orders_to_recalculate)} đơn hàng cần tính lại lãi vay\n")
        print("🔄 Bắt đầu tính lại...\n")

        updated_count = 0
        changed_count = 0
        for idx, order_info in enumerate(orders_to_recalculate, 1):
            order_id = order_info['id']
            order_name = order_info['name']
            old_interest = order_info['old_interest']
            
            try:
                # Gọi calculate_interest
                result = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'calculate_interest',
                    [[order_id]]
                )

                if result:
                    # Đọc lại để xem giá trị mới
                    updated = models.execute_kw(
                        DB, uid, PASSWORD,
                        'sale.order', 'read',
                        [[order_id]],
                        {'fields': ['interest_amount', 'interest_per_kg']}
                    )[0]

                    new_interest = updated.get('interest_amount', 0) or 0
                    new_interest_per_kg = updated.get('interest_per_kg', 0) or 0

                    if abs(new_interest - old_interest) > 0.01:
                        changed_count += 1
                        print(f"[{idx}/{len(orders_to_recalculate)}] {order_name}: "
                              f"{old_interest:,.0f} → {new_interest:,.0f} VNĐ "
                              f"({new_interest_per_kg:.2f} VNĐ/kg)")
                    else:
                        if idx % 50 == 0:
                            print(f"[{idx}/{len(orders_to_recalculate)}] {order_name}: Không thay đổi")
                else:
                    print(f"[{idx}/{len(orders_to_recalculate)}] {order_name}: ❌ Lỗi khi tính lãi")

                updated_count += 1

            except Exception as e:
                print(f"[{idx}/{len(orders_to_recalculate)}] {order_name}: ❌ Lỗi: {e}")

        print()
        print("=" * 80)
        print(f"KẾT QUẢ:")
        print(f"  - Tổng số đơn đã xử lý: {updated_count}")
        print(f"  - Số đơn có thay đổi: {changed_count}")
        print(f"  - Số đơn không thay đổi: {updated_count - changed_count}")
        print("=" * 80)

        return 0
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

