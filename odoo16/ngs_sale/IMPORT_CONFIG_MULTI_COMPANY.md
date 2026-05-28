# Import Sale Order Config - Multi-Company Setup

## 📋 Tổng Quan

Mỗi công ty cần có 1 `import.sale.order.config` riêng để:
- **Import đơn hàng từ PAKD**: Lấy warehouse, pricelist, payment term từ config
- **Tạo đơn mua**: Lấy warehouse từ config để set picking type

## ⚙️ Cấu Hình Model

### Model: `import.sale.order.config`

**Fields:**
- `company_id` (required): Công ty - mỗi công ty có 1 config riêng
- `warehouse_id` (required): Kho hàng - dùng cho import và tạo đơn mua
- `payment_term_id` (required): Điều khoản thanh toán - dùng cho import
- `pricelist_id` (required): Bảng giá bán - dùng cho import
- `purchase_pricelist_id` (required): Bảng giá mua - dùng cho import

**Constraint:**
- `_check_company_auto = True`: Tự động check company cho các related fields

## 🔄 Logic Lấy Config

### 1. Import Đơn Hàng từ PAKD (`import_from_excel()`)

**Location:** `models/sale_order.py` - dòng ~511-521

**Logic:**
```python
# Lấy config theo company để support multi-company
company = self.env.user.company_id
setting = self.env['import.sale.order.config'].search([
    ('company_id', '=', company.id)
], limit=1)

# Fallback: Nếu không tìm thấy config theo company, lấy config đầu tiên (backward compatibility)
if not setting:
    setting = self.env['import.sale.order.config'].search([], limit=1)
    if setting:
        _logger.warning(f"Không tìm thấy import.sale.order.config cho company {company.name}, sử dụng config mặc định")
```

**Sử dụng:**
- `warehouse_id`: Set vào sale order khi import
- `payment_term_id`: Set vào sale order khi import
- `pricelist_id`: Set vào sale order khi import
- `purchase_pricelist_id`: Set vào sale order khi import

### 2. Tạo Đơn Mua (`action_create_purchase_order()`)

**Location:** `models/sale_order.py` - dòng ~943-985

**Logic lấy warehouse (theo thứ tự ưu tiên):**

1. **Ưu tiên 1**: Lấy từ `import.sale.order.config` của company
   ```python
   import_config = self.env['import.sale.order.config'].search([
       ('company_id', '=', company.id)
   ], limit=1)
   if import_config and import_config.warehouse_id:
       warehouse = import_config.warehouse_id
   ```

2. **Ưu tiên 2**: Lấy từ sale order (nếu có)
   ```python
   elif self.warehouse_id:
       warehouse = self.warehouse_id
   ```

3. **Ưu tiên 3**: Tìm warehouse đầu tiên của company
   ```python
   else:
       warehouse = self.env['stock.warehouse'].search([
           ('company_id', '=', company.id)
       ], limit=1, order='id')
   ```

4. **Fallback**: Tìm warehouse với code KHH (backward compatibility)
   ```python
   if not warehouse:
       warehouse = self.env['stock.warehouse'].search([
           ('code', '=', 'KHH'),
           ('company_id', '=', company.id)
       ], limit=1)
   ```

**Sử dụng:**
- `warehouse_id`: Tìm picking type để set vào purchase order

## 📝 Setup Cho Mỗi Company

### Bước 1: Tạo Config Cho Mỗi Company

1. Vào: **Settings > Technical > Database Structure > Models**
2. Tìm model: `import.sale.order.config`
3. Tạo record cho mỗi company:

**Company 1:**
- `company_id`: Company 1
- `warehouse_id`: Warehouse của Company 1 (ví dụ: KHH)
- `payment_term_id`: Payment term của Company 1
- `pricelist_id`: Pricelist bán của Company 1
- `purchase_pricelist_id`: Pricelist mua của Company 1

**Company 2:**
- `company_id`: Company 2
- `warehouse_id`: Warehouse của Company 2 (ví dụ: NSG)
- `payment_term_id`: Payment term của Company 2
- `pricelist_id`: Pricelist bán của Company 2
- `purchase_pricelist_id`: Pricelist mua của Company 2

### Bước 2: Verify

1. **Test Import từ PAKD:**
   - Switch sang Company 1
   - Import đơn từ PAKD
   - Verify: Sale order có warehouse, pricelist, payment term từ config Company 1

2. **Test Tạo Đơn Mua:**
   - Tạo sale order ở Company 1
   - Click "Tạo đơn mua"
   - Verify: Purchase order có picking type từ warehouse trong config Company 1

3. **Test Multi-Company:**
   - Company 1: Import đơn → Warehouse từ config Company 1
   - Company 2: Import đơn → Warehouse từ config Company 2

## ✅ Verification Checklist

- [ ] Mỗi company có 1 `import.sale.order.config` record
- [ ] Config có `company_id` đúng
- [ ] Config có `warehouse_id` đúng (warehouse của company đó)
- [ ] Config có `payment_term_id` đúng
- [ ] Config có `pricelist_id` đúng
- [ ] Config có `purchase_pricelist_id` đúng
- [ ] Test import từ PAKD: Warehouse lấy từ config đúng
- [ ] Test tạo đơn mua: Warehouse lấy từ config đúng

## 🔍 Troubleshooting

### Lỗi: "Không tìm thấy import.sale.order.config cho company X"

**Nguyên nhân:** Chưa tạo config cho company đó

**Giải pháp:**
1. Tạo `import.sale.order.config` cho company
2. Set đầy đủ các fields: warehouse_id, payment_term_id, pricelist_id, purchase_pricelist_id

### Lỗi: "Không tìm thấy phương thức vận chuyển"

**Nguyên nhân:** Warehouse trong config không có picking type incoming

**Giải pháp:**
1. Kiểm tra warehouse có picking type với:
   - `sequence_code` = 'IN'
   - `code` = 'incoming'
2. Nếu không có, tạo picking type cho warehouse

### Warehouse không đúng khi import

**Nguyên nhân:** Config không filter theo company

**Giải pháp:**
1. Verify config có `company_id` đúng
2. Verify code filter theo `company_id` khi search config

## 📊 Flow Diagram

```
Import từ PAKD:
  → Lấy company hiện tại
  → Tìm import.sale.order.config (company_id = current company)
  → Lấy warehouse_id, payment_term_id, pricelist_id, purchase_pricelist_id
  → Tạo sale order với các giá trị từ config

Tạo đơn mua:
  → Lấy company của purchase order
  → Tìm import.sale.order.config (company_id = purchase company)
  → Lấy warehouse_id từ config (ưu tiên 1)
  → Tìm picking type từ warehouse
  → Set picking_type_id vào purchase order
```

## 🔗 Related Files

- `models/sale_order.py` - Logic import và tạo đơn mua
- `wizards/import_sale_order_config.py` - Model config
- `wizards/import_sale_order_config.xml` - View config
