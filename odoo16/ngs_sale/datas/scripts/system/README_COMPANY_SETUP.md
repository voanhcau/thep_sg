# Setup Công Ty Mới - Quick Start Guide

## 🚀 Sử Dụng Nhanh

### 1. Export Cấu Hình Từ Công Ty Hiện Tại

```bash
cd /Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/scripts/system

# Export từ công ty ID 1 (local)
./setup_new_company.sh local export 1

# Hoặc dùng trực tiếp Python
python3 export_accounting_config.py local 1
```

**Output:** File JSON sẽ được tạo: `accounting_config_company_1_YYYYMMDD_HHMMSS.json`

### 2. Import Cấu Hình Vào Công Ty Mới

```bash
# Import vào công ty ID 2 với tên "Công Ty Mới"
./setup_new_company.sh local import accounting_config_company_1_20250101_120000.json 2 "Công Ty Mới"

# Hoặc dùng trực tiếp Python
python3 import_accounting_config.py local accounting_config_company_1_20250101_120000.json 2 "Công Ty Mới"
```

## 📋 Các Cấu Hình Được Import

✅ Chart of Accounts (Bảng tài khoản)  
✅ Account Groups (Nhóm tài khoản)  
✅ Journals (Sổ nhật ký)  
✅ Taxes (Thuế)  
✅ Tax Groups (Nhóm thuế)  
✅ Fiscal Positions (Vị trí tài chính)  
✅ Payment Terms (Điều khoản thanh toán)  
✅ Company Custom Settings (Cài đặt công ty)  
✅ Config Parameters (Tham số cấu hình)  

## ⚙️ Sau Khi Import - Cần Thiết Lập Thêm

1. **Company Information**: VAT, Address, Contact Info
2. **Users & Access Rights**: Assign users vào công ty mới
3. **Sequences**: Reset journal sequences
4. **Fiscal Year**: Thiết lập năm tài chính
5. **Warehouses**: Tạo warehouse nếu dùng Inventory

Xem chi tiết trong [COMPANY_SETUP_GUIDE.md](./COMPANY_SETUP_GUIDE.md)

## 🔧 Environment Variables

Scripts sử dụng environment variables từ `.env` file hoặc có thể set trực tiếp:

```bash
export ODOO_URL_LOCAL="http://localhost:6069"
export ODOO_DB_LOCAL="16.thepnamsaigon.03.11.2025"
export ODOO_USERNAME_LOCAL="nsgit"
export ODOO_PASSWORD_LOCAL="1"
```

## ⚠️ Lưu Ý

- **LUÔN backup database trước khi import**
- **Test trên staging trước khi production**
- **Verify tất cả cấu hình sau khi import**

## 📞 Support

Xem [COMPANY_SETUP_GUIDE.md](./COMPANY_SETUP_GUIDE.md) để biết chi tiết và troubleshooting.
