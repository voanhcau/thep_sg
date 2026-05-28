#!/usr/bin/env python3
"""
Script kiểm tra tính lãi vay cho tất cả đơn hàng (bao gồm lãi vay đơn mua)
và so sánh với logic Google Sheets

Hỗ trợ 3 môi trường: prod, staging, local
Usage:
    python check_all_orders_with_po_interest.py          # Dùng default (PROD)
    python check_all_orders_with_po_interest.py prod     # Dùng PROD
    python check_all_orders_with_po_interest.py staging  # Dùng STAGING
    python check_all_orders_with_po_interest.py local    # Dùng LOCAL
"""
import os
import sys
import xmlrpc.client
from datetime import datetime
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False

def parse_date(date_str):
    """Parse date string to date object"""
    if date_str is None:
        return None
    if isinstance(date_str, str):
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d/%m/%Y', '%d-%m-%Y', '%m/%d/%Y']:
            try:
                return datetime.strptime(date_str, fmt).date()
            except:
                continue
        raise ValueError(f"Không thể parse ngày: {date_str}")
    if hasattr(date_str, 'date'):
        return date_str.date()
    return date_str

def calculate_interest_so_manual(order_data, payments_list, start_date, lending_rate):
    """Tính lãi vay đơn bán thủ công theo công thức Google Sheets (Cách 2)"""
    start_date = parse_date(start_date) if isinstance(start_date, str) else start_date
    
    total_interest = 0
    remaining_amount = order_data['amount_untaxed']
    last_payment_date = start_date
    
    for idx, payment in enumerate(payments_list, 1):
        payment_date = parse_date(payment['date'])
        payment_amount = payment['amount'] / 1.1  # Trước VAT
        
        # Bỏ qua thanh toán trước ngày bắt đầu
        if payment_date < start_date:
            remaining_amount = remaining_amount - payment_amount
            if remaining_amount < 0:
                remaining_amount = 0
            continue
        
        # Tính số ngày
        days_diff = (payment_date - last_payment_date).days
        if days_diff < 0:
            days_diff = 0
        
        if remaining_amount < 0:
            remaining_amount = 0
        
        # Tính lãi vay
        interest = days_diff * remaining_amount * lending_rate
        if interest < 0:
            interest = 0
        
        total_interest += interest
        remaining_amount = remaining_amount - payment_amount
        last_payment_date = payment_date
        
        if remaining_amount < 0:
            remaining_amount = 0
    
    if total_interest < 0:
        total_interest = 0
    
    return total_interest

