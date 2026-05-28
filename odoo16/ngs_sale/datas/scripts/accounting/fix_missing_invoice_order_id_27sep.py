# -*- coding: utf-8 -*-
import xmlrpclib
import time
import logging
from login_prod import uid, password, db, models

__logger = logging.getLogger(__name__)

def fix_missing_invoice_order_id():
    """Fix cac invoice thieu invoice_order_id"""
    
    print "=========================================="
    print "FIX MISSING INVOICE ORDER ID"
    print "=========================================="
    print "Database:", db
    print "User ID:", uid
    print "Time:", time.strftime("%Y-%m-%d %H:%M:%S")
    print
    
    # Tim cac invoice thieu invoice_order_id
    print "Tim cac invoice thieu invoice_order_id..."
    
    missing_invoices = models.execute_kw(
        db, uid, password,
        'account.move', 'search_read',
        [[
            ('move_type', 'in', ['in_invoice', 'out_invoice']),
            ('state', '=', 'posted'),
            ('invoice_order_id', '=', False)
        ]],
        {
            'fields': ['id', 'name', 'move_type', 'partner_id', 'ref', 'invoice_origin'],
            'limit': 100  # Test voi 100 invoice truoc
        }
    )
    
    if not missing_invoices:
        print "Khong tim thay invoice nao thieu invoice_order_id!"
        return
    
    # Thong ke
    vendor_bills = [inv for inv in missing_invoices if inv['move_type'] == 'in_invoice']
    customer_invoices = [inv for inv in missing_invoices if inv['move_type'] == 'out_invoice']
    
    print "THONG KE (Gioi han 100 invoice dau):"
    print "  Tong so invoice thieu:", len(missing_invoices)
    print "  Hoa don mua (vendor bills):", len(vendor_bills)
    print "  Hoa don ban (customer invoices):", len(customer_invoices)
    print
    
    # Hien thi danh sach chi tiet (10 dau)
    print "DANH SACH CHI TIET (10 invoice dau):"
    for i, inv in enumerate(missing_invoices[:10]):
        partner_name = inv['partner_id'][1] if inv['partner_id'] else 'N/A'
        print "  %d. %s: %s (ID: %s) | Partner: %s | Ref: %s | Origin: %s" % (
            i+1, inv['move_type'].upper(), inv['name'], inv['id'],
            partner_name, inv['ref'], inv['invoice_origin']
        )
    
    if len(missing_invoices) > 10:
        print "  ... va %d invoice khac" % (len(missing_invoices) - 10)
    print
    
    # Xac nhan truoc khi fix
    print "CANH BAO: Script se sua doi %d invoice records!" % len(missing_invoices)
    confirm = raw_input("Ban co muon tiep tuc? (y/N): ")
    if confirm.lower() not in ['y', 'yes']:
        print "Huy bo thao tac."
        return
    
    print "\nBAT DAU QUA TRINH FIX..."
    print "=" * 50
    
    # Xu ly tung invoice
    total_processed = 0
    total_fixed = 0
    fixed_vendor_bills = 0
    fixed_customer_invoices = 0
    
    for inv in missing_invoices:
        total_processed += 1
        
        print "[%d/%d] Xu ly %s %s (ID: %s)" % (
            total_processed, len(missing_invoices),
            inv['move_type'], inv['name'], inv['id']
        )
        
        try:
            # Goi method _compute_invoice_order_id
            result = models.execute_kw(
                db, uid, password,
                'account.move', '_compute_invoice_order_id',
                [[inv['id']]]
            )
            
            # Kiem tra xem da fix chua
            updated_inv = models.execute_kw(
                db, uid, password,
                'account.move', 'read',
                [[inv['id']]],
                {'fields': ['invoice_order_id']}
            )
            
            if updated_inv and updated_inv[0]['invoice_order_id']:
                total_fixed += 1
                if inv['move_type'] == 'in_invoice':
                    fixed_vendor_bills += 1
                else:
                    fixed_customer_invoices += 1
                
                linked_info = updated_inv[0]['invoice_order_id']
                linked_name = linked_info[1] if isinstance(linked_info, list) else str(linked_info)
                print "  -> THANH CONG: %s lien ket voi %s" % (inv['name'], linked_name)
            else:
                print "  -> KHONG FIX DUOC: %s - khong tim thay counterpart" % inv['name']
            
            # Delay nho de khong qua tai server
            time.sleep(0.2)
            
        except Exception as e:
            print "  -> LOI: %s - %s" % (inv['name'], str(e))
            continue
    
    # Ket qua cuoi cung
    print "\n" + "=" * 50
    print "KET QUA CUOI CUNG:"
    print "  Tong so xu ly:", total_processed
    print "  Fix thanh cong:", total_fixed
    print "    - Vendor bills:", fixed_vendor_bills
    print "    - Customer invoices:", fixed_customer_invoices
    print "  Khong fix duoc:", total_processed - total_fixed
    
    if total_processed > 0:
        success_rate = float(total_fixed) / total_processed * 100
        print "  Ti le thanh cong: %.1f%%" % success_rate
    
    print "Hoan thanh vao luc:", time.strftime("%Y-%m-%d %H:%M:%S")
    print "=========================================="

