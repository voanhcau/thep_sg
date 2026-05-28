#!/usr/bin/env python3
"""
Script tính lại lãi vay cho TẤT CẢ đơn hàng (không chỉ đơn đã thanh toán)
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
        print("TÍNH LẠI LÃI VAY CHO TẤT CẢ ĐƠN HÀNG")
        print("=" * 80)
        print()

        # Tìm TẤT CẢ đơn hàng có payment_term_id
        print("🔍 Đang tìm tất cả đơn hàng có điều khoản thanh toán...")
        
        # Tìm tất cả đơn hàng có payment_term_id (không giới hạn state)
        all_order_ids = models.execute_kw(
            DB, uid, PASSWORD,
            'sale.order', 'search',
            [[('payment_term_id', '!=', False)]],
            {'limit': 0}  # Không giới hạn
        )

        print(f"📊 Tìm thấy {len(all_order_ids)} đơn hàng có điều khoản TT\n")

        # Lọc các đơn hàng có điều khoản TT với lending_rate > 0
        print("🔍 Đang lọc các đơn hàng có lãi suất > 0...")
        orders_to_recalculate = []
        batch_size = 100
        
        for i in range(0, len(all_order_ids), batch_size):
            batch_ids = all_order_ids[i:i+batch_size]
            orders = models.execute_kw(
                DB, uid, PASSWORD,
                'sale.order', 'read',
                [batch_ids],
                {
                    'fields': [
                        'name', 'payment_term_id', 'state', 'invoice_ids',
                        'interest_amount', 'interest_per_kg'
                    ]
                }
            )
            
            for order in orders:
                if not order['payment_term_id']:
                    continue
                
                # Kiểm tra payment_term có lending_rate > 0
                payment_term = models.execute_kw(
                    DB, uid, PASSWORD,
                    'account.payment.term', 'read',
                    [[order['payment_term_id'][0]]],
                    {'fields': ['name', 'lending_rate']}
                )
                if not payment_term or payment_term[0].get('lending_rate', 0) <= 0:
                    continue
                
                orders_to_recalculate.append(order['id'])

        print(f"📊 Có {len(orders_to_recalculate)} đơn hàng cần tính lại lãi vay\n")
        print("🔄 Bắt đầu tính lại...\n")

        changed_count = 0
        unchanged_count = 0
        error_count = 0

        for idx, order_id in enumerate(orders_to_recalculate, 1):
            try:
                # Đọc thông tin hiện tại
                order = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'read',
                    [[order_id]],
                    {'fields': ['name', 'interest_amount', 'interest_per_kg']}
                )[0]
                
                order_name = order['name']
                old_interest = order.get('interest_amount', 0)
                old_interest_per_kg = order.get('interest_per_kg', 0)
                
                # Chạy lại calculate_interest
                models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'calculate_interest',
                    [[order_id]]
                )
                
                # Đọc lại kết quả
                updated_order = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'read',
                    [[order_id]],
                    {'fields': ['interest_amount', 'interest_per_kg']}
                )[0]
                
                new_interest = updated_order.get('interest_amount', 0)
                new_interest_per_kg = updated_order.get('interest_per_kg', 0)
                
                # Kiểm tra có thay đổi không
                if abs(old_interest - new_interest) > 0.01 or abs(old_interest_per_kg - new_interest_per_kg) > 0.01:
                    changed_count += 1
                    if changed_count <= 20:  # Chỉ hiển thị 20 đơn đầu tiên có thay đổi
                        print(f"[{idx}/{len(orders_to_recalculate)}] {order_name}: {old_interest:,.0f} → {new_interest:,.0f} VNĐ ({new_interest_per_kg:,.2f} VNĐ/kg)")
                else:
                    unchanged_count += 1
                    if idx % 100 == 0:  # Hiển thị mỗi 100 đơn
                        print(f"[{idx}/{len(orders_to_recalculate)}] Đã xử lý {idx} đơn hàng...")
                
            except xmlrpc.client.Fault as fault:
                error_count += 1
                if error_count <= 10:  # Chỉ hiển thị 10 lỗi đầu tiên
                    print(f"[{idx}/{len(orders_to_recalculate)}] ❌ Lỗi {order_name if 'order_name' in locals() else order_id}: {fault}")
            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    print(f"[{idx}/{len(orders_to_recalculate)}] ❌ Lỗi {order_name if 'order_name' in locals() else order_id}: {e}")

        print("\n" + "=" * 80)
        print("KẾT QUẢ:")
        print(f"  - Tổng số đơn đã xử lý: {len(orders_to_recalculate)}")
        print(f"  - Số đơn có thay đổi: {changed_count}")
        print(f"  - Số đơn không thay đổi: {unchanged_count}")
        print(f"  - Số đơn lỗi: {error_count}")
        print("=" * 80)

        return 0
    except Exception as e:
        print(f"❌ Lỗi tổng quát: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

