# Parallel Run Notes

Dung file shell chung:

```bash
cd scripts
PYTHON_BIN=../.venv/bin/python ./crawl_parts.sh 1 2 3
```

## Chay Nhieu Terminal

Co the mo 2-3 terminal va chia danh sach part thu cong.

Vi du 3 terminal:

```bash
cd scripts
PYTHON_BIN=../.venv/bin/python ./crawl_parts.sh 1 4 7 10
```

```bash
cd scripts
PYTHON_BIN=../.venv/bin/python ./crawl_parts.sh 2 5 8 11
```

```bash
cd scripts
PYTHON_BIN=../.venv/bin/python ./crawl_parts.sh 3 6 9 12
```

## Cau Hinh Cham Hon

Neu Google Maps bat dau tra nhieu `Khong tim thay`, nen dung lai va chay cham hon:

```bash
cd scripts
PYTHON_BIN=../.venv/bin/python SLEEP_TIME=10 REST_BETWEEN_PARTS=60 ./crawl_parts.sh 1 2 3
```

Bien cau hinh:

- `SLEEP_TIME`: so giay nghi giua tung dong trong mot part.
- `REST_BETWEEN_PARTS`: so giay nghi giua cac part.
- `WAIT_TIME`: so giay doi Google Maps render ket qua.
- `BATCH_SIZE`: so dong trong mot batch output.

## Resume

Neu batch output da ton tai trong:

```text
work/part/output_part_XX/ket_qua_tu_START_den_END.xlsx
```

script se bo qua batch do. Vi vay neu dang chay bi dung, co the chay lai cung lenh.
