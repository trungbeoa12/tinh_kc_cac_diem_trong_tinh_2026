# Lich chay song song

Data `20260504` co khoang 308 part sau khi chay:

```bash
python split_to_part_100.py
```

Chay hai terminal voi cau hinh mac dinh:

- `SLEEP_TIME=3`: nghi 3 giay giua moi request Google Maps trong 1 part.
- `REST_BETWEEN_PARTS=300`: nghi 5 phut sau moi part.

```bash
./run_schedule_A.sh
./run_schedule_B.sh
```

- `run_schedule_A.sh`: chay cac part le `1, 3, 5, ..., 307`.
- `run_schedule_B.sh`: chay cac part chan `2, 4, 6, ..., 308`.

Chay rieng mot part:

```bash
PART_ID=1 python run_crawl_part.py
```

Neu muon chay cham hon:

```bash
SLEEP_TIME=5 REST_BETWEEN_PARTS=600 ./run_schedule_A.sh
SLEEP_TIME=5 REST_BETWEEN_PARTS=600 ./run_schedule_B.sh
```

Neu bi dung giua chung, chay lai cung lenh. Script crawl se bo qua output part/batch da ton tai.
