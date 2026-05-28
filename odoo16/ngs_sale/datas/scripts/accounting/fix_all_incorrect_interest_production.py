#!/usr/bin/env python3
"""
Script chạy lại calculate_interest cho tất cả các đơn hàng có lãi vay sai trên production
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
        print("CHẠY LẠI calculate_interest CHO TẤT CẢ ĐƠN HÀNG CÓ LÃI VAY SAI")
        print("=" * 80)
        print()

        # Danh sách các đơn hàng sai (từ kết quả check_interest_calculation.py)
        incorrect_orders = [
            'S09580', 'S09551', 'S09548', 'S09542', 'S09541', 'S09532', 'S09543', 'S09526',
            'S09524', 'S09523', 'S09498', 'S09492', 'S09486', 'S09473', 'S09445', 'S09455',
            'S09412', 'S09379', 'S09394', 'S09378', 'S09319', 'S09374', 'S09320', 'S09316',
            'S09315', 'S09283', 'S09247', 'S09238', 'S09216', 'S09198', 'S09194', 'S09212',
            'S09176', 'S09168', 'S09150', 'S09149', 'S09144', 'S09140', 'S09135', 'S09119',
            'S09153', 'S09091', 'S09081', 'S09073', 'S09006', 'S08977', 'S09005', 'S08950',
            'S08948'
        ]

        print(f"📊 Tổng số đơn hàng cần sửa: {len(incorrect_orders)}\n")

        success_count = 0
        error_count = 0

        for idx, order_name in enumerate(incorrect_orders, 1):
            print(f"[{idx}/{len(incorrect_orders)}] {order_name}... ", end="", flush=True)
            
            try:
                # Tìm đơn hàng
                order_ids = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'search',
                    [[('name', '=', order_name)]]
                )
                
                if not order_ids:
                    print(f"⚠️ Không tìm thấy")
                    error_count += 1
                    continue
                
                order_id = order_ids[0]
                
                # Đọc thông tin hiện tại
                order = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'read',
                    [[order_id]],
                    {'fields': ['interest_amount', 'interest_per_kg']}
                )[0]
                
                old_interest = order.get('interest_amount', 0)
                
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
                
                if old_interest != new_interest:
                    print(f"✅ {old_interest:,.0f} → {new_interest:,.0f} VNĐ")
                else:
                    print(f"ℹ️ Không đổi ({old_interest:,.0f} VNĐ)")
                
                success_count += 1

            except Exception as e:
                print(f"❌ Lỗi: {e}")
                error_count += 1
        
        print("\n" + "=" * 80)
        print("KẾT QUẢ:")
        print(f"  ✅ Thành công: {success_count}/{len(incorrect_orders)}")
        print(f"  ❌ Lỗi: {error_count}/{len(incorrect_orders)}")
        print("=" * 80)
        
        return 0
    except Exception as e:
        print(f"❌ Lỗi tổng quát: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

