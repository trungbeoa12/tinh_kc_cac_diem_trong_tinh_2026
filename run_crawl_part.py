#!/usr/bin/env python
# coding: utf-8

# In[9]:


import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ========== CẤU HÌNH ==========
# PART_ID có thể set qua biến môi trường: PART_ID=12 python run_crawl_part.py
PART_ID = int(os.environ.get("PART_ID", "1"))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, "part")
OUTPUT_FOLDER = os.path.join(DATA_FOLDER, f"output_part_{PART_ID:02d}")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

BATCH_SIZE = 100
SLEEP_TIME = 2
WAIT_TIME = 10

# ========== TRÌNH DUYỆT ==========
class GoogleMapsDistanceCalculator:
    def __init__(self):
        self.driver = None
        self.setup_driver()

    def setup_driver(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        try:
            url = f"https://www.google.com/maps/dir/{lat1},{lon1}/{lat2},{lon2}/data=!4m2!4m1!3e0"
            self.driver.get(url)
            time.sleep(4)
            try:
                element = WebDriverWait(self.driver, WAIT_TIME).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.xB1mrd-T3iPGc-iSfDt-ij8cu"))
                )
                return element.text
            except:
                try:
                    element = WebDriverWait(self.driver, WAIT_TIME).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "div.XdKEzd"))
                    )
                    return element.text
                except:
                    return "Không tìm thấy"
        except Exception as e:
            print(f"❌ Lỗi: {str(e)}")
            return None

    def close(self):
        if self.driver:
            self.driver.quit()

# ========== CHẠY CRAWL ==========
def crawl_with_resume(df_input):
    # Đảm bảo index liên tục từ 0 để dùng với at[idx, ...]
    df = df_input.copy().reset_index(drop=True)
    total_rows = len(df)
    total_batches = (total_rows + BATCH_SIZE - 1) // BATCH_SIZE

    if 'Khoảng cách đường bộ' not in df.columns:
        df['Khoảng cách đường bộ'] = None

    for batch_idx in range(total_batches):
        start_idx = batch_idx * BATCH_SIZE
        end_idx = min((batch_idx + 1) * BATCH_SIZE, total_rows)
        output_file = os.path.join(OUTPUT_FOLDER, f"ket_qua_tu_{start_idx}_den_{end_idx - 1}.xlsx")

        if os.path.exists(output_file):
            print(f"✅ Bỏ qua batch {start_idx}-{end_idx - 1} (đã tồn tại)")
            continue

        print(f"\n🚀 Bắt đầu batch {start_idx}-{end_idx - 1}...")
        calculator = GoogleMapsDistanceCalculator()

        for idx in range(start_idx, end_idx):
            if pd.notna(df.at[idx, 'Khoảng cách đường bộ']):
                continue

            row = df.loc[idx]
            # Với bộ dữ liệu mới ml_thay_doi_drop_2025_sang_2026.xlsx,
            # sử dụng tên cột: vi_do_1, kinh_do_1, vi_do_2, kinh_do_2
            lat1, lon1 = row['vi_do_1'], row['kinh_do_1']
            lat2, lon2 = row['vi_do_2'], row['kinh_do_2']

            print(f"🔍 Dòng {idx}: ({lat1},{lon1}) → ({lat2},{lon2})")
            distance = calculator.calculate_distance(lat1, lon1, lat2, lon2)
            df.at[idx, 'Khoảng cách đường bộ'] = distance
            print(f"➡️  Kết quả: {distance}")
            time.sleep(SLEEP_TIME)

        calculator.close()
        df.iloc[start_idx:end_idx].to_excel(output_file, index=False)
        print(f"📁 Đã lưu batch vào: {output_file}")

    print("\n🎉 Đã hoàn thành tất cả các batch.")

# ========== CHẠY ==========
file_path = os.path.join(DATA_FOLDER, f"df_part_{PART_ID:02d}.pkl")
df_part = pd.read_pickle(file_path)
crawl_with_resume(df_part)

