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

# 讀取CSV檔案並返回處理過的數據    
def read_csv_file_with_pandas(file_path):
    """使用 pandas 讀取 CSV 檔案並返回處理過的數據"""
    try:
        # 讀取 CSV 檔案
        df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)

        # 過濾掉 Internal_IP 為 '0' 的行
        df = df[df['Internal_IP'] != '0']

        df = df.fillna('')

        # 選擇需要的列，並將每一行轉換為字典
        data = df[['Internal_IP', 'Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port', 
                   'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time', 'Remark', 
                   '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']].to_dict(orient='records')

        # 將欄位名稱轉換為需要的格式
        for row in data:
            row['ip'] = row.pop('Internal_IP')
            row['machine_id'] = row.pop('Machine_ID')
            row['local'] = row.pop('Local')
            row['device_name'] = row.pop('Device_Name')
            row['tcp_port'] = row.pop('TCP_Port')
            row['com_port'] = row.pop('COM_Port')
            row['os_spec'] = row.pop('OS_Spec')
            row['ip_source'] = row.pop('IP_Source')
            row['category'] = row.pop('Category')
            row['online_test'] = row.pop('Online_Test')
            row['set_time'] = row.pop('Set_Time')
            row['remark'] = row.pop('Remark')
            row['suixiu'] = row.pop('歲修')
            row['File_Place'] = row.pop('File_Place')
            row['Column_Position'] = row.pop('所在區域(柱位)')
            row['status'] = row.pop('alive_or_dead')

        return data

    except Exception as e:
        print(f"Error reading file: {e}")
        return None


