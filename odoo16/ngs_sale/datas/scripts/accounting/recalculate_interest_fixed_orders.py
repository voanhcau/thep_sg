#!/usr/bin/env python3
"""
Script chạy lại calculate_interest() cho các đơn hàng có vấn đề sau khi sửa code
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

# Danh sách đơn cần tính lại
ORDERS_TO_RECALCULATE = ['S09194', 'S09473', 'S09168', 'S09140', 'S09005', 'S08950']

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
        print("CHẠY LẠI calculate_interest() CHO CÁC ĐƠN HÀNG")
        print("=" * 80)
        print()

        # Tìm các đơn hàng
        orders = models.execute_kw(
            DB, uid, PASSWORD,
            'sale.order', 'search',
            [[('name', 'in', ORDERS_TO_RECALCULATE)]]
        )

        if not orders:
            print("❌ Không tìm thấy đơn hàng nào")
            return 1

        print(f"📊 Tìm thấy {len(orders)} đơn hàng cần tính lại\n")

        # Lấy thông tin trước khi tính
        orders_info = models.execute_kw(
            DB, uid, PASSWORD,
            'sale.order', 'read',
            [orders],
            {'fields': ['name', 'interest_amount', 'interest_per_kg']}
        )

        print("📋 THÔNG TIN TRƯỚC KHI TÍNH LẠI:")
        for order in orders_info:
            print(f"  {order['name']}: Lãi vay = {order.get('interest_amount', 0):,.0f} VNĐ, Lãi/kg = {order.get('interest_per_kg', 0):,.2f} VNĐ/kg")
        print()

        # Chạy calculate_interest() cho từng đơn
        print("🔄 Đang tính lại lãi vay...\n")
        success_count = 0
        error_count = 0

        for order_id in orders:
            order_info = [o for o in orders_info if o['id'] == order_id][0]
            order_name = order_info['name']
            
            print(f"  [{success_count + error_count + 1}/{len(orders)}] {order_name}...", end=" ")
            
            try:
                # Gọi calculate_interest()
                result = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'calculate_interest',
                    [[order_id]]
                )
                
                # Đọc lại để lấy giá trị mới
                updated_order = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'read',
                    [[order_id]],
                    {'fields': ['name', 'interest_amount', 'interest_per_kg']}
                )[0]
                
                old_interest = order_info.get('interest_amount', 0) or 0
                new_interest = updated_order.get('interest_amount', 0) or 0
                old_interest_per_kg = order_info.get('interest_per_kg', 0) or 0
                new_interest_per_kg = updated_order.get('interest_per_kg', 0) or 0
                
                print(f"✅ Hoàn thành")
                print(f"     Cũ: {old_interest:,.0f} VNĐ ({old_interest_per_kg:,.2f} VNĐ/kg)")
                print(f"     Mới: {new_interest:,.0f} VNĐ ({new_interest_per_kg:,.2f} VNĐ/kg)")
                
                if old_interest != new_interest:
                    diff = new_interest - old_interest
                    print(f"     Thay đổi: {diff:+,.0f} VNĐ")
                
                success_count += 1
                print()
                
            except Exception as e:
                print(f"❌ Lỗi: {e}")
                error_count += 1
                print()

        print("=" * 80)
        print("KẾT QUẢ:")
        print(f"  ✅ Thành công: {success_count}/{len(orders)}")
        print(f"  ❌ Lỗi: {error_count}/{len(orders)}")
        print("=" * 80)

        return 0
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