def test_specific_invoice(invoice_id):
    """Test fix cho 1 invoice cu the"""
    
    print "=========================================="
    print "TEST FIX CHO INVOICE ID:", invoice_id
    print "=========================================="
    
    # Lay thong tin invoice
    invoice = models.execute_kw(
        db, uid, password,
        'account.move', 'search_read',
        [[('id', '=', invoice_id)]],
        {'fields': ['id', 'name', 'move_type', 'partner_id', 'invoice_order_id'], 'limit': 1}
    )
    
    if not invoice:
        print "Khong tim thay invoice ID:", invoice_id
        return
    
    inv = invoice[0]
    partner_name = inv['partner_id'][1] if inv['partner_id'] else 'N/A'
    current_order_id = inv['invoice_order_id']
    
    print "Thong tin invoice:"
    print "  ID:", inv['id']
    print "  Ten:", inv['name']
    print "  Loai:", inv['move_type']
    print "  Partner:", partner_name
    print "  invoice_order_id hien tai:", current_order_id[1] if current_order_id else 'NULL'
    print
    
    # Fix invoice
    print "Dang fix..."
    try:
        result = models.execute_kw(
            db, uid, password,
            'account.move', '_compute_invoice_order_id',
            [[invoice_id]]
        )
        
        # Kiem tra ket qua
        updated_inv = models.execute_kw(
            db, uid, password,
            'account.move', 'read',
            [[invoice_id]],
            {'fields': ['invoice_order_id']}
        )
        
        new_order_id = updated_inv[0]['invoice_order_id'] if updated_inv else None
        
        print "Ket qua:"
        if new_order_id and new_order_id != current_order_id:
            linked_name = new_order_id[1] if isinstance(new_order_id, list) else str(new_order_id)
            print "  THANH CONG: invoice_order_id = %s" % linked_name
        else:
            print "  KHONG THAY DOI: van la", current_order_id[1] if current_order_id else 'NULL'
        
    except Exception as e:
        print "  LOI:", str(e)
    
    print "=========================================="

def count_missing_only():
    """Chi count so luong thieu, khong fix"""
    
    print "=========================================="
    print "COUNT MISSING INVOICE ORDER ID"
    print "=========================================="
    print "Database:", db
    print
    
    # Count tong so invoice posted
    total_invoices = models.execute_kw(
        db, uid, password,
        'account.move', 'search_count',
        [[
            ('move_type', 'in', ['in_invoice', 'out_invoice']),
            ('state', '=', 'posted')
        ]]
    )
    
    # Count missing
    missing_count = models.execute_kw(
        db, uid, password,
        'account.move', 'search_count',
        [[
            ('move_type', 'in', ['in_invoice', 'out_invoice']),
            ('state', '=', 'posted'),
            ('invoice_order_id', '=', False)
        ]]
    )
    
    # Count by type
    missing_vendor_bills = models.execute_kw(
        db, uid, password,
        'account.move', 'search_count',
        [[
            ('move_type', '=', 'in_invoice'),
            ('state', '=', 'posted'),
            ('invoice_order_id', '=', False)
        ]]
    )
    
    missing_customer_invoices = models.execute_kw(
        db, uid, password,
        'account.move', 'search_count',
        [[
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_order_id', '=', False)
        ]]
    )
    
    print "THONG KE TONG QUAN:"
    print "  Tong so invoice posted:", total_invoices
    print "  Invoice thieu invoice_order_id:", missing_count
    print "    - Vendor bills:", missing_vendor_bills
    print "    - Customer invoices:", missing_customer_invoices
    
    if total_invoices > 0:
        missing_rate = float(missing_count) / total_invoices * 100
        print "  Ti le thieu: %.1f%%" % missing_rate
    
    print "=========================================="

