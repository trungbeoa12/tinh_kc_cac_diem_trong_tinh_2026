# Tinh khoang cach cac diem trong tinh 2026

Project nay luu ket qua crawl khoang cach duong bo Google Maps cho data `20260504`.

Trang thai hien tai: **data da crawl va chuan hoa xong**. Thu muc `part/`, cac output batch trung gian, retry part va `.venv` da duoc xoa de giu project gon.

## File Ket Qua Cuoi

File can dung:

```text
data_20260504/final/road_distance_20260504_final.xlsx
```

Thong tin file:

- Tong dong: `30,750`
- Dong co khoang cach hop le: `30,611`
- Dong con `Khong tim thay`: `139`
- Khoang cach da duoc chuan hoa ve don vi km.
- Cot `Khoang cach duong bo km` duoc dinh dang 2 chu so thap phan trong Excel.

## Cot Quan Trong Trong File Cuoi

- `global_index`: index 0-based theo file crawl input ban dau.
- `original_excel_row`: so dong trong Excel goc, tinh ca header.
- `ma_phong_ban_1`, `ten_phong_ban_1`, `kinh_do_1`, `vi_do_1`: diem bat dau.
- `ma_phong_ban_2`, `ten_phong_ban_2`, `kinh_do_2`, `vi_do_2`: diem ket thuc.
- `khoang_cach_chim_bay`: khoang cach chim bay tinh truoc khi crawl.
- `tinh_thanh`: tinh/thanh cua cap diem.
- `Khoang cach duong bo`: gia tri text lay tu Google Maps, vi du `1 hr 8 min\n33.8 km`.
- `Khoang cach duong bo km`: khoang cach da tach va quy doi ve km.
- `thoi gian`: thoi gian di chuyen tach tu Google Maps.
- `crawl_status`: trang thai sau merge/retry.

## Chuan Bi Chay Cho Data Moi

### Tao Input Data Tu Template

Neu can chay crawl cho data moi:

1. **Su dung template san co:**

```text
docs/data_template.xlsx
```

2. **Xem huong dan:**

```text
docs/data_template_guide.md
```

3. **Tao thu muc data moi:**

```bash
mkdir -p data_YYYYMMDD/input
cp docs/data_template.xlsx data_YYYYMMDD/input/branches_YYYYMMDD.xlsx
```

4. **Dien du lieu va cap nhat config:**

```python
# scripts/config.py
DATA_VERSION = "YYYYMMDD"  # Thay doi thanh ngay data
```

5. **Chay crawl:**

```bash
python scripts/build_crawl_pairs.py
python scripts/split_crawl_parts.py
cd scripts && ./crawl_parts.sh 1 2 3 ...
python scripts/finalize_results.py
```

## Quy Tac Chuan Hoa Khoang Cach

Cot `Khoang cach duong bo km` duoc tao tu cot text `Khoang cach duong bo`:

- Gia tri `km` giu nguyen va lam tron/format 2 chu so thap phan.
- Gia tri `m` duoc quy doi sang km.
- Vi du:
  - `900 m` -> `0.90`
  - `24.6 km` -> `24.60`
  - `106 km` -> `106.00`
- Cac dong `Khong tim thay` de trong cot km va cot thoi gian.

## File Input Goc

```text
data_20260504/input/branches_20260504.xlsx
data_20260504/input/crawl_pairs_20260504.xlsx
```

- `branches_20260504.xlsx`: danh sach diem goc.
- `crawl_pairs_20260504.xlsx`: danh sach cap diem cung tinh dung lam input crawl.

Quy uoc cho lan chay moi:

- Moi dot data nen dat trong mot thu muc rieng dang `data_YYYYMMDD/`.
- File diem goc dat tai:

```text
data_YYYYMMDD/input/branches_YYYYMMDD.xlsx
```

- File crawl input sau khi generate dat tai:

```text
data_YYYYMMDD/input/crawl_pairs_YYYYMMDD.xlsx
```

- File ket qua cuoi dat trong:

```text
data_YYYYMMDD/final/
```

- File doi soat/loi con lai dat trong:

```text
data_YYYYMMDD/diagnostics/
```

Voi dot hien tai, `YYYYMMDD = 20260504`.

## File Kiem Tra Con Lai

```text
data_20260504/diagnostics/failed_rows_20260504.xlsx
data_20260504/diagnostics/failed_rows_20260504.csv
data_20260504/diagnostics/finalize_summary_20260504.txt
```

Sau retry con `139` dong `Khong tim thay`. Nhom nay chu yeu lien quan:

- Tuyen `PGD Con Dao` voi dat lien.
- Tuyen `PGD Ba Ria` den mot so diem TP. Ho Chi Minh/Binh Duong.

## Cau Truc Thu Muc

```text
data_20260504/
  final/        file ket qua cuoi
  input/        file input goc
  diagnostics/  file doi soat dong con loi

scripts/        script xu ly/crawl da dung
docs/           tai lieu huong dan ban dau
work/           file part/output tam khi crawl lai, khong commit
```

