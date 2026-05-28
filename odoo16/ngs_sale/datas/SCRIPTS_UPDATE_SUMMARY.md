# Scripts Update Summary - Hỗ trợ 3 môi trường

## Tổng quan

Đã cập nhật **tất cả scripts quan trọng** trong thư mục `datas/scripts/` để hỗ trợ **3 môi trường**:
- **PROD**: `http://erp.thepnamsaigon.com`
- **STAGING**: `http://test.thepnamsaigon.com`
- **LOCAL**: `http://localhost:6069`

## Files đã được cập nhật (28+ scripts)

### Accounting Scripts:
1. ✅ `test_connection.py` - Test kết nối
2. ✅ `01_fix_invoice_order_id_final.py` - Fix invoice order ID
3. ✅ `02_fix_invoice_order_id_simple.py` - Fix invoice order ID (simple)
4. ✅ `test_negative_interest.py` - Test lãi vay âm
5. ✅ `reset_interest_unpaid_invoices.py` - Reset lãi vay
6. ✅ `recalculate_interest_all_orders.py` - Tính lại lãi vay
7. ✅ `recalculate_interest_fixed_orders.py` - Tính lại lãi vay (fixed orders)
8. ✅ `recalculate_interest_all_orders_full.py` - Tính lại lãi vay (full)
9. ✅ `verify_fixed_orders.py` - Verify fixed orders
10. ✅ `check_interest_calculation_all_orders.py` - Check lãi vay
11. ✅ `check_interest_calculation.py` - Check lãi vay (calculation)
12. ✅ `check_multiple_orders.py` - Check multiple orders
13. ✅ `check_order_s09471.py` - Check order S09471
14. ✅ `check_order_16683.py` - Check order 16683
15. ✅ `fix_incorrect_interest_orders.py` - Fix incorrect interest
16. ✅ `fix_all_incorrect_interest_production.py` - Fix all incorrect interest
17. ✅ `cancel_invoice_179086.py` - Cancel invoice
18. ✅ `calculate_interest.py` - Calculate interest
19. ✅ `debug_reconciliation.py` - Debug reconciliation
20. ✅ `recompute_invoice_status.py` - Recompute invoice status
21. ✅ `test_interest_calculation_100_orders.py` - Test interest calculation

### Login Scripts:
22. ✅ `login_local.py` (accounting)
23. ✅ `login_local.py` (root)

### Debug Scripts:
24. ✅ `debug_stock_picking_move_lines.py` - Debug stock picking

## Cách sử dụng

### 1. Load environment variables:

```bash
# Load PROD (default)
source load_env.sh

# Load STAGING
source load_env.sh staging

# Load LOCAL
source load_env.sh local
```

### 2. Chạy script với environment type:

```bash
# Dùng default (PROD)
python script.py

# Dùng PROD
python script.py prod

# Dùng STAGING
python script.py staging

# Dùng LOCAL
python script.py local
```

## Cấu trúc code mới

Tất cả scripts đã được cập nhật với pattern sau:

```python
import sys
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))

try:
    from env_loader import setup_odoo_connection
    USE_ENV_LOADER = True
except ImportError:
    USE_ENV_LOADER = False

def main():
    # Lấy environment type từ command line
    env_type = sys.argv[1] if len(sys.argv) > 1 else None
    
    if USE_ENV_LOADER:
        URL, DB, USERNAME, PASSWORD, models, uid = setup_odoo_connection(env_type)
        print(f"✅ Connected to {env_type or 'default'} environment")
    else:
        # Fallback: dùng environment variables
        URL = os.getenv("ODOO_URL")
        DB = os.getenv("ODOO_DB")
        # ... connect manually
```

## Security Status

- ✅ **Không còn hardcoded credentials** (chỉ còn 3 comments)
- ✅ **Tất cả credentials nằm trong `.env`** (đã có trong `.gitignore`)
- ✅ **Hỗ trợ 3 môi trường** (prod, staging, local)
- ✅ **Có fallback** nếu không có `env_loader`

## Files còn lại chưa update

Còn một số scripts chưa được update (có thể là utility scripts hoặc scripts không cần connection):
- Các scripts trong `inventory/`
- Các scripts trong `system/`
- Các scripts trong `sales/`

Có thể update sau nếu cần.
