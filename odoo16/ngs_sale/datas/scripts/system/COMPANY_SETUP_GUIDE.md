# Hướng Dẫn Setup Công Ty Mới và Import Cấu Hình Kế Toán

## 📋 Tổng Quan

Tài liệu này hướng dẫn cách setup một công ty mới trong Odoo và import cấu hình kế toán từ công ty hiện tại.

## 🎯 Mục Tiêu

1. Export cấu hình kế toán từ công ty nguồn
2. Tạo công ty mới
3. Import cấu hình kế toán vào công ty mới
4. Thiết lập các cấu hình cần thiết cho công ty mới

## 📦 Các Cấu Hình Được Export/Import

### 1. Chart of Accounts (Bảng tài khoản)
- Tất cả các tài khoản kế toán
- Account Groups (Nhóm tài khoản)
- Account Tags (Thẻ tài khoản)

### 2. Journals (Sổ nhật ký)
- Sales Journal
- Purchase Journal
- Bank Journal
- Cash Journal
- Miscellaneous Journal

### 3. Taxes (Thuế)
- Tax Groups (Nhóm thuế)
- Tax Rules (Quy tắc thuế)
- Tax Accounts (Tài khoản thuế)

### 4. Fiscal Positions (Vị trí tài chính)
- Fiscal Position Rules
- Tax Mappings
- Account Mappings

### 5. Payment Terms (Điều khoản thanh toán)
- Payment Term Lines

### 6. Company Settings (Cài đặt công ty)
- Sale Description
- Purchase Description
- Signature Settings
- Interest Calculation Settings
- Delivery Receipt Settings

### 7. Config Parameters (Tham số cấu hình)
- Payment Term Calculation
- Delivery Receipt Notes

## 🚀 Các Bước Thực Hiện

### Bước 1: Export Cấu Hình Từ Công Ty Nguồn

```bash
cd /Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/scripts/system

# Export từ công ty ID 1 (local)
python export_accounting_config.py local 1

# Export từ công ty ID 1 (staging)
python export_accounting_config.py staging 1

# Export từ công ty ID 1 (production)
python export_accounting_config.py prod 1
```

**Output:** File JSON sẽ được tạo với tên: `accounting_config_company_1_YYYYMMDD_HHMMSS.json`

### Bước 2: Tạo Công Ty Mới (Nếu chưa có)

#### Cách 1: Tạo thủ công trong Odoo UI
1. Vào **Settings > Companies & Contacts > Companies**
2. Click **Create**
3. Điền thông tin:
   - **Name**: Tên công ty mới
   - **Country**: Vietnam
   - **Currency**: VND
   - **Phone, Email, Address**: Thông tin liên hệ
4. Click **Save**

#### Cách 2: Script sẽ tự động tạo (nếu không chỉ định company_id)

### Bước 3: Import Cấu Hình Vào Công Ty Mới

```bash
# Import vào công ty ID 2 với tên "Công Ty Mới"
python import_accounting_config.py local accounting_config_company_1_20250101_120000.json 2 "Công Ty Mới"

# Hoặc để script tự tạo công ty mới
python import_accounting_config.py local accounting_config_company_1_20250101_120000.json None "Công Ty Mới"
```

### Bước 4: Thiết Lập Bổ Sung Cho Công Ty Mới

Sau khi import, cần thiết lập thêm các mục sau:

#### 4.1. Cấu Hình Công Ty (res.company)

**Trong Odoo UI:**
1. Vào **Settings > Companies & Contacts > Companies**
2. Chọn công ty mới
3. Cập nhật các thông tin:
   - **VAT Number**: Mã số thuế
   - **Street, City, State, Country**: Địa chỉ
   - **Phone, Email, Website**: Thông tin liên hệ
   - **Logo**: Logo công ty

**Các field custom từ ngs_sale đã được import tự động:**
- `sale_description`: Nội dung và điều khoản bán hàng
- `purchase_description`: Nội dung và điều khoản mua hàng
- `signature`: Chữ ký
- `signature_so`: Hiển thị chữ ký lên YCBG
- `signature_po`: Hiển thị chữ ký lên XNKG
- `interest_calculation_extra_days`: Số ngày bổ sung tính lãi vay
- `delivery_receipt_construction_site`: HTML mặc định cho biên bản giao nhận
- `delivery_receipt_footer_notes`: Ghi chú cuối biên bản giao nhận
- `hide_report_footer`: Ẩn footer báo cáo

#### 4.2. Cấu Hình Kế Toán (Accounting Settings)

**Trong Odoo UI:**
1. Vào **Accounting > Configuration > Settings**
2. Chọn công ty mới
3. Cấu hình:
   - **Chart of Accounts**: Đã được import
   - **Fiscal Year**: Thiết lập năm tài chính
   - **Tax Calculation**: Rounding Method
   - **Currency**: Đồng tiền chính

#### 4.3. Cấu Hình Journals (Sổ Nhật Ký)

