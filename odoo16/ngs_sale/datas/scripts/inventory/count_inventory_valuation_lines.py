# -*- coding: utf-8 -*-
"""
Script đếm trực tiếp từ Account Move Lines theo điều kiện:
- Sổ nhật ký = "inventory valuation"
- Trạng thái = "Chưa vào sổ" (Draft)
- Database: 16.thepnamsaigon.01.10.2025
"""
import xmlrpc.client as xmlrpclib
import time
import logging
import sys
import codecs

# Set UTF-8 encoding for stdout
sys.stdout = codecs.getwriter('utf-8')(sys.stdout)

__logger = logging.getLogger(__name__)

# Cấu hình kết nối
import os
sys.path.append('/Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/login_configs')
from login_16_thepnamsaigon import uid, password, db, models

def count_inventory_valuation_lines():
    """Đếm trực tiếp từ Account Move Lines"""
    print("==========================================")
    print("COUNT INVENTORY VALUATION LINES")
    print("==========================================")
    print("Database:", db)
    print("User ID:", uid)
    print("Time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # Tìm journal có tên "inventory valuation"
    print("Tim journal 'inventory valuation'...")
    all_journals = models.execute_kw(db, uid, password, 
        "account.journal", "search_read",
        [[]],
        {'fields': ['id', 'name', 'code', 'type']}
    )
    
    # Lọc journals có tên chứa "inventory valuation"
    journal_ids = []
    for journal in all_journals:
        if 'inventory valuation' in journal['name'].lower():
            journal_ids.append(journal['id'])
            print("  - %s (Code: %s, Type: %s)" % (
                journal['name'], 
                journal['code'],
                journal['type']
            ))
    
    if not journal_ids:
        print("Khong tim thay journal 'inventory valuation'!")
        return
    
    print("Tim thay %d journal(s):" % len(journal_ids))
    print()
    
    # Đếm trực tiếp từ Account Move Lines
    print("Dem truc tiep tu Account Move Lines...")
    print("Dieu kien:")
    print("  - Journal: inventory valuation")
    print("  - Move State: draft (Chua vao so)")
    print()
    
    # Domain để lọc account move lines
    line_domain = [
        ('journal_id', 'in', journal_ids),
        ('move_id.state', '=', 'draft')
    ]
    
    # Đếm số lượng account move lines
    line_count = models.execute_kw(db, uid, password, 
        "account.move.line", "search_count",
        [line_domain]
    )
    
    print("KET QUA DEM:")
    print("  Tong so Account Move Lines (dong but toan):", line_count)
    print()
    
    # Lấy thông tin chi tiết một số lines
    print("CHI TIET ACCOUNT MOVE LINES (10 dong dau tien):")
    print("-" * 120)
    print("%-8s %-15s %-20s %-15s %-15s %-15s %-15s" % (
        "ID", "Account", "Journal", "Debit", "Credit", "Balance", "Date"
    ))
    print("-" * 120)
    
    # Lấy thông tin chi tiết
    move_lines = models.execute_kw(db, uid, password, 
        "account.move.line", "search_read",
        [line_domain],
        {'fields': [
            'id', 'name', 'ref', 'debit', 'credit', 'balance',
            'account_id', 'journal_id', 'move_id',
            'date', 'create_date', 'write_date'
        ]},
        {'limit': 10}
    )
    
    total_debit = 0
    total_credit = 0
    
    for line in move_lines:
        account_name = line.get('account_id', [False, 'N/A'])[1] if line.get('account_id') else 'N/A'
        journal_name = line.get('journal_id', [False, 'N/A'])[1] if line.get('journal_id') else 'N/A'
        
        debit = line.get('debit', 0)
        credit = line.get('credit', 0)
        balance = line.get('balance', 0)
        
        total_debit += debit
        total_credit += credit
        
        print("%-8s %-15s %-20s %-15.2f %-15.2f %-15.2f %-15s" % (
            line['id'],
            account_name[:14],
            journal_name[:19],
            debit,
            credit,
            balance,
            line.get('date', 'N/A')
        ))
    
    print("-" * 120)
    print("%-8s %-15s %-20s %-15.2f %-15.2f %-15s %-15s" % (
        "TOTAL", "", "", total_debit, total_credit, "", ""
    ))
    print("-" * 120)
    
    # Thống kê theo account
    print("\nTHONG KE THEO ACCOUNT (top 10):")
    account_stats = {}
    for line in move_lines:
        account_id = line.get('account_id', [False, 'N/A'])[0] if line.get('account_id') else False
        account_name = line.get('account_id', [False, 'N/A'])[1] if line.get('account_id') else 'N/A'
        
        if account_id not in account_stats:
            account_stats[account_id] = {
                'name': account_name,
                'count': 0,
                'total_debit': 0,
                'total_credit': 0
            }
        
        account_stats[account_id]['count'] += 1
        account_stats[account_id]['total_debit'] += line.get('debit', 0)
        account_stats[account_id]['total_credit'] += line.get('credit', 0)
    
    # Sắp xếp theo số lượng lines
    sorted_accounts = sorted(account_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    
    for account_id, stats in sorted_accounts[:10]:
        print("  %s: %d lines, Debit: %.2f, Credit: %.2f" % (
            stats['name'][:50],
            stats['count'],
            stats['total_debit'],
            stats['total_credit']
        ))
    
    print("\n" + "="*60)
    print("TONG KET:")
    print("="*60)
    print("So luong dong but toan (Account Move Lines): %d" % line_count)
    print("Tong Debit: %.2f" % total_debit)
    print("Tong Credit: %.2f" % total_credit)
    print("="*60)

def main():
    """Hàm chính"""
    start_time = time.time()
    print("==========================================")
    print("SCRIPT COUNT INVENTORY VALUATION LINES")
    print("==========================================")
    print("Thoi gian bat dau:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Database:", db)
    print()
    
    try:
        count_inventory_valuation_lines()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("\n==========================================")
        print("HOAN THANH")
        print("==========================================")
        print("Thoi gian ket thuc:", time.strftime("%Y-%m-%d %H:%M:%S"))
        print("Thoi gian xu ly: %.2f giay" % duration)
        
    except Exception as e:
        print("LOI CHUNG: %s" % str(e))
        __logger.error("Script error: %s" % str(e))

if __name__ == '__main__':
    main()


