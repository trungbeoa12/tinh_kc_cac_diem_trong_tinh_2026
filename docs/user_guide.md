# Huong Dan Su Dung Cho Nguoi Khong Chuyen CNTT

Tai lieu nay mo ta cach dung project theo tung buoc. Neu chi can lay ket qua da xu ly xong, chi can xem muc 1.

## 1. Lay File Ket Qua Da Co

Mo file nay bang Excel:

```text
data_20260504/final/road_distance_20260504_final.xlsx
```

Trong file:

- `Khoang cach duong bo km`: khoang cach duong bo da chuan hoa ve km.
- `thoi gian`: thoi gian di chuyen Google Maps tra ve.
- `crawl_status`: `ok` la dong da co ket qua; `not_found_or_error` la dong Google Maps khong tim thay.

File cac dong con loi:

```text
data_20260504/diagnostics/failed_rows_20260504.xlsx
```

## 2. Chuan Bi May De Chay Lai

May can co:

- Python 3.9 tro len.
- Google Chrome.
- Internet.

Mo Terminal tai thu muc project, sau do chay:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r scripts/requirements.txt
```

Lenh tren tao moi truong Python rieng va cai cac thu vien can thiet.

## 3. Dat File Data Moi

### a) Tao Thu Muc Data

Moi lan co data moi, tao thu muc theo ngay:

```text
data_YYYYMMDD/input/
```

Vi du ngay `20260601`:

```text
data_20260601/input/
```

### b) Su Dung Template

Co san file template de coppy va dien du lieu:

```text
docs/data_template.xlsx
```

**Cach dung:**

1. Mo file `docs/data_template.xlsx`
2. Sheet `Huong dan` - xem huong dan dien du lieu
3. Sheet `Data` - xoa cac dong sample, dien du lieu cua ban
4. Luu file voi ten:

```text
data_YYYYMMDD/input/branches_YYYYMMDD.xlsx
```

Vi du ngay `20260601`:

```text
data_20260601/input/branches_20260601.xlsx
```

### c) Cac Cot Bat Buoc

File Excel can co cac cot:

- `Ma phong ban` - So hieu duy nhat (VD: 1001, 1002)
- `Ten phong ban` - Ten day du cua phong/chi nhanh
- `KINH DO` - Toa do kinh do (VD: 106.6296)
- `VI DO` - Toa do vi do (VD: 10.7769)
- `Tinh` - Tinh/Thanh pho (VD: Ho Chi Minh, Ha Noi)

**Quan Trong: Khong de trong bat ky cot nao!**

### d) Cap Nhat Config

Truoc khi chay cac script, cap nhat phien ban data trong `scripts/config.py`:

```python
# scripts/config.py
DATA_VERSION = "20260601"  # Thay doi thanh YYYYMMDD cua data moi
```

Sau do toan bo cac scripts se tu dung duong dan chinh xac cho data nay. Khong can thay doi cac lenh.

## 4. Tao Danh Sach Cap Diem Can Crawl

Lenh se tu dung duong dan tu config.py:

```bash
./.venv/bin/python scripts/build_crawl_pairs.py
```

Neu co data version khac (khong co trong config), co the chi dinh:

```bash
./.venv/bin/python scripts/build_crawl_pairs.py --version 20260601
```

Ket qua tao ra:

```text
data_YYYYMMDD/input/crawl_pairs_YYYYMMDD.xlsx
```

## 5. Chia Thanh Cac Part

```bash
./.venv/bin/python scripts/split_crawl_parts.py \
  --rows-per-part 100
```

Neu can chi dinh phien ban data:

```bash
./.venv/bin/python scripts/split_crawl_parts.py \
  --version 20260601 \
  --rows-per-part 100
```

Ket qua tam se nam trong:

```text
work/part/
```

## 6. Crawl Google Maps

Chay thu part 1 truoc:

```bash
cd scripts
PART_FOLDER=../work/part PYTHON_BIN=../.venv/bin/python ./crawl_parts.sh 1
```

Neu ket qua on, co the chay nhieu part:

```bash
cd scripts
PART_FOLDER=../work/part PYTHON_BIN=../.venv/bin/python SLEEP_TIME=10 REST_BETWEEN_PARTS=60 ./crawl_parts.sh 1 2 3 4 5
```

Neu Google Maps tra nhieu `Khong tim thay`, dung terminal bang `Ctrl+C`, nghi 20-30 phut, roi chay lai cham hon.

## 7. Tao File Ket Qua Cuoi

Sau khi crawl xong, quay ve root project va chay:

```bash
./.venv/bin/python scripts/finalize_results.py
```

Neu co phien ban data khac:

```bash
./.venv/bin/python scripts/finalize_results.py --version 20260601
```

File can giao/bao cao:

```text
data_YYYYMMDD/final/road_distance_YYYYMMDD_final.xlsx
```

## 8. Retry Cac Dong That Bai (Neu Can)

Neu sau buoc 7 con co nhieu dong `not_found_or_error`, co the chay lai:

### a) Kiem Tra Dong That Bai

Mo file nay de xem danh sach:

```text
data_YYYYMMDD/diagnostics/failed_rows_YYYYMMDD.xlsx
```

Neu chi con it dong (duoi 100), co the thong qua. Neu con nhieu, tien hanh retry.

### b) Chuan Bi Dung Cho Retry

Tao file input cho retry:

```bash
./.venv/bin/python scripts/retry_failed.py
```

Neu co phien ban data khac:

```bash
./.venv/bin/python scripts/retry_failed.py --version 20260601
```

Ket qua se la file:

```text
data_YYYYMMDD/input/crawl_pairs_retry_YYYYMMDD.xlsx
```

### c) Chia Va Crawl Lai

```bash
./.venv/bin/python scripts/split_crawl_parts.py \
  --source data_YYYYMMDD/input/crawl_pairs_retry_YYYYMMDD.xlsx \
  --part-folder work/part_retry

cd scripts
PART_FOLDER=../work/part_retry ./crawl_parts.sh 1 2 3
```

Neu bi rate-limit, dung terminal bang `Ctrl+C` va chay cham hon:

```bash
cd scripts
PART_FOLDER=../work/part_retry SLEEP_TIME=5 WAIT_TIME=15 REST_BETWEEN_PARTS=120 ./crawl_parts.sh 1 2 3
```

### d) Sau Retry - Tao Lai File Final

```bash
./.venv/bin/python scripts/finalize_results.py \
  --part-folder work/part_retry
```

## 9. Don File Tam

Sau khi da co file final va da kiem tra xong, co the xoa thu muc tam:

```text
work/
```

Khong xoa thu muc `data_YYYYMMDD/final/`, `data_YYYYMMDD/input/`, `data_YYYYMMDD/diagnostics/`.
