## Mục đích dự án

- **Bài toán**: Tính toán, lưu trữ và khai thác **khoảng cách đường bộ** giữa các phòng giao dịch/chi nhánh (PGD/CN) trong và ngoài tỉnh, phục vụ các bài toán GIS và phân tích mạng lưới đơn vị.
- **Nguồn dữ liệu chính**:
  - File danh mục PGD/CN kèm toạ độ (`dia_chi_toa_do_pgd_20250512.xlsx`).
  - Bảng tất cả cặp điểm với khoảng cách chim bay và (sau này) khoảng cách đường bộ (`full_trong_tinh_sau_sat_nhap_20250520.xlsx`).
  - Các file kết quả top 1 khoảng cách đường bộ trong tỉnh.

## Cấu trúc thư mục chính

- **Thư mục gốc** `crawl_all_khoang_cach/`
  - `run_crawl_part.py`: Script crawl khoảng cách đường bộ từ Google Maps theo từng "part" dữ liệu.
  - `run_crawl_part.ipynb`: Notebook phiên bản tương đương `run_crawl_part.py`, dùng để chạy thử/ghi log trong môi trường notebook.
  - `xu_ly_data_kc_20250520.ipynb`: Notebook xử lý bảng khoảng cách trong tỉnh, lọc/suy diễn các cặp khoảng cách cần thiết (ví dụ chọn cặp gần nhất).
  - `top_1_gan_nhat_trong_tinh.ipynb`: Notebook tìm **cặp điểm gần nhất trong tỉnh** (top 1 khoảng cách đường bộ cho từng phòng ban trong tỉnh).
  - `top_1_tinh_cu_moi.ipynb`: Notebook so sánh/tổng hợp theo **tỉnh cũ – tỉnh mới sau sáp nhập**, sinh các bảng kết quả theo cấu trúc quản lý hành chính mới.
  - `.ipynb_checkpoints/`: Checkpoint tự sinh của Jupyter, không cần chỉnh tay.
  - (Có thể tồn tại thư mục `data/`, `etl_20250604/`, `part/` ở đường dẫn tuyệt đối được tham chiếu trong các notebook/script.)

## Luồng xử lý dữ liệu tổng quát

1. **Chuẩn bị danh mục đơn vị và toạ độ**
   - Đọc file danh mục PGD/CN có toạ độ (`dia_chi_toa_do_pgd_20250512.xlsx`).
   - Chuẩn hoá thông tin mã phòng ban, tên phòng ban, tỉnh hiện tại, tỉnh sau sáp nhập.

2. **Tạo tất cả cặp điểm nội tỉnh**
   - Tạo bảng tất cả cặp kết hợp giữa các đơn vị cùng tỉnh (hoặc theo quy tắc bạn đã định nghĩa).
   - Tính **khoảng cách chim bay** (đã có trong `full_trong_tinh_sau_sat_nhap_20250520.xlsx`).
   - Lưu bảng này làm input cho bước crawl khoảng cách đường bộ.

3. **Crawl khoảng cách đường bộ từ Google Maps**
   - Dữ liệu nguồn được **chia thành nhiều phần (part)**: `df_part_01.pkl`, `df_part_02.pkl`, ..., `df_part_35.pkl` (đường dẫn mặc định trong script: `/home/trungdt2/Downloads/crawl_all_khoang_cach/part`).
   - Mỗi part tương ứng với một subset của bảng full, được lưu dưới dạng `pandas.DataFrame` (pickle).
   - **Script chính**: `run_crawl_part.py` / `run_crawl_part.ipynb`.
   - Kết quả mỗi batch lưu thành file Excel: `output_part_XX/ket_qua_tu_{start}_{end}.xlsx`.

4. **Ghép kết quả các part & làm sạch**
   - Sau khi chạy xong tất cả các part, ghép các file Excel kết quả lại thành một bảng đầy đủ `Khoảng cách đường bộ`.
   - Xử lý missing, loại bỏ dòng không tìm thấy đường bộ, chuẩn hoá format, kiểu dữ liệu.

5. **Phân tích top 1 khoảng cách trong tỉnh**
   - Dùng `xu_ly_data_kc_20250520.ipynb` và/hoặc `top_1_gan_nhat_trong_tinh.ipynb`:
     - Loại bỏ các bản ghi không có khoảng cách đường bộ.
     - Nhóm theo `Mã phòng ban 1` (hoặc `Mã phòng ban 2`) và chọn bản ghi có **khoảng cách đường bộ nhỏ nhất**.
     - Lưu kết quả ra Excel, ví dụ `top1_duong_bo_trong_tinh.xlsx`.

