# Project Overview

Project nay dung de tinh khoang cach duong bo giua cac diem/PGD trong cung tinh bang Google Maps.

## Trang Thai Hien Tai

Data `20260504` da xu ly xong.

File ket qua cuoi:

```text
data_20260504/final/road_distance_20260504_final.xlsx
```

Thong ke:

- Tong dong: `30,750`
- Dong co khoang cach hop le: `30,611`
- Dong con `Khong tim thay`: `139`

## Luong Xu Ly

```text
data_YYYYMMDD/input/branches_YYYYMMDD.xlsx
-> scripts/build_crawl_pairs.py
-> data_YYYYMMDD/input/crawl_pairs_YYYYMMDD.xlsx
-> scripts/split_crawl_parts.py
-> work/part/df_part_XX.pkl
-> scripts/crawl_part.py hoac scripts/crawl_parts.sh
-> work/part/output_part_XX/ket_qua_tu_...xlsx
-> scripts/finalize_results.py
-> data_YYYYMMDD/final/road_distance_YYYYMMDD_final.xlsx
```

## File Input Goc Can Co

File input goc nen dat ten:

```text
data_YYYYMMDD/input/branches_YYYYMMDD.xlsx
```

Cot bat buoc:

- `Mã phòng ban`
- `Tên phòng ban`
- `KINH ĐỘ`
- `VĨ ĐỘ`
- `Tỉnh`

## Quy Uoc Thu Muc

- `data_YYYYMMDD/input/`: file dau vao.
- `data_YYYYMMDD/final/`: file ket qua cuoi.
- `data_YYYYMMDD/diagnostics/`: file doi soat loi.
- `work/`: file tam khi crawl, khong commit.
- `scripts/`: ma lenh xu ly.
- `docs/`: tai lieu huong dan.
