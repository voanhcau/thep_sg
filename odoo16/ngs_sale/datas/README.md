# NGS Sale Data Scripts Directory

Thư mục chứa các script xử lý dữ liệu, import/export và maintenance cho module `ngs_sale`.

## 📁 Cấu trúc thư mục

```
datas/
├── scripts/
│   ├── accounting/     # Scripts xử lý kế toán
│   ├── inventory/      # Scripts xử lý kho hàng  
│   ├── sales/          # Scripts xử lý bán hàng
│   └── system/         # Scripts hệ thống, import/export
├── login_configs/      # File cấu hình kết nối DB
├── configs/            # File cấu hình XML
├── data_files/         # File dữ liệu
│   ├── excel/          # File Excel
│   └── xml/            # File XML data
└── archived/           # File cũ đã lưu trữ
```

## 🔐 Login Configs (`login_configs/`)

| File | Mô tả | Môi trường |
|------|-------|------------|
| `login_local.py` | Kết nối DB local development | Local |
| `login_test.py` | Kết nối DB staging/test | Staging |
| `login_prod.py` | Kết nối DB production | Production |
| `login_27sep*.py` | Kết nối DB ngày 27/9 | Archive |

## 💰 Accounting Scripts (`scripts/accounting/`)

| File | Mô tả | Chức năng |
|------|-------|-----------|
| `01_fix_invoice_order_id_final.py` | Sửa invoice_order_id (phiên bản cuối) | Sửa lỗi liên kết hóa đơn-đơn hàng |
| `02_fix_invoice_order_id_simple.py` | Sửa invoice_order_id (phiên bản đơn giản) | Sửa lỗi cơ bản |
| `03_fix_missing_invoice_order_id_main.py` | Sửa invoice_order_id bị thiếu (chính) | Tìm và sửa ID bị thiếu |
| `04_recompute_invoice_status.py` | Tính lại trạng thái hóa đơn | Đồng bộ trạng thái SO/PO |
| `account_move_reconciliation.py` | Đối soát bút toán kế toán | Reconcile account moves |
| `calculate_interest.py` | Tính lãi suất | Tính toán lãi suất |
| `fix_missing_invoice_order_id_27sep*.py` | Sửa lỗi ngày 27/9 | Archive fixes |

## 📦 Inventory Scripts (`scripts/inventory/`)

| File | Mô tả | Chức năng |
|------|-------|-----------|
| `01_post_inventory_valuation_moves.py` | **POST inventory valuation** | Chuyển từ "Dự thảo" → "Vào sổ" |
| `02_update_inventory_valuation_to_draft.py` | **DRAFT inventory valuation** | Chuyển từ "Vào sổ" → "Dự thảo" |

### 🎯 Chi tiết Inventory Scripts

#### `01_post_inventory_valuation_moves.py`
- **Mục đích**: Chuyển bút toán inventory valuation từ Draft → Posted
- **Điều kiện**: Journal = "inventory valuation", State = "draft"
- **Kết quả**: ~6,962 dòng bút toán được POST
- **Cảnh báo**: ⚠️ Không thể hoàn tác sau khi POST!

#### `02_update_inventory_valuation_to_draft.py`  
- **Mục đích**: Chuyển bút toán inventory valuation từ Posted → Draft
- **Điều kiện**: Journal = "inventory valuation", State = "posted"
- **Kết quả**: Đưa về trạng thái có thể chỉnh sửa

## 🛒 Sales Scripts (`scripts/sales/`)

| File | Mô tả | Chức năng |
|------|-------|-----------|
| `compute_margin_all.py` | Tính margin tất cả sản phẩm | Cập nhật tỷ suất lợi nhuận |
| `update_discount_value_sale_order_line.py` | Cập nhật giá trị chiết khấu | Sửa discount SO lines |
| `update_so.py` | Cập nhật sale order | Cập nhật đơn hàng |

## ⚙️ System Scripts (`scripts/system/`)

| File | Mô tả | Chức năng |
|------|-------|-----------|
| `import_Baremfull.py` | Import dữ liệu Barem | Import bảng lương |
| `import_product_category.py` | Import danh mục sản phẩm | Cập nhật categories |
| `import_product_supplierinfo.py` | Import thông tin nhà cung cấp | Cập nhật supplier info |
| `import_so.py` | Import sale orders | Import đơn hàng |
| `test_*.py` | Test scripts | Kiểm thử các chức năng |
| `run_script_interactive.py` | Chạy script tương tác | Interactive runner |

## 📋 Config Files (`configs/`)

| File | Mô tả |
|------|-------|
| `config_parameter.xml` | Tham số cấu hình hệ thống |
| `cron_invoice_order_id.xml` | Cron job sửa invoice_order_id |
| `res_partner_type_datas.xml` | Dữ liệu loại đối tác |
| `sale_processing_state.xml` | Trạng thái xử lý bán hàng |
| `supplier_delivery_type.xml` | Loại giao hàng nhà cung cấp |

## 📊 Data Files (`data_files/`)

### Excel Files (`data_files/excel/`)
- `Barem-*.xlsm` - File bảng lương theo thời gian
- `Baremfull-*.xlsx` - File bảng lương đầy đủ
- `import_so.xlsm` - Template import sale orders
- `update_so.xlsx` - Template cập nhật sale orders
- `11.11.2024.xlsx` - Dữ liệu ngày 11/11/2024

## 🗄️ Archived (`archived/`)

File cũ, script test, hoặc không còn sử dụng:
- `*oct.script.py` - Scripts tháng 10
- `*apr.py` - Scripts tháng 4  
- `*11.2014.py` - Scripts năm 2014

## 🚀 Cách sử dụng

### 1. Chọn môi trường
```bash
# Development
export LOGIN_CONFIG="login_local"

# Staging  
export LOGIN_CONFIG="login_test"

# Production (cẩn thận!)
export LOGIN_CONFIG="login_prod"
```

### 2. Chạy script
```bash
cd /Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas

# Inventory valuation - POST (Draft → Posted)
python scripts/inventory/01_post_inventory_valuation_moves.py

# Inventory valuation - DRAFT (Posted → Draft)  
python scripts/inventory/02_update_inventory_valuation_to_draft.py

# Fix invoice order ID
python scripts/accounting/01_fix_invoice_order_id_final.py

# Recompute invoice status
python scripts/accounting/04_recompute_invoice_status.py
```

### 3. Non-interactive mode
```bash
# Tự động xác nhận (không cần nhập y/n)
AUTO_CONFIRM=y python scripts/inventory/01_post_inventory_valuation_moves.py
```

## ⚠️ Lưu ý quan trọng

### 🔴 Production Scripts (Nguy hiểm)
- `01_post_inventory_valuation_moves.py` - **KHÔNG THỂ HOÀN TÁC**
- `01_fix_invoice_order_id_final.py` - Thay đổi dữ liệu kế toán
- `04_recompute_invoice_status.py` - Ảnh hưởng trạng thái đơn hàng

### 🟡 Test trước khi Production
1. Luôn test trên `login_test.py` trước
2. Backup database trước khi chạy
3. Chạy trong giờ ít người dùng
4. Có kế hoạch rollback

### 🟢 Safe Scripts
- Các script trong `system/test_*` 
- Scripts chỉ đọc dữ liệu
- Scripts có tính năng dry-run

## 📞 Liên hệ

- **Developer**: Bruce Nguyen
- **Module**: ngs_sale
- **Last Updated**: 2025-09-29

---

💡 **Tip**: Luôn đọc kỹ script trước khi chạy và test trên staging trước!
