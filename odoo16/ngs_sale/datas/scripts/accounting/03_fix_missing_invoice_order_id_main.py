import xmlrpclib
import time
import logging
from login_local import uid, password, db, models

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
            'limit': 1000  # Gioi han 1000 de an toan
        }
    )
    
    if not missing_invoices:
        print "Khong tim thay invoice nao thieu invoice_order_id!"
        return
    
    # Thong ke
    vendor_bills = [inv for inv in missing_invoices if inv['move_type'] == 'in_invoice']
    customer_invoices = [inv for inv in missing_invoices if inv['move_type'] == 'out_invoice']
    
    print "THONG KE:"
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
            time.sleep(0.1)
            
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

if __name__ == "__main__":
    print "Chon chuc nang:"
    print "1. Fix tat ca invoice thieu invoice_order_id"
    print "2. Test fix cho 1 invoice cu the"
    print "3. Thoat"
    
    choice = raw_input("Nhap lua chon (1-3): ")
    
    if choice == '1':
        fix_missing_invoice_order_id()
    elif choice == '2':
        invoice_id = raw_input("Nhap Invoice ID: ")
        try:
            invoice_id = int(invoice_id)
            test_specific_invoice(invoice_id)
        except ValueError:
            print "Invoice ID khong hop le!"
    elif choice == '3':
        print "Thoat."
    else:
        print "Lua chon khong hop le!"
