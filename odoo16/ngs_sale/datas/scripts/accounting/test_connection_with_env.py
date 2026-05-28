#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script test kết nối với hỗ trợ 3 môi trường (prod/staging/local)
Usage:
    python test_connection_with_env.py          # Dùng default (PROD)
    python test_connection_with_env.py prod     # Dùng PROD
    python test_connection_with_env.py staging  # Dùng STAGING
    python test_connection_with_env.py local    # Dùng LOCAL
"""

import sys
import logging
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

from env_loader import setup_odoo_connection, get_env_config

# Cấu hình logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Lấy environment type từ command line argument
    env_type = sys.argv[1] if len(sys.argv) > 1 else None
    
    try:
        # Setup connection
        url, db, username, password, models, uid = setup_odoo_connection(env_type)
        
        logging.info(f"✅ Connected to {env_type or 'default'} environment")
        logging.info(f"   URL: {url}")
        logging.info(f"   DB: {db}")
        logging.info(f"   Username: {username}")
        logging.info(f"   User ID: {uid}")
        
        # Test kết nối bằng cách lấy thông tin version
        import xmlrpc.client
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        version = common.version()
        logging.info(f"✅ Odoo version: {version}")
        
        # Test tìm đơn hàng
        logging.info("🔍 Tìm đơn hàng...")
        all_orders = models.execute_kw(
            db, uid, password,
            'sale.order', 'search',
            [('id', '>', 0)],
            {'limit': 5}
        )
        logging.info(f"✅ Tìm thấy {len(all_orders)} đơn hàng")
        
        logging.info("\n✅ Test kết nối thành công!")
        return 0
        
    except ValueError as e:
        logging.error(f"❌ Error: {e}")
        logging.error("   Vui lòng kiểm tra file .env và đảm bảo đã set đầy đủ biến môi trường")
        return 1
    except Exception as e:
        logging.error(f"❌ Lỗi kết nối: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
