import os
from math import ceil

import pandas as pd


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# File Excel nguồn mà bạn đưa:
SOURCE_FILE = os.path.join(
    BASE_DIR,
    "data_20260313/output_2026/ml_thay_doi_drop_2025_sang_2026.xlsx",
)

# Nơi lưu các file df_part_XX.pkl để crawl
PART_FOLDER = os.path.join(BASE_DIR, "part")

# Số dòng mỗi part
ROWS_PER_PART = 100


def main() -> None:
    print("Đọc file nguồn:", SOURCE_FILE)
    if not os.path.exists(SOURCE_FILE):
        raise FileNotFoundError(f"Không tìm thấy file: {SOURCE_FILE}")

    df = pd.read_excel(SOURCE_FILE)
    print("Tổng số dòng:", len(df))
    print("Các cột:", list(df.columns))

    # Nếu chưa có cột 'Khoảng cách đường bộ' thì thêm để khớp script crawl
    if "Khoảng cách đường bộ" not in df.columns:
        df["Khoảng cách đường bộ"] = None

    os.makedirs(PART_FOLDER, exist_ok=True)

    num_parts = ceil(len(df) / ROWS_PER_PART)
    print("Số part sẽ tạo:", num_parts)

    for part_idx in range(num_parts):
        start = part_idx * ROWS_PER_PART
        end = min((part_idx + 1) * ROWS_PER_PART, len(df))
        df_part = df.iloc[start:end].copy()

        part_id = part_idx + 1
        out_path = os.path.join(PART_FOLDER, f"df_part_{part_id:02d}.pkl")
        df_part.to_pickle(out_path)
        print(f"Đã lưu part {part_id:02d}: dòng {start}–{end-1} -> {out_path}")

    print("Hoàn tất chia part.")


if __name__ == "__main__":
    main()
