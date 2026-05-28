# Hướng Dẫn Restore Code - Multi-Company Warehouse Fix

## 📋 Các Vị Trí Đã Sửa

### 1. File: `models/sale_order.py`

#### Vị trí 1: Dòng ~933-953 (trong method `action_create_purchase_order()`)

**Code cũ (cần restore):**
```python
# Tìm phương thức vận chuyển của kho KHH
warehouse = self.env['stock.warehouse'].search([
    ('code', '=', 'KHH')
], limit=1)
picking_type_id = None
if warehouse:
    picking_type = self.env['stock.picking.type'].search([
        ('warehouse_id', '=', warehouse.id),
        ('sequence_code', '=', 'IN'),
        ('code', '=', 'incoming')
    ], limit=1)
    if picking_type:
        picking_type_id = picking_type.id
        _logger.info(f"Tìm thấy phương thức vận chuyển: {picking_type.name}")
    else:
        _logger.warning("Không tìm thấy phương thức vận chuyển cho kho KHH")
else:
    _logger.warning("Không tìm thấy kho KHH")

if not picking_type_id:
    raise UserError(u"Không tìm thấy phương thức vận chuyển của kho mã KHH")
```

**Code mới (đã sửa):**
```python
# Tìm phương thức vận chuyển của kho - support multi-company
# Lấy warehouse từ company của purchase order (hoặc từ sale order's warehouse)
company = purchase.company_id if purchase else self.company_id
warehouse = None
picking_type_id = None

# Ưu tiên 1: Lấy warehouse từ sale order nếu có
if self.warehouse_id:
    warehouse = self.warehouse_id
    _logger.info(f"Sử dụng warehouse từ sale order: {warehouse.name} (code: {warehouse.code})")
else:
    # Ưu tiên 2: Tìm warehouse đầu tiên của company
    warehouse = self.env['stock.warehouse'].search([
        ('company_id', '=', company.id)
    ], limit=1, order='id')
    if warehouse:
        _logger.info(f"Sử dụng warehouse đầu tiên của company {company.name}: {warehouse.name} (code: {warehouse.code})")
    else:
        # Fallback: Tìm warehouse với code KHH (backward compatibility)
        warehouse = self.env['stock.warehouse'].search([
            ('code', '=', 'KHH'),
            ('company_id', '=', company.id)
        ], limit=1)
        if warehouse:
            _logger.info(f"Sử dụng warehouse KHH (backward compatibility): {warehouse.name}")

if warehouse:
    picking_type = self.env['stock.picking.type'].search([
        ('warehouse_id', '=', warehouse.id),
        ('sequence_code', '=', 'IN'),
        ('code', '=', 'incoming'),
        ('company_id', '=', company.id)
    ], limit=1)
    if picking_type:
        picking_type_id = picking_type.id
        _logger.info(f"Tìm thấy phương thức vận chuyển: {picking_type.name} (warehouse: {warehouse.name})")
    else:
        _logger.warning(f"Không tìm thấy phương thức vận chuyển cho warehouse {warehouse.name} (company: {company.name})")
else:
    _logger.warning(f"Không tìm thấy warehouse cho company {company.name}")

if not picking_type_id:
    raise UserError(u"Không tìm thấy phương thức vận chuyển (picking type) cho warehouse của công ty %s. Vui lòng kiểm tra cấu hình warehouse và picking type." % company.name)
```

#### Vị trí 2: Dòng ~511 (trong method `import_from_excel()`)

**Code cũ (cần restore):**
```python
setting = self.env['import.sale.order.config'].search([], limit=1)
```

**Code mới (đã sửa):**
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
        _logger.warning(f"Không tìm thấy import.sale.order.config cho company {company.name}, sử dụng config mặc định (ID: {setting.id})")
```

### 2. File: `wizards/import_sale_order_config.py`

#### Vị trí: Dòng ~23-30 (class definition)

**Code cũ (cần restore):**
```python
class ImportSaleOrderConfig(models.Model):
    _name = "import.sale.order.config"
    _description = "Import Sale Order Configuration"

    payment_term_id = fields.Many2one('account.payment.term', string=u'Điều khoản thanh toán', required=True)
    pricelist_id = fields.Many2one('product.pricelist', string=u'Bảng giá bán', required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string=u'Kho hàng', required=True)
    purchase_pricelist_id = fields.Many2one('product.pricelist', string=u'Bảng giá mua', required=True)
```

**Code mới (đã sửa):**
```python
class ImportSaleOrderConfig(models.Model):
    _name = "import.sale.order.config"
    _description = "Import Sale Order Configuration"
    _check_company_auto = True

    company_id = fields.Many2one('res.company', string=u'Công ty', required=True, default=lambda self: self.env.company)
    payment_term_id = fields.Many2one('account.payment.term', string=u'Điều khoản thanh toán', required=True, check_company=True)
    pricelist_id = fields.Many2one('product.pricelist', string=u'Bảng giá bán', required=True, check_company=True)
    warehouse_id = fields.Many2one('stock.warehouse', string=u'Kho hàng', required=True, check_company=True)
    purchase_pricelist_id = fields.Many2one('product.pricelist', string=u'Bảng giá mua', required=True, check_company=True)
```

## 🔄 Cách Restore

### Option 1: Restore từng file

1. **File `models/sale_order.py`:**
   - Tìm dòng ~933-953: Thay code mới bằng code cũ (phần 1)
   - Tìm dòng ~511: Thay code mới bằng code cũ (phần 2)

2. **File `wizards/import_sale_order_config.py`:**
   - Tìm dòng ~23-30: Thay code mới bằng code cũ

### Option 2: Dùng Git (nếu có)

```bash
# Xem thay đổi
git diff models/sale_order.py
git diff wizards/import_sale_order_config.py

# Restore file
git checkout HEAD -- models/sale_order.py
git checkout HEAD -- wizards/import_sale_order_config.py
```

### Option 3: Dùng IDE (VS Code / PyCharm)

1. Right-click vào file
2. Chọn "Local History" hoặc "Git" > "Discard Changes"
3. Chọn version cũ để restore

## 📝 Tóm Tắt Thay Đổi

| File | Dòng | Thay Đổi |
|------|------|----------|
| `models/sale_order.py` | ~933-953 | Thay logic lấy warehouse (hardcode KHH → multi-company) |
| `models/sale_order.py` | ~511 | Thêm filter company_id khi search config |
| `wizards/import_sale_order_config.py` | ~23-30 | Thêm field `company_id` và `_check_company_auto` |

## ⚠️ Lưu Ý

Sau khi restore:
- Code sẽ quay về hardcode warehouse 'KHH'
- Config không filter theo company
- Cần đảm bảo có warehouse với code 'KHH' trong database

## 🔗 Files Liên Quan

- `models/sale_order.py` - File chính đã sửa
- `wizards/import_sale_order_config.py` - Model config đã sửa
- `MULTI_COMPANY_WAREHOUSE_FIX.md` - Documentation về fix (có thể xóa nếu restore)