def calculate_interest_po_manual(po_amount_untaxed, po_lending_days, lending_rate):
    """Tính lãi vay đơn mua thủ công theo công thức Google Sheets"""
    # Công thức: lending_rate * remaining_amount_po * lending_days
    # remaining_amount_po = giá trị PO (trước VAT)
    if not po_lending_days or po_lending_days <= 0:
        return 0
    return lending_rate * po_amount_untaxed * po_lending_days

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
        print("KIỂM TRA TÍNH LÃI VAY CHO TẤT CẢ ĐƠN HÀNG (BAO GỒM LÃI VAY ĐƠN MUA)")
        print("=" * 80)
        print()

        # Tìm tất cả đơn hàng có payment_term_id và lending_rate > 0
        print("🔍 Đang tìm các đơn hàng...")
        
        all_order_ids = models.execute_kw(
            DB, uid, PASSWORD,
            'sale.order', 'search',
            [[('payment_term_id', '!=', False)]],
            {'limit': 0}
        )

        print(f"📊 Tìm thấy {len(all_order_ids)} đơn hàng có điều khoản TT\n")
        print("🔄 Đang kiểm tra...\n")

        issues = []
        correct = []
        no_invoice = []
        no_payments = []
        no_start_date = []
        
        batch_size = 100
        checked_count = 0
        
        for i in range(0, len(all_order_ids), batch_size):
            batch_ids = all_order_ids[i:i+batch_size]
            orders = models.execute_kw(
                DB, uid, PASSWORD,
                'sale.order', 'read',
                [batch_ids],
                {
                    'fields': [
                        'name', 'payment_term_id', 'amount_untaxed', 'total_product_qty',
                        'received_date', 'interest_amount', 'interest_per_kg',
                        'invoice_ids', 'auto_purchase_order_id'
                    ]
                }
            )
            
            for order_data in orders:
                checked_count += 1
                order_name = order_data['name']
                order_id = order_data['id']
                current_interest = order_data.get('interest_amount', 0)
                current_interest_per_kg = order_data.get('interest_per_kg', 0)
                
                # Kiểm tra payment_term có lending_rate > 0
                if not order_data['payment_term_id']:
                    continue
                
                payment_term = models.execute_kw(
                    DB, uid, PASSWORD,
                    'account.payment.term', 'read',
                    [[order_data['payment_term_id'][0]]],
                    {'fields': ['name', 'lending_rate']}
                )
                if not payment_term or payment_term[0].get('lending_rate', 0) <= 0:
                    continue
                
                lending_rate = payment_term[0]['lending_rate'] / 100
                
                # Lấy thông tin invoice và payments
                if not order_data.get('invoice_ids'):
                    no_invoice.append(order_name)
                    continue
                
                invoices = models.execute_kw(
                    DB, uid, PASSWORD,
                    'account.move', 'search_read',
                    [[('id', 'in', order_data['invoice_ids'])]],
                    {'fields': ['name', 'state', 'invoice_date', 'invoice_payments_widget']}
                )
                
                all_payments = []
                for inv in invoices:
                    if inv['state'] != 'posted':
                        continue
                    payment_info = inv.get('invoice_payments_widget')
                    if payment_info and isinstance(payment_info, dict) and payment_info.get('content'):
                        for payment in payment_info['content']:
                            all_payments.append(payment)
                
                if not all_payments:
                    no_payments.append(order_name)
                    continue
                
                # Sắp xếp payments theo ngày
                all_payments = sorted(all_payments, key=lambda x: x.get('date') or '')
                
                # Xác định ngày bắt đầu
                received_date = order_data.get('received_date')
                if received_date:
                    received_date = parse_date(received_date)
                
                invoice_dates = [parse_date(inv.get('invoice_date')) for inv in invoices if inv.get('invoice_date')]
                invoice_date = min(invoice_dates) if invoice_dates else None
                
                start_date = received_date
                if not start_date and invoice_date:
                    start_date = invoice_date
                elif invoice_date and received_date and invoice_date < received_date:
                    start_date = invoice_date
                
                if not start_date:
                    no_start_date.append(order_name)
                    continue
                
                # Tính lãi vay đơn bán thủ công
                manual_interest_so = calculate_interest_so_manual(order_data, all_payments, start_date, lending_rate)
                
                # Tính lãi vay đơn mua thủ công
                manual_interest_po = 0
                if order_data.get('auto_purchase_order_id'):
                    po_id = order_data['auto_purchase_order_id'][0]
                    po = models.execute_kw(
                        DB, uid, PASSWORD,
                        'purchase.order', 'read',
                        [[po_id]],
                        {'fields': ['amount_untaxed', 'payment_term_id']}
                    )[0]
                    
                    if po.get('payment_term_id'):
                        po_pt = models.execute_kw(
                            DB, uid, PASSWORD,
                            'account.payment.term', 'read',
                            [[po['payment_term_id'][0]]],
                            {'fields': ['lending_days']}
                        )[0]
                        po_lending_days = po_pt.get('lending_days', 0)
                        if po_lending_days and po_lending_days > 0:
                            manual_interest_po = calculate_interest_po_manual(
                                po['amount_untaxed'],
                                po_lending_days,
                                lending_rate
                            )
                
                # Tính lãi vay cuối cùng (SO - PO)
                manual_final_interest = manual_interest_so - manual_interest_po
                manual_interest_per_kg = manual_final_interest / order_data['total_product_qty'] if order_data['total_product_qty'] > 0 else 0
                
                # So sánh
                diff_interest = abs(current_interest - manual_final_interest)
                diff_per_kg = abs(current_interest_per_kg - manual_interest_per_kg)
                
                if diff_interest > 0.01 or diff_per_kg > 0.01:
                    issues.append({
                        'order': order_name,
                        'system_interest': current_interest,
                        'system_interest_per_kg': current_interest_per_kg,
                        'manual_interest_so': manual_interest_so,
                        'manual_interest_po': manual_interest_po,
                        'manual_final_interest': manual_final_interest,
                        'manual_interest_per_kg': manual_interest_per_kg,
                        'diff_interest': diff_interest,
                        'diff_per_kg': diff_per_kg
                    })
                else:
                    correct.append(order_name)
                
                if checked_count % 500 == 0:
                    print(f"  Đã kiểm tra {checked_count}/{len(all_order_ids)} đơn hàng...")

        print("\n" + "=" * 80)
        print("KẾT QUẢ KIỂM TRA:")
        print("=" * 80)
        print(f"  ✅ Đúng: {len(correct)}/{checked_count}")
        print(f"  ❌ Sai: {len(issues)}/{checked_count}")
        print(f"  ⚠️ Không có hoá đơn: {len(no_invoice)}")
        print(f"  ⚠️ Không có thanh toán: {len(no_payments)}")
        print(f"  ⚠️ Không có ngày bắt đầu: {len(no_start_date)}")
        
        if issues:
            print(f"\n📋 CÁC ĐƠN HÀNG CÓ SỰ KHÁC BIỆT (hiển thị 20 đơn đầu tiên):")
            for issue in issues[:20]:
                print(f"  - {issue['order']}:")
                print(f"    Hệ thống: {issue['system_interest']:,.0f} VNĐ ({issue['system_interest_per_kg']:,.2f} VNĐ/kg)")
                print(f"    Thủ công: {issue['manual_final_interest']:,.0f} VNĐ ({issue['manual_interest_per_kg']:,.2f} VNĐ/kg)")
                print(f"    (SO: {issue['manual_interest_so']:,.0f}, PO: {issue['manual_interest_po']:,.0f})")
                print(f"    Chênh lệch: {issue['diff_interest']:,.0f} VNĐ ({issue['diff_per_kg']:,.2f} VNĐ/kg)")
        
        return 0
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())



