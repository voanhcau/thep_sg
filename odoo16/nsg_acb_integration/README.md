# ACB Integration Module - NSG ERP

## Tổng quan

Module tích hợp ngân hàng ACB cho hệ thống NSG ERP, cho phép nhận thông báo giao dịch tự động từ ACB và xử lý thanh toán.

## Thông tin API ACB

### API Endpoint
- **URL**: `https://sandbox.acb.com.vn/acb/open/transactions/notification-api-adapter/v1/rtxn-notification`
- **Phương thức**: `POST`
- **Client ID**: `30735a42d5313ce3a29284d3cbfd1d8f`
- **Secret Key**: `c3a571706fe79e816e918d6386d23a4f`

### Webhook Endpoint
- **URL**: `{domain}/acb/webhook/transaction`
- **Test URL**: `{domain}/acb/webhook/test`

## Cài đặt

1. **Copy module vào thư mục addon**:
   ```bash
   cp -r nsg_acb_integration /path/to/odoo/addons/
   ```

2. **Restart Odoo server**:
   ```bash
   sudo systemctl restart odoo
   ```

3. **Cập nhật danh sách addon**:
   - Vào Apps trong Odoo
   - Update Apps List

4. **Cài đặt module**:
   - Tìm "ACB Integration"
   - Click Install

## Cấu hình

### 1. Cấu hình ACB

Vào **ACB Integration > Cấu hình > Cấu hình ACB**:

- **Tên cấu hình**: ACB Production Configuration
- **API Base URL**: `https://sandbox.acb.com.vn/acb/open/transactions/notification-api-adapter/v1`
- **API Notification URL**: `https://sandbox.acb.com.vn/acb/open/transactions/notification-api-adapter/v1/rtxn-notification`
- **Client ID**: `30735a42d5313ce3a29284d3cbfd1d8f`
- **Secret Key**: `c3a571706fe79e816e918d6386d23a4f`
- **Virtual Account ID**: `ACB001`
- **Virtual Account Prefix**: `NSG`

### 2. Webhook URL

Cung cấp cho ACB webhook endpoint:
```
https://yourdomain.com/acb/webhook/transaction
```

## Test API và Monitoring

### 1. Test Endpoints

#### Test Webhook Endpoint
```bash
curl -X GET https://yourdomain.com/acb/webhook/test
```

Kết quả mong đợi:
```json
{
  "status": "success",
  "message": "ACB Webhook endpoint is working",
  "timestamp": "2024-01-15T10:30:00.000Z",
  "endpoint": "/acb/webhook/test",
  "version": "1.0.0"
}
```

#### Test ACB API Connection
Vào **ACB Integration > Công cụ > Test ACB API** hoặc click nút "Test API" trong form cấu hình.

#### Test Webhook từ UI
Vào **ACB Integration > Công cụ > Test Webhook**

### 2. Lấy giao dịch thủ công

#### Từ UI
Vào **ACB Integration > Công cụ > Lấy giao dịch từ API**

#### Từ Code
```python
# Lấy cấu hình ACB
acb_config = env['acb.config'].search([('active', '=', True)], limit=1)

# Lấy giao dịch từ 24h qua
from datetime import datetime, timedelta
from_date = datetime.now() - timedelta(days=1)
to_date = datetime.now()

result = acb_config.fetch_transactions(from_date, to_date)
```

### 3. Kiểm tra trạng thái hệ thống

Vào **ACB Integration > Công cụ > Trạng thái hệ thống** để xem:
- Số lượng cấu hình active
- Thống kê giao dịch theo nguồn (webhook/API/manual)
- Số lượng API calls
- Giao dịch đã xử lý/lỗi/pending

## Logging và Monitoring

### 1. Log Levels

Module sử dụng Python logging với các level:
- **INFO**: Thông tin chung về webhook và API calls
- **DEBUG**: Chi tiết về data parsing và processing
- **WARNING**: Lỗi không nghiêm trọng
- **ERROR**: Lỗi nghiêm trọng cần xử lý
- **CRITICAL**: Lỗi hệ thống

### 2. Log Locations

Kiểm tra log trong file log của Odoo:
```bash
tail -f /var/log/odoo/odoo.log | grep -i acb
```

### 3. Log Examples

#### Webhook Request
```
=== ACB WEBHOOK REQUEST RECEIVED ===
Timestamp: 2024-01-15 10:30:00
Request IP: 192.168.1.100
User Agent: ACB-Webhook/1.0
Request Headers: {
  "Content-Type": "application/json",
  "Accept": "application/json"
}
RAW WEBHOOK DATA:
{
  "clientId": "30735a42d5313ce3a29284d3cbfd1d8f",
  "clientRequestId": "req_001",
  "checksum": "abc123...",
  "requests": [...]
}
```

#### API Call
```
=== Calling ACB API ===
API URL: https://sandbox.acb.com.vn/acb/open/transactions/notification-api-adapter/v1/rtxn-notification
Client ID: 30735a42d5313ce3a29284d3cbfd1d8f
Request data: {...}
Response status code: 200
Response JSON: {...}
```

### 4. Performance Monitoring

Module tự động track:
- **API Call Count**: Số lần gọi API
- **Last API Call**: Thời gian gọi API cuối
- **Response Time**: Thời gian xử lý webhook/API
- **Transaction Processing**: Thời gian xử lý giao dịch

## API Documentation

### 1. Request Format (ACB → Odoo)

