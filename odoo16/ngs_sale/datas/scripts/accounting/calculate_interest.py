import os
import xmlrpc.client
import logging
from datetime import datetime
import sys
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False


# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('calculate_interest.log'),
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

# Search các đơn hàng từ 1/2/2024 có hóa đơn và đã xác nhận
domain = [
    ('date_order', '>=', '2024-02-01'),
    ('invoice_ids', '!=', False),
    ('state', '=', 'sale')
]

sale_order_ids = models.execute_kw(
    db, uid, password,
    'sale.order', 'search',
    [domain]
)

logging.info(f"Found {len(sale_order_ids)} sale orders to process")

# Đọc thông tin chi tiết của các đơn hàng
sale_orders = models.execute_kw(
    db, uid, password,
    'sale.order', 'read',
    [sale_order_ids],
    {'fields': ['name', 'invoice_ids']}
)

# Lọc các đơn có hóa đơn đã thanh toán đủ (amount_residual = 0)
fully_paid_orders = []
for order in sale_orders:
    invoice_ids = order['invoice_ids']
    invoices = models.execute_kw(
        db, uid, password,
        'account.move', 'read',
        [invoice_ids],
        {'fields': ['amount_residual']}
    )
    
    # Chỉ lấy những đơn có tất cả hóa đơn đã thanh toán đủ
    if all(inv['amount_residual'] == 0 for inv in invoices):
        fully_paid_orders.append(order['id'])

logging.info(f"Found {len(fully_paid_orders)} fully paid orders")

# Tính lãi vay cho từng đơn
success_count = 0
for order_id in fully_paid_orders:
    logging.info(f"Processing order ID: {order_id}")
    try:
        # Gọi hàm calculate_interest
        result = models.execute_kw(
            db, uid, password,
            'sale.order', 'calculate_interest',
            [order_id]
        )
    except Exception as e:
        continue
        logging.error(f"Error processing order ID {order_id}: {e}")
    else:
        success_count += 1
        logging.info(f"Successfully processed order ID: {order_id}")

logging.info(f"Completed! Successfully processed {success_count} orders")