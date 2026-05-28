#!/usr/bin/env python3
"""
Script reset lãi vay về 0 cho các đơn bán hàng (SO) có hoá đơn khách hàng
đã / chưa vào sổ nhưng CHƯA THANH TOÁN ĐỦ.

Logic:
- Làm việc trên hoá đơn khách hàng (`account.move`, `move_type = 'out_invoice'`)
- Chọn tất cả hoá đơn:
    + state != 'cancel'
    + amount_residual > 0  (chưa thanh toán đủ: chưa thanh toán hoặc thanh toán một phần)
- Từ hoá đơn → tìm SO liên quan qua:
    move.line_ids.sale_line_ids.order_id
- Với mỗi SO tìm được:
    + Nếu `interest_amount != 0` hoặc `interest_per_kg != 0` thì reset:
        - `interest_amount = 0`
        - `interest_per_kg = 0`
        - `price_landing = 0` trên tất cả dòng `sale.order.line`
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
        print("RESET LÃI VAY VỀ 0 CHO CÁC ĐƠN BÁN HÀNG CÓ HOÁ ĐƠN KHÁCH HÀNG CHƯA THANH TOÁN ĐỦ")
        print("=" * 80)
        print()

        # 1. Tìm tất cả hoá đơn khách hàng chưa thanh toán đủ
        print("🔍 Đang tìm các hoá đơn khách hàng (account.move) chưa thanh toán đủ...")

        invoice_domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '!=', 'cancel'),
            ('amount_residual', '>', 0),
        ]

        invoice_ids = models.execute_kw(
            DB, uid, PASSWORD,
            'account.move', 'search',
            [invoice_domain],
            {'limit': 0}
        )

        print(f"📊 Tìm thấy {len(invoice_ids)} hoá đơn khách hàng chưa thanh toán đủ\n")

        if not invoice_ids:
            print("✅ Không có hoá đơn nào chưa thanh toán đủ → Không có SO cần reset")
            return 0

        # 2. Từ hoá đơn → lấy SO qua line_ids.sale_line_ids.order_id
        print("🔍 Đang map hoá đơn → đơn bán hàng (SO)...\n")

        orders_map = {}  # order_id -> {'name', 'interest_amount', 'interest_per_kg'}
        batch_size = 100

        for i in range(0, len(invoice_ids), batch_size):
            batch_invoice_ids = invoice_ids[i:i + batch_size]

            invoices = models.execute_kw(
                DB, uid, PASSWORD,
                'account.move', 'read',
                [batch_invoice_ids],
                {
                    'fields': ['name', 'line_ids', 'amount_total', 'amount_residual']
                }
            )

            all_line_ids = set()
            for inv in invoices:
                for line_id in inv.get('line_ids', []):
                    all_line_ids.add(line_id)

            if not all_line_ids:
                continue

            move_lines = models.execute_kw(
                DB, uid, PASSWORD,
                'account.move.line', 'search_read',
                [[('id', 'in', list(all_line_ids))]],
                {'fields': ['sale_line_ids']}
            )

            all_sale_line_ids = set()
            for ml in move_lines:
                for sl_id in ml.get('sale_line_ids') or []:
                    all_sale_line_ids.add(sl_id)

            if not all_sale_line_ids:
                continue

            sale_lines = models.execute_kw(
                DB, uid, PASSWORD,
                'sale.order.line', 'search_read',
                [[('id', 'in', list(all_sale_line_ids))]],
                {'fields': ['order_id']}
            )

            order_ids_in_batch = set()
            for sl in sale_lines:
                order_field = sl.get('order_id')
                if isinstance(order_field, list) and len(order_field) >= 1:
                    order_ids_in_batch.add(order_field[0])

            if not order_ids_in_batch:
                continue

            orders = models.execute_kw(
                DB, uid, PASSWORD,
                'sale.order', 'read',
                [list(order_ids_in_batch)],
                {'fields': ['name', 'interest_amount', 'interest_per_kg']}
            )

            for order in orders:
                order_id = order['id']
                if order_id not in orders_map:
                    orders_map[order_id] = {
                        'name': order['name'],
                        'interest_amount': order.get('interest_amount', 0),
                        'interest_per_kg': order.get('interest_per_kg', 0),
                    }

        # 3. Lọc ra các SO thực sự cần reset (lãi vay khác 0)
        orders_to_reset = []
        for order_id, data in orders_map.items():
            if data['interest_amount'] != 0 or data['interest_per_kg'] != 0:
                orders_to_reset.append({
                    'id': order_id,
                    'name': data['name'],
                    'interest_amount': data['interest_amount'],
                    'interest_per_kg': data['interest_per_kg'],
                })

        print(f"📊 Tìm thấy {len(orders_to_reset)} đơn bán hàng cần reset lãi vay\n")
        
        if not orders_to_reset:
            print("✅ Không có đơn hàng nào cần reset")
            return 0
        
        print("🔄 Bắt đầu reset lãi vay...\n")
        
        success_count = 0
        error_count = 0
        
        for idx, order_data in enumerate(orders_to_reset, 1):
            order_id = order_data['id']
            order_name = order_data['name']
            old_interest = order_data['interest_amount']
            old_interest_per_kg = order_data['interest_per_kg']
            
            try:
                # Reset interest_amount và interest_per_kg
                models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'write',
                    [[order_id], {
                        'interest_amount': 0,
                        'interest_per_kg': 0,
                    }],
                )

                # Reset price_landing cho tất cả các line
                order = models.execute_kw(
                    DB, uid, PASSWORD,
                    'sale.order', 'read',
                    [[order_id]],
                    {'fields': ['order_line']}
                )[0]

                if order.get('order_line'):
                    for line_id in order['order_line']:
                        models.execute_kw(
                            DB, uid, PASSWORD,
                            'sale.order.line', 'write',
                            [[line_id], {'price_landing': 0}],
                        )
                
                success_count += 1
                if idx <= 20:  # Chỉ hiển thị 20 đơn đầu tiên
                    print(f"[{idx}/{len(orders_to_reset)}] {order_name}: {old_interest:,.0f} VNĐ ({old_interest_per_kg:,.2f} VNĐ/kg) → 0 VNĐ (0.00 VNĐ/kg)")
                elif idx % 100 == 0:
                    print(f"[{idx}/{len(orders_to_reset)}] Đã xử lý {idx} đơn hàng...")
                
            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    print(f"[{idx}/{len(orders_to_reset)}] ❌ Lỗi {order_name}: {e}")
        
        print("\n" + "=" * 80)
        print("KẾT QUẢ:")
        print(f"  ✅ Thành công: {success_count}/{len(orders_to_reset)}")
        print(f"  ❌ Lỗi: {error_count}/{len(orders_to_reset)}")
        print("=" * 80)
        
        return 0
    except Exception as e:
        print(f"❌ Lỗi tổng quát: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())