## Scripts

Thu muc `scripts/` con giu cac script tham khao:

- `build_crawl_pairs.py`: tao danh sach cap diem cung tinh va tinh khoang cach chim bay.
- `split_crawl_parts.py`: chia input crawl thanh cac part 100 dong.
- `crawl_part.py`: crawl mot part bang Selenium/Google Maps.
- `crawl_parts.sh`: file shell chung de chay danh sach part neu can crawl lai.
- `finalize_results.py`: merge output crawl, tach km/thoi gian va tao diagnostics.
- `requirements.txt`: package can cai neu tao lai moi truong Python.

Luu y: hien tai project khong con `.venv` va khong con thu muc `part/`. Neu chay lai, cac file tam se duoc tao trong `work/part/`.

## Chay Lai Project

Huong dan tung buoc cho nguoi it dung Terminal:

```text
docs/user_guide.md
```

Tu root project:

```bash
python3 -m venv .venv
./.venv/bin/python -m pip install -r scripts/requirements.txt
```

Tao file crawl input tu file diem goc:

```bash
./.venv/bin/python scripts/build_crawl_pairs.py
```

Voi dot data moi, nen truyen ro duong dan:

```bash
./.venv/bin/python scripts/build_crawl_pairs.py \
  --input data_YYYYMMDD/input/branches_YYYYMMDD.xlsx \
  --output data_YYYYMMDD/input/crawl_pairs_YYYYMMDD.xlsx \
  --sample work/crawl_pairs_YYYYMMDD_sample.csv
```

Chia part 100 dong:

```bash
./.venv/bin/python scripts/split_crawl_parts.py
```

Voi dot data moi:

```bash
./.venv/bin/python scripts/split_crawl_parts.py \
  --source data_YYYYMMDD/input/crawl_pairs_YYYYMMDD.xlsx \
  --part-folder work/part \
  --rows-per-part 100
```

Chay mot vai part:

```bash
cd scripts
PYTHON_BIN=../.venv/bin/python ./crawl_parts.sh 1 2 3
```

Chay cham hon de giam rui ro bi Google Maps throttle:

```bash
cd scripts
PYTHON_BIN=../.venv/bin/python SLEEP_TIME=10 REST_BETWEEN_PARTS=60 ./crawl_parts.sh 1 2 3
```

Output crawl se nam tai:

```text
work/part/output_part_XX/
```

Neu muon dung thu muc part khac:

```bash
cd scripts
PART_FOLDER=../work/part PYTHON_BIN=../.venv/bin/python ./crawl_parts.sh 1 2 3
```

Merge output crawl va tach cot khoang cach/thoi gian:

```bash
./.venv/bin/python scripts/finalize_results.py
```

Voi dot data moi:

```bash
./.venv/bin/python scripts/finalize_results.py \
  --source data_YYYYMMDD/input/crawl_pairs_YYYYMMDD.xlsx \
  --part-folder work/part \
  --final data_YYYYMMDD/final/road_distance_YYYYMMDD_final.xlsx \
  --remaining data_YYYYMMDD/diagnostics/failed_rows_YYYYMMDD.xlsx \
  --summary data_YYYYMMDD/diagnostics/finalize_summary_YYYYMMDD.txt
```

File merge cuoi cua dot `20260504` da duoc luu san trong `data_20260504/final/`.

## Recrawl HIGH/MEDIUM Suspects

Repo da co san input compare va batch recrawl cho dot `20260504` vs `20260312`:

```text
debug_outputs/compare_20260504_vs_20260312/
debug_outputs/recrawl_all_suspects_20260504_vs_20260312/
```

Neu can tao lai 3 batch tu file HIGH/MEDIUM:

```bash
./.venv/bin/python scripts/prepare_recrawl_all_suspects_batches.py
```

Chay recrawl tuan tu ca 3 batch:

```bash
bash debug_outputs/recrawl_all_suspects_20260504_vs_20260312/run_all_recrawl_batches.sh
```

Hoac chay tung batch:

```bash
bash debug_outputs/recrawl_all_suspects_20260504_vs_20260312/run_recrawl_batch_01.sh
bash debug_outputs/recrawl_all_suspects_20260504_vs_20260312/run_recrawl_batch_02.sh
bash debug_outputs/recrawl_all_suspects_20260504_vs_20260312/run_recrawl_batch_03.sh
```

Output moi se nam trong `debug_outputs/recrawl_all_suspects_20260504_vs_20260312/output_batch_XX/`.
Script recrawl khong ghi de output da ton tai neu khong truyen `--overwrite`.

## Tai Lieu Cu

Tai lieu trong `docs/`:

- `user_guide.md`: huong dan su dung tung buoc cho nguoi khong chuyen CNTT.
- `project_overview.md`: tong quan ky thuat ngan gon.
- `parallel_run_notes.md`: ghi chu khi chay nhieu terminal.
- `crawl_guide_legacy.md`: tai lieu cu trong giai do crawl ban dau, chi giu de tham khao.
