# Hướng Dẫn Setup Import Sale Order Config - Multi-Company

## 📋 Tổng Quan

Mỗi công ty cần có 1 `import.sale.order.config` riêng để:
- **Import đơn hàng từ PAKD**: Lấy warehouse, pricelist, payment term từ config
- **Tạo đơn mua**: Lấy warehouse từ config để set picking type

## ✅ Code Đã Được Cập Nhật

### 1. Model `import.sale.order.config`
- ✅ Đã thêm field `company_id` (required)
- ✅ Đã thêm `_check_company_auto = True`
- ✅ Đã thêm `check_company=True` cho các related fields

### 2. Logic Lấy Config

**Import từ PAKD (`import_from_excel()`):**
- ✅ Filter config theo `company_id`
- ✅ Lấy warehouse, payment_term, pricelist từ config

**Tạo đơn mua (`action_create_purchase_order()`):**
- ✅ Ưu tiên 1: Lấy warehouse từ `import.sale.order.config` của company
- ✅ Ưu tiên 2: Lấy warehouse từ sale order
- ✅ Ưu tiên 3: Lấy warehouse đầu tiên của company
- ✅ Fallback: Tìm warehouse KHH (backward compatibility)

## 📝 Cách Setup

### Bước 1: Tạo Config Cho Mỗi Company

1. **Vào Odoo UI:**
   - Sales > Import Config (hoặc Settings > Technical > Database Structure > Models > import.sale.order.config)

2. **Tạo record cho Company 1:**
   - Click **Create**
   - Điền thông tin:
     - **Company**: Company 1 (ví dụ: Nam Sài Gòn)
     - **Kho hàng**: Warehouse của Company 1 (ví dụ: KHH)
     - **Điều khoản thanh toán**: Payment term của Company 1
     - **Bảng giá bán**: Pricelist bán của Company 1
     - **Bảng giá mua**: Pricelist mua của Company 1
   - Click **Save**

3. **Tạo record cho Company 2:**
   - Click **Create**
   - Điền thông tin:
     - **Company**: Company 2 (ví dụ: Thép Nam Sài Gòn)
     - **Kho hàng**: Warehouse của Company 2 (ví dụ: NSG)
     - **Điều khoản thanh toán**: Payment term của Company 2
     - **Bảng giá bán**: Pricelist bán của Company 2
     - **Bảng giá mua**: Pricelist mua của Company 2
   - Click **Save**

### Bước 2: Verify Setup

1. **Kiểm tra Config:**
   - Vào: Sales > Import Config
   - Verify: Mỗi company có 1 record
   - Verify: Các fields đã được điền đầy đủ

2. **Test Import từ PAKD:**
   - Switch sang Company 1
   - Import đơn từ PAKD
   - Verify: Sale order có:
     - Warehouse từ config Company 1
     - Payment term từ config Company 1
     - Pricelist từ config Company 1

3. **Test Tạo Đơn Mua:**
   - Tạo sale order ở Company 1
   - Click "Tạo đơn mua"
   - Verify: Purchase order có picking type từ warehouse trong config Company 1

## 🔍 Logic Chi Tiết

### Khi Import từ PAKD

```
1. Lấy company hiện tại (self.env.user.company_id)
2. Tìm import.sale.order.config với company_id = current company
3. Nếu không tìm thấy → Lấy config đầu tiên (backward compatibility)
4. Tạo sale order với:
   - warehouse_id = config.warehouse_id
   - payment_term_id = config.payment_term_id
   - pricelist_id = config.pricelist_id
   - purchase_pricelist_id = config.purchase_pricelist_id
```

### Khi Tạo Đơn Mua

```
1. Lấy company của purchase order
2. Tìm import.sale.order.config với company_id = purchase company
3. Lấy warehouse theo thứ tự ưu tiên:
   a. Từ config (ưu tiên 1)
   b. Từ sale order (ưu tiên 2)
   c. Warehouse đầu tiên của company (ưu tiên 3)
   d. Warehouse KHH của company (fallback)
4. Tìm picking type từ warehouse
5. Set picking_type_id vào purchase order
```

## ⚠️ Lưu Ý

1. **Mỗi company phải có 1 config:**
   - Nếu không có config, sẽ dùng config đầu tiên (backward compatibility)
   - Nên tạo config cho tất cả các company

2. **Warehouse phải có picking type:**
   - Warehouse trong config phải có picking type với:
     - `sequence_code` = 'IN'
     - `code` = 'incoming'
   - Nếu không có, sẽ báo lỗi khi tạo đơn mua

3. **Company ID phải đúng:**
   - Config phải có `company_id` đúng với company cần dùng
   - Nếu sai, sẽ lấy config của company khác

## 📊 Example

**Company 1 (Nam Sài Gòn):**
```
import.sale.order.config:
  - company_id: 1 (Nam Sài Gòn)
  - warehouse_id: KHH (Kho HH)
  - payment_term_id: Thanh toán 30 ngày
  - pricelist_id: Bảng giá bán Company 1
  - purchase_pricelist_id: Bảng giá mua Company 1
```

**Company 2 (Thép Nam Sài Gòn):**
```
import.sale.order.config:
  - company_id: 2 (Thép Nam Sài Gòn)
  - warehouse_id: NSG (Kho NSG)
  - payment_term_id: Thanh toán 45 ngày
  - pricelist_id: Bảng giá bán Company 2
  - purchase_pricelist_id: Bảng giá mua Company 2
```

## 🔗 Files Đã Cập Nhật

- `models/sale_order.py` - Logic import và tạo đơn mua
- `wizards/import_sale_order_config.py` - Model config (đã thêm company_id)
- `wizards/import_sale_order_config.xml` - View config (đã thêm company_id vào tree view)
