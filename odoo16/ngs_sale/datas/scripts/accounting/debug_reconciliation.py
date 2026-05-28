#!/usr/bin/env python3
import sys
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False
# -*- coding: utf-8 -*-
"""
Script debug tính toán đối chiếu công nợ cho partner ID 957
"""

import os
import xmlrpc.client
import logging
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Thông tin kết nối
# Get connection với hỗ trợ 3 môi trường
env_type = sys.argv[1] if len(sys.argv) > 1 else None

if USE_ENV_LOADER:
    try:
        url, db, username, password, models, uid = setup_odoo_connection(env_type)
        print(f"✅ Connected to {env_type or 'default'} environment")
    except Exception as e:
        print(f"❌ Error loading environment: {e}")
        sys.exit(1)
else:
    # Fallback: dùng environment variables trực tiếp
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USERNAME")
    password = os.getenv("ODOO_PASSWORD")
    
    if not all([url, db, username, password]):
        print("❌ Missing environment variables. Please:")
        print("   1. Run: source load_env.sh [prod|staging|local]")
        print("   2. Or set: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD")
        sys.exit(1)
    
    import xmlrpc.client
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        print("❌ Authentication failed")
        sys.exit(1)
logging.info("Authentication successful")

def debug_reconciliation():
    """Debug tính toán đối chiếu công nợ"""
    partner_id = 957
    date_from = '2025-03-01'
    date_to = '2025-03-31'
    company_id = 1
    
    logging.info(f"\n{'='*60}")
    logging.info(f"DEBUG ĐỐI CHIẾU CÔNG NỢ")
    logging.info(f"{'='*60}")
    logging.info(f"Partner ID: {partner_id}")
    logging.info(f"Từ ngày: {date_from}")
    logging.info(f"Đến ngày: {date_to}")
    
    # Đọc thông tin partner
    partner = models.execute_kw(
        db, uid, password,
        'res.partner', 'read',
        [partner_id],
        {'fields': ['name', 'is_company']}
    )[0]
    logging.info(f"Partner: {partner['name']}")
    
    # Tìm các move lines trong kỳ
    domain = [
        ('partner_id', '=', partner_id),
        ('company_id', '=', company_id),
        ('date', '>=', date_from),
        ('date', '<=', date_to),
        ('parent_state', '=', 'posted'),
    ]
    
    move_lines = models.execute_kw(
        db, uid, password,
        'account.move.line', 'search_read',
        [domain],
        {'fields': [
            'id', 'date', 'move_id', 'account_id', 'account_type', 
            'debit', 'credit', 'balance', 'reconciled', 
            'move_name', 'ref'
        ]}
    )
    
    logging.info(f"\nTổng số move lines: {len(move_lines)}")
    
    # Filter chỉ lấy receivable/payable
    receivable_payable_lines = [
        line for line in move_lines 
        if line.get('account_type') in ['asset_receivable', 'liability_payable']
    ]
    
    logging.info(f"Số move lines công nợ (receivable/payable): {len(receivable_payable_lines)}")
    
    # Tính tổng
    total_debit = sum(line['debit'] for line in receivable_payable_lines)
    total_credit = sum(line['credit'] for line in receivable_payable_lines)
    
    logging.info(f"\n{'='*60}")
    logging.info(f"KẾT QUẢ TÍNH TOÁN:")
    logging.info(f"{'='*60}")
    logging.info(f"Tổng phát sinh nợ (debit): {total_debit:,.0f}")
    logging.info(f"Tổng phát sinh có (credit): {total_credit:,.0f}")
    
    # Chi tiết các move lines
    logging.info(f"\n{'='*60}")
    logging.info(f"CHI TIẾT CÁC MOVE LINES CÔNG NỢ:")
    logging.info(f"{'='*60}")
    for line in receivable_payable_lines[:20]:  # Chỉ hiển thị 20 dòng đầu
        move_id = line.get('move_id', [None])[0] if line.get('move_id') else None
        move_info = {}
        if move_id:
            move_info = models.execute_kw(
                db, uid, password,
                'account.move', 'read',
                [move_id],
                {'fields': ['move_type', 'payment_state', 'state']}
            )[0]
        
        logging.info(
            f"ID: {line['id']}, Date: {line['date']}, "
            f"Account: {line['account_id'][1] if line['account_id'] else 'N/A'}, "
            f"Type: {line.get('account_type', 'N/A')}, "
            f"Debit: {line['debit']:,.0f}, Credit: {line['credit']:,.0f}, "
            f"Move: {line.get('move_name', 'N/A')}, "
            f"Move Type: {move_info.get('move_type', 'N/A')}, "
            f"Payment State: {move_info.get('payment_state', 'N/A')}, "
            f"Reconciled: {line.get('reconciled', False)}"
        )
    
    if len(receivable_payable_lines) > 20:
        logging.info(f"... và {len(receivable_payable_lines) - 20} dòng khác")
    
    # Kiểm tra xem có move lines nào bị reconcile không
    reconciled_lines = [line for line in receivable_payable_lines if line.get('reconciled', False)]
    logging.info(f"\nSố move lines đã reconcile: {len(reconciled_lines)}")
    
    # Tính lại nếu loại trừ reconciled
    unreconciled_lines = [line for line in receivable_payable_lines if not line.get('reconciled', False)]
    total_debit_unreconciled = sum(line['debit'] for line in unreconciled_lines)
    total_credit_unreconciled = sum(line['credit'] for line in unreconciled_lines)
    
    logging.info(f"\nNếu loại trừ reconciled:")
    logging.info(f"Tổng phát sinh nợ (debit): {total_debit_unreconciled:,.0f}")
    logging.info(f"Tổng phát sinh có (credit): {total_credit_unreconciled:,.0f}")
    
    # Kiểm tra dư nợ đầu kỳ
    logging.info(f"\n{'='*60}")
    logging.info(f"KIỂM TRA DƯ NỢ ĐẦU KỲ:")
    logging.info(f"{'='*60}")
    
    # Tìm move lines trước kỳ
    domain_before = [
        ('partner_id', '=', partner_id),
        ('company_id', '=', company_id),
        ('date', '<', date_from),
        ('parent_state', '=', 'posted'),
    ]
    
    move_lines_before = models.execute_kw(
        db, uid, password,
        'account.move.line', 'search_read',
        [domain_before],
        {'fields': ['account_type', 'debit', 'credit', 'balance']}
    )
    
    receivable_payable_before = [
        line for line in move_lines_before 
        if line.get('account_type') in ['asset_receivable', 'liability_payable']
    ]
    
    initial_balance = sum(line['balance'] for line in receivable_payable_before)
    logging.info(f"Dư nợ đầu kỳ (tính từ balance): {initial_balance:,.0f}")
    
    # Tính dư cuối kỳ
    ending_balance = initial_balance + total_debit - total_credit
    logging.info(f"\nDư nợ cuối kỳ: {initial_balance:,.0f} + {total_debit:,.0f} - {total_credit:,.0f} = {ending_balance:,.0f}")
    
    logging.info(f"\n{'='*60}")
    logging.info(f"KẾT QUẢ:")
    logging.info(f"Dư đầu kỳ: {initial_balance:,.0f}")
    logging.info(f"Phát sinh nợ: {total_debit:,.0f}")
    logging.info(f"Phát sinh có: {total_credit:,.0f}")
    logging.info(f"Dư cuối kỳ: {ending_balance:,.0f}")
    logging.info(f"{'='*60}")

if __name__ == "__main__":
    debug_reconciliation()

