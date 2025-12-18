import sys
# 更換
from datetime import datetime
import json
import os
import subprocess
import pandas as pd
from ping3 import ping  # type: ignore
from tqdm import tqdm # type: ignore
import csv
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from logging.handlers import RotatingFileHandler
from filelock import FileLock, Timeout
import warnings
import shutil
warnings.simplefilter(action='ignore', category=FutureWarning)

import configparser

# -------------------------------------------------
#  讀取 config.ini（固定用 .py 所在資料夾）
# -------------------------------------------------
config = configparser.ConfigParser()

# 取得目前這個 .py 檔所在的資料夾
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 如果你檔名就是 config.ini，就這樣寫
config_path = os.path.join(BASE_DIR, "config.ini")

# 如果你想分不同線別，用專屬 ini（例如 EAP_K11_3F.ini），就改這裡的檔名
# config_path = os.path.join(BASE_DIR, "EAP_K11_3F.ini")

if not os.path.exists(config_path):
    print(f"❌ 找不到設定檔：{config_path}")
    sys.exit(1)

# 讀取 ini
config.read(config_path, encoding="utf-8")

# 檢查 Paths 區段是否存在
if "Paths" not in config:
    print(f"❌ 設定檔 {config_path} 缺少 [Paths] 區段")
    sys.exit(1)

# 取得路徑設定
try:
    LOG_FILE = config.get("Paths", "log_file")
    SOURCE_FILES = [
        x.strip() for x in config.get("Paths", "source_files").split(",")
        if x.strip()
    ]
except Exception as e:
    print(f"❌ 讀取 [Paths] 設定失敗：{e}")
    sys.exit(1)

# 設定 logging（使用 RotatingFileHandler，最大 100MB，不保留備份）
log_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=100*1024*1024,  # 100MB
    backupCount=0,           # 不保留備份，達到 100MB 後清空重新開始
    encoding='utf-8'
)
log_handler.setLevel(logging.INFO)
log_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    handlers=[log_handler, console_handler]
)


def get_status_file(path):
    """
    根據 CSV 來源檔名產生 prev_XXX.json
    """
    file_name = os.path.basename(path)
    safe_name = file_name.replace(" ", "_")
    prev_file = os.path.join(BASE_DIR, f"prev_{safe_name}.json")
    return prev_file

