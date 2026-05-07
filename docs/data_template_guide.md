# Data Template Guide

## Overview

File `data_template.xlsx` được cung cấp để giúp bạn chuẩn bị dữ liệu mới một cách dễ dàng.

## 📋 Cấu Trúc File Template

Template có 2 sheets:

### Sheet 1: "Hướng dẫn" 
- Hướng dẫn chi tiết cách điền dữ liệu
- Mô tả từng cột
- Ví dụ cụ thể

### Sheet 2: "Data"
- Dữ liệu sample (5 hàng ví dụ)
- Cấu trúc cột chính xác
- Định dạng đúng (số thực cho tọa độ)

## ✅ Cách Sử Dụng

### Bước 1: Chuẩn Bị Data Mới

```bash
# Tạo thư mục cho data mới (ví dụ: 20260601)
mkdir -p data_20260601/input
```

### Bước 2: Copy Template

```bash
# Copy file template
cp docs/data_template.xlsx data_20260601/input/branches_20260601.xlsx
```

### Bước 3: Điền Dữ Liệu

1. Mở file `data_20260601/input/branches_20260601.xlsx`
2. Sheet "Hướng dẫn" - đọc hướng dẫn
3. Sheet "Data" - xóa 5 hàng sample, điền dữ liệu của bạn
4. Lưu file

### Bước 4: Cập Nhật Config

```python
# scripts/config.py
DATA_VERSION = "20260601"  # Thay đổi thành ngày của data mới
```

### Bước 5: Chạy Crawl

```bash
# Tất cả scripts sẽ auto-detect paths từ config
python scripts/build_crawl_pairs.py
python scripts/split_crawl_parts.py
cd scripts && ./crawl_parts.sh 1 2 3 ...
python scripts/finalize_results.py
```

## 📝 Định Dạng Dữ Liệu

### Mã Phòng Ban
- **Kiểu:** Số nguyên
- **Yêu cầu:** Duy nhất (không trùng)
- **Ví dụ:** `1001`, `1002`, `1003`

### Tên Phòng Ban
- **Kiểu:** Văn bản
- **Yêu cầu:** Không để trống
- **Ví dụ:** `Chi nhánh TP. Hồ Chí Minh`, `Van phong Ha Noi`

### KINH ĐỘ
- **Kiểu:** Số thực (4 chữ số thập phân)
- **Range:** ~93-109 cho Việt Nam
- **Ví dụ:** `106.6296`, `105.8342`
- **Lưu ý:** Không dùng định dạng độ-phút-giây (°′″)

### VĨ ĐỘ
- **Kiểu:** Số thực (4 chữ số thập phân)
- **Range:** ~8-23 cho Việt Nam
- **Ví dụ:** `10.7769`, `21.0285`
- **Lưu ý:** Không dùng định dạng độ-phút-giây (°′″)

### Tỉnh
- **Kiểu:** Văn bản
- **Yêu cầu:** Tên tỉnh/thành phố theo chuẩn
- **Ví dụ:** `Hồ Chí Minh`, `Hà Nội`, `Đà Nẵng`

## ⚠️ Lưu Ý Quan Trọng

❌ **Không được:**
- Để trống bất kỳ cột nào
- Tạo cột mới thêm vào
- Thay đổi tên cột
- Sử dụng định dạng tọa độ độ-phút-giây

✅ **Nên:**
- Kiểm tra dữ liệu trước khi chạy
- Đảm bảo mã phòng ban duy nhất
- Sử dụng tên tỉnh chuẩn
- Lưu file dưới tên: `branches_YYYYMMDD.xlsx`

## 🔍 Kiểm Tra Dữ Liệu

Sau khi điền dữ liệu, có thể chạy:

```bash
python scripts/build_crawl_pairs.py
```

Script sẽ báo lỗi nếu:
- Cột bị thiếu
- Mã phòng ban trùng
- Tọa độ không hợp lệ
- Cột trống

## 📞 Hỗ Trợ

Nếu gặp lỗi khi chạy, kiểm tra:

1. **File không tìm thấy:**
   - Kiểm tra tên file là `branches_YYYYMMDD.xlsx`
   - Đường dẫn đúng: `data_YYYYMMDD/input/branches_YYYYMMDD.xlsx`

2. **Lỗi cột bị thiếu:**
   - Không xóa bất kỳ cột nào
   - Đảm bảo tên cột chính xác (viết hoa, dấu cách)

3. **Lỗi tọa độ:**
   - Phải là số thực, ví dụ: `106.6296` (không phải `106°38'`)
   - Kinh độ: ~93-109
   - Vĩ độ: ~8-23

4. **Mã phòng ban trùng:**
   - Mỗi phòng phải có mã duy nhất
   - Không có hàng nào có cùng giá trị trong cột "Mã phòng ban"