**Kiểm tra và cấu hình:**
1. Vào **Accounting > Configuration > Journals**
2. Kiểm tra các journals đã được import:
   - **Sales Journal**: Sổ bán hàng
   - **Purchase Journal**: Sổ mua hàng
   - **Bank Journal**: Sổ ngân hàng
   - **Cash Journal**: Sổ tiền mặt
3. Cập nhật **Default Accounts** nếu cần
4. Cấu hình **Sequence** cho mỗi journal

#### 4.4. Cấu Hình Taxes (Thuế)

**Kiểm tra:**
1. Vào **Accounting > Configuration > Taxes**
2. Kiểm tra các taxes đã được import
3. Verify **Tax Accounts** đã được map đúng
4. Kiểm tra **Tax Groups**

#### 4.5. Cấu Hình Fiscal Positions

**Kiểm tra:**
1. Vào **Accounting > Configuration > Fiscal Positions**
2. Kiểm tra các fiscal positions đã được import
3. Verify **Tax Mappings** và **Account Mappings**

#### 4.6. Cấu Hình Payment Terms

**Kiểm tra:**
1. Vào **Accounting > Configuration > Payment Terms**
2. Kiểm tra các payment terms đã được import
3. Verify **Payment Term Lines**

#### 4.7. Cấu Hình Users & Access Rights

**Thiết lập quyền truy cập:**
1. Vào **Settings > Users & Companies > Users**
2. Assign users vào công ty mới
3. Cấu hình **Access Rights** cho từng user

#### 4.8. Cấu Hình Warehouse & Locations

**Nếu sử dụng Inventory:**
1. Vào **Inventory > Configuration > Warehouses**
2. Tạo warehouse cho công ty mới
3. Cấu hình **Stock Locations**

#### 4.9. Cấu Hình Products & Categories

**Nếu cần:**
1. Import products từ công ty nguồn (nếu cần)
2. Cấu hình **Product Categories**
3. Cấu hình **Pricelists**

#### 4.10. Cấu Hình Partners

**Nếu cần:**
1. Import partners từ công ty nguồn (nếu cần)
2. Cấu hình **Partner Categories**
3. Cấu hình **Payment Terms** cho partners

## ⚠️ Lưu Ý Quan Trọng

### 1. Backup Database
**LUÔN backup database trước khi import:**
```bash
# Backup Odoo database
pg_dump -U odoo -d database_name > backup_before_import.sql
```

### 2. Test Trên Staging Trước
- Luôn test trên staging environment trước
- Verify tất cả cấu hình đã import đúng
- Test các workflows cơ bản

### 3. ID Mapping
- Script tự động map old IDs -> new IDs
- Một số relationships có thể cần điều chỉnh thủ công

### 4. Currency & Country
- Đảm bảo currency và country được set đúng
- Vietnam: Country ID = 241, Currency = VND

### 5. Sequences
- Journal sequences cần được reset cho công ty mới
- Check **Settings > Technical > Sequences**

### 6. Fiscal Year
- Thiết lập **Fiscal Year** cho công ty mới
- Vào **Accounting > Configuration > Fiscal Years**

### 7. Opening Balances
- Nếu cần, nhập **Opening Balances** cho các tài khoản
- Vào **Accounting > Configuration > Chart of Accounts > Opening Balances**

## 🔍 Checklist Sau Khi Import

- [ ] Company information đã được cập nhật đầy đủ
- [ ] Chart of Accounts đã được import đúng
- [ ] Journals đã được tạo và cấu hình đúng
- [ ] Taxes đã được import và map đúng accounts
- [ ] Fiscal Positions đã được import
- [ ] Payment Terms đã được import
- [ ] Company custom settings đã được import
- [ ] Config parameters đã được import
- [ ] Users đã được assign vào công ty mới
- [ ] Access rights đã được cấu hình
- [ ] Sequences đã được reset
- [ ] Fiscal Year đã được thiết lập
- [ ] Test tạo invoice thành công
- [ ] Test tạo payment thành công
- [ ] Test reports hoạt động đúng

## 🐛 Troubleshooting

### Lỗi: Account not found
- Kiểm tra account code có đúng không
- Verify account đã được import

### Lỗi: Journal sequence error
- Reset journal sequence
- Vào **Settings > Technical > Sequences**

### Lỗi: Tax mapping error
- Kiểm tra tax accounts đã được map
- Verify fiscal positions

### Lỗi: Currency mismatch
- Kiểm tra currency của company
- Verify currency của accounts

## 📞 Support

Nếu gặp vấn đề, liên hệ dev team hoặc check logs:
```bash
# Check Odoo logs
tail -f /var/log/odoo/odoo.log
```

## 📚 Tài Liệu Tham Khảo

- [Odoo Accounting Documentation](https://www.odoo.com/documentation/16.0/applications/finance.html)
- [Odoo Multi-Company Setup](https://www.odoo.com/documentation/16.0/applications/general/companies.html)
