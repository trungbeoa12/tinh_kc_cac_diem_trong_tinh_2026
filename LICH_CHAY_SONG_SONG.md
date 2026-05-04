# Lịch chạy song song 2 terminal (part 12 → 56)

Đã chạy xong **part 1–11**. Dùng 2 terminal để chạy song song phần còn lại (part 12–56).

## Cách chạy

1. **Terminal 1** (script A – part chẵn 12, 14, 16, …, 56):

```bash
cd /home/trungdt2/Documents/GIS_VTB_Project2025/crawl_all_khoang_cach
./run_schedule_A.sh
```

2. **Terminal 2** (script B – part lẻ 13, 15, 17, …, 55):

```bash
cd /home/trungdt2/Documents/GIS_VTB_Project2025/crawl_all_khoang_cach
./run_schedule_B.sh
```

Chạy đồng thời cả hai terminal để crawl song song.

## Nội dung từng script

| Script | File Python | Các part chạy lần lượt |
|--------|-------------|-------------------------|
| **run_schedule_A.sh** | `run_crawl_part.py` | 12, 14, 16, 18, …, 54, 56 |
| **run_schedule_B.sh** | `run_crawl_part_B.py` | 13, 15, 17, 19, …, 53, 55 |

## Chạy 1 part bằng tay (không dùng lịch)

```bash
PART_ID=20 python run_crawl_part.py
PART_ID=21 python run_crawl_part_B.py
```

## Lưu ý

- Mỗi terminal dùng một file Python riêng (`run_crawl_part.py` và `run_crawl_part_B.py`) nên có thể chạy song song an toàn.
- Nếu cần chạy lại từ part nhỏ hơn (ví dụ từ part 1), sửa dãy số trong `run_schedule_A.sh` và `run_schedule_B.sh` cho phù hợp.
