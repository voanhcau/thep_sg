# coding=utf-8
"""
Script recompute invoice status sử dụng hàm public recompute_invoice_status()
"""
try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib
import time
import logging
from login_prod import uid, password, db, models

__logger = logging.getLogger(__name__)

def recompute_sale_orders():
    """Chạy lại recompute_invoice_status cho tất cả Sale Order"""
    print("==========================================")
    print("RECOMPUTE SALE ORDER INVOICE STATUS")
    print("==========================================")
    print("Database:", db)
    print("User ID:", uid)
    print("Time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # Lấy tất cả Sale Order
    print("Tim cac Sale Order...")
    sale_orders = models.execute_kw(db, uid, password, 
        "sale.order", "search_read",
        [[]],  # Empty domain để lấy tất cả
        {'fields': ['id', 'name', 'state', 'invoice_status']}
    )
    
    if not sale_orders:
        print("Khong tim thay Sale Order nao!")
        return
    
    print("THONG KE:")
    print("  Tong so Sale Order:", len(sale_orders))
    print("  Ghi chu: Su dung ham public recompute_invoice_status()")
    print()
    
    success_count = 0
    error_count = 0
    
    # Xử lý từng đơn hàng
    for i, order in enumerate(sale_orders, 1):
        order_id = order['id']
        order_name = order['name']
        current_status = order.get('invoice_status', 'N/A')
        
        try:
            # Sử dụng hàm public recompute_invoice_status() mới
            result = models.execute_kw(db, uid, password, 
                "sale.order", "recompute_invoice_status",
                [[order_id]]
            )
            
            new_status = result['orders'][0]['invoice_status'] if result['orders'] else 'N/A'
            print("  [%d/%d] %s: %s -> %s" % (i, len(sale_orders), order_name, current_status, new_status))
            success_count += 1
            
        except Exception as e:
            print("  [%d/%d] ERROR %s: %s" % (i, len(sale_orders), order_name, str(e)))
            error_count += 1
    
    print()
    print("KET QUA SALE ORDER:")
    print("  Thanh cong:", success_count)
    print("  Loi:", error_count)
    print("  Tong:", len(sale_orders))

def recompute_purchase_orders():
    """Chạy lại recompute_invoice_status cho tất cả Purchase Order"""
    print("==========================================")
    print("RECOMPUTE PURCHASE ORDER INVOICE STATUS")
    print("==========================================")
    print("Database:", db)
    print("User ID:", uid)
    print("Time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # Lấy tất cả Purchase Order
    print("Tim cac Purchase Order...")
    purchase_orders = models.execute_kw(db, uid, password, 
        "purchase.order", "search_read",
        [[]],  # Empty domain để lấy tất cả
        {'fields': ['id', 'name', 'state', 'invoice_status']}
    )
    
    if not purchase_orders:
        print("Khong tim thay Purchase Order nao!")
        return
    
    print("THONG KE:")
    print("  Tong so Purchase Order:", len(purchase_orders))
    print("  Ghi chu: Su dung ham public recompute_invoice_status()")
    print()
    
    success_count = 0
    error_count = 0
    
    # Xử lý từng đơn hàng
    for i, order in enumerate(purchase_orders, 1):
        order_id = order['id']
        order_name = order['name']
        current_status = order.get('invoice_status', 'N/A')
        
        try:
            # Sử dụng hàm public recompute_invoice_status() mới
            result = models.execute_kw(db, uid, password, 
                "purchase.order", "recompute_invoice_status",
                [[order_id]]
            )
            
            new_status = result['orders'][0]['invoice_status'] if result['orders'] else 'N/A'
            print("  [%d/%d] %s: %s -> %s" % (i, len(purchase_orders), order_name, current_status, new_status))
            success_count += 1
            
        except Exception as e:
            print("  [%d/%d] ERROR %s: %s" % (i, len(purchase_orders), order_name, str(e)))
            error_count += 1
    
    print()
    print("KET QUA PURCHASE ORDER:")
    print("  Thanh cong:", success_count)
    print("  Loi:", error_count)
    print("  Tong:", len(purchase_orders))

def recompute_specific_orders():
    """Chạy lại cho các đơn hàng cụ thể từ hình ảnh"""
    print("==========================================")
    print("RECOMPUTE SPECIFIC ORDERS")
    print("==========================================")
    print("Database:", db)
    print("User ID:", uid)
    print("Time:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print()
    
    # PO P06906 và SO S07598 từ hình ảnh
    specific_orders = [
        ('sale.order', 'S07598'),
        ('purchase.order', 'P06906')
    ]
    
    for model_name, order_name in specific_orders:
        try:
            # Tìm đơn hàng theo tên
            order_ids = models.execute_kw(db, uid, password, 
                model_name, "search",
                [('name', '=', order_name)],
                {'limit': 1}
            )
            
            if not order_ids:
                print("Khong tim thay %s" % order_name)
                continue
            
            order_id = order_ids[0]
            
            # Lấy thông tin hiện tại
            current_order = models.execute_kw(db, uid, password, 
                model_name, "read",
                [order_id],
                {'fields': ['name', 'invoice_status', 'invoice_state']}
            )
            
            current_status = current_order[0].get('invoice_status', 'N/A')
            current_state = current_order[0].get('invoice_state', 'N/A')
            
            print("--- %s (Truoc) ---" % order_name)
            print("  invoice_status: %s" % current_status)
            print("  invoice_state: %s" % current_state)
            
            # Sử dụng hàm public recompute_invoice_status() mới
            result = models.execute_kw(db, uid, password, 
                model_name, "recompute_invoice_status",
                [[order_id]]
            )
            
            # Lấy thông tin sau khi cập nhật
            updated_order = models.execute_kw(db, uid, password, 
                model_name, "read",
                [order_id],
                {'fields': ['name', 'invoice_status', 'invoice_state']}
            )
            
            new_status = updated_order[0].get('invoice_status', 'N/A')
            new_state = updated_order[0].get('invoice_state', 'N/A')
            
            print("--- %s (Sau) ---" % order_name)
            print("  invoice_status: %s" % new_status)
            print("  invoice_state: %s" % new_state)
            print("  Thay doi: %s -> %s" % (current_status, new_status))
            print()
            
        except Exception as e:
            print("ERROR %s: %s" % (order_name, str(e)))

def main():
    """Hàm chính"""
    start_time = time.time()
    print("==========================================")
    print("SCRIPT RECOMPUTE INVOICE STATUS")
    print("==========================================")
    print("Thoi gian bat dau:", time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Ghi chu: Khong gioi han so luong, xu ly tat ca")
    print()
    
    try:
        # 1. Xử lý các đơn hàng cụ thể trước
        print("BUOC 1: Xu ly cac don hang cu the...")
        recompute_specific_orders()
        
        # 2. Xử lý tất cả Sale Order
        print("\nBUOC 2: Xu ly tat ca Sale Order...")
        recompute_sale_orders()
        
        # 3. Xử lý tất cả Purchase Order  
        print("\nBUOC 3: Xu ly tat ca Purchase Order...")
        recompute_purchase_orders()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("==========================================")
        print("HOAN THANH")
        print("==========================================")
        print("Thoi gian ket thuc:", time.strftime("%Y-%m-%d %H:%M:%S"))
        print("Thoi gian xu ly: %.2f giay" % duration)
        # Tính tổng số đơn hàng đã xử lý
        total_orders = 0
        try:
            # Lấy số lượng từ các function đã chạy
            sale_count = len(models.execute_kw(db, uid, password, "sale.order", "search", [[]]))
            purchase_count = len(models.execute_kw(db, uid, password, "purchase.order", "search", [[]]))
            total_orders = sale_count + purchase_count
        except:
            total_orders = 1  # Fallback để tránh chia cho 0
            
        print("Trung binh: %.2f giay/don hang" % (duration / max(1, total_orders)))
        
    except Exception as e:
        print("LOI CHUNG: %s" % str(e))
        __logger.error("Script error: %s" % str(e))

if __name__ == '__main__':
    main()
