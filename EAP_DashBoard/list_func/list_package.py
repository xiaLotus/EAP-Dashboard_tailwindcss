import csv
import sys
import time
from flask import Flask, jsonify, request, redirect, url_for, send_file, abort # type: ignore
from flask_cors import CORS # type: ignore
from collections import OrderedDict
import json
import os
import re
import pandas as pd # type: ignore
import tempfile
import zipfile
from list_func.csv_func import read_csv_file_with_pandas


# 測試 IP 是否合格標準
def validate_ip(ip):
    # 定義 IP 格式的正則表達式
    ip_pattern = r'^([0-9]{1,3}\.){3}[0-9]{1,3}$'

    # 檢查 IP 格式是否正確
    if not re.match(ip_pattern, ip):
        return False
    
    # 分割 IP 地址為每個部分
    parts = ip.split('.')
    
    # 檢查每個部分是否在 0 到 255 之間
    for part in parts:
        if not part.isdigit():  # 檢查是否是數字
            return False
        
        num = int(part)
        if num < 0 or num > 255:
            return False
    
    return True


# 獲取資料夾列表
def list_subdirectories(directory_path):
    """遍歷指定資料夾，列出所有子資料夾名稱"""
    subdirectories = []
    if os.path.exists(directory_path) and os.path.isdir(directory_path):
        for item in os.listdir(directory_path):
            full_path = os.path.join(directory_path, item)
            if os.path.isdir(full_path):
                if item == 'backup_suixiu':
                    pass
                else:
                    subdirectories.append(item)
    return subdirectories

# 遍歷指定資料夾，列出所有子資料夾名稱並按數字順序排序
def list_testsubdirectories(folder_path):
    """遍歷指定資料夾，列出所有子資料夾名稱並按數字順序排序"""
    try:
        subdirectories = [
            f for f in os.listdir(folder_path) 
            if os.path.isdir(os.path.join(folder_path, f)) and f != "其他 區網(10)"
        ]
        
        # 使用自定義排序函數來對資料夾進行排序
        subdirectories.sort(key=lambda x: int(re.sub(r'\D', '', x)))  # 排除非數字字符並按數字排序
        
        return subdirectories
    except Exception as e:
        print(f"Error reading directory {folder_path}: {e}")
        return []
    
# 提取括號內數字
def extract_number(s):
    match = re.search(r'\((\d+)\)', s)
    return int(match.group(1)) if match else float('inf')


# 從給定的資料夾路徑獲取檔案名，並去除副檔名
def get_files_from_folder(folder_path):
    """從給定的資料夾路徑獲取檔案名，並去除副檔名"""
    if not os.path.exists(folder_path):
        return {"error": "Folder not found"}, 404

    try:
        files = os.listdir(folder_path)
        files_without_extension = [os.path.splitext(file)[0] for file in files]
        unique_files = list(set(files_without_extension))
        unique_files = sorted(unique_files, key = extract_number)
        return {"files": unique_files} if files else {"files": []}
    except Exception as e:
        return {"error": str(e)}, 500
    




def group_floors_by_prefix(floors):
    grouped = {}

    # First group: K11, K25
    group_1 = {floor: data for floor, data in floors.items() if floor.startswith(('K11', 'K25'))}
    if group_1:
        grouped["F3"] = group_1
    
    # Second group: K18, K21, K22
    group_2 = {floor: data for floor, data in floors.items() if floor.startswith(('K21', 'K22'))}
    if group_2:
        grouped["F1"] = group_2

    # Third group
    group_3 = {floor: data for floor, data in floors.items() if floor.startswith(('K18'))}
    if group_3:
        grouped["F5"] = group_3

    return grouped


def sort_key(floor_name):
    # 提取樓層名稱中的數字部分，例如 "K11-3F" 會提取出 3
    match = re.search(r'(\d+)', floor_name)
    return int(match.group(0)) if match else 0



def get_csv_choose_data(file_path, all, eap, eqp, switch, aliveOrDeadText):
    """讀取CSV檔案並返回處理過的數據"""
    data = []
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        # 有空行跳過
        df = df[df['Internal_IP'] != '0'] 


        # 如果條件為 all，不管其他都包含，包括一開始默認
        if all:
            pass
        
        # # 如果是 EAP 的話
        categories = []

        df['Category'] = df['Category'].str.strip()

        if eap:
            # df = df[df['Category'] == "EAP"]
            categories.append("EAP")
            # print(df)

        if eqp:
            # df = df[df['Category'] == "EQP"]
            categories.append("EQP")
            # print(df)

        if switch:
            # df = df[df['Category'] == "Switch"] 
            categories.append("Switch") 
            # print(df) 

        if categories:
            df = df[df['Category'].isin(categories)]

        if aliveOrDeadText == "A":
            df = df[df['alive_or_dead'] == "alive"]  
            # print(df)

        if aliveOrDeadText == "D":
            df = df[df['alive_or_dead'] == "dead"] 
        
        df = df.fillna('')
        # 處理篩選後的資料
        for _, row in df.iterrows():
            ip = row['Internal_IP']
            data.append({
                "ip": ip,
                "machine_id": row['Machine_ID'],
                "local": row['Local'],
                "device_name": row['Device_Name'],
                "tcp_port": row['TCP_Port'],
                "com_port": row['COM_Port'],
                "os_spec": row['OS_Spec'],
                "ip_source": row['IP_Source'],
                "category": row['Category'],
                "online_test": row['Online_Test'],
                "set_time": row['Set_Time'],
                "remark": row['Remark'],
                "suixiu": row['歲修'],
                "File_Place": row['File_Place'],
                "Column_Position": row['所在區域(柱位)'],
                "status": row['alive_or_dead']
            })

    except Exception as e:
        print(f"Error reading file: {e}")
        return None
    return data