# Huong Dan Su Dung Crawl Google Maps

> Luu y: day la tai lieu cu trong giai do crawl ban dau. Ten file va cau truc thu muc trong tai lieu nay co the khong con dung sau khi project da duoc don dep. Neu can chay lai project, dung `docs/user_guide.md` va `README.md`.

## 1. Data Dang Dung

Project hien chi giu luong crawl cho data moi:

- File goc: `data_20260504/data_20260504.xlsx`
- File input crawl: `data_20260504/ml_to_hop_crawl_20260504.xlsx`
- Part crawl: `part/df_part_XX.pkl`
- Output crawl: `part/output_part_XX/ket_qua_tu_...xlsx`

Luong xu ly:

```text
data_20260504/data_20260504.xlsx
-> generate_crawl_input.py
-> data_20260504/ml_to_hop_crawl_20260504.xlsx
-> split_to_part_100.py
-> part/df_part_XX.pkl
-> run_crawl_part.py
-> part/output_part_XX/ket_qua_tu_...xlsx
```

## 2. Chuan Bi Moi Truong

```bash
cd /home/trungdt2/Documents/crawl_all_khoang_cach/tinh_kc_cac_diem_trong_tinh_2026
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install pandas selenium webdriver-manager openpyxl
```

May can co Google Chrome. Lan chay dau tien co the can internet de `webdriver-manager` tai ChromeDriver.

## 3. Tao File Input Crawl

Chay:

```bash
python generate_crawl_input.py
```

Script nay doc `data_20260504/data_20260504.xlsx`, tao tat ca cap diem cung tinh, tinh them `khoang_cach_chim_bay`, va ghi ra:

```text
data_20260504/ml_to_hop_crawl_20260504.xlsx
data_20260504/sample_ml_to_hop_crawl_20260504_head.csv
```

## 4. Chia Part

Chay:

```bash
python split_to_part_100.py
```

Voi data hien tai:

- Tong dong input crawl: `30,750`
- So dong moi part: `100`
- Tong so part: `308`
- Part cuoi: `50` dong

## 5. Test Truoc Khi Chay Dai

Test 1 dong dau tien:

```bash
PART_ID=1 MAX_ROWS=1 BATCH_SIZE=1 SLEEP_TIME=1 WAIT_TIME=10 python run_crawl_part.py
```

Neu thanh cong, output test se nam o:

```text
part/output_part_01/ket_qua_tu_0_den_0.xlsx
```

Test 5 dong:

```bash
PART_ID=1 MAX_ROWS=5 BATCH_SIZE=5 SLEEP_TIME=2 WAIT_TIME=10 python run_crawl_part.py
```

## 6. Chay Mot Part

Chay part 1:

```bash
PART_ID=1 python run_crawl_part.py
```

Chay part khac:

```bash
PART_ID=25 python run_crawl_part.py
```

Mac dinh moi part co 100 dong. Output cua part 25 se nam o:

```text
part/output_part_25/
```

## 7. Chay Song Song Hai Terminal

Hai script da co san:

- `run_schedule_A.sh`: chay cac part le `1, 3, 5, ..., 307`
- `run_schedule_B.sh`: chay cac part chan `2, 4, 6, ..., 308`

Mac dinh:

- `SLEEP_TIME=3`: nghi 3 giay giua moi request Google Maps trong 1 part.
- `REST_BETWEEN_PARTS=300`: nghi 5 phut sau moi part.
- `WAIT_TIME=10`: doi toi da 10 giay de Google Maps tra ket qua.
- `BATCH_SIZE=100`: xu ly 100 dong moi part.

Terminal 1:

```bash
./run_schedule_A.sh
```

Terminal 2:

```bash
./run_schedule_B.sh
```

## 8. Chay Cham Hon Cho An Toan

Neu muon giam nguy co bi Google chan:

Terminal 1:

```bash
SLEEP_TIME=5 REST_BETWEEN_PARTS=600 ./run_schedule_A.sh
```

Terminal 2:

```bash
SLEEP_TIME=5 REST_BETWEEN_PARTS=600 ./run_schedule_B.sh
```

Trong do:

- `SLEEP_TIME=5`: nghi 5 giay giua tung dong crawl.
- `REST_BETWEEN_PARTS=600`: nghi 10 phut sau moi part.

## 9. Resume Khi Bi Dung Giua Chung

Script co co che resume theo file output. Neu output cua batch da ton tai, script se bo qua:

```text
part/output_part_XX/ket_qua_tu_START_den_END.xlsx
```

Vi vay neu may tat hoac terminal bi dung, chi can chay lai lenh cu:

```bash
./run_schedule_A.sh
./run_schedule_B.sh
```

## 10. Luu Y

- Neu ket qua co nhieu dong `Khong tim thay`, tang `SLEEP_TIME` len `5` hoac `7`.
- Neu Google Maps load cham, tang `WAIT_TIME` len `15` hoac `20`.
- Khong nen xoa thu muc `part/output_part_XX` neu muon resume.
- Neu muon crawl lai tu dau, can xoa output cu trong `part/output_part_XX`.
