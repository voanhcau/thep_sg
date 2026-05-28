# -*- coding: utf-8 -*-
"""
Script chuyển các bút toán Inventory Valuation từ "Dự thảo" thành "Vào sổ"
Điều kiện lọc:
- Sổ nhật ký = "inventory valuation"
- Trạng thái hiện tại = "Chưa vào sổ" (Draft)
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

# Cấu hình kết nối - import từ login_16_thepnamsaigon
import os
sys.path.append('/Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/login_configs')
from login_prod import uid, password, db, models

def post_inventory_valuation_to_draft():
    """Chuyển các bút toán Inventory Valuation từ Draft sang Posted"""
    print("==========================================")
    print("POST INVENTORY VALUATION TO POSTED")
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
    
    # Tìm các account moves có journal inventory valuation và state = draft
    print("Tim cac Account Moves...")
    print("Dieu kien:")
    print("  - Journal: inventory valuation")
    print("  - State: draft (Chua vao so)")
    print()
    
    # Domain để lọc account moves - tìm moves ở trạng thái draft
    domain = [
        ('journal_id', 'in', journal_ids),
        ('state', '=', 'draft')
    ]
    
    # Lấy thông tin account moves
    account_moves = models.execute_kw(db, uid, password, 
        "account.move", "search_read",
        [domain],
        {'fields': [
            'id', 'name', 'ref', 'date', 'state', 'journal_id',
            'amount_total', 'amount_untaxed', 'amount_tax'
        ]}
    )
    
    if not account_moves:
        print("Khong tim thay Account Move nao thoa man dieu kien!")
        print("Tat ca cac moves da o trang thai posted roi.")
        return
    
    print("THONG KE TRUOC KHI CAP NHAT:")
    print("  Tong so Account Moves:", len(account_moves))
    print()
    
    # Hiển thị một số thông tin trước khi cập nhật
    print("CHI TIET ACCOUNT MOVES (5 dong dau tien):")
    print("-" * 120)
    print("%-8s %-15s %-20s %-15s %-15s %-15s %-10s" % (
        "ID", "Name", "Journal", "Date", "Amount Total", "State", "Lines"
    ))
    print("-" * 120)
    
    total_amount = 0
    for i, move in enumerate(account_moves[:5]):  # Chỉ hiển thị 5 dòng đầu
        journal_name = move.get('journal_id', [False, 'N/A'])[1] if move.get('journal_id') else 'N/A'
        amount = move.get('amount_total', 0)
        total_amount += amount
        
        # Đếm số dòng trong move
        try:
            line_count = models.execute_kw(db, uid, password, 
                "account.move.line", "search_count",
                [('move_id', '=', move['id'])]
            )
        except:
            line_count = 0
        
        print("%-8s %-15s %-20s %-15s %-15.2f %-10s %-10s" % (
            move['id'],
            move.get('name', '')[:14],
            journal_name[:19],
            move.get('date', 'N/A'),
            amount,
            move.get('state', 'N/A'),
            line_count
        ))
    
    if len(account_moves) > 5:
        print("... va %d moves khac" % (len(account_moves) - 5))
    
    print("-" * 120)
    print("Tong so moves: %d, Tong tien: %.2f" % (len(account_moves), total_amount))
    print("-" * 120)
    
    # Xác nhận trước khi cập nhật
    print("\nCANH BAO:")
    print("Ban sap chuyen %d Account Moves tu trang thai 'draft' sang 'posted'." % len(account_moves))
    print("Dieu nay co the anh huong den cac tinh nang lien quan.")
    
    # Cho phép xác nhận không tương tác qua biến môi trường AUTO_CONFIRM
    import os
    auto_confirm = os.environ.get('AUTO_CONFIRM', '').lower()
    if auto_confirm in ('y', 'n'):
        confirm = auto_confirm
    else:
        try:
            confirm = raw_input("\nBan co chac chan muon tiep tuc? (y/n): ").lower().strip()
        except NameError:
            confirm = input("\nBan co chac chan muon tiep tuc? (y/n): ").lower().strip()
    
    if confirm != 'y':
        print("Huy bo thao tac.")
        return
    
    print("\nBat dau cap nhat...")
    
    # Cập nhật từng account move
    success_count = 0
    error_count = 0
    
    for i, move in enumerate(account_moves, 1):
        move_id = move['id']
        move_name = move.get('name', 'N/A')
        
        # Gọi action action_post để chuyển từ draft sang posted
        result = models.execute_kw(db, uid, password, 
            "account.move", "action_post",
            [move_id]
        )
        
        print("  [%d/%d] %s: Chuyen thanh cong" % (i, len(account_moves), move_name))
        success_count += 1
    
    print("\nKET QUA CAP NHAT:")
    print("  Thanh cong:", success_count)
    print("  Loi:", error_count)
    print("  Tong:", len(account_moves))
    
    # Kiểm tra lại sau khi cập nhật
    print("\nKIEM TRA LAI SAU KHI CAP NHAT:")
    updated_moves = models.execute_kw(db, uid, password, 
        "account.move", "search_read",
        [domain],
        {'fields': ['id', 'name', 'state']}
    )
    
    posted_count = sum(1 for move in updated_moves if move.get('state') == 'posted')
    draft_count = sum(1 for move in updated_moves if move.get('state') == 'draft')
    
    print("  So moves o trang thai posted: %d" % posted_count)
    print("  So moves o trang thai draft: %d" % draft_count)
    
    if draft_count == 0:
        print("\nSUCCESS: Tat ca cac inventory valuation moves da duoc chuyen sang posted!")
    else:
        print("\nWARNING: Van con %d moves chua duoc chuyen. Can kiem tra them." % draft_count)

def main():
    """Hàm chính"""
    start_time = time.time()
    print("==========================================")
    print("SCRIPT POST INVENTORY VALUATION TO DRAFT")
    print("==========================================")
    print("Thoi gian bat dau:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Database:", db)
    print()
    
    try:
        post_inventory_valuation_to_draft()
        
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
