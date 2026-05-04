## 1. Mục tiêu

- **Đầu vào**: File Excel `ml_thay_doi_drop_2025_sang_2026.xlsx` chứa các cặp PGD/CN và tọa độ (`kinh_do_1`, `vi_do_1`, `kinh_do_2`, `vi_do_2`).
- **Quy trình**:
  1. Chia file Excel thành nhiều file nhỏ `df_part_XX.pkl` (mỗi file 100 dòng).
  2. Dùng `run_crawl_part.py` để crawl khoảng cách đường bộ từ Google Maps cho từng part.
- **Đầu ra**: Các file Excel kết quả trong thư mục `part/output_part_XX/ket_qua_tu_...xlsx`.

---

## 2. Chuẩn bị môi trường

- Mở terminal và chạy:

```bash
cd /home/trungdt2/Documents/GIS_VTB_Project2025/crawl_all_khoang_cach

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pandas selenium webdriver-manager openpyxl
```

- Đảm bảo máy đã cài **Google Chrome**.

---

## 3. Bước 1: Chia file Excel thành các part 100 dòng

- Script chia part: `split_to_part_100.py`
- Đường dẫn file Excel nguồn đã được cấu hình sẵn trong script:

```python
BASE_DIR = "/home/trungdt2/Documents/GIS_VTB_Project2025/crawl_all_khoang_cach"
SOURCE_FILE = os.path.join(
    BASE_DIR,
    "data_20260313/output_2026/ml_thay_doi_drop_2025_sang_2026.xlsx",
)
PART_FOLDER = os.path.join(BASE_DIR, "part")
ROWS_PER_PART = 100
```

- Cách chạy:

```bash
cd /home/trungdt2/Documents/GIS_VTB_Project2025/crawl_all_khoang_cach
source .venv/bin/activate   # nếu đang dùng venv
python split_to_part_100.py
```

- Kết quả:
  - Thư mục `part/` sẽ có:
    - `df_part_01.pkl`, `df_part_02.pkl`, ..., `df_part_NN.pkl`
  - Mỗi file `.pkl` là 1 `DataFrame` ~100 dòng, đã có sẵn cột `Khoảng cách đường bộ` (ban đầu là `None`).

---

## 4. Bước 2: Cấu hình script crawl `run_crawl_part.py`

- File: `run_crawl_part.py`
- Phần cấu hình quan trọng:

```python
PART_ID = 1  # <== 👈 Thay số này thành từ 1 đến 56 (tương ứng số part)
DATA_FOLDER = "/home/trungdt2/Documents/GIS_VTB_Project2025/crawl_all_khoang_cach/part"

BATCH_SIZE = 100   # số dòng xử lý mỗi batch
SLEEP_TIME = 2     # thời gian nghỉ giữa các request (giây)
WAIT_TIME = 10     # timeout chờ Google Maps trả kết quả (giây)
```

- Mapping cột tọa độ trong dữ liệu mới:

```python
lat1, lon1 = row['vi_do_1'], row['kinh_do_1']
lat2, lon2 = row['vi_do_2'], row['kinh_do_2']
```

---

## 5. Bước 3: Chạy crawl cho từng part

### 5.1. Chạy cho `PART_ID = 1`

1. Mở `run_crawl_part.py`, đảm bảo:

```python
PART_ID = 1
```

2. Trong terminal:

```bash
cd /home/trungdt2/Documents/GIS_VTB_Project2025/crawl_all_khoang_cach
source .venv/bin/activate
python run_crawl_part.py
```

3. Script sẽ:
   - Đọc file: `part/df_part_01.pkl`
   - Chạy crawl Google Maps cho tối đa 100 dòng.
   - Lưu kết quả vào:
     - Thư mục: `part/output_part_01/`
     - File: `ket_qua_tu_0_den_99.xlsx`

### 5.2. Chạy cho các `PART_ID` tiếp theo

- Lặp lại cho từng part:

1. Mở `run_crawl_part.py`, đổi:

```python
PART_ID = 2   # rồi 3, 4, ..., tới số part tối đa
```

2. Chạy lại:

```bash
python run_crawl_part.py
```

- Mỗi part sẽ tạo 1 thư mục kết quả riêng:
  - `part/output_part_02/ket_qua_tu_0_den_99.xlsx`
  - ...

---

## 6. Gộp kết quả các part (tùy chọn)

- Sau khi crawl xong tất cả `PART_ID`, có thể gộp lại:

```python
import os
import pandas as pd

BASE_DIR = "/home/trungdt2/Documents/GIS_VTB_Project2025/crawl_all_khoang_cach"
PART_FOLDER = os.path.join(BASE_DIR, "part")

all_dfs = []

for part_id in range(1, 57):  # điều chỉnh số part tối đa
    folder = os.path.join(PART_FOLDER, f"output_part_{part_id:02d}")
    if not os.path.isdir(folder):
        continue

    for fname in os.listdir(folder):
        if fname.endswith(".xlsx"):
            path = os.path.join(folder, fname)
            all_dfs.append(pd.read_excel(path))

full_df = pd.concat(all_dfs, ignore_index=True)
out_path = os.path.join(BASE_DIR, "data_20260313/output_2026/kc_duong_bo_full_2026.xlsx")
full_df.to_excel(out_path, index=False)
print("Đã lưu file tổng:", out_path)
```

---

## 7. Một số lưu ý

- **Google có thể chặn** nếu crawl quá nhanh:
  - Tăng `SLEEP_TIME` lên 3–5 giây.
  - Giảm số part chạy song song (chỉ nên 1 script trên 1 máy).
- Nếu ChromeDriver lỗi version:
  - Xóa cache webdriver-manager hoặc cập nhật Google Chrome.
- Khi cần chia lại dữ liệu nguồn:
  - Chỉ cần sửa đường dẫn trong `split_to_part_100.py` và chạy lại script.

