#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test kết nối đơn giản nhất
Hỗ trợ 3 môi trường: prod, staging, local
Usage:
    python test_connection.py          # Dùng default (PROD)
    python test_connection.py prod     # Dùng PROD
    python test_connection.py staging  # Dùng STAGING
    python test_connection.py local    # Dùng LOCAL
"""

import sys
import os
import xmlrpc.client
import logging
from pathlib import Path

# Add login_configs to path để import env_loader
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Lấy environment type từ command line argument
env_type = sys.argv[1] if len(sys.argv) > 1 else None

if USE_ENV_LOADER:
    try:
        url, db, username, password, models, uid = setup_odoo_connection(env_type)
        logging.info(f"✅ Using {env_type or 'default'} environment from .env")
        # Tạo common để dùng cho version check
        import xmlrpc.client
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
    except Exception as e:
        logging.error(f"❌ Error loading environment: {e}")
        exit(1)
else:
    # Fallback: dùng environment variables trực tiếp
    url = os.getenv("ODOO_URL")
    db = os.getenv("ODOO_DB")
    username = os.getenv("ODOO_USERNAME")
password = os.getenv("ODOO_PASSWORD")

    if not all([url, db, username, password]):
        logging.error("❌ Missing environment variables. Please:")
        logging.error("   1. Run: source load_env.sh [prod|staging|local]")
        logging.error("   2. Or set: ODOO_URL, ODOO_DB, ODOO_USERNAME, ODOO_PASSWORD")
    exit(1)

    # Connect manually
    import xmlrpc.client
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        logging.error("❌ Authentication failed")
        exit(1)

try:
    logging.info("✅ Authentication successful")
    
    # Test kết nối bằng cách lấy thông tin version
    version = common.version()
    logging.info(f"✅ Odoo version: {version}")
    
    # Test tìm đơn hàng đơn giản nhất
    logging.info("🔍 Tìm đơn hàng...")
    
    # Tìm tất cả đơn hàng (với domain cơ bản)
    all_orders = models.execute_kw(
        db, uid, password,
        'sale.order', 'search',
        [('id', '>', 0)],
        {'limit': 5}
    )
    
    logging.info(f"✅ Tìm thấy {len(all_orders)} đơn hàng")
    
    # Đọc thông tin 3 đơn hàng đầu
    for i, order_id in enumerate(all_orders[:3], 1):
        try:
            order = models.execute_kw(
                db, uid, password,
                'sale.order', 'read',
                [order_id],
                {'fields': ['name', 'amount_untaxed', 'state']}
            )[0]
            logging.info(f"   {i}. {order['name']} - {order['amount_untaxed']:,.0f} VNĐ - {order['state']}")
        except Exception as e:
            logging.error(f"   {i}. Lỗi đọc đơn hàng {order_id}: {e}")
    
    # Tìm đơn hàng S08193 cụ thể
    logging.info("\n🔍 Tìm đơn hàng S08193...")
    try:
        s08193_orders = models.execute_kw(
            db, uid, password,
            'sale.order', 'search',
            [('name', '=', 'S08193')]
        )
        
        if s08193_orders:
            logging.info(f"✅ Tìm thấy đơn hàng S08193 (ID: {s08193_orders[0]})")
            
            # Đọc thông tin chi tiết
            order = models.execute_kw(
                db, uid, password,
                'sale.order', 'read',
                [s08193_orders[0]],
                {'fields': ['name', 'partner_id', 'date_order', 'amount_untaxed', 'state']}
            )[0]
            
            logging.info(f"   - Tên: {order['name']}")
            logging.info(f"   - Khách hàng: {order['partner_id'][1] if order['partner_id'] else 'N/A'}")
            logging.info(f"   - Ngày đặt hàng: {order['date_order']}")
            logging.info(f"   - Số tiền: {order['amount_untaxed']:,.0f} VNĐ")
            logging.info(f"   - Trạng thái: {order['state']}")
            
        else:
            logging.warning("❌ Không tìm thấy đơn hàng S08193")
            
    except Exception as e:
        logging.error(f"❌ Lỗi tìm đơn hàng S08193: {e}")
    
    logging.info("\n✅ Test kết nối thành công!")
    
except Exception as e:
    logging.error(f"❌ Lỗi kết nối: {e}")
