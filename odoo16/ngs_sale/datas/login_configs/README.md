# Login Configuration Files

## 🔐 Cấu hình kết nối Database

| File | Môi trường | Database | URL |
|------|------------|----------|-----|
| `login_local.py` | **Development** | `16.thepnamsaigon.27.09.2025` | `localhost:6069` |
| `login_test.py` | **Staging** | `test.thepnamsaigon.com` | `test.thepnamsaigon.com` |
| `login_prod.py` | **Production** | `thepnamsaigon.com` | `thepnamsaigon.com` |

## 📋 Archive Files
- `login_27sep*.py` - Backup configs từ ngày 27/9
- `login_interactive.py` - Config cho interactive mode

## 🚀 Sử dụng trong scripts

```python
# Import theo môi trường
from login_local import uid, password, db, models    # Local
from login_test import uid, password, db, models     # Staging  
from login_prod import uid, password, db, models     # Production
```

## ⚠️ Bảo mật

- **KHÔNG** commit file `login_prod.py` lên Git
- **LUÔN** test trên staging trước khi production
- **Kiểm tra** database name trước khi chạy script
