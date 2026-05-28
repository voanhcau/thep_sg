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
Script để cập nhật lại invoice_status_custom cho Purchase Order và Sale Order
Chạy hàm recompute_invoice_status() cho cả 2 loại đơn hàng
"""

import os
import xmlrpc.client
import logging
import sys
from datetime import datetime

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('recompute_invoice_status.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Thông tin kết nối
# Get connection với hỗ trợ 3 môi trường
env_type = sys.argv[1] if len(sys.argv) > 1 else None

if USE_ENV_LOADER:
    try:
        url, db, username, password, models, uid = setup_odoo_connection(env_type)
        print(f"✅ Connected to {env_type or 'default'} environment")
        # Tạo common để dùng cho version check
        import xmlrpc.client
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
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
logging.info("="*60)
logging.info("BẮT ĐẦU CẬP NHẬT INVOICE_STATUS_CUSTOM")
logging.info("="*60)
logging.info(f"Database: {db}")
logging.info(f"Thời gian: {datetime.now()}")
logging.info("Authentication successful")

def recompute_purchase_order_invoice_status():
    """Cập nhật invoice_status_custom cho Purchase Orders"""
    logging.info("\n" + "="*60)
    logging.info("XỬ LÝ PURCHASE ORDERS")
    logging.info("="*60)
    
    try:
        # Tìm tất cả purchase orders
        po_ids = models.execute_kw(
            db, uid, password,
            'purchase.order', 'search',
            [[]],
            {'limit': 0}  # Không giới hạn số lượng
        )
        
        logging.info(f"Tìm thấy {len(po_ids)} Purchase Orders")
        
        if not po_ids:
            logging.info("Không có Purchase Order nào để xử lý")
            return
        
        # Chia nhỏ thành các batch để xử lý (100 orders mỗi batch)
        batch_size = 100
        total_updated = 0
        total_errors = 0
        
        for i in range(0, len(po_ids), batch_size):
            batch_ids = po_ids[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(po_ids) + batch_size - 1) // batch_size
            
            logging.info(f"\nXử lý batch {batch_num}/{total_batches} ({len(batch_ids)} orders)...")
            
            try:
                # Gọi hàm recompute_invoice_status cho batch này
                # Lưu ý: Hàm này sẽ tự động tính lại và lưu vào database
                result = models.execute_kw(
                    db, uid, password,
                    'purchase.order', 'recompute_invoice_status',
                    [batch_ids],
                    {}
                )
                
                if result:
                    updated_count = result.get('updated_count', 0) if isinstance(result, dict) else len(batch_ids)
                    total_updated += updated_count
                    logging.info(f"✅ Batch {batch_num}: Đã cập nhật {updated_count} orders")
                    
                    # Log một vài orders đầu tiên của batch (nếu có)
                    if isinstance(result, dict) and result.get('orders'):
                        for order_info in result['orders'][:5]:
                            logging.info(f"   - {order_info.get('name', 'N/A')}: {order_info.get('invoice_status_custom', 'N/A')}")
                else:
                    # Nếu không có kết quả, coi như đã cập nhật thành công
                    total_updated += len(batch_ids)
                    logging.info(f"✅ Batch {batch_num}: Đã xử lý {len(batch_ids)} orders")
                    
            except Exception as e:
                total_errors += len(batch_ids)
                logging.error(f"❌ Batch {batch_num}: Lỗi khi xử lý: {e}")
                import traceback
                logging.error(traceback.format_exc())
        
        logging.info(f"\n✅ Hoàn thành xử lý Purchase Orders:")
        logging.info(f"   - Tổng số: {len(po_ids)}")
        logging.info(f"   - Đã cập nhật: {total_updated}")
        logging.info(f"   - Lỗi: {total_errors}")
        
    except Exception as e:
        logging.error(f"❌ Lỗi khi xử lý Purchase Orders: {e}")
        import traceback
        logging.error(traceback.format_exc())

def recompute_sale_order_invoice_status():
    """Cập nhật invoice_status_custom cho Sale Orders"""
    logging.info("\n" + "="*60)
    logging.info("XỬ LÝ SALE ORDERS")
    logging.info("="*60)
    
    try:
        # Tìm tất cả sale orders
        so_ids = models.execute_kw(
            db, uid, password,
            'sale.order', 'search',
            [[]],
            {'limit': 0}  # Không giới hạn số lượng
        )
        
        logging.info(f"Tìm thấy {len(so_ids)} Sale Orders")
        
        if not so_ids:
            logging.info("Không có Sale Order nào để xử lý")
            return
        
        # Chia nhỏ thành các batch để xử lý (100 orders mỗi batch)
        batch_size = 100
        total_updated = 0
        total_errors = 0
        
        for i in range(0, len(so_ids), batch_size):
            batch_ids = so_ids[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(so_ids) + batch_size - 1) // batch_size
            
            logging.info(f"\nXử lý batch {batch_num}/{total_batches} ({len(batch_ids)} orders)...")
            
            try:
                # Gọi hàm recompute_invoice_status cho batch này
                # Lưu ý: Hàm này sẽ tự động tính lại và lưu vào database
                result = models.execute_kw(
                    db, uid, password,
                    'sale.order', 'recompute_invoice_status',
                    [batch_ids],
                    {}
                )
                
                if result:
                    updated_count = result.get('updated_count', 0) if isinstance(result, dict) else len(batch_ids)
                    total_updated += updated_count
                    logging.info(f"✅ Batch {batch_num}: Đã cập nhật {updated_count} orders")
                    
                    # Log một vài orders đầu tiên của batch (nếu có)
                    if isinstance(result, dict) and result.get('orders'):
                        for order_info in result['orders'][:5]:
                            logging.info(f"   - {order_info.get('name', 'N/A')}: {order_info.get('invoice_status_custom', 'N/A')}")
                else:
                    # Nếu không có kết quả, coi như đã cập nhật thành công
                    total_updated += len(batch_ids)
                    logging.info(f"✅ Batch {batch_num}: Đã xử lý {len(batch_ids)} orders")
                    
            except Exception as e:
                total_errors += len(batch_ids)
                logging.error(f"❌ Batch {batch_num}: Lỗi khi xử lý: {e}")
                import traceback
                logging.error(traceback.format_exc())
        
        logging.info(f"\n✅ Hoàn thành xử lý Sale Orders:")
        logging.info(f"   - Tổng số: {len(so_ids)}")
        logging.info(f"   - Đã cập nhật: {total_updated}")
        logging.info(f"   - Lỗi: {total_errors}")
        
    except Exception as e:
        logging.error(f"❌ Lỗi khi xử lý Sale Orders: {e}")
        import traceback
        logging.error(traceback.format_exc())

def main():
    """Hàm chính"""
    start_time = datetime.now()
    
    try:
        # Test kết nối
        version = common.version()
        logging.info(f"Odoo version: {version}")
        
        # Xử lý Purchase Orders
        recompute_purchase_order_invoice_status()
        
        # Xử lý Sale Orders
        recompute_sale_order_invoice_status()
        
        # Tổng kết
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logging.info("\n" + "="*60)
        logging.info("HOÀN THÀNH CẬP NHẬT INVOICE_STATUS_CUSTOM")
        logging.info("="*60)
        logging.info(f"Thời gian bắt đầu: {start_time}")
        logging.info(f"Thời gian kết thúc: {end_time}")
        logging.info(f"Tổng thời gian: {duration:.2f} giây")
        logging.info("="*60)
        
    except Exception as e:
        logging.error(f"❌ Lỗi trong quá trình xử lý: {e}")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1)

if __name__ == "__main__":
    main()