def fix_all_missing_invoice_order_id():
    """Fix tat ca invoice thieu invoice_order_id (khong gioi han)"""
    
    print "=========================================="
    print "FIX TAT CA INVOICE THIEU INVOICE ORDER ID"
    print "=========================================="
    print "Database:", db
    print "User ID:", uid
    print "Time:", time.strftime("%Y-%m-%d %H:%M:%S")
    print
    
    if not uid:
        print "Authentication failed! Cannot proceed."
        return
    
    # Count truoc khi fix
    print "Dem so luong invoice thieu..."
    missing_count = models.execute_kw(
        db, uid, password,
        'account.move', 'search_count',
        [[
            ('move_type', 'in', ['in_invoice', 'out_invoice']),
            ('state', '=', 'posted'),
            ('invoice_order_id', '=', False)
        ]]
    )
    
    if missing_count == 0:
        print "Khong co invoice nao thieu invoice_order_id!"
        return
    
    print "Tim thay %d invoice thieu invoice_order_id" % missing_count
    print
    
    # Canh bao va xac nhan
    print "CANH BAO: Script se fix TAT CA %d invoice records!" % missing_count
    print "   Qua trinh nay co the mat nhieu thoi gian."
    print "   Khong nen ngat giua chung."
    print
    confirm = raw_input("Ban CHAC CHAN muon fix tat ca? (yes/NO): ")
    if confirm.lower() != 'yes':
        print "Huy bo thao tac."
        return
    
    print "\nBAT DAU QUA TRINH FIX TAT CA..."
    print "=" * 60
    
    # Xu ly theo batch de tranh qua tai
    batch_size = 200
    offset = 0
    total_processed = 0
    total_fixed = 0
    fixed_vendor_bills = 0
    fixed_customer_invoices = 0
    total_errors = 0
    
    start_time = time.time()
    
    while True:
        # Lay batch hien tai
        print "\n--- BATCH %d (offset: %d, size: %d) ---" % (offset // batch_size + 1, offset, batch_size)
        
        missing_invoices = models.execute_kw(
            db, uid, password,
            'account.move', 'search_read',
            [[
                ('move_type', 'in', ['in_invoice', 'out_invoice']),
                ('state', '=', 'posted'),
                ('invoice_order_id', '=', False)
            ]],
            {
                'fields': ['id', 'name', 'move_type', 'partner_id', 'ref', 'invoice_origin'],
                'limit': batch_size,
                'offset': offset,
                'order': 'create_date desc'  # Xu ly invoice moi truoc
            }
        )
        
        if not missing_invoices:
            print "Het invoice de xu ly."
            break
        
        print "Xu ly %d invoice trong batch nay..." % len(missing_invoices)
        
        # Xu ly tung invoice trong batch
        batch_fixed = 0
        batch_errors = 0
        
        for i, inv in enumerate(missing_invoices):
            total_processed += 1
            
            print "[%d/%d] (Tong: %d) %s %s (ID: %s)" % (
                i + 1, len(missing_invoices), total_processed,
                inv['move_type'], inv['name'], inv['id']
            ),
            
            try:
                # Goi method compute_invoice_order_id_public (public method)
                result = models.execute_kw(
                    db, uid, password,
                    'account.move', 'compute_invoice_order_id_public',
                    [[inv['id']]]
                )
                
                if result and result.get('success') and result.get('invoice_order_id'):
                    total_fixed += 1
                    batch_fixed += 1
                    if inv['move_type'] == 'in_invoice':
                        fixed_vendor_bills += 1
                    else:
                        fixed_customer_invoices += 1
                    
                    print " -> OK %s" % result.get('invoice_order_name', 'Fixed')
                else:
                    print " -> No counterpart"
                
                # Delay nho de khong qua tai server
                time.sleep(0.05)
                
            except Exception as e:
                total_errors += 1
                batch_errors += 1
                print " -> LOI: %s" % str(e)
                continue
        
        # Thong ke batch
        elapsed = time.time() - start_time
        print "\nBatch summary:"
        print "  Processed: %d" % len(missing_invoices)
        print "  Fixed: %d" % batch_fixed
        print "  Errors: %d" % batch_errors
        print "  Time elapsed: %.1f seconds" % elapsed
        
        # Tiep tuc batch tiep theo
        offset += batch_size
        
        # Nghi 1 giay giua cac batch
        time.sleep(1)
    
    # Ket qua cuoi cung
    total_time = time.time() - start_time
    print "\n" + "=" * 60
    print "KET QUA CUOI CUNG - FIX TAT CA:"
    print "  Tong so xu ly:", total_processed
    print "  Fix thanh cong:", total_fixed
    print "    - Vendor bills:", fixed_vendor_bills
    print "    - Customer invoices:", fixed_customer_invoices
    print "  Loi:", total_errors
    print "  Khong fix duoc:", total_processed - total_fixed - total_errors
    
    if total_processed > 0:
        success_rate = float(total_fixed) / total_processed * 100
        print "  Ti le thanh cong: %.1f%%" % success_rate
    
    print "  Thoi gian tong: %.1f giay (%.1f phut)" % (total_time, total_time / 60)
    print "Hoan thanh vao luc:", time.strftime("%Y-%m-%d %H:%M:%S")
    print "=" * 60

if __name__ == "__main__":
    print "Chon chuc nang:"
    print "1. Chi count so luong thieu (khong fix)"
    print "2. Fix cac invoice thieu invoice_order_id (gioi han 100)"
    print "3. Test fix cho 1 invoice cu the"
    print "4. [CANH BAO] Fix TAT CA invoice thieu invoice_order_id (KHONG GIOI HAN)"
    print "5. Thoat"
    
    choice = raw_input("Nhap lua chon (1-5): ")
    
    if choice == '1':
        count_missing_only()
    elif choice == '2':
        fix_missing_invoice_order_id()
    elif choice == '3':
        invoice_id = raw_input("Nhap Invoice ID: ")
        try:
            invoice_id = int(invoice_id)
            test_specific_invoice(invoice_id)
        except ValueError:
            print "Invoice ID khong hop le!"
    elif choice == '4':
        fix_all_missing_invoice_order_id()
    elif choice == '5':
        print "Thoat."
    else:
        print "Lua chon khong hop le!"
