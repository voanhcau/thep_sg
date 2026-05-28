# Hướng dẫn sử dụng chức năng "Lấy giao dịch ACB"

## Tổng quan
Module ACB Integration đã được cập nhật với chức năng lấy giao dịch thủ công từ API ACB. Bạn có thể lấy giao dịch theo khoảng thời gian tùy chỉnh và tự động xử lý chúng.

## Cách sử dụng

### 1. Cách truy cập nhanh nhất
**Menu: ACB Integration → Công cụ → Lấy giao dịch**

### 2. Cách khác
1. Vào **ACB Integration → Cấu hình → Cấu hình ACB**
2. Mở một record cấu hình ACB
3. Bấm nút **"Lấy giao dịch"** ở header

### 3. Sử dụng Wizard

Wizard "Lấy giao dịch ACB" cung cấp các tùy chọn:

#### Khoảng thời gian có sẵn:
- **Hôm nay**: Từ 00:00 hôm nay đến hiện tại
- **Hôm qua**: Cả ngày hôm qua
- **Tuần này**: Từ thứ 2 tuần này đến hiện tại
- **Tuần trước**: Cả tuần trước
- **Tháng này**: Từ ngày 1 tháng này đến hiện tại
- **Tháng trước**: Cả tháng trước
- **Tùy chỉnh**: Chọn khoảng thời gian cụ thể

#### Tùy chọn khác:
- **Cấu hình ACB**: Chọn cấu hình ACB để sử dụng
- **Tự động xử lý giao dịch**: Tự động gọi `action_process()` cho các giao dịch sau khi lấy về

### 4. Kết quả

Sau khi lấy giao dịch:
- Hiển thị thông báo số lượng giao dịch đã lấy
- Có thể bấm **"Xem giao dịch"** để xem danh sách giao dịch vừa lấy
- Giao dịch sẽ được lưu vào bảng `acb.transaction`

## Tính năng kỹ thuật

### Validations:
- Kiểm tra "Từ ngày" phải nhỏ hơn "Đến ngày"
- Khoảng thời gian không được quá 30 ngày
- Kiểm tra trùng lặp giao dịch bằng `transaction_code`

### Xử lý tự động:
- Tìm khách hàng dựa trên `reference_number`, `virtual_account_number`, hoặc `partner_customer_code`
- Tự động tạo payment cho giao dịch credit
- Ghi log chi tiết quá trình xử lý

### Performance:
- Hỗ trợ phân trang (page size = 100)
- Xử lý batch transactions
- Logging chi tiết để debug

## Lưu ý

1. **Cấu hình ACB**: Đảm bảo cấu hình ACB đã được thiết lập đúng với `client_id`, `secret_key`, và `api_base_url`

2. **Quyền truy cập**: Cần có quyền `base.group_user` để sử dụng wizard

3. **Giới hạn thời gian**: Không lấy quá 30 ngày một lần để tránh timeout

4. **Trùng lặp**: Hệ thống tự động kiểm tra và bỏ qua giao dịch trùng lặp

5. **Logging**: Tất cả hoạt động đều được ghi log chi tiết trong `_logger`

## Troubleshooting

### Nếu không lấy được giao dịch:
1. Kiểm tra cấu hình ACB
2. Kiểm tra kết nối internet
3. Xem log để biết chi tiết lỗi

### Nếu giao dịch không được xử lý tự động:
1. Kiểm tra thông tin khách hàng có đúng không
2. Kiểm tra cấu hình journal ngân hàng
3. Xem field `error_message` trong giao dịch

## API Reference

### Models:
- `acb.fetch.wizard`: Wizard lấy giao dịch
- `acb.transaction`: Giao dịch ACB
- `acb.config`: Cấu hình ACB

### Key Methods:
- `acb.config.fetch_transactions()`: Lấy giao dịch từ API
- `acb.transaction.action_process()`: Xử lý giao dịch
- `acb.transaction.create_from_api_data()`: Tạo giao dịch từ API data 