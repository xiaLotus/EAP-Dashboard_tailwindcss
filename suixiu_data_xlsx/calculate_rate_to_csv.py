#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
妥善率計算與CSV記錄腳本
從 K11.json 和 K22.json 計算總妥善率並記錄到CSV文件
"""

import json
import csv
import os
from datetime import datetime

# ===== 配置 =====
K11_JSON_PATH = "K11.json"
K22_JSON_PATH = "K22.json"
CSV_OUTPUT_PATH = "hourly_rate.csv"


def calculate_overall_rate(json_data):
    """
    計算整體妥善率
    
    Args:
        json_data: K11.json 或 K22.json 的數據
        
    Returns:
        float: 妥善率（0-100）
    """
    total_actual = 0
    total_abnormal = 0
    
    # 遍歷所有樓層
    for floor_name, floor_data in json_data.items():
        actual = floor_data.get('實際數量', [])
        abnormal = floor_data.get('異常數量', [])
        
        # 處理多站點數據（二維陣列）
        if actual and isinstance(actual[0], list):
            for group_idx, group in enumerate(actual):
                for item_idx, value in enumerate(group):
                    total_actual += int(value) if value else 0
                    total_abnormal += int(abnormal[group_idx][item_idx]) if abnormal[group_idx][item_idx] else 0
        # 處理單站點數據（一維陣列）
        else:
            for item_idx, value in enumerate(actual):
                total_actual += int(value) if value else 0
                total_abnormal += int(abnormal[item_idx]) if abnormal[item_idx] else 0
    
    if total_actual == 0:
        return 0.0
    
    rate = (1 - total_abnormal / total_actual) * 100
    return round(rate, 2)


def load_json(filepath):
    """載入JSON文件"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ 找不到文件: {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"❌ JSON格式錯誤: {filepath}")
        return None


def init_csv_file(filepath):
    """初始化CSV文件（如果不存在則創建表頭）"""
    if not os.path.exists(filepath):
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['時間戳記', 'K11妥善率(%)', 'K22妥善率(%)', '記錄時間'])
        print(f"✅ 已創建CSV文件: {filepath}")


def append_to_csv(filepath, timestamp, k11_rate, k22_rate):
    """追加數據到CSV文件"""
    try:
        with open(filepath, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            recorded_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([timestamp, k11_rate, k22_rate, recorded_time])
        print(f"✅ 已追加數據到CSV")
        return True
    except Exception as e:
        print(f"❌ 寫入CSV失敗: {e}")
        return False


def read_csv(filepath, limit=None):
    """
    讀取CSV文件
    
    Args:
        filepath: CSV文件路徑
        limit: 限制讀取的行數（None表示全部）
        
    Returns:
        list: 數據列表，每行為dict格式
    """
    try:
        data = []
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append({
                    'timestamp': row['時間戳記'],
                    'k11_rate': float(row['K11妥善率(%)']),
                    'k22_rate': float(row['K22妥善率(%)']),
                    'recorded_time': row['記錄時間']
                })
                
                if limit and len(data) >= limit:
                    break
        
        return data
    except FileNotFoundError:
        print(f"❌ CSV文件不存在: {filepath}")
        return []
    except Exception as e:
        print(f"❌ 讀取CSV失敗: {e}")
        return []


def get_latest_records(filepath, count=15):
    """
    獲取最新的N筆記錄
    
    Args:
        filepath: CSV文件路徑
        count: 要獲取的記錄數量
        
    Returns:
        list: 最新的N筆記錄
    """
    try:
        data = []
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            data = list(reader)
        
        # 返回最後count筆記錄
        return data[-count:] if len(data) > count else data
    except Exception as e:
        print(f"❌ 讀取CSV失敗: {e}")
        return []


def main():
    """主函數"""
    print("=" * 60)
    print("📊 妥善率計算與CSV記錄")
    print(f"⏰ 執行時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 載入JSON數據
    print("\n📁 載入JSON數據...")
    k11_data = load_json(K11_JSON_PATH)
    k22_data = load_json(K22_JSON_PATH)
    
    if not k11_data or not k22_data:
        print("❌ 無法載入數據文件，程序終止")
        return
    
    # 2. 計算妥善率
    print("\n🧮 計算妥善率...")
    k11_rate = calculate_overall_rate(k11_data)
    k22_rate = calculate_overall_rate(k22_data)
    
    print(f"   K11 總妥善率: {k11_rate}%")
    print(f"   K22 總妥善率: {k22_rate}%")
    
    # 3. 初始化CSV文件（如果需要）
    init_csv_file(CSV_OUTPUT_PATH)
    
    # 4. 寫入CSV
    print("\n💾 寫入CSV文件...")
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    success = append_to_csv(CSV_OUTPUT_PATH, timestamp, k11_rate, k22_rate)
    
    if success:
        # 5. 顯示最新的5筆記錄
        print("\n📋 最新5筆記錄:")
        recent = get_latest_records(CSV_OUTPUT_PATH, 5)
        
        print(f"{'時間':<20} {'K11(%)':<10} {'K22(%)':<10}")
        print("-" * 40)
        for record in recent:
            print(f"{record['時間戳記']:<20} {record['K11妥善率(%)']:<10} {record['K22妥善率(%)']:<10}")
    
    print("\n" + "=" * 60)
    print("✅ 任務完成")
    print("=" * 60)


# ===== 示例用法 =====
def example_usage():
    """示例：如何使用這個腳本"""
    
    print("\n" + "=" * 60)
    print("📚 示例用法")
    print("=" * 60)
    
    # 示例1：讀取最新15筆記錄
    print("\n1️⃣ 讀取最新15筆記錄:")
    recent_15 = get_latest_records(CSV_OUTPUT_PATH, 15)
    print(f"   獲取到 {len(recent_15)} 筆記錄")
    
    # 示例2：讀取所有記錄
    print("\n2️⃣ 讀取所有記錄:")
    all_data = read_csv(CSV_OUTPUT_PATH)
    print(f"   總共 {len(all_data)} 筆記錄")
    
    # 示例3：提取數據供圖表使用
    print("\n3️⃣ 提取數據供圖表使用:")
    if recent_15:
        timestamps = [record['時間戳記'] for record in recent_15]
        k11_rates = [float(record['K11妥善率(%)']) for record in recent_15]
        k22_rates = [float(record['K22妥善率(%)']) for record in recent_15]
        
        print(f"   時間戳記: {timestamps[:3]}...")
        print(f"   K11妥善率: {k11_rates[:3]}...")
        print(f"   K22妥善率: {k22_rates[:3]}...")


if __name__ == "__main__":
    # 執行主程序
    main()
    
    # 顯示示例用法（可選）
    # example_usage()