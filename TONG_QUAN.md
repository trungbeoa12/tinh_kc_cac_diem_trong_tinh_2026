# Tong quan project

Project hien chi giu luong crawl Google Maps cho data `20260504`.

## File chinh

- `data_20260504/data_20260504.xlsx`: danh sach diem goc gom ma phong ban, ten phong ban, kinh do, vi do, tinh.
- `generate_crawl_input.py`: tao tat ca cap diem cung tinh va tinh khoang cach chim bay.
- `data_20260504/ml_to_hop_crawl_20260504.xlsx`: file input cho buoc chia part.
- `split_to_part_100.py`: chia input crawl thanh cac file `part/df_part_XX.pkl`, moi part 100 dong.
- `run_crawl_part.py`: dung Selenium mo Google Maps va lay khoang cach duong bo cho tung part.
- `run_schedule_A.sh`, `run_schedule_B.sh`: chay song song cac part le/chan.

## Luong xu ly

```text
data_20260504/data_20260504.xlsx
-> generate_crawl_input.py
-> data_20260504/ml_to_hop_crawl_20260504.xlsx
-> split_to_part_100.py
-> part/df_part_XX.pkl
-> run_crawl_part.py
-> part/output_part_XX/ket_qua_tu_...xlsx
```

## Cot bat buoc trong file goc

- `Mã phòng ban`
- `Tên phòng ban`
- `KINH ĐỘ`
- `VĨ ĐỘ`
- `Tỉnh`