```json
{
  "clientId": "30735a42d5313ce3a29284d3cbfd1d8f",
  "clientRequestId": "unique_request_id",
  "checksum": "hmac_sha256_hash",
  "requestMeta": {
    "requestType": "NOTIFICATION"
  },
  "pagination": {
    "page": 1,
    "pageSize": 100,
    "totalPage": 1
  },
  "requests": [
    {
      "transactions": [
        {
          "transactionStatus": "COMPLETED",
          "transactionChannel": "IBFT",
          "transactionCode": "TXN001",
          "accountNumber": "887988",
          "transactionDate": "2024-01-15T10:30:00.000Z",
          "effectiveDate": "2024-01-15T10:30:00.000Z",
          "debitOrCredit": "credit",
          "amount": 500000,
          "transactionContent": "THANH TOAN HOA DON",
          "virtualAccountInfo": {
            "vaPrefiexId": "ACB001",
            "vaNbr": "NSG001"
          },
          "issueBankName": "ACB",
          "virtualAccount": "ACB001",
          "referenceNumber": "REF001",
          "partnerCustomerCode": "CUST001",
          "partnerCustomerName": "KHACH HANG ABC",
          "partnerCustomerType": "ORG"
        }
      ]
    }
  ]
}
```

### 2. Response Format (Odoo → ACB)

#### Success Response
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "responseCode": "00000000",
  "message": "Success",
  "responseBody": {
    "index": 1,
    "referenceCode": "123456"
  }
}
```

#### Error Response
```json
{
  "timestamp": "2024-01-15T10:30:00.000Z",
  "responseCode": "40000000",
  "message": "Thiếu trường bắt buộc: clientId",
  "responseBody": {
    "index": 1,
    "referenceCode": "000000"
  }
}
```

### 3. Checksum Validation

Checksum được tạo bằng HMAC-SHA256:
```
message = clientId + clientRequestId + amount + transactionDate
checksum = HMAC-SHA256(secret_key, message)
```

## Xử lý giao dịch

### 1. Luồng xử lý tự động

1. **Nhận webhook** từ ACB
2. **Validate** checksum và dữ liệu
3. **Tạo transaction record** trong hệ thống
4. **Tìm khách hàng** dựa trên reference number/virtual account
5. **Tạo payment record** tự động (nếu cấu hình)
6. **Gửi email thông báo** (nếu có lỗi)

### 2. Xử lý thủ công

Có thể xử lý giao dịch thủ công bằng cách:
- Vào form giao dịch → Click "Xử lý"
- Hoặc sử dụng **Công cụ > Đồng bộ thủ công**

### 3. Cron Jobs

Module có các cron job tự động:
- **Process Pending Transactions**: Mỗi 15 phút
- **API Health Check**: Mỗi 1 giờ
- **Update Statistics**: Mỗi 30 phút
- **Cleanup Old Transactions**: Mỗi ngày (tắt mặc định)

## Troubleshooting

### 1. Webhook không nhận được

1. **Kiểm tra URL**: Đảm bảo `{domain}/acb/webhook/transaction` accessible
2. **Test endpoint**: `curl -X GET {domain}/acb/webhook/test`
3. **Kiểm tra firewall**: Mở port cho ACB IP
4. **Kiểm tra log**: Tìm error trong Odoo log

### 2. Checksum validation failed

1. **Kiểm tra secret key** trong cấu hình
2. **Kiểm tra format** dữ liệu gửi từ ACB
3. **Debug log** để xem message được hash

### 3. API connection error

1. **Test API**: Vào **Công cụ > Test ACB API**
2. **Kiểm tra network**: Ping đến API endpoint
3. **Kiểm tra credentials**: Client ID và Secret Key
4. **Kiểm tra proxy/firewall**

### 4. Transaction processing error

1. **Kiểm tra log** chi tiết lỗi
2. **Xử lý thủ công**: Vào form transaction → "Xử lý"
3. **Kiểm tra partner mapping**: Reference number có đúng không
4. **Kiểm tra journal**: Bank journal có tồn tại không

### 5. Các lỗi thường gặp

#### "Không tìm thấy cấu hình ACB"
- Đảm bảo có cấu hình ACB active
- Kiểm tra Client ID trong request

#### "Checksum không hợp lệ"
- Kiểm tra secret key
- Đảm bảo format message đúng

#### "Không thể kết nối đến API ACB"
- Kiểm tra network connectivity
- Verify API URL
- Check proxy settings

## Email Notifications

Module tự động gửi email khi có lỗi:

### 1. Transaction Error Email
- **Trigger**: Khi giao dịch bị lỗi
- **Recipients**: Company email
- **Content**: Chi tiết lỗi và hướng dẫn xử lý

### 2. API Connection Error Email
- **Trigger**: Khi API health check fail
- **Recipients**: Company email
- **Content**: Thông tin cấu hình và lỗi kết nối

## Security

### 1. Access Rights
- **User**: Xem giao dịch
- **Manager**: Xem + tạo + sửa giao dịch
- **Admin**: Full access + cấu hình

### 2. Data Protection
- Secret key được encrypt
- Log không chứa sensitive data
- Webhook endpoint có checksum validation

### 3. Rate Limiting
- Mặc định 100 API calls/hour
- Có thể cấu hình trong System Parameters

## Performance

### 1. Database Indexes
- transaction_code, client_id, account_number được index
- transaction_date được index cho query nhanh

### 2. Cleanup
- Tự động xóa giao dịch cũ > 6 tháng (nếu enable cron)
- Chỉ xóa giao dịch đã processed/cancelled

### 3. Monitoring
- Track API response time
- Monitor webhook processing time
- Statistics dashboard real-time

## Support

Để được hỗ trợ, vui lòng cung cấp:
1. **Log files** với timestamp cụ thể
2. **Configuration** đang sử dụng (ẩn secret key)
3. **Sample request/response** data
4. **Error screenshots** từ UI

---

**Phiên bản**: 1.0.0  
**Tương thích**: Odoo 16.0  
**Tác giả**: NSG Development Team  
**Cập nhật**: 2024-01-15 