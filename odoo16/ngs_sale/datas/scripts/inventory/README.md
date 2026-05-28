# Inventory Scripts

## 📦 Scripts xử lý kho hàng

### `01_post_inventory_valuation_moves.py`
- **Chức năng**: POST inventory valuation moves (Draft → Posted)
- **Điều kiện**: Journal = "inventory valuation", State = "draft"  
- **Kết quả**: ~6,962 dòng bút toán
- **⚠️ Cảnh báo**: KHÔNG THỂ HOÀN TÁC sau khi POST!

### `02_update_inventory_valuation_to_draft.py`
- **Chức năng**: Chuyển inventory valuation về Draft (Posted → Draft)
- **Điều kiện**: Journal = "inventory valuation", State = "posted"
- **Kết quả**: Đưa về trạng thái có thể chỉnh sửa

### `03_post_inventory_valuation_to_draft.py`
- **Chức năng**: Chuyển inventory valuation từ Posted về Draft (Posted → Draft)
- **Điều kiện**: Journal = "inventory valuation", State = "posted"
- **Kết quả**: Chuyển từ "Vào sổ" thành "Dự thảo"
- **⚠️ Cảnh báo**: Có thể ảnh hưởng đến các tính năng liên quan

### `count_inventory_valuation_draft.py`
- **Chức năng**: Đếm số lượng bút toán theo điều kiện
- **Điều kiện**: Journal = "inventory valuation", State = "draft"
- **Kết quả**: Thống kê số lượng moves và move lines

## 🚀 Cách chạy

```bash
cd /Users/brucenguyen/Source/16/nsgerp/ngs_sale/datas

# Đếm số lượng bút toán
python scripts/inventory/count_inventory_valuation_draft.py

# POST moves (cẩn thận!)
AUTO_CONFIRM=y python scripts/inventory/01_post_inventory_valuation_moves.py

# Chuyển về DRAFT (cũ)
AUTO_CONFIRM=y python scripts/inventory/02_update_inventory_valuation_to_draft.py

# Chuyển từ Posted về Draft (mới)
AUTO_CONFIRM=y python scripts/inventory/03_post_inventory_valuation_to_draft.py
```
