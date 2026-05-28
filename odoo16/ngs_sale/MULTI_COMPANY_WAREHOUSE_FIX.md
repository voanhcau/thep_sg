# Fix Multi-Company Warehouse Selection

## 📋 Vấn Đề

Khi tạo đơn mua và import/tạo đơn từ PAKD, code đang hardcode warehouse:
1. **Hardcode warehouse code 'KHH'** trong `action_create_purchase_order()` (dòng 934-936)
2. **Lấy warehouse từ config không filter theo company** trong `import_from_excel()` (dòng 511, 551)

Điều này không phù hợp với mô hình multi-company vì:
- Mỗi company có warehouse riêng
- Không thể hardcode theo 1 mã kho
- Config cần phải theo company

## ✅ Giải Pháp

### 1. Fix `action_create_purchase_order()` - Lấy Warehouse Tự Động

**Trước:**
```python
# Hardcode tìm warehouse với code 'KHH'
warehouse = self.env['stock.warehouse'].search([
    ('code', '=', 'KHH')
], limit=1)
```

**Sau:**
```python
# Lấy warehouse từ company - support multi-company
company = purchase.company_id if purchase else self.company_id
warehouse = None

# Ưu tiên 1: Lấy warehouse từ sale order nếu có
if self.warehouse_id:
    warehouse = self.warehouse_id
# Ưu tiên 2: Tìm warehouse đầu tiên của company
else:
    warehouse = self.env['stock.warehouse'].search([
        ('company_id', '=', company.id)
    ], limit=1, order='id')
    # Fallback: Tìm warehouse với code KHH (backward compatibility)
    if not warehouse:
        warehouse = self.env['stock.warehouse'].search([
            ('code', '=', 'KHH'),
            ('company_id', '=', company.id)
        ], limit=1)
```

**Logic:**
1. Ưu tiên: Lấy warehouse từ sale order (nếu có)
2. Thứ 2: Lấy warehouse đầu tiên của company
3. Fallback: Tìm warehouse KHH của company (backward compatibility)

### 2. Fix `import_from_excel()` - Filter Config Theo Company

**Trước:**
```python
setting = self.env['import.sale.order.config'].search([], limit=1)
```

**Sau:**
```python
# Lấy config theo company để support multi-company
company = self.env.user.company_id
setting = self.env['import.sale.order.config'].search([
    ('company_id', '=', company.id)
], limit=1)

# Fallback: Nếu không tìm thấy config theo company, lấy config đầu tiên (backward compatibility)
if not setting:
    setting = self.env['import.sale.order.config'].search([], limit=1)
```

### 3. Thêm `company_id` vào Model `import.sale.order.config`

**Thêm field:**
```python
company_id = fields.Many2one('res.company', string=u'Công ty', required=True, default=lambda self: self.env.company)
```

**Thêm `_check_company_auto = True`** để tự động check company cho các related fields.

## 📝 Files Đã Sửa

1. **`models/sale_order.py`**
   - Fix `action_create_purchase_order()`: Lấy warehouse tự động theo company
   - Fix `import_from_excel()`: Filter config theo company

2. **`wizards/import_sale_order_config.py`**
   - Thêm field `company_id`
   - Thêm `_check_company_auto = True`
   - Thêm `check_company=True` cho các related fields

## 🔄 Migration Steps

### Bước 1: Update Code
- Code đã được update trong các files trên

### Bước 2: Update Database
Cần chạy migration để:
1. Thêm field `company_id` vào bảng `import_sale_order_config`
2. Set `company_id` cho các records hiện có (nếu có)

**SQL Migration (nếu cần):**
```sql
-- Thêm column company_id
ALTER TABLE import_sale_order_config ADD COLUMN company_id INTEGER;
ALTER TABLE import_sale_order_config ADD CONSTRAINT import_sale_order_config_company_id_fkey 
    FOREIGN KEY (company_id) REFERENCES res_company(id);

-- Set company_id cho records hiện có (lấy company đầu tiên)
UPDATE import_sale_order_config 
SET company_id = (SELECT id FROM res_company LIMIT 1)
WHERE company_id IS NULL;

-- Set NOT NULL sau khi đã có data
ALTER TABLE import_sale_order_config ALTER COLUMN company_id SET NOT NULL;
```

### Bước 3: Tạo Config Cho Mỗi Company

Sau khi update code, cần tạo `import.sale.order.config` cho mỗi company:

1. Vào: **Settings > Technical > Database Structure > Models**
2. Tìm model: `import.sale.order.config`
3. Tạo record cho mỗi company với:
   - `company_id`: Company tương ứng
   - `warehouse_id`: Warehouse của company đó
   - `payment_term_id`: Payment term của company
   - `pricelist_id`: Pricelist của company
   - `purchase_pricelist_id`: Purchase pricelist của company

## ✅ Verification

Sau khi fix, verify:

1. **Tạo đơn mua từ sale order:**
   - Warehouse được lấy tự động từ sale order hoặc company
   - Không còn hardcode 'KHH'

2. **Import đơn từ PAKD:**
   - Config được lấy theo company hiện tại
   - Warehouse được lấy từ config của company đó

3. **Multi-company:**
   - Mỗi company có config riêng
   - Warehouse được lấy đúng theo company

## 🔍 Testing

### Test Case 1: Tạo Purchase Order từ Sale Order
1. Tạo sale order với warehouse A (company 1)
2. Click "Tạo đơn mua"
3. Verify: Purchase order có warehouse A

### Test Case 2: Import từ PAKD
1. Switch sang company 2
2. Import đơn từ PAKD
3. Verify: Sale order có warehouse từ config của company 2

### Test Case 3: Multi-Company
1. Company 1: Có warehouse KHH
2. Company 2: Có warehouse NSG
3. Import đơn ở company 1 → Warehouse KHH
4. Import đơn ở company 2 → Warehouse NSG

## 📊 Impact

- ✅ **Backward Compatible**: Vẫn support warehouse KHH nếu có (fallback)
- ✅ **Multi-Company Ready**: Mỗi company có warehouse riêng
- ✅ **Flexible**: Ưu tiên warehouse từ sale order nếu có
- ⚠️  **Breaking Change**: Cần tạo config cho mỗi company (nếu chưa có)

## 🔗 Related Files

- `models/sale_order.py` - Sale order model với logic tạo purchase order
- `wizards/import_sale_order_config.py` - Config model cho import
- `wizards/import_sale_order.py` - Wizard import từ PAKD