# 針對更新 csv 原始表，比如 【K18-9F 區網(41)】 or【其他 區網(10)】
def update_csv(filepath: str, ip: str, machine_id: str, local: str, device_name: str, tcp_port: str, com_port: str, 
                os_spec: str, ip_source: str, category: str, online_test: str, set_time: str, remark: str, 
                suixiu: str, file_place: str, Column_Position: str, status: str):
    """針對更新 csv 原始表，比如 【K18-9F 區網(41)】 or【其他 區網(10)】"""
    df = pd.read_csv(filepath, encoding='utf-8-sig', dtype=str)
    df = df.apply(lambda x: x.fillna(''), axis=0)
    # 確保 'Internal_IP' 列是字符串型，並將空值轉換為 NaN
    df['Internal_IP'] = df['Internal_IP'].astype(str)
    df['Machine_ID'] = df['Machine_ID'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['Local'] = df['Local'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['Device_Name'] = df['Device_Name'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['TCP_Port'] = df['TCP_Port'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['COM_Port'] = df['COM_Port'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['OS_Spec'] = df['OS_Spec'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['IP_Source'] = df['IP_Source'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['Category'] = df['Category'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['Online_Test'] = df['Online_Test'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['Set_Time'] = df['Set_Time'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['Remark'] = df['Remark'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['歲修'] = df['歲修'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['File_Place'] = df['File_Place'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['所在區域(柱位)'] = df['所在區域(柱位)'].apply(lambda x: str(x) if pd.notna(x) else '')
    df['alive_or_dead'] = df['alive_or_dead'].apply(lambda x: str(x) if pd.notna(x) else '')
    # 如果 IP 是 0.0.0.0，使用 Machine_ID 和 Device_Name 作為更新條件
    if ip == "0.0.0.0":
        df.loc[(df['Machine_ID'] == machine_id) & (df['Device_Name'] == device_name), 
               ['Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port',
                'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time',
                'Remark', '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']] = \
            [str(machine_id), str(local), str(device_name), str(tcp_port), str(com_port), str(os_spec), 
             str(ip_source), str(category), str(online_test), str(set_time), str(remark), str(suixiu), 
             str(file_place), str(Column_Position), str(status)]    
    # 更新 IP 相對應的行`
    else:
        df.loc[df['Internal_IP'] == ip, ['Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port',
                                            'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time',
                                            'Remark', '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']] = \
                [str(machine_id), str(local), str(device_name), str(tcp_port), str(com_port), str(os_spec), 
                str(ip_source), str(category), str(online_test), str(set_time), str(remark), str(suixiu), 
                str(file_place), str(Column_Position), str(status)]

    # 檢查是否成功更新
    if df[df['Internal_IP'] == ip].empty:
        return jsonify({"error": "IP not found"}), 404

    # 將更新後的數據寫回 CSV 文件
    df.to_csv(filepath, index=False, encoding='utf-8-sig')

    return None

# 針對更新 其他表
def update_another_csv(filepath: str, ip: str, machine_id: str, local: str, device_name: str, tcp_port: str, com_port: str, 
                os_spec: str, ip_source: str, category: str, online_test: str, set_time: str, remark: str, 
                suixiu: str, file_place: str, Column_Position: str, status: str):
    df = pd.read_csv(filepath, encoding='utf-8-sig', dtype=str)
    df = df.fillna('')

    # 判斷是否存在相同 Device_Name
    mask = df['Device_Name'] == device_name

    if mask.any():
        # 更新已存在的資料
        df.loc[mask, 'Internal_IP'] = ip
        df.loc[mask, 'Machine_ID'] = machine_id
        df.loc[mask, 'Local'] = local
        df.loc[mask, 'TCP_Port'] = tcp_port
        df.loc[mask, 'COM_Port'] = com_port
        df.loc[mask, 'OS_Spec'] = os_spec
        df.loc[mask, 'IP_Source'] = ip_source
        df.loc[mask, 'Category'] = category
        df.loc[mask, 'Online_Test'] = online_test
        df.loc[mask, 'Set_Time'] = set_time
        df.loc[mask, 'Remark'] = remark
        df.loc[mask, '歲修'] = suixiu
        df.loc[mask, 'File_Place'] = file_place
        df.loc[mask, '所在區域(柱位)'] = Column_Position
        df.loc[mask, 'alive_or_dead'] = status
    else:
        # 新增一筆資料
        new_row = {
            'Internal_IP': str(ip),
            'Machine_ID': str(machine_id),
            'Local': str(local),
            'Device_Name': str(device_name),
            'TCP_Port': str(tcp_port),
            'COM_Port': str(com_port),
            'OS_Spec': str(os_spec),
            'IP_Source': str(ip_source),
            'Category': str(category),
            'Online_Test': str(online_test),
            'Set_Time': str(set_time),
            'Remark': str(remark),
            '歲修': str(suixiu),
            'File_Place': str(file_place),
            '所在區域(柱位)': str(Column_Position),
            'alive_or_dead': status
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    df.to_csv(filepath, index=False, encoding='utf-8-sig')
    return jsonify({'其他: 10': 200})



# 針對更新歲修原始表 suixiu.csv
def suixiu_csv_update(suixiu_file_path: str, ip: str, machine_id: str, local: str, device_name: str, tcp_port: str, com_port: str, 
                os_spec: str, ip_source: str, category: str, online_test: str, set_time: str, remark: str, 
                suixiu: str, file_place: str, Column_Position: str, status: str, BASE_DIRECTORY):
    """針對更新歲修原始表 suixiu.csv"""
    if suixiu == 'Y':
        suixiu_df = pd.read_csv(suixiu_file_path, encoding='utf-8-sig', dtype=str)
        suixiu_df = suixiu_df.apply(lambda x: x.fillna(''), axis=0)
        # 確保 'Internal_IP' 列是字符串型
        suixiu_df['Internal_IP'] = suixiu_df['Internal_IP'].astype(str)

        # 更新 歲修 表
        if ip == "0.0.0.0":
            suixiu_df.loc[(suixiu_df['Machine_ID'] == machine_id) & (suixiu_df['Device_Name'] == device_name), 
                ['Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port',
                    'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time',
                    'Remark', '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']] = \
                [str(machine_id), str(local), str(device_name), str(tcp_port), str(com_port), str(os_spec), 
                str(ip_source), str(category), str(online_test), str(set_time), str(remark), str(suixiu), 
                str(file_place), str(Column_Position), str(status)]    
        # 更新 IP 相對應的行`
        else:
            suixiu_df.loc[suixiu_df['Internal_IP'] == ip, ['Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port',
                                                'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time',
                                                'Remark', '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']] = \
                    [str(machine_id), str(local), str(device_name), str(tcp_port), str(com_port), str(os_spec), 
                    str(ip_source), str(category), str(online_test), str(set_time), str(remark), str(suixiu), 
                    str(file_place), str(Column_Position), str(status)]

        # 檢查是否存在需要新增的行
        if ip == "0.0.0.0":
            # 檢查是否需要新增行
            if suixiu_df[(suixiu_df['Machine_ID'] == machine_id) & (suixiu_df['Device_Name'] == device_name)].empty:
                new_row = {
                            'Internal_IP': str(ip),
                            'Machine_ID': str(machine_id),
                            'Local': str(local),
                            'Device_Name': str(device_name),
                            'TCP_Port': str(tcp_port),
                            'COM_Port': str(com_port),
                            'OS_Spec': str(os_spec),
                            'IP_Source': str(ip_source),
                            'Category': str(category),
                            'Online_Test': str(online_test),
                            'Set_Time': str(set_time),
                            'Remark': str(remark),
                            '歲修': str(suixiu),
                            'File_Place': str(file_place),
                            '所在區域(柱位)': str(Column_Position),
                            'alive_or_dead': 'dead'
                        }
                suixiu_df = pd.concat([suixiu_df, pd.DataFrame([new_row], columns=suixiu_df.columns)], ignore_index=True)
        else:
            # 檢查 IP 相對應的行是否存在
            if suixiu_df[suixiu_df['Internal_IP'] == ip].empty:
                new_row = {
                            'Internal_IP': str(ip),
                            'Machine_ID': str(machine_id),
                            'Local': str(local),
                            'Device_Name': str(device_name),
                            'TCP_Port': str(tcp_port),
                            'COM_Port': str(com_port),
                            'OS_Spec': str(os_spec),
                            'IP_Source': str(ip_source),
                            'Category': str(category),
                            'Online_Test': str(online_test),
                            'Set_Time': str(set_time),
                            'Remark': str(remark),
                            '歲修': str(suixiu),
                            'File_Place': str(file_place),
                            '所在區域(柱位)': str(Column_Position),
                            'alive_or_dead': 'dead' 
                        }
                suixiu_df = pd.concat([suixiu_df, pd.DataFrame([new_row], columns=suixiu_df.columns)], ignore_index=True)


        suixiu_df.to_csv(suixiu_file_path, index=False, encoding='utf-8-sig')

    elif suixiu in ["N", ""] :
        suixiu_file_path = f'{BASE_DIRECTORY}\suixiu.csv'
        suixiu_df = pd.read_csv(suixiu_file_path, encoding='utf-8-sig')
        suixiu_df = suixiu_df.apply(lambda x: x.fillna(''), axis=0)
        # 確保 'Internal_IP' 列是字符串型
        suixiu_df['Internal_IP'] = suixiu_df['Internal_IP'].astype(str)
        if ip == "0.0.0.0":
            suixiu_df = suixiu_df[~((suixiu_df['Machine_ID'] == machine_id) & (suixiu_df['Device_Name'] == device_name))]
            suixiu_df['alive_or_dead'] = 'dead'
        else:
            suixiu_df = suixiu_df[suixiu_df['Internal_IP'] != ip]
        suixiu_df.to_csv(suixiu_file_path, index=False, encoding='utf-8-sig')
    
    return None