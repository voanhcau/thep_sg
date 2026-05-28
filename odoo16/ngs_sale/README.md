# Module NGS Sale

Module quản lý bán hàng mở rộng cho Odoo, bổ sung các chức năng đặc thù cho nghiệp vụ bán hàng.

## Tổng quan chức năng

Module này mở rộng chức năng bán hàng của Odoo với các tính năng:

1. **Quản lý đơn hàng bán**
   - Thêm trường thông tin bổ sung (loại khách hàng, kiểu mua bán, ...)
   - Tính toán lợi nhuận, chiết khấu
   - Quản lý thanh toán và tính lãi vay
   - Import đơn hàng từ Excel

2. **Tự động tạo đơn mua hàng**
   - Tạo đơn mua từ đơn bán
   - Cập nhật thông tin đơn mua
   - Liên kết đơn mua - đơn bán

3. **Quản lý giá và chiết khấu**
   - Bảng giá mua và bán
   - Tính toán chiết khấu
   - Cập nhật giá tự động

4. **Báo cáo và thống kê**
   - Báo cáo doanh số
   - Thống kê lợi nhuận
   - Theo dõi thanh toán

## Cấu trúc module

### Models

#### 1. sale_order.py
Quản lý đơn hàng bán với các chức năng chính:

- **SaleOrder**: Class chính quản lý đơn hàng bán
  - `action_approve()`: Duyệt đơn hàng
  - `action_create_purchase_order()`: Tạo đơn mua hàng
  - `calculate_interest()`: Tính lãi vay
  - `action_update_prices()`: Cập nhật giá bán
  - `_compute_margin()`: Tính lợi nhuận
  - `import_from_excel()`: Import từ Excel

- **SaleOrderLine**: Quản lý dòng đơn hàng
  - `_compute_margin()`: Tính lợi nhuận
  - `_compute_price_unit()`: Tính đơn giá
  - `_onchange_quantity_another1()`: Xử lý thay đổi số lượng

#### 2. purchase_order.py
Quản lý đơn mua hàng liên kết với đơn bán.

#### 3. sale_commission_tool.py
Quản lý hoa hồng cho nhân viên bán hàng.

#### 4. account_move.py
Mở rộng chức năng hóa đơn và thanh toán.

#### 5. res_partner.py
Mở rộng thông tin đối tác.

#### 6. res_company.py
Cấu hình công ty.

### Views

- Form view đơn hàng bán
- Tree view danh sách đơn hàng
- Form view đơn mua hàng
- Các view báo cáo

### Security

- Phân quyền người dùng
- Quy tắc bảo mật dữ liệu

### Reports

- Báo cáo đơn hàng
- Báo cáo doanh số
- Báo cáo lợi nhuận

## Cài đặt và sử dụng

1. Cài đặt module:
```bash
pip install -r requirements.txt
```

2. Cập nhật module trong Odoo:
- Vào Apps > Update Apps List
- Tìm và cài đặt module NGS Sale

3. Cấu hình:
- Thiết lập bảng giá mua/bán
- Cấu hình loại khách hàng
- Thiết lập quy tắc tính hoa hồng

## Phụ thuộc

- Odoo 16.0
- Python 3.8+
- Các module Odoo core: sale, purchase, account

## Hỗ trợ

Liên hệ support@example.com để được hỗ trợ. 