6. **Đối chiếu tỉnh cũ – tỉnh mới sau sáp nhập**
   - Dùng `top_1_tinh_cu_moi.ipynb` (và các notebook ETL liên quan):
     - Join thêm thông tin tỉnh hiện tại/tỉnh sau sáp nhập theo mã phòng ban.
     - Lọc các cặp điểm có cùng tỉnh hiện tại hoặc cùng tỉnh sau sáp nhập tuỳ mục đích.
     - Sinh bảng **top 1 khoảng cách đường bộ** theo tỉnh mới, dùng cho phân tích tái cấu trúc mạng lưới sau sáp nhập.

## Chi tiết script crawl `run_crawl_part.py`

- **Mục tiêu**: Với mỗi part dữ liệu, tự động mở Google Maps, nhập 2 toạ độ (lat/lon) và lấy text khoảng cách đường bộ trả về.
- **Cấu hình chính** (đầu file):
  - `PART_ID`: số part cần chạy (1–35).
  - `DATA_FOLDER`: thư mục chứa các file `df_part_XX.pkl`.
  - `OUTPUT_FOLDER`: thư mục lưu kết quả Excel chia batch theo index.
  - `BATCH_SIZE`: số dòng xử lý mỗi lần (mặc định 100).
  - `SLEEP_TIME`: thời gian nghỉ giữa mỗi request để tránh bị chặn.
  - `WAIT_TIME`: timeout chờ load phần tử khoảng cách trên trang Google Maps.
- **Lớp `GoogleMapsDistanceCalculator`**:
  - Cấu hình Chrome headless (không hiển thị giao diện).
  - Ghép URL Google Maps dạng:
    - `https://www.google.com/maps/dir/{lat1},{lon1}/{lat2},{lon2}/data=!4m2!4m1!3e0`
  - Chờ phần tử DOM hiển thị khoảng cách (`div.xB1mrd-T3iPGc-iSfDt-ij8cu` hoặc `div.XdKEzd`).
  - Trả về text khoảng cách (ví dụ: `"12,3 km"`), nếu không tìm thấy thì trả `"Không tìm thấy"`.
- **Hàm `crawl_with_resume(df_input)`**:
  - Chia dataframe thành các batch liên tiếp theo index.
  - Với mỗi batch:
    - Nếu file kết quả `ket_qua_tu_{start}_{end-1}.xlsx` đã tồn tại thì bỏ qua (cơ chế resume).
    - Tạo mới `GoogleMapsDistanceCalculator` cho batch đó.
    - Loop từng dòng:
      - Nếu cột `Khoảng cách đường bộ` đã có giá trị, bỏ qua.
      - Gọi Google Maps để lấy khoảng cách đường bộ, ghi lại vào dataframe.
    - Đóng trình duyệt, lưu batch ra Excel.

## Cách chạy nhanh từng phần

- **1. Chuẩn bị môi trường Python**
  - Tạo môi trường ảo (khuyến nghị, Python 3.11):

```bash
python -m venv .venv
source .venv/bin/activate
pip install pandas selenium webdriver-manager openpyxl
```

- **2. Chuẩn bị dữ liệu part để crawl**
  - Đảm bảo tồn tại các file `df_part_XX.pkl` tại thư mục:
    - `/home/trungdt2/Downloads/crawl_all_khoang_cach/part`
  - Mỗi file phải có tối thiểu các cột:
    - `VĨ ĐỘ 1`, `KINH ĐỘ 1`, `VĨ ĐỘ 2`, `KINH ĐỘ 2`
    - `Khoảng cách đường bộ` (có thể chưa tồn tại, script sẽ tự tạo).

- **3. Chạy 1 part crawl**
  - Mở `run_crawl_part.py`, chỉnh:
    - `PART_ID = <số part bạn muốn chạy>`
  - Chạy:

```bash
python run_crawl_part.py
```

- **4. Xử lý kết quả & top 1**
  - Mở các notebook:
    - `xu_ly_data_kc_20250520.ipynb`
    - `top_1_gan_nhat_trong_tinh.ipynb`
    - `top_1_tinh_cu_moi.ipynb`
  - Chạy lần lượt các cell theo thứ tự đã soạn, cập nhật lại đường dẫn input/output nếu bạn đổi cấu trúc thư mục.

## Ghi chú & gợi ý mở rộng

- **Chống bị Google chặn**:
  - Tăng `SLEEP_TIME`, giảm `BATCH_SIZE`, hoặc random hoá thời gian chờ.
  - Có thể cấu hình thêm proxy/rotate user-agent nếu cần an toàn hơn.
- **Hiệu năng**:
  - Có thể chia nhiều PART_ID và chạy song song trên nhiều máy/môi trường khác nhau.
- **Tái sử dụng**:
  - Logic crawl có thể tái sử dụng cho bài toán khác bằng cách đổi:
    - Nguồn toạ độ input.
    - Cách parse phần tử khoảng cách trên giao diện Google Maps.

