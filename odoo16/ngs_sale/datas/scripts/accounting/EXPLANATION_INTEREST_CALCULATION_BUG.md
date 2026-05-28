# Giải thích lỗi tính lãi vay (Interest Calculation Bug)

## Vấn đề ban đầu

Đơn hàng **S09194** quá hạn 1 ngày nhưng lãi vay = 0 VNĐ (sai, phải là 7,765 VNĐ).

## Nguyên nhân

### 1. Cấu hình `interest_calculation_extra_days = -1`

Công ty đã cấu hình `order.company_id.interest_calculation_extra_days = -1`, có nghĩa là "cho phép trễ 1 ngày trước khi tính lãi".

### 2. Logic tính toán trong code

Trong hàm `calculate_interest()`, logic tính số ngày tính lãi như sau:

```python
if overdue_days > 0:
    days_diff = overdue_days + order.company_id.interest_calculation_extra_days
    # Với overdue_days = 1 và interest_calculation_extra_days = -1
    # days_diff = 1 + (-1) = 0
    # → Không tính lãi!
```

### 3. Kết quả

- **Ngày bắt đầu tính lãi**: 2025-11-09
- **Ngày đến hạn**: 2025-11-14 (9/11 + 5 ngày)
- **Ngày thanh toán**: 2025-11-15
- **Số ngày quá hạn**: 1 ngày
- **interest_calculation_extra_days**: -1
- **days_diff**: 1 + (-1) = **0** ❌
- **Lãi vay**: 0 × 45,677,840 × 0.00017 = **0 VNĐ** ❌

## Giải pháp

### Cách 1: Sửa cấu hình (Đã làm)

Thay đổi `interest_calculation_extra_days` từ `-1` về `0`:

- **days_diff**: 1 + 0 = **1** ✅
- **Lãi vay**: 1 × 45,677,840 × 0.00017 = **7,765 VNĐ** ✅

### Cách 2: Sửa logic code (Đã làm)

Code đã được cập nhật để xử lý trường hợp `days_diff <= 0`:

```python
if overdue_days > 0:
    days_diff_raw = overdue_days + order.company_id.interest_calculation_extra_days
    if days_diff_raw <= 0:
        days_diff = 0
        _logger.info(f"⚠️ Quá hạn {overdue_days} ngày nhưng có {abs(order.company_id.interest_calculation_extra_days)} ngày cho phép trễ, không tính lãi")
    else:
        days_diff = days_diff_raw
        _logger.info(f"✅ Tính lãi cho {days_diff} ngày quá hạn")
```

## Ý nghĩa của `interest_calculation_extra_days`

- **Giá trị âm** (ví dụ: `-1`): Cho phép trễ X ngày trước khi tính lãi
  - Quá hạn 1 ngày + `-1` = 0 ngày tính lãi (miễn lãi 1 ngày)
  - Quá hạn 2 ngày + `-1` = 1 ngày tính lãi (chỉ tính 1 ngày)

- **Giá trị dương** (ví dụ: `+1`): Thêm X ngày vào số ngày tính lãi
  - Quá hạn 1 ngày + `+1` = 2 ngày tính lãi (tính thêm 1 ngày)

- **Giá trị 0**: Tính lãi theo số ngày quá hạn thực tế
  - Quá hạn 1 ngày + `0` = 1 ngày tính lãi

## Kết luận

**Lỗi do cả 2 nguyên nhân:**

1. ✅ **Cấu hình sai**: `interest_calculation_extra_days = -1` không phù hợp với yêu cầu tính lãi khi quá hạn
2. ✅ **Code thiếu xử lý**: Code không có logic rõ ràng để xử lý trường hợp `days_diff <= 0` và log cảnh báo

**Sau khi sửa:**
- Cấu hình: `interest_calculation_extra_days = 0`
- Code: Đã thêm logic xử lý và log cảnh báo
- Kết quả: Lãi vay tính đúng = 7,765 VNĐ ✅

