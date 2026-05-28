#!/usr/bin/env python3
"""
Script chạy lại calculate_interest cho các đơn hàng có lãi vay sai

Hỗ trợ 3 môi trường: prod, staging, local
Usage:
    python fix_incorrect_interest_orders.py          # Dùng default (PROD)
    python fix_incorrect_interest_orders.py prod     # Dùng PROD
    python fix_incorrect_interest_orders.py staging  # Dùng STAGING
    python fix_incorrect_interest_orders.py local    # Dùng LOCAL
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

# Danh sách các đơn hàng có lãi vay sai (từ kết quả check_interest_calculation.py)
ORDERS_TO_FIX = ['S08948', 'S08834', 'S08800', 'S08641', 'S08536']

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
        print("CHẠY LẠI calculate_interest CHO CÁC ĐƠN HÀNG CÓ LÃI VAY SAI")
        print("=" * 80)
        print()

        # Tìm các đơn hàng
        for order_name in ORDERS_TO_FIX:
            print(f"🔍 Đang tìm đơn hàng {order_name}...")
            order_ids = models.execute_kw(
                DB, uid, PASSWORD,
                'sale.order', 'search',
                [[('name', '=', order_name)]]
            )
            
            if not order_ids:
                print(f"  ⚠️ Không tìm thấy đơn hàng {order_name}")
                continue
            
            order_id = order_ids[0]
            
            # Đọc thông tin hiện tại
            order = models.execute_kw(
                DB, uid, PASSWORD,
                'sale.order', 'read',
                [[order_id]],
                {'fields': ['name', 'interest_amount', 'interest_per_kg']}
            )[0]
            
            old_interest = order.get('interest_amount', 0)
            old_interest_per_kg = order.get('interest_per_kg', 0)
            
            print(f"  📊 Lãi vay hiện tại: {old_interest:,.0f} VNĐ ({old_interest_per_kg:,.2f} VNĐ/kg)")
            
            # Chạy lại calculate_interest
            print(f"  🔄 Đang tính lại lãi vay...")
            try:
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
                
                print(f"  ✅ Lãi vay mới: {new_interest:,.0f} VNĐ ({new_interest_per_kg:,.2f} VNĐ/kg)")
                if old_interest != new_interest:
                    print(f"  📈 Thay đổi: {new_interest - old_interest:,.0f} VNĐ")
                else:
                    print(f"  ⚠️ Không thay đổi (vẫn = 0)")
                
            except Exception as e:
                print(f"  ❌ Lỗi: {e}")
                import traceback
                traceback.print_exc()
            
            print()
        
        print("=" * 80)
        print("HOÀN THÀNH")
        print("=" * 80)
        
        return 0
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

