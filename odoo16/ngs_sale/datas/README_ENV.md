# Environment Variables Setup - Hướng dẫn sử dụng

## Tổng quan

Tất cả scripts đã được cập nhật để hỗ trợ **3 môi trường**:
- **PROD** (Production): `http://erp.thepnamsaigon.com`
- **STAGING** (Test): `http://test.thepnamsaigon.com`
- **LOCAL** (Development): `http://localhost:6069`

## Cài đặt

### 1. Tạo file .env

```bash
cd /Users/brucenguyen/Source/16
cp .env.example .env
nano .env  # Chỉnh sửa với thông tin thực tế
```

### 2. Load environment variables

```bash
# Load PROD (default)
source load_env.sh

# Load STAGING
source load_env.sh staging

# Load LOCAL
source load_env.sh local
```

## Cách sử dụng trong scripts

### Cách 1: Sử dụng env_loader (Khuyến nghị)

```python
import sys
from pathlib import Path

# Add login_configs to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))
from env_loader import setup_odoo_connection

# Lấy environment type từ command line
env_type = sys.argv[1] if len(sys.argv) > 1 else None

# Setup connection
url, db, username, password, models, uid = setup_odoo_connection(env_type)
```

**Usage:**
```bash
python script.py          # Dùng default (PROD)
python script.py prod     # Dùng PROD
python script.py staging # Dùng STAGING
python script.py local    # Dùng LOCAL
```

### Cách 2: Sử dụng environment variables trực tiếp

```python
import os

url = os.getenv("ODOO_URL")
db = os.getenv("ODOO_DB")
username = os.getenv("ODOO_USERNAME")
password = os.getenv("ODOO_PASSWORD")

if not all([url, db, username, password]):
    print("❌ Missing environment variables")
    print("   Run: source load_env.sh [prod|staging|local]")
    sys.exit(1)
```

**Usage:**
```bash
source load_env.sh staging
python script.py
```

## Template Script

Xem file `scripts/SCRIPT_TEMPLATE.py` để có template đầy đủ.

## Files đã được cập nhật

Tất cả scripts trong `datas/scripts/` đã được cập nhật để:
- ✅ Không còn hardcoded credentials
- ✅ Hỗ trợ 3 môi trường
- ✅ Đọc từ .env file
- ✅ Có validation và error handling

## Migration Guide

Để update script cũ sang format mới:

1. **Thêm import env_loader:**
   ```python
   import sys
   from pathlib import Path
   sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'login_configs'))
   from env_loader import setup_odoo_connection
   ```

2. **Thay thế phần connection:**
   ```python
   # OLD:
   url = os.getenv("ODOO_URL", "http://localhost:6069")
   db = os.getenv("ODOO_DB")
   # ... connect manually
   
   # NEW:
   env_type = sys.argv[1] if len(sys.argv) > 1 else None
   url, db, username, password, models, uid = setup_odoo_connection(env_type)
   ```

3. **Thêm command line argument support:**
   ```python
   env_type = sys.argv[1] if len(sys.argv) > 1 else None
   ```

## Security Notes

- ⚠️ **KHÔNG commit file `.env` vào git**
- ✅ File `.env` đã được thêm vào `.gitignore`
- ✅ Tất cả hardcoded credentials đã được xóa
- ✅ Chỉ có `.env.example` được commit (không chứa thông tin nhạy cảm)
