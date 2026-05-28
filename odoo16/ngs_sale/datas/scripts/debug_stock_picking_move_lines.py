#!/usr/bin/env python3
"""
Script debug stock.picking move_lines để kiểm tra all_move_lines và sorted_lines

Hỗ trợ 3 môi trường: prod, staging, local
Usage:
    python debug_stock_picking_move_lines.py          # Dùng default (PROD)
    python debug_stock_picking_move_lines.py prod     # Dùng PROD
    python debug_stock_picking_move_lines.py staging  # Dùng STAGING
    python debug_stock_picking_move_lines.py local    # Dùng LOCAL
"""
import os
import sys
import xmlrpc.client
import json
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

        picking_id = 17929
        print("=" * 80)
        print(f"KIỂM TRA STOCK.PICKING ID={picking_id}")
        print("=" * 80)
        print()

        # 1. Đọc stock.picking
        picking = models.execute_kw(
            DB, uid, PASSWORD,
            'stock.picking', 'read',
            [[picking_id]],
            {'fields': ['name', 'move_ids_without_package', 'move_line_ids_without_package', 'move_line_ids', 'state']}
        )

        if not picking:
            print(f"❌ Không tìm thấy stock.picking id={picking_id}")
            return 1

        picking = picking[0]
        print(f"📦 Stock Picking: {picking['name']}")
        print(f"   State: {picking.get('state', 'N/A')}")
        print(f"   move_ids_without_package: {picking.get('move_ids_without_package', [])}")
        print(f"   move_line_ids_without_package: {picking.get('move_line_ids_without_package', [])}")
        print(f"   move_line_ids (tất cả): {picking.get('move_line_ids', [])}")
        print()

        # 2. Đọc move_line_ids_without_package
        move_line_ids = picking.get('move_line_ids_without_package', [])
        if not move_line_ids:
            print("⚠️  Không có move_line_ids_without_package")
            print("   Thử dùng move_line_ids (tất cả)...")
            move_line_ids = picking.get('move_line_ids', [])
            if not move_line_ids:
                print("❌ Không có move_line_ids nào")
                return 1
            print(f"   Tìm thấy {len(move_line_ids)} move_line_ids (có thể trong package)")

        print(f"📋 Tìm thấy {len(move_line_ids)} move lines")
        print()

        move_lines = models.execute_kw(
            DB, uid, PASSWORD,
            'stock.move.line', 'read',
            [move_line_ids],
            {
                'fields': [
                    'id', 'product_id', 'qty_done', 'quantity_another1',
                    'move_id', 'move_id.sale_line_id', 'move_id.sale_line_id.sequence',
                    'move_id.sale_line_id.quantity_another1'
                ]
            }
        )

        print("=" * 80)
        print("ALL_MOVE_LINES (move_line_ids_without_package):")
        print("=" * 80)
        for idx, ml in enumerate(move_lines, 1):
            product_name = ml.get('product_id', ['', ''])[1] if ml.get('product_id') else 'N/A'
            move_id = ml.get('move_id', [None, ''])[0] if ml.get('move_id') else None
            sale_line_id = None
            sale_line_sequence = None
            sale_line_qty_another1 = None
            
            if move_id:
                # Đọc move để lấy sale_line_id
                move = models.execute_kw(
                    DB, uid, PASSWORD,
                    'stock.move', 'read',
                    [[move_id]],
                    {'fields': ['sale_line_id', 'sale_line_id.sequence', 'sale_line_id.quantity_another1']}
                )
                if move and move[0].get('sale_line_id'):
                    sale_line_id = move[0]['sale_line_id'][0]
                    sale_line_sequence = move[0].get('sale_line_id.sequence', 0)
                    sale_line_qty_another1 = move[0].get('sale_line_id.quantity_another1', 0)

            print(f"\n[{idx}] Move Line ID: {ml['id']}")
            print(f"    Product: {product_name}")
            print(f"    qty_done: {ml.get('qty_done', 0)}")
            print(f"    quantity_another1 (trên move_line): {ml.get('quantity_another1', 0)}")
            print(f"    move_id: {move_id}")
            print(f"    sale_line_id: {sale_line_id}")
            print(f"    sale_line.sequence: {sale_line_sequence}")
            print(f"    sale_line.quantity_another1: {sale_line_qty_another1}")

        print()
        print("=" * 80)
        print("SORTED_LINES (theo sale_line.sequence, fallback move_line.id):")
        print("=" * 80)
        
        # Đọc tất cả move_ids để lấy sale_line_id và sequence
        move_ids = list(set([ml.get('move_id', [None])[0] for ml in move_lines if ml.get('move_id')]))
        moves = {}
        if move_ids:
            moves_data = models.execute_kw(
                DB, uid, PASSWORD,
                'stock.move', 'read',
                [move_ids],
                {'fields': ['id', 'sale_line_id', 'sale_line_id.sequence']}
            )
            for move in moves_data:
                moves[move['id']] = move
        
        # Tạo danh sách với sequence để sắp xếp
        move_line_data = []
        for ml in move_lines:
            move_id = ml.get('move_id', [None])[0] if ml.get('move_id') else None
            sale_line_sequence = 0
            if move_id and move_id in moves:
                move = moves[move_id]
                if move.get('sale_line_id'):
                    sale_line_sequence = move.get('sale_line_id.sequence', 0)
            
            move_line_data.append({
                'ml': ml,
                'sequence': sale_line_sequence,
                'id': ml['id']
            })
        
        sorted_data = sorted(move_line_data, key=lambda x: (x['sequence'], x['id']))
        
        for idx, data in enumerate(sorted_data, 1):
            ml = data['ml']
            product_name = ml.get('product_id', ['', ''])[1] if ml.get('product_id') else 'N/A'
            move_id = ml.get('move_id', [None])[0] if ml.get('move_id') else None
            sale_line_qty = None
            if move_id and move_id in moves:
                move = moves[move_id]
                if move.get('sale_line_id'):
                    sale_line = models.execute_kw(
                        DB, uid, PASSWORD,
                        'sale.order.line', 'read',
                        [[move['sale_line_id'][0]]],
                        {'fields': ['quantity_another1']}
                    )
                    if sale_line:
                        sale_line_qty = sale_line[0].get('quantity_another1', 0)
            
            print(f"\n[{idx}] Move Line ID: {ml['id']} (sale_line.sequence: {data['sequence']})")
            print(f"    Product: {product_name}")
            print(f"    quantity_another1 (trên move_line): {ml.get('quantity_another1', 0)}")
            print(f"    quantity_another1 (trên sale_line): {sale_line_qty}")

        print()
        print("=" * 80)
        print("KẾT LUẬN:")
        print("=" * 80)
        print(f"- Tổng số move_lines: {len(move_lines)}")
        move_lines_with_qty = [ml for ml in move_lines if ml.get('quantity_another1', 0) > 0]
        print(f"- Move_lines có quantity_another1 > 0: {len(move_lines_with_qty)}")
        move_lines_without_qty = [ml for ml in move_lines if not ml.get('quantity_another1', 0)]
        print(f"- Move_lines KHÔNG có quantity_another1: {len(move_lines_without_qty)}")
        
        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
