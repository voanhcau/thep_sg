# Migrate Company Settings - Hướng Dẫn Đầy Đủ

Scripts để export/import cấu hình kế toán và setup công ty mới trong Odoo.

## 📁 Files

- `export_accounting_config.py` - Export cấu hình kế toán từ công ty nguồn
- `import_accounting_config.py` - Import cấu hình kế toán vào công ty mới
- `test_import_verification.py` - Test tự động và verification
- `setup_new_company.sh` - Helper script để chạy export/import dễ dàng
- `delete_companies.py` / `delete_companies.sql` - Xóa công ty (cẩn thận!)

---

## 🚀 Quick Start

### Task 1: Clone Accounting Config từ Company 1 → Company 2

#### Bước 1: Export từ Company 1
```bash
cd /Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/scripts/migrate-company-settings
python3 export_accounting_config.py local 1
```

Output: `accounting_config_company_1_YYYYMMDD_HHMMSS.json`

#### Bước 2: Import vào Company 2
```bash
python3 import_accounting_config.py test accounting_config_company_1_*.json 2
```

### Task 2: Setup Contacts cho Company 2

Sau khi Task 1 hoàn thành, chạy:
```bash
cd /Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas/scripts/system
python3 setup_company_2_contacts.py test
```

Script này sẽ:
- Set `property_account_receivable_id = 131` cho tất cả contacts
- Set `property_account_payable_id = 331` cho tất cả contacts
- Set Payment Terms "Thanh toán ngay"
- Set Price List "[Bán] Mặc định (VND)"

**Lưu ý**: Chỉ set nếu chưa có giá trị (không override)

---

## 🧪 Test Tự Động

### Chạy Test & Verification

```bash
# Test với công ty đã tồn tại (Company 2)
python3 test_import_verification.py test 1 2 "Thép Nam Sài Gòn"

# Test với công ty mới (tự động tạo)
python3 test_import_verification.py test 1 None "Tên Công Ty Test"
```

Script sẽ tự động:
1. ✅ Export từ công ty nguồn
2. ✅ Import vào công ty đích
3. ✅ Verify data trước và sau import
4. ✅ Test workflows cơ bản
5. ✅ Tạo test report chi tiết

### Test Report

Sau khi chạy, script tạo file `test_report_YYYYMMDD_HHMMSS.md` với:
- Test summary (pass rate, counts)
- Detailed verification results cho từng model
- Workflow test results
- Recommendations
- Next steps

---

## 📊 Các Cấu Hình Được Export/Import

### ✅ Accounting (Kế Toán) - HOÀN CHỈNH

- ✅ **Chart of Accounts** (222 accounts)
- ✅ **Account Groups** (nếu có)
- ✅ **Journals** (21 journals) + Bank Account mapping
- ✅ **Taxes** (4 taxes) + Repartition Lines
- ✅ **Tax Groups** (2 groups)
- ✅ **Fiscal Positions** (3 positions) + Tax/Account mappings
- ✅ **Payment Terms** (CHỈ những cái có company_id)
- ✅ **Account Tags** (3 tags)
- ✅ **Bank Accounts** (res.partner.bank)
- ✅ **Config Parameters** (nsgerp.*)
- ✅ **Sequences** (ir.sequence cho journals và account moves)
- ✅ **Reconcile Models** (account.reconcile.model)

### ⚠️ Master Data Dùng Chung (SKIP Export/Import)

Các master data sau **KHÔNG có `company_id`**, nghĩa là **dùng chung** giữa tất cả các công ty. **KHÔNG CẦN** export/import:

1. **res.partner.type** - Dùng chung
2. **supplier.delivery.type** - Dùng chung
3. **sale.processing.state** - Dùng chung
4. **sale.order.fee** - Dùng chung
5. **purchase.report.tool** - Dùng chung
6. **UOM Categories** - Dùng chung
7. **UOM Units** - Dùng chung
8. **Product Categories** - Dùng chung (trong Odoo 16)
9. **Payment Methods** - Dùng chung

### ⚠️ Master Data Cần Setup Thủ Công

- **Warehouses** - Cấu trúc phức tạp, cần setup thủ công
- **sale.commission.rate** - Cần supplier mapping
- **sale.commission.config** - Cần commission_tool mapping
- **sale.barem** - Cần supplier/product mapping

---

## ⚙️ Company Settings

### Custom Fields từ ngs_sale Module

Các fields sau cần module `ngs_sale` được cài đặt trên công ty đích:

- `sale_description`
- `purchase_description`
- `signature`, `signature_so`, `signature_po`
- `interest_calculation_extra_days`
- `delivery_receipt_construction_site`
- `delivery_receipt_footer_notes`
- `hide_report_footer`