class Ping_EAP:
    def __init__(self, file_path):
        self.file_path = file_path
        self.ip_addresses = []
        self.device_names = []
        self.ping_results = {}

    def read_ip_addresses_from_csv(self):
        with open(self.file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                self.ip_addresses.append(row[0])
                self.device_names.append(row[3])

    def ping_host(self, ip_address, timeout_sec):
        try:
            # Windows ping，-n 1 一次，-w timeout 以毫秒為單位
            result = subprocess.run(
                ['ping', '-n', '1', ip_address, '-w', str(timeout_sec * 1000)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=timeout_sec + 1  # 給一點餘裕
            )
            output = result.stdout

            # 必須包含 TTL 代表真實回應
            if "TTL=" in output:
                return ip_address, "alive"
            else:
                return ip_address, "dead"

        except subprocess.TimeoutExpired:
            return ip_address, "dead"
        except Exception:
            return ip_address, "dead"

    def scan_all(self):
        print("🔍 第一次快速掃描中（timeout=2 秒）...")
        dead_list = []

        # 第一次快速掃描
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {
                executor.submit(self.ping_host, ip, 2): ip
                for ip in self.ip_addresses
            }
            for future in tqdm(as_completed(futures), total=len(futures)):
                ip, result = future.result()
                self.ping_results[ip] = result
                if result == "dead":
                    dead_list.append(ip)

        retry_dead_list = []
        if dead_list:
            print("🔁 第二次慢速重試中（timeout=8 秒）...")
            with ThreadPoolExecutor(max_workers=30) as executor:
                futures = {
                    executor.submit(self.ping_host, ip, 8): ip
                    for ip in dead_list
                }
                for future in tqdm(as_completed(futures), total=len(futures)):
                    ip, result = future.result()
                    if result == "alive":
                        self.ping_results[ip] = "alive"  # 覆蓋之前的 dead
                    else:
                        retry_dead_list.append(ip)

        # 第三次使用 Device_Name 重試
        if retry_dead_list:
            print("🔁 第三次使用 Device_Name 重試中（timeout=8 秒）...")
            success_by_device = []   # 暫存成功訊息
            fail_by_device = []      # 暫存失敗訊息

            with ThreadPoolExecutor(max_workers=20) as executor:
                futures = {}
                for ip in retry_dead_list:
                    try:
                        idx = self.ip_addresses.index(ip)
                        device_name = self.device_names[idx]
                        if device_name.strip():
                            futures[executor.submit(self.ping_host, device_name, 8)] = (ip, device_name)
                    except ValueError:
                        continue

                for future in tqdm(as_completed(futures), total=len(futures)):
                    (ip, device_name) = futures[future]
                    _, result = future.result()
                    if result == "alive":
                        self.ping_results[ip] = "alive"  # 以 IP 為 key 更新狀態
                        success_by_device.append((ip, device_name))
                    else:
                        fail_by_device.append((ip, device_name))

            # ★ 第三輪全部完成後，才一次性輸出彙整 log
            if success_by_device:
                logging.info("✅ 第三輪 Device_Name 成功替代清單（共 %d 筆）：", len(success_by_device))
                for ip, dev in success_by_device:
                    logging.info("  - Device_Name=%s 替代 IP=%s → alive", dev, ip)
            if fail_by_device:
                logging.warning("❌ 第三輪 Device_Name 仍無回應清單（共 %d 筆）：", len(fail_by_device))
                for ip, dev in fail_by_device:
                    logging.warning("  - Device_Name=%s 替代 IP=%s → dead", dev, ip)

    def update_csv_with_alive_status(self):
        rows = []
        with open(self.file_path, mode='r', encoding='utf-8-sig') as file:
            reader = csv.reader(file)
            header = next(reader)

            # 如果有 alive_or_dead 欄位，先找到 index 並從每行中刪除
            if 'alive_or_dead' in header:
                index_to_remove = header.index('alive_or_dead')
                header.pop(index_to_remove)
            else:
                index_to_remove = None  # 沒有也 ok

            header.append('alive_or_dead')
            rows.append(header)

            for row in reader:
                if index_to_remove is not None and len(row) > index_to_remove:
                    row.pop(index_to_remove)  # 刪除舊的 alive_or_dead 欄位

                ip_address = row[0]
                status = self.ping_results.get(ip_address, "dead")
                row.append(status)
                rows.append(row)

        with open(self.file_path, mode='w', encoding='utf-8-sig', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)


    def display_results(self):
        formatted_devices = []
        pingable_formatted_devices = []

        for ip, device_name in zip(self.ip_addresses, self.device_names):
            if re.match(r'\d{8}-W\d{2,3}', device_name):
                formatted_devices.append((ip, device_name))
                if self.ping_results.get(ip) == "alive":
                    pingable_formatted_devices.append(ip)

        total_pingable = list(ip for ip, status in self.ping_results.items() if status == "alive")
        return len(total_pingable), len(formatted_devices), len(pingable_formatted_devices)


def write_error_task(file_path):
    lock_path = file_path + ".lock"
    json_lock_path = r"\\20220530-w03\Data\EAP_Health_level\error_data\error_lose_ipcount.json.lock"

    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')


        filtered_df = df[
            (df["alive_or_dead"].astype(str).str.lower() == "dead") &    
            (df["Machine_ID"].notna()) & 
            (df["Machine_ID"].astype(str).str.strip() != '')  
        ]

        if filtered_df.empty:
            logging.info(f"⚠️ 無符合條件資料，略過：{file_path}")
            return

        # file_place = filtered_df["File_Place"].iloc[0]
        current_file_name = os.path.basename(file_path)
        file_place = current_file_name

        # 先針對每個分類做切分
        categories = ['EAP', 'EQP', 'Switch']

        for category in categories:
            category_df = filtered_df[filtered_df['Category'].astype(str).str.strip() == category]
            
            if category_df.empty:
                continue 

            # csv_output_path = r"\\20220530-w03\Data\EAP_Health_level\error_data\error_lose_machine.csv"
            csv_output_path = rf"\\20220530-w03\Data\EAP_Health_level\error_data\error_lose_machine_{category}.csv"

            with FileLock(csv_output_path + ".lock", timeout=30):
                if os.path.exists(csv_output_path):
                    existing_df = pd.read_csv(csv_output_path, encoding='utf-8-sig')
                    # existing_df = existing_df[existing_df["File_Place"] != file_place]
                    combined_df = pd.concat([existing_df, category_df], ignore_index=True)
                    updated_df = combined_df.drop_duplicates(subset=["Internal_IP", "Machine_ID"])
                    # updated_df = pd.concat([existing_df, category_df], ignore_index=True)
                else:
                    updated_df = category_df

                updated_df.to_csv(csv_output_path, index=False, encoding='utf-8-sig')
                logging.info(f"✅ 已更新 {csv_output_path}，排除重複的 File_Place：{file_place}")
                
        # JSON 寫入加鎖
        today_str = datetime.now().strftime("%Y%m%d")
        ip_count_path = rf"\\20220530-w03\Data\EAP_Health_level\error_data\Daily_error\error_lose_ipcount_{today_str}.json"


        df = pd.read_csv(file_path, encoding='utf-8-sig')
        # 所以正確做法是：直接抓出第一個 Internal_IP == '0' 那行
        cutoff_rows = df[
            df["Internal_IP"].astype(str).str.strip() == "0"
        ]

        if not cutoff_rows.empty:
            cutoff_index = cutoff_rows.index[0]
            df = df.iloc[:cutoff_index]  # 保留 0 出現前的所有資料

        filtered_df = df[
            (df["alive_or_dead"].astype(str).str.lower().str.strip() == "dead") & 
            (df["Machine_ID"].notna()) & 
            (df["Machine_ID"].astype(str).str.strip() != '')  
        ]


        with FileLock(json_lock_path, timeout=30):
            if os.path.exists(ip_count_path):
                with open(ip_count_path, "r", encoding="utf-8-sig") as f:
                    try:
                        ip_loss_data = json.load(f)
                    except json.JSONDecodeError:
                        ip_loss_data = {}
            else:
                ip_loss_data = {}

            if file_place not in ip_loss_data:
                ip_loss_data[file_place] = {}

        for _, row in filtered_df.iterrows():
            ip = str(row["Internal_IP"]).strip()
            machine = str(row["Machine_ID"]).strip()
            
            # 檢查 IP 無效
            if ip in ["", "0", "nan"]:
                continue

            # 檢查 Machine_ID 無效
            if machine in ["", "0", "nan"]:
                continue

            if machine not in ip_loss_data[file_place]:
                ip_loss_data[file_place][ip] = {
                    "ip": ip,
                    "machine": machine,
                    "count": 1
                }
            else:
                ip_loss_data[file_place][ip]["count"] += 1

        with open(ip_count_path, "w", encoding="utf-8-sig") as f:
            json.dump(ip_loss_data, f, ensure_ascii=False, indent=4)

        logging.info(f"✅ 已更新 IP loss 計數檔案：{ip_count_path}")

    except Timeout:
        logging.error(f"❌ 檔案鎖取得失敗（被其他程式佔用中）：{lock_path} 或 {json_lock_path}")





def backup_csv_before_ping(csv_path):
    """
    備份 CSV 檔案，保留 5 份備份（backup_1 到 backup_5）
    放在各自的檔名資料夾中
    
    備份輪替：
    - backup_5 被刪除
    - backup_4 → backup_5
    - backup_3 → backup_4
    - backup_2 → backup_3
    - backup_1 → backup_2
    - 原始檔 → backup_1
    """
    file_name = os.path.basename(csv_path)
    file_name_without_ext = os.path.splitext(file_name)[0]
    
    # 建立檔名專屬資料夾
    backup_dir = os.path.join(BASE_DIR, "backups", file_name_without_ext)
    os.makedirs(backup_dir, exist_ok=True)
    
    logging.info(f"📦 開始備份 CSV：{file_name}")
    
    # 備份檔案路徑
    backup_files = [os.path.join(backup_dir, f"backup_{i}.csv") for i in range(1, 6)]
    
    # 輪替備份：從後往前
    # 刪除最舊的 backup_5
    if os.path.exists(backup_files[4]):
        try:
            os.remove(backup_files[4])
            logging.info(f"🗑️ 已刪除最舊的備份：backup_5.csv")
        except Exception as e:
            logging.error(f"❌ 刪除 backup_5 失敗：{e}")
    
    # backup_4 → backup_5, backup_3 → backup_4, ..., backup_1 → backup_2
    for i in range(4, 0, -1):
        if os.path.exists(backup_files[i-1]):
            try:
                os.rename(backup_files[i-1], backup_files[i])
                logging.info(f"📝 已將 backup_{i} 改名為 backup_{i+1}")
            except Exception as e:
                logging.error(f"❌ backup_{i} → backup_{i+1} 改名失敗：{e}")
    
    # 複製原始檔為 backup_1
    try:
        shutil.copy2(csv_path, backup_files[0])
        logging.info(f"📋 已複製原始 CSV 為 backup_1.csv")
    except Exception as e:
        logging.error(f"❌ 複製 CSV 失敗：{e}")
    
    return backup_dir

def check_dead_devices():
    from datetime import datetime
        
    eap_list = []      # EAP 设备列表
    eqp_list = []      # EQP 设备列表
    switch_list = []   # Switch 设备列表
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    logging.info(f"========== 开始检查 Dead 设备 ==========")
    logging.info(f"BASE_DIR: {BASE_DIR}")
    logging.info(f"file_path 共有 {len(file_path)} 个档案")
    
    for i, path in enumerate(file_path):
        logging.info(f"--- 档案 {i+1}/{len(file_path)} ---")
        logging.info(f"路径: {path}")
        
        if not os.path.exists(path):
            logging.warning(f"⚠️ 档案不存在: {path}")
            continue
            
        file_name = os.path.basename(path)
        file_name_without_ext = os.path.splitext(file_name)[0]
        
        # 建立备份资料夹路径
        backup_dir = os.path.join(BASE_DIR, "backups", file_name_without_ext)
        
        # 5 份备份档案路径
        backup_1_file = os.path.join(backup_dir, "backup_1.csv")
        backup_2_file = os.path.join(backup_dir, "backup_2.csv")
        backup_3_file = os.path.join(backup_dir, "backup_3.csv")
        backup_4_file = os.path.join(backup_dir, "backup_4.csv")
        backup_5_file = os.path.join(backup_dir, "backup_5.csv")
        
        logging.info(f"档案存在: True")
        logging.info(f"备份资料夹: {backup_dir}")
        
        # 检查备份档案是否存在
        backup_1_exists = os.path.exists(backup_1_file)
        backup_2_exists = os.path.exists(backup_2_file)
        backup_3_exists = os.path.exists(backup_3_file)
        backup_4_exists = os.path.exists(backup_4_file)
        backup_5_exists = os.path.exists(backup_5_file)
        
        logging.info(f"备份状态: backup_1={backup_1_exists}, backup_2={backup_2_exists}, backup_3={backup_3_exists}, backup_4={backup_4_exists}, backup_5={backup_5_exists}")
        
        # 读取当前原始 CSV
        try:
            current_df = pd.read_csv(path, encoding='utf-8-sig')
            current_status = dict(zip(
                current_df['Internal_IP'].astype(str), 
                current_df['alive_or_dead'].astype(str).str.lower().str.strip()
            ))
            
            logging.info(f"🔍 检查档案：{file_name}")
            logging.info(f"   原始 CSV: {path}")
            logging.info(f"   原始笔数: {len(current_df)}")
            
        except Exception as e:
            logging.error(f"❌ 读取原始 CSV 失败 {file_name}：{e}")
            continue
        
        # 读取所有备份的状态
        backup_1_status = {}
        backup_2_status = {}
        backup_3_status = {}
        backup_4_status = {}
        backup_5_status = {}
        
        if backup_1_exists:
            try:
                backup_1_df = pd.read_csv(backup_1_file, encoding='utf-8-sig')
                backup_1_status = dict(zip(
                    backup_1_df['Internal_IP'].astype(str), 
                    backup_1_df['alive_or_dead'].astype(str).str.lower().str.strip()
                ))
                logging.info(f"   已读取 backup_1，笔数: {len(backup_1_df)}")
            except Exception as e:
                logging.error(f"❌ 读取 backup_1 失败：{e}")
        
        if backup_2_exists:
            try:
                backup_2_df = pd.read_csv(backup_2_file, encoding='utf-8-sig')
                backup_2_status = dict(zip(
                    backup_2_df['Internal_IP'].astype(str), 
                    backup_2_df['alive_or_dead'].astype(str).str.lower().str.strip()
                ))
                logging.info(f"   已读取 backup_2，笔数: {len(backup_2_df)}")
            except Exception as e:
                logging.error(f"❌ 读取 backup_2 失败：{e}")
        
        if backup_3_exists:
            try:
                backup_3_df = pd.read_csv(backup_3_file, encoding='utf-8-sig')
                backup_3_status = dict(zip(
                    backup_3_df['Internal_IP'].astype(str), 
                    backup_3_df['alive_or_dead'].astype(str).str.lower().str.strip()
                ))
                logging.info(f"   已读取 backup_3，笔数: {len(backup_3_df)}")
            except Exception as e:
                logging.error(f"❌ 读取 backup_3 失败：{e}")
        
        if backup_4_exists:
            try:
                backup_4_df = pd.read_csv(backup_4_file, encoding='utf-8-sig')
                backup_4_status = dict(zip(
                    backup_4_df['Internal_IP'].astype(str), 
                    backup_4_df['alive_or_dead'].astype(str).str.lower().str.strip()
                ))
                logging.info(f"   已读取 backup_4，笔数: {len(backup_4_df)}")
            except Exception as e:
                logging.error(f"❌ 读取 backup_4 失败：{e}")
        
        if backup_5_exists:
            try:
                backup_5_df = pd.read_csv(backup_5_file, encoding='utf-8-sig')
                backup_5_status = dict(zip(
                    backup_5_df['Internal_IP'].astype(str), 
                    backup_5_df['alive_or_dead'].astype(str).str.lower().str.strip()
                ))
                logging.info(f"   已读取 backup_5，笔数: {len(backup_5_df)}")
            except Exception as e:
                logging.error(f"❌ 读取 backup_5 失败：{e}")
        
        # 对每个 IP 进行检查
        for ip, current in current_status.items():
            # 获取该 IP 在各个 backup 的状态
            backup_1 = backup_1_status.get(ip, "")
            backup_2 = backup_2_status.get(ip, "")
            backup_3 = backup_3_status.get(ip, "")
            backup_4 = backup_4_status.get(ip, "")
            backup_5 = backup_5_status.get(ip, "")
            
            # 获取该 IP 的 Category 和 Machine_ID
            try:
                ip_row = current_df[current_df['Internal_IP'].astype(str) == ip]
                if ip_row.empty:
                    continue
                
                category = str(ip_row['Category'].values[0]).strip().upper()
                machine_id = str(ip_row['Machine_ID'].values[0]).strip()
                
                # 分类筛选逻辑
                if category in ['EAP', 'EQP']:
                    # EAP/EQP：只记录有 Machine_ID 的
                    if machine_id in ['', 'nan', 'None']:
                        continue
                elif category == 'SWITCH':
                    # Switch：不管 Machine_ID，全部记录
                    pass
                else:
                    # 其他类别：跳过
                    continue
                
            except Exception as e:
                logging.error(f"   IP {ip}: 读取 Category/Machine_ID 失败：{e}")
                continue
            
            # 根据 Category 套用不同的检查规则
            if category == 'EAP':
                # EAP 规则：current=dead AND (任一 backup=dead)
                if current == "dead" and (backup_1 == "dead" or backup_2 == "dead" or backup_3 == "dead" or backup_4 == "dead" or backup_5 == "dead"):
                    eap_list.append((current_time, ip, file_name))
                    logging.error(f"🚨 {file_name} - {ip} (EAP): current=dead and (backup_1={backup_1} or backup_2={backup_2} or backup_3={backup_3} or backup_4={backup_4} or backup_5={backup_5})")
            
            elif category == 'EQP':
                # EQP 规则：current=dead AND (任一 backup=dead)
                if current == "dead" and (backup_1 == "dead" or backup_2 == "dead" or backup_3 == "dead" or backup_4 == "dead" or backup_5 == "dead"):
                    eqp_list.append((current_time, ip, file_name))
                    logging.error(f"🚨 {file_name} - {ip} (EQP): current=dead and (backup_1={backup_1} or backup_2={backup_2} or backup_3={backup_3} or backup_4={backup_4} or backup_5={backup_5})")
            
            elif category == 'SWITCH':
                # Switch 规则：current=dead AND (任一 backup=alive)
                if current == "dead" and (backup_1 == "alive" or backup_2 == "alive" or backup_3 == "alive" or backup_4 == "alive" or backup_5 == "alive"):
                    switch_list.append((current_time, ip, file_name))
                    logging.error(f"🚨 {file_name} - {ip} (Switch): current=dead and (backup_1={backup_1} or backup_2={backup_2} or backup_3={backup_3} or backup_4={backup_4} or backup_5={backup_5})")
    
    # 输出到 ../EAP.txt
    if eap_list:
        eap_path = os.path.join(BASE_DIR, "..", "EAP.txt")
        try:
            with open(eap_path, 'a', encoding='utf-8') as f:
                for time_str, ip, source in eap_list:
                    f.write(f"{time_str} | {ip} | {source}\n")
            logging.info(f"✅ 已将 {len(eap_list)} 笔 EAP 设备写入：{eap_path}")
        except Exception as e:
            logging.error(f"❌ 写入 EAP.txt 失败：{e}")
    else:
        logging.info("✅ 无 EAP 连续 dead 设备")
    
    # 输出到 ../EQP.txt
    if eqp_list:
        eqp_path = os.path.join(BASE_DIR, "..", "EQP.txt")
        try:
            with open(eqp_path, 'a', encoding='utf-8') as f:
                for time_str, ip, source in eqp_list:
                    f.write(f"{time_str} | {ip} | {source}\n")
            logging.info(f"✅ 已将 {len(eqp_list)} 笔 EQP 设备写入：{eqp_path}")
        except Exception as e:
            logging.error(f"❌ 写入 EQP.txt 失败：{e}")
    else:
        logging.info("✅ 无 EQP 连续 dead 设备")
    
    # 输出到 ../Switch.txt
    if switch_list:
        switch_path = os.path.join(BASE_DIR, "..", "Switch.txt")
        try:
            with open(switch_path, 'a', encoding='utf-8') as f:
                for time_str, ip, source in switch_list:
                    f.write(f"{time_str} | {ip} | {source}\n")
            logging.info(f"✅ 已将 {len(switch_list)} 笔 Switch 设备写入：{switch_path}")
        except Exception as e:
            logging.error(f"❌ 写入 Switch.txt 失败：{e}")
    else:
        logging.info("✅ 无 Switch 从 alive 变 dead 设备")
    
    
    
    for i, path in enumerate(file_path):
        logging.info(f"--- 檔案 {i+1}/{len(file_path)} ---")
        logging.info(f"路徑: {path}")
        
        if not os.path.exists(path):
            logging.warning(f"⚠️ 檔案不存在: {path}")
            continue
            
        file_name = os.path.basename(path)
        file_name_without_ext = os.path.splitext(file_name)[0]
        
        # 建立備份資料夾路徑
        backup_dir = os.path.join(BASE_DIR, "backups", file_name_without_ext)
        
        # 5 份備份檔案路徑
        backup_files = [os.path.join(backup_dir, f"backup_{i}.csv") for i in range(1, 6)]
        
        logging.info(f"檔案存在: True")
        logging.info(f"備份資料夾: {backup_dir}")
        
        # 檢查備份檔案是否存在
        backup_exists = [os.path.exists(f) for f in backup_files]
        logging.info(f"備份狀態: backup_1={backup_exists[0]}, backup_2={backup_exists[1]}, backup_3={backup_exists[2]}, backup_4={backup_exists[3]}, backup_5={backup_exists[4]}")
        
        # 至少需要 backup_5（最舊的）才能開始檢查
        if not backup_exists[4]:
            logging.info(f"⚠️ 備份檔案不完整（需要 backup_5），跳過：{file_name}")
            continue
            
        try:
            # 讀取當前原始 CSV
            current_df = pd.read_csv(path, encoding='utf-8-sig')
            
            # 讀取 backup_5（最舊的備份）
            backup_5_df = pd.read_csv(backup_files[4], encoding='utf-8-sig')
            
            logging.info(f"🔍 檢查檔案：{file_name}")
            logging.info(f"   backup_5 CSV: {backup_files[4]}")
            logging.info(f"   原始 CSV: {path}")
            logging.info(f"   backup_5 筆數: {len(backup_5_df)}, 原始筆數: {len(current_df)}")
            
            # 讀取所有備份的狀態（用於 Switch 檢查）
            all_backup_status = []
            for j, backup_file in enumerate(backup_files):
                if backup_exists[j]:
                    try:
                        backup_df = pd.read_csv(backup_file, encoding='utf-8-sig')
                        backup_status = dict(zip(
                            backup_df['Internal_IP'].astype(str), 
                            backup_df['alive_or_dead'].astype(str).str.lower().str.strip()
                        ))
                        all_backup_status.append(backup_status)
                    except Exception as e:
                        logging.error(f"❌ 讀取 backup_{j+1} 失敗：{e}")
                        all_backup_status.append({})
                else:
                    all_backup_status.append({})
             
            # backup_5 狀態（最舊的）
            backup_5_status = dict(zip(
                backup_5_df['Internal_IP'].astype(str), 
                backup_5_df['alive_or_dead'].astype(str).str.lower().str.strip()
            ))
                
            # 當前狀態
            current_status = dict(zip(
                current_df['Internal_IP'].astype(str), 
                current_df['alive_or_dead'].astype(str).str.lower().str.strip()
            ))
            
            # Debug: 顯示前幾筆資料
            logging.info(f"   backup_5 前3筆 IP 狀態: {dict(list(backup_5_status.items())[:3])}")
            logging.info(f"   原始前3筆 IP 狀態: {dict(list(current_status.items())[:3])}")
                
            for ip, current in current_status.items():
                backup_5 = backup_5_status.get(ip, "")
                
                # 獲取該 IP 的 Category 和 Machine_ID
                try:
                    ip_row = current_df[current_df['Internal_IP'].astype(str) == ip]
                    if ip_row.empty:
                        logging.debug(f"   IP {ip}: 找不到對應的資料，跳過")
                        continue
                    
                    category = str(ip_row['Category'].values[0]).strip().upper()
                    machine_id = str(ip_row['Machine_ID'].values[0]).strip()
                    
                    # 分類篩選邏輯
                    if category in ['EAP', 'EQP']:
                        # EAP/EQP：只記錄有 Machine_ID 的
                        if machine_id in ['', 'nan', 'None']:
                            logging.debug(f"   IP {ip}: {category} 但 Machine_ID 為空，跳過")
                            continue
                        logging.debug(f"   IP {ip}: {category}, Machine_ID={machine_id}, 符合條件")
                    elif category == 'SWITCH':
                        # Switch：不管 Machine_ID，全部記錄
                        logging.debug(f"   IP {ip}: Switch, 不檢查 Machine_ID")
                    else:
                        # 其他類別：跳過
                        logging.debug(f"   IP {ip}: Category={category}, 不在 EAP/EQP/Switch 範圍，跳過")
                        continue
                    
                except Exception as e:
                    logging.error(f"   IP {ip}: 讀取 Category/Machine_ID 失敗：{e}")
                    continue
                
                # Debug: 顯示每個 IP 的比對
                logging.debug(f"   IP {ip}: backup_5={backup_5}, current={current}, category={category}")
                
                # 根據 Category 套用不同的檢查規則
                should_alarm = False
                target_list = None
                
                if category == 'SWITCH':
                    # Switch 特別規則：檢查任一備份中是否有 alive，且當前是 dead
                    has_alive_in_backups = any(
                        backup.get(ip, "") == "alive" 
                        for backup in all_backup_status
                    )
                    
                    if current == "dead" and has_alive_in_backups:
                        should_alarm = True
                        target_list = switch_list
                        logging.error(f"🚨 {file_name} - {ip} (Switch): 從 alive 變 dead（備份中有 alive 記錄）")
                    elif current == "dead" and not has_alive_in_backups:
                        # Switch 一直都是 dead，不記錄
                        logging.debug(f"   IP {ip} (Switch): 一直都是 dead，不記錄")
                elif category == 'EAP':
                    # EAP 規則：backup_5=dead AND current=dead
                    if backup_5 == "dead" and current == "dead":
                        should_alarm = True
                        target_list = eap_list
                        logging.error(f"🚨 {file_name} - {ip} (EAP): 連續 dead (backup_5={backup_5}, current={current})")
                elif category == 'EQP':
                    # EQP 規則：backup_5=dead AND current=dead
                    if backup_5 == "dead" and current == "dead":
                        should_alarm = True
                        target_list = eqp_list
                        logging.error(f"🚨 {file_name} - {ip} (EQP): 連續 dead (backup_5={backup_5}, current={current})")
                
                # 寫入對應的 list
                if should_alarm and target_list is not None:
                    target_list.append((current_time, ip, file_name))
             
        except Exception as e:
            logging.error(f"❌ 比對失敗 {file_name}：{e}")
            import traceback
            logging.error(traceback.format_exc())
    
    # 輸出到 ../EAP.txt
    if eap_list:
        eap_path = os.path.join(BASE_DIR, "..", "EAP.txt")
        try:
            with open(eap_path, 'a', encoding='utf-8') as f:
                for time_str, ip, source in eap_list:
                    f.write(f"{time_str} | {ip} | {source}\n")
            logging.info(f"✅ 已將 {len(eap_list)} 筆 EAP 設備寫入：{eap_path}")
        except Exception as e:
            logging.error(f"❌ 寫入 EAP.txt 失敗：{e}")
    else:
        logging.info("✅ 無 EAP 連續 dead 設備")
    
    # 輸出到 ../EQP.txt
    if eqp_list:
        eqp_path = os.path.join(BASE_DIR, "..", "EQP.txt")
        try:
            with open(eqp_path, 'a', encoding='utf-8') as f:
                for time_str, ip, source in eqp_list:
                    f.write(f"{time_str} | {ip} | {source}\n")
            logging.info(f"✅ 已將 {len(eqp_list)} 筆 EQP 設備寫入：{eqp_path}")
        except Exception as e:
            logging.error(f"❌ 寫入 EQP.txt 失敗：{e}")
    else:
        logging.info("✅ 無 EQP 連續 dead 設備")
    
    # 輸出到 ../Switch.txt
    if switch_list:
        switch_path = os.path.join(BASE_DIR, "..", "Switch.txt")
        try:
            with open(switch_path, 'a', encoding='utf-8') as f:
                for time_str, ip, source in switch_list:
                    f.write(f"{time_str} | {ip} | {source}\n")
            logging.info(f"✅ 已將 {len(switch_list)} 筆 Switch 設備寫入：{switch_path}")
        except Exception as e:
            logging.error(f"❌ 寫入 Switch.txt 失敗：{e}")
    else:
        logging.info("✅ 無 Switch 從 alive 變 dead 設備")
    





if __name__ == '__main__':
    import time

    # file_path = 'K11\\3F\\K11-3F 區網(27).csv'
    # file_path = [
    #     # 其他
    #     r"\\20220530-w03\Data\EAP_Health_level\source\其他\其他 區網(10).csv", 
    #     # 歲修表
    #     r"\\20220530-w03\Data\EAP_Health_level\source\suixiu.csv", 
    # ]

    file_path = SOURCE_FILES


    # start_time = time.time()

    # for path in file_path:
    #     if not os.path.exists(path):
    #         print(f"❌ 檔案不存在：{path}")
    #         continue

    #     logging.info(f"✅ {path} - 檔案存在，可以讀取！")

    #     backup_csv_before_ping(path)

    #     ping_eap = Ping_EAP(path)
    #     ping_eap.read_ip_addresses_from_csv()
    #     ping_eap.scan_all()

    #     total_pingable, formatted_count, formatted_pingable = ping_eap.display_results()
    #     ping_eap.update_csv_with_alive_status()

    #     with open(path, mode='r', encoding='utf-8-sig') as f:
    #         total_lines = len(f.readlines()) - 1

    #     # logging.info(f"📊 成功 Ping 數: {total_pingable} / {total_lines} ({total_pingable / total_lines * 100:.2f}%)")
    #     # logging.info(f"🎯 符合格式且成功 Ping: {formatted_pingable} / {formatted_count} ({formatted_pingable / formatted_count * 100:.2f}%)")
    #     # 成功 ping 數統計
    #     if total_lines > 0:
    #         success_ratio = total_pingable / total_lines * 100
    #         logging.info(f"📊 成功 Ping 數: {total_pingable} / {total_lines} ({success_ratio:.2f}%)")
    #     else:
    #         logging.info("📊 成功 Ping 數: 無資料行可供計算。")

    #     # 格式符合且成功 ping 統計
    #     if formatted_count > 0:
    #         formatted_ratio = formatted_pingable / formatted_count * 100
    #         logging.info(f"🎯 符合格式且成功 Ping: {formatted_pingable} / {formatted_count} ({formatted_ratio:.2f}%)")
    #     else:
    #         logging.info("🎯 無符合格式的設備（裝置名稱不符合正則條件），略過統計。")

    #     df = pd.read_csv(path, encoding='utf-8-sig')
    #     write_error_task(path)

    # logging.info(f"✅ 任務完成，耗時 {time.time() - start_time:.2f} 秒")

    check_dead_devices()