**Cách setup**: Sau khi import, vào **Settings > Companies & Contacts > Companies** và set các fields này thủ công.

### Anglo-Saxon Accounting

**Anglo-Saxon Accounting** là một setting có thể bật/tắt cho từng công ty.

#### Sự Khác Biệt

- **Anglo-Saxon (Bật)**: COGS được ghi nhận khi **bán hàng**
- **Continental (Tắt)**: COGS được ghi nhận khi **mua hàng**

#### Yêu Cầu

- Module `account_anglo_saxon` phải được cài đặt
- Script export/import đã tự động xử lý field này

#### Cách Bật

1. Vào: **Settings > Companies & Contacts > Companies**
2. Chọn công ty
3. Tìm field: **Anglo-Saxon Accounting**
4. Check để bật

---

## 🎯 Best Practices

### 1. Luôn Backup Database Trước Khi Import

```bash
pg_dump -U postgres -d database_name > backup_before_import.sql
```

### 2. Test Trên Test Environment Trước

- Test trên `http://test.thepnamsaigon.com/` trước
- Verify kết quả
- Sau đó mới chạy trên production

### 3. Thứ Tự Thực Hiện

1. **Task 1**: Clone accounting config (export → import)
2. **Task 2**: Setup contacts (property accounts, payment terms, pricelist)
3. **Verify**: Chạy test verification
4. **Manual Setup**: Setup warehouses, custom fields, etc.

### 4. Chỉ Set Nếu Chưa Có (No Override)

Tất cả scripts đều **chỉ set nếu chưa có giá trị**, không override giá trị hiện có.

### 5. Verify Sau Khi Import

Luôn chạy `test_import_verification.py` sau khi import để verify:
- Số lượng records đúng
- Data integrity
- Workflows hoạt động

---

## 🔧 Troubleshooting

### Lỗi: "Custom fields require ngs_sale module"

**Nguyên nhân**: Module `ngs_sale` chưa được cài đặt trên công ty đích.

**Giải pháp**:
1. Vào: **Apps > Search 'ngs_sale' > Install**
2. Sau đó set các custom fields thủ công trong company settings

### Lỗi: "Account code not found in target company"

**Nguyên nhân**: Account code không tồn tại trong công ty đích.

**Giải pháp**: Đảm bảo đã clone accounting config (Task 1) trước khi chạy Task 2.

### Lỗi: "Warehouse needs manual setup"

**Nguyên nhân**: Warehouse có cấu trúc phức tạp (locations, routes, etc.).

**Giải pháp**: Setup warehouse thủ công trong Odoo UI:
1. Vào: **Inventory > Configuration > Warehouses**
2. Tạo warehouse mới hoặc copy từ warehouse mẫu

---

## ⚠️ Xóa Công Ty (Cẩn Thận!)

### Cảnh Báo

Script xóa công ty sẽ **XÓA VĨNH VIỄN** công ty và tất cả data liên quan!
**Hãy backup database trước khi chạy!**

### Cách Xóa

#### Cách 1: SQL Script (Khuyến nghị)

```bash
# Backup trước
pg_dump -U postgres -d database_name > backup_before_delete.sql

# Chạy SQL script
psql -U postgres -d database_name -f delete_companies.sql
```

#### Cách 2: Python Script

```bash
python3 delete_companies.py [env] [company_ids]
```

**Lưu ý**: Cần xóa `ir.property` trước để tránh duplicate key constraint.

---

## 📝 Manual Setup Checklist

Sau khi import, cần setup thủ công:

- [ ] Install module `ngs_sale` trên công ty mới
- [ ] Set custom fields trong company settings
- [ ] Setup warehouses (nếu cần)
- [ ] Assign users to company
- [ ] Configure access rights
- [ ] Setup fiscal year
- [ ] Test creating invoices
- [ ] Test creating sales orders
- [ ] Verify reports work correctly

---

## 📚 Tham Khảo

- Odoo Documentation: [Multi-Company](https://www.odoo.com/documentation/16.0/developer/reference/backend/orm.html#multi-company)
- Odoo Documentation: [Property Fields](https://www.odoo.com/documentation/16.0/developer/reference/backend/orm.html#property-fields)

---

## 💡 Tips

1. **Luôn chạy test verification** sau khi import
2. **Review test report** để phát hiện vấn đề sớm
3. **Backup thường xuyên** trước khi thực hiện thay đổi lớn
4. **Test trên test environment** trước khi chạy production
5. **Document các thay đổi** để dễ traceback sau này

---

**Last Updated**: 2026-01-05
