import csv
from datetime import datetime
from shutil import move
import shutil
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
from ldap3 import Server, Connection, ALL, NTLM # type: ignore
from ldap3.core.exceptions import LDAPException, LDAPBindError # type: ignore
from waitress import serve

# 其他包的引用
from list_func.list_package import list_subdirectories, list_testsubdirectories, get_files_from_folder, validate_ip, group_floors_by_prefix,sort_key, get_csv_choose_data
from list_func.csv_func import read_csv_file_with_pandas, update_csv, suixiu_csv_update, update_another_csv


app = Flask(__name__)
CORS(app, supports_credentials = True)
# 放置檔案處
BASE_DIRECTORY = r'static\source'
# BASE_DIRECTORY = r'D:\Data\EAP_Health_level\source'

app.config['UPLOAD_FOLDER'] = BASE_DIRECTORY
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 最大文件大小為 64 MB


# 設置上傳檔案的資料夾
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploaded_files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 允許的檔案擴展名
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def authenticate_user(username, password):
    try:
        # server = Server('ldap://KHADDC02.kh.asegroup.com', get_info = ALL)
        # 使用 NTLM
        user = f'kh\\{username}'
        password = f'{password}'

        # 建立連接
        # conn = Connection(server, user = user, password = password, authentication = NTLM)
        return True
        # 嘗試綁定
        # if conn.bind():
        #     # app.logger.info(f"User {username} login successful.")
        #     return True
        # else:
        #     # app.logger.warning(f"Login failed for user {username}: {conn.last_error}")
        #     return False
    except Exception as e:
        # app.logger.error(f"Error during authentication for user {username}: {e}")
        return False


def rename_and_move_closest_file(file_names):
    # 取得目前時間
    current_time = datetime.now()
    # 變數初始化
    closest_file = None
    closest_time_diff = None
    # 逐一處理每個檔案 
    for file_name in file_names:
        # 確保檔案名稱符合預期格式 (以日期時間開頭)
        if len(file_name) >= 15 and file_name[8] == '_':  # 假設檔案名稱至少有 15 字元並包含時間戳記
            # 提取檔案名稱中的時間戳記部分 (例如 "20250322_181611")
            timestamp_str = file_name[:15]  # 取前 15 字元，包含 "YYYYMMDD_HHMMSS"

            try:
                # 轉換時間戳記為 datetime 物件
                file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                # 計算與現在時間的時間差
                time_diff = abs(current_time - file_time)
                    
                # 如果這是目前找到的最接近的檔案，則更新
                if closest_time_diff is None or time_diff < closest_time_diff:
                    closest_time_diff = time_diff
                    closest_file = file_name
            except ValueError:
                    # 如果時間戳記格式不正確，跳過該檔案
                continue
    return closest_file


# 總表取得
daily_json = r"\\20220530-W03\Data\EAP_Health_level\error_data\Daily_error"
error_lose_machine_EAP = r"\\20220530-W03\Data\EAP_Health_level\error_data\error_lose_machine_EAP.csv"
error_lose_machine_EQP = r"\\20220530-W03\Data\EAP_Health_level\error_data\error_lose_machine_EQP.csv"
error_lose_machine_Switch = r"\\20220530-W03\Data\EAP_Health_level\error_data\error_lose_machine_Switch.csv"

from pandas.errors import EmptyDataError

def _safe_read_csv(path):
    """讀不到或空檔就回 []，並確保每欄為字串、不產生 NaN。"""
    if not path or not os.path.exists(path):
        return []
    try:
        df = pd.read_csv(
            path,
            encoding="utf-8-sig",
            dtype=str,        # 避免型別推斷
            na_filter=False,  # 不產生 NaN（直接保留空字串）
            engine="c",
            memory_map=True
        )
        if df.empty:
            return []
        return df.to_dict(orient="records")
    except (EmptyDataError, FileNotFoundError):
        return []
    except Exception as e:
        print(f"⚠️ 讀取失敗 {path}: {e}")
        return []

@app.route("/api/csv-data-all")
def get_csv_data_all():
    data = {
        "EAP": _safe_read_csv(error_lose_machine_EAP),
        "EQP": _safe_read_csv(error_lose_machine_EQP),
        "Switch": _safe_read_csv(error_lose_machine_Switch),
    }
    return jsonify(data)
    

@app.route('/api/device-summary')
def get_device_summary():
    today = datetime.now()
    formatted_date = today.strftime('%Y%m%d')
    with open(f'{daily_json}\\error_lose_ipcount_{formatted_date}.json', 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    return jsonify(data)

# 首頁登入
@app.route('/api/login', methods=['POST'])
def get_current_user():
    data = request.get_json()
    
    # 從資料中提取用戶名和密碼
    username = data.get('username')
    password = data.get('password')
    print("username: ", username, "password: ", password)
    
    # if authenticate_user(username, password):
    return jsonify({"success": True, "message": "登入成功!"})
    # else:
    #     return jsonify({"success": False, "message": "帳號或密碼錯誤，請重新輸入"})

# 獲取 Unit 資料夾底下的 folders 名稱
@app.route('/get_unit', methods=['GET'])
def get_unit():
    """
        取得各棟別名稱
    """
    subfolders = list_subdirectories(BASE_DIRECTORY)
    return jsonify({"folders": subfolders})

# 獲取指定 Floor 資料夾底下的 folders 名稱
@app.route('/get_floorfolders', methods=['GET'])
def get_floorfolders():
    folder = request.args.get('folder')
    if not folder:
        return jsonify({"error": "Folder name is required"}), 400

    folder_path = os.path.join(BASE_DIRECTORY, folder)
    floorfolders = list_testsubdirectories(folder_path)
    return jsonify({"floorfolders": floorfolders})


# 秀出檔案名稱
@app.route('/<unit>/<floor>/', methods=['GET'])
def get_files(unit, floor):
    # 組合檔案路徑
    folder_path = os.path.join(BASE_DIRECTORY, unit, floor)
    
    # 調試：打印 folder_path
    print(f"Requested folder path: {folder_path}")
    return jsonify(get_files_from_folder(folder_path))


# 取得其他資料夾內部的區網資訊
@app.route('/get_other', methods=['GET'])
def get_other():
    """取得其他資料夾內部的區網資訊"""
    folder_path = os.path.join(BASE_DIRECTORY, '其他')
        # 調試：打印 folder_path
    print(f"Requested folder path: {folder_path}")
    return jsonify(get_files_from_folder(folder_path))


# 普通抓取 csv 資料
@app.route('/<unit>/<floor>/<filename>', methods=['GET'])
def get_csv_alive(unit, floor, filename):
    """普通抓取 csv 資料"""
    file_path = rf"{BASE_DIRECTORY}\{unit}\{floor}\{filename}.csv"
    data = read_csv_file_with_pandas(file_path)
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "File not found or could not be read"}), 400


# 針對 其他 區網(10).csv 特別撰寫
@app.route('/show_another_data', methods=['GET'])
def show_another_data():
    """針對 其他 區網(10).csv 特別撰寫"""
    file_path = rf"{BASE_DIRECTORY}\其他\其他 區網(10).csv"
    data = read_csv_file_with_pandas(file_path)
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "File not found or could not be read"}), 400


# 取得歲修那張表的全部資料
@app.route('/show_suixiu_card', methods=['GET'])
def show_suixiu_card():
    try:
        file_path = f"{BASE_DIRECTORY}/suixiu.csv"
        data = read_csv_file_with_pandas(file_path)
        if data:
            return jsonify(data)
        else:
            return jsonify({"error": "Folder name is required"}), 400
    except Exception as e:
        print(f"Error : {e}")
        return jsonify({"error": "Folder name is required"}), 502

# 針對非其他區網的資訊
@app.post("/update_single_place_status/<string:UnitName>/<string:FloorName>/<string:Filename>/<string:ip>")
def update_single_place_status(UnitName: str, FloorName: str, Filename, ip: str):

    print("更新普通資訊")
    print(f"更新前檢查備份資料夾: {BASE_DIRECTORY}\\{UnitName}\\{FloorName}\\{Filename}")
    os.makedirs(f"{BASE_DIRECTORY}\\{UnitName}\\{FloorName}\\{Filename}", exist_ok=True)

    source_filepath = f"{BASE_DIRECTORY}\\{UnitName}\\{FloorName}\\{Filename}.csv"
    backup_filepath = f"{BASE_DIRECTORY}\\{UnitName}\\{FloorName}\\{Filename}\\{Filename}.csv"

    try:
        shutil.copy2(source_filepath, backup_filepath)
        print(f"備份成功：{backup_filepath}")
    except Exception as e:
        print(f"備份失敗：{e}")
        return jsonify({"message": "備份失敗，請檢查檔案路徑或權限"}), 500
    
    # 取得目前的日期時間，並格式化為 yyyymmdd_hhmmss
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 組合新的檔案名稱
    new_file_name = f"{timestamp}_{os.path.basename(Filename)}.csv"
    new_file_path_with_timestamp = os.path.join(f"{BASE_DIRECTORY}\\{UnitName}\\{FloorName}\\{Filename}", new_file_name)
    os.rename(f"{BASE_DIRECTORY}\\{UnitName}\\{FloorName}\\{Filename}\\{Filename}.csv", new_file_path_with_timestamp)

    # ⛔ 防止 request.json 為 None
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400

    """針對非其他區網的資訊"""
    ip = data.get('ip') 
    machine_id = data.get('machine_id') 
    local = data.get('local') 
    Column_Position = data.get('Column_Position')
    device_name = data.get('device_name') 
    tcp_port = data.get('tcp_port') 
    com_port = data.get('com_port') 
    os_spec = data.get('os_spec') 
    ip_source = data.get('ip_source') 
    category = data.get('category') 
    online_test = data.get('online_test') 
    set_time = data.get('set_time') 
    remark = data.get('remark') 
    suixiu = data.get('suixiu') 
    file_place = data.get('file_place')
    status = data.get('status') 

    # 填漏 卡控
    if (len(ip) == 0) or (ip == "0.0.0.0"):
        return jsonify({"message": "請詳細檢查資訊有無寫錯"}), 405

    filepath = rf"{BASE_DIRECTORY}\{UnitName}\{FloorName}\{Filename}.csv"
    print(f"{filepath} 已更新資訊")
    # df = pd.read_csv(filepath, encoding='utf-8-sig')
    # 呼叫共用函數更新 CSV
    update_error = update_csv(filepath, ip, machine_id, local, device_name, tcp_port, com_port, os_spec, 
                              ip_source, category, online_test, set_time, remark, suixiu, file_place, Column_Position, status)

    if update_error:
        return update_error
    
    suixiu_file_path = rf'{BASE_DIRECTORY}\suixiu.csv'
    suixiu_csv_update_error = suixiu_csv_update(suixiu_file_path, ip, machine_id, local, device_name, tcp_port, com_port, os_spec, 
                              ip_source, category, online_test, set_time, remark, suixiu, file_place, Column_Position, status, BASE_DIRECTORY)

    if suixiu_csv_update_error:
        return suixiu_csv_update_error

    return jsonify({"message": "Status updated successfully"}), 200


# 針對其他區網的資料
@app.post("/update_suixiu")
def update_suixiu():

    print("更新其他區網資訊")
    print(f"更新前檢查備份資料夾: {BASE_DIRECTORY}\\backup_suixiu")
    os.makedirs(f"{BASE_DIRECTORY}\\backup_suixiu", exist_ok=True)

    source_filepath = f"{BASE_DIRECTORY}\\suixiu.csv"
    backup_filepath = f"{BASE_DIRECTORY}\\backup_suixiu\\suixiu.csv"

    try:
        shutil.copy2(source_filepath, backup_filepath)
        print(f"備份成功：{backup_filepath}")
    except Exception as e:
        print(f"備份失敗：{e}")
        return jsonify({"message": "備份失敗，請檢查檔案路徑或權限"}), 500
    
    # 取得目前的日期時間，並格式化為 yyyymmdd_hhmmss
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 組合新的檔案名稱
    new_file_name = f"{timestamp}_suixiu.csv"
    new_file_path_with_timestamp = os.path.join(f"{BASE_DIRECTORY}\\backup_suixiu", new_file_name)
    os.rename(f"{BASE_DIRECTORY}\\backup_suixiu\\suixiu.csv", new_file_path_with_timestamp)

    if not request.is_json:
        return jsonify({"error": "Invalid content-type, must be application/json"}), 400
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON payload"}), 400

    """針對其他區網的資料"""
    ip = data.get('ip') 
    machine_id = data.get('machine_id') 
    local = data.get('local') 
    Column_Position = data.get('Column_Position')
    device_name = data.get('device_name') 
    tcp_port = data.get('tcp_port') 
    com_port = data.get('com_port') 
    os_spec = data.get('os_spec') 
    ip_source = data.get('ip_source') 
    category = data.get('category') 
    online_test = data.get('online_test') 
    set_time = data.get('set_time') 
    remark = data.get('remark') 
    suixiu = data.get('suixiu') 
    file_place = data.get('file_place')
    status = data.get('status') 

    filepath = rf"{BASE_DIRECTORY}\其他\其他 區網(10).csv"

    if (device_name == "") or (not device_name):
        return jsonify({"message": "歲修更新表出包了"}), 404

    ip_currect = validate_ip(ip)

    if ip_currect:
        suixiu_file_path = rf'{BASE_DIRECTORY}\suixiu.csv'
        suixiu_csv_update_error = suixiu_csv_update(suixiu_file_path, ip, machine_id, local, device_name, tcp_port, com_port, os_spec, 
                                ip_source, category, online_test, set_time, remark, suixiu, file_place, Column_Position, status, BASE_DIRECTORY)
        
        if suixiu_csv_update_error:
            return suixiu_csv_update_error
    

    # 在歲修這張表使用的時候要注意是否更新其他網段。
    print('更新')
    filepath = rf"{BASE_DIRECTORY}\其他\其他 區網(10).csv"
    update_error = update_another_csv(filepath, ip, machine_id, local, device_name, tcp_port, com_port, os_spec, 
                                ip_source, category, online_test, set_time, remark, suixiu, file_place, Column_Position, status)

    if update_error:
        return update_error

    else:
        return jsonify({"message": "Status updated successfully"}), 200


# 針對其他區網的資料
@app.post("/update_other/<string:unitname>/<string:filename>/<string:device_name>")
def update_other(unitname: str, filename: str, device_name: str):

    print("更新其他區網資訊")
    print(f"更新前檢查備份資料夾: {BASE_DIRECTORY}\\{unitname}\\{filename}")
    os.makedirs(f"{BASE_DIRECTORY}\\{unitname}\\{filename}", exist_ok=True)

    source_filepath = f"{BASE_DIRECTORY}\\{unitname}\\{filename}.csv"
    backup_filepath = f"{BASE_DIRECTORY}\\{unitname}\\{filename}\\{filename}.csv"

    try:
        shutil.copy2(source_filepath, backup_filepath)
        print(f"備份成功：{backup_filepath}")
    except Exception as e:
        print(f"備份失敗：{e}")
        return jsonify({"message": "備份失敗，請檢查檔案路徑或權限"}), 500
    
    # 取得目前的日期時間，並格式化為 yyyymmdd_hhmmss
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 組合新的檔案名稱
    new_file_name = f"{timestamp}_{os.path.basename(filename)}.csv"
    new_file_path_with_timestamp = os.path.join(f"{BASE_DIRECTORY}\\{unitname}\\{filename}", new_file_name)
    os.rename(f"{BASE_DIRECTORY}\\{unitname}\\{filename}\\{filename}.csv", new_file_path_with_timestamp)

    # ⛔ 防止 request.json 為 None
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415
    
    data = request.get_json()
    if data is None:
        return jsonify({"error": "Invalid JSON body"}), 400
    
    """針對其他區網的資料"""
    ip = data.get('ip')  # type: ignore
    machine_id = data.get('machine_id') 
    local = data.get('local') 
    Column_Position = data.get('Column_Position')
    device_name = data.get('device_name') 
    tcp_port = data.get('tcp_port') 
    com_port = data.get('com_port') 
    os_spec = data.get('os_spec') 
    ip_source = data.get('ip_source') 
    category = data.get('category') 
    online_test = data.get('online_test') 
    set_time = data.get('set_time') 
    remark = data.get('remark') 
    suixiu = data.get('suixiu') 
    file_place = data.get('file_place')
    status = data.get('status') 

    filepath = rf"{BASE_DIRECTORY}\{unitname}\{filename}.csv"
    print(filepath)
    update_error = update_csv(filepath, ip, machine_id, local, device_name, tcp_port, com_port, os_spec, 
                              ip_source, category, online_test, set_time, remark, suixiu, file_place, Column_Position, status)

    if update_error:
        return update_error
    

    suixiu_file_path = rf'{BASE_DIRECTORY}\suixiu.csv'
    suixiu_csv_update_error = suixiu_csv_update(suixiu_file_path, ip, machine_id, local, device_name, tcp_port, com_port, os_spec, 
                              ip_source, category, online_test, set_time, remark, suixiu, file_place, Column_Position, status, BASE_DIRECTORY)

    if suixiu_csv_update_error:
        return suixiu_csv_update_error

    
    return jsonify({"message": "Status updated successfully"}), 200



# 取得歲修的圓餅資料
@app.route('/get_suixiu_circle_data', methods=['GET'])
def get_suixiu_circle_data():
    with open(rf'{BASE_DIRECTORY}\grouped_output.json', 'r', encoding='utf-8-sig') as status_file:
            total_data = json.load(status_file)
    
    # print("total: ", total_data)
    
    return jsonify({"total_data": total_data})

# 取得歲修各樓層
@app.route('/get_suixiu_EachFloor', methods=['GET'])
def get_suixiu_EachFloor():
    try:
        with open(rf'{BASE_DIRECTORY}\\total.json', 'r', encoding='utf-8-sig') as status_file:
            eachfloor = json.load(status_file)

        sorted_eachfloor = OrderedDict(sorted(eachfloor.items(), key=lambda x: sort_key(x[0])))
        # print(sorted_eachfloor)
        grouped_floors = group_floors_by_prefix(sorted_eachfloor)
        # print(grouped_floors)
        return jsonify({"eachfloor": grouped_floors})

    except Exception as e:
        # 若有錯誤，返回錯誤訊息
        return jsonify({"error": str(e)}), 500



# 各樓層取得狀態
@app.route('/get_progress_data/<string:data>', methods=['GET'])
def get_progress_data(data: str):
    with open(f'{BASE_DIRECTORY}/status.json', 'r', encoding='utf-8-sig') as file:
        status_data = json.load(file)

    
    if data in status_data:
        return jsonify({data: status_data[data]})
    else:
        return jsonify({"error": "Not found"}), 400

# 取得歲修整體狀態
@app.route('/get_suixiu_status', methods=['GET'])
def get_suixiu_status():
    data = 'suixiu'
    with open(f'{BASE_DIRECTORY}/status.json', 'r', encoding='utf-8-sig') as file:
        status_data = json.load(file)

    if data in status_data:
        return jsonify({data: status_data[data]})
    else:
        return jsonify({"error": "Not found"}), 400


# 取的其他那張表的 data
@app.route('/get_other_status_data', methods=['GET'])
def get_other_status_data():
    data = '其他 區網(10)'
    with open(f'{BASE_DIRECTORY}/status.json', 'r', encoding='utf-8-sig') as file:
        status_data = json.load(file)

    if data in status_data:
        return jsonify({data: status_data[data]})
    else:
        return jsonify({"error": "Not found"}), 400    


# 選擇大部分表的按鈕
@app.route('/select_Button_data/<string:UnitName>/<string:FloorName>/<string:Filename>', methods=['POST'])
def select_Button_data(UnitName: str, FloorName: str, Filename: str):
    """專門篩選普通資料的部分"""
    # 從請求中獲取 JSON 資料
    data = request.get_json()
    button_stats = data.get('buttonStats', {})
    aliveOrDeadText = data.get('aliveOrDeadText')

    # 分別解包
    all = button_stats['all']
    eap = button_stats['eap']
    eqp = button_stats['eqp']
    switch = button_stats['switch']

    # print(all, eap, eqp, switch, aliveOrDeadText)
    file_path = rf"{BASE_DIRECTORY}\{UnitName}\{FloorName}\{Filename}.csv"

    data = get_csv_choose_data(file_path, all, eap, eqp, switch, aliveOrDeadText)
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "File not found or could not be read"}), 400



# 選擇其他那張表的按鈕
@app.route('/select_Another_button/<string:unitname>/<string:filename>', methods=['POST'])
def select_Another_button(unitname: str, filename: str):
    """專門篩選其他資料的部分"""
    # 從請求中獲取 JSON 資料
    data = request.get_json()
    button_stats = data.get('buttonStats', {})
    aliveOrDeadText = data.get('aliveOrDeadText')

    # 分別解包
    all = button_stats['all']
    eap = button_stats['eap']
    eqp = button_stats['eqp']
    switch = button_stats['switch']

    # 假設我們根據接收到的資料來更新按鈕狀態
    file_path = rf"{BASE_DIRECTORY}\{unitname}\{filename}.csv"

    data = get_csv_choose_data(file_path, all, eap, eqp, switch, aliveOrDeadText)
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "File not found or could not be read"}), 400


# 選擇歲修那張表的按鈕
@app.route('/select_suixiu_button', methods=['POST'])
def select_suixiu_button():
    """專門篩選其他資料的部分"""
    # 從請求中獲取 JSON 資料
    data = request.get_json()
    button_stats = data.get('buttonStats', {})
    aliveOrDeadText = data.get('aliveOrDeadText')

    # 分別解包
    all = button_stats['all']
    eap = button_stats['eap']
    eqp = button_stats['eqp']
    switch = button_stats['switch']

    # 假設我們根據接收到的資料來更新按鈕狀態
    file_path = rf"{BASE_DIRECTORY}\suixiu.csv"

    data = get_csv_choose_data(file_path, all, eap, eqp, switch, aliveOrDeadText)
    if data is not None:
        return jsonify(data)
    return jsonify({"error": "File not found or could not be read"}), 400



@app.route('/get_csv_files', methods=['GET'])
def get_csv_files():
    folder_path = BASE_DIRECTORY
    if not os.path.exists(folder_path):
        return jsonify({"error": "Folder not found"}), 404
    
    csv_files = []
    for root, dirs, files in os.walk(folder_path):
        # 解析資料夾路徑，判斷當前層級
        path_parts = os.path.relpath(root, BASE_DIRECTORY).split(os.sep)
        current_level = len(path_parts)  # 當前資料夾的層級（相對於 BASE_DIRECTORY）

        # 檢查是否要忽略該資料夾（例如，忽略某些特定名稱的資料夾）
        if "backup_suixiu" in dirs:  # 假設 "ignore_this_folder" 是你要忽略的資料夾名稱
            dirs.remove("backup_suixiu")
        if "其他 區網(10)" in dirs:  # 假設 "ignore_this_folder" 是你要忽略的資料夾名稱
            dirs.remove("其他 區網(10)")

        # 當第二層資料夾有 .csv 檔案時，停止搜尋子資料夾
        if current_level == 2 and any(file.endswith('.csv') for file in files):
            dirs[:] = []  # 停止搜尋第二層的子資料夾

        # 檢查是否有 .csv 檔案
        for file in files:
            if file.endswith('.csv'):
                # 解析檔案路徑
                building = path_parts[0]  # 棟別
                floor = path_parts[1] if len(path_parts) > 1 else ''  # 樓層

                file_name_without_extension = file.replace('.csv', '')

                # 將檔案資訊儲存
                csv_files.append({
                    'file_name': file_name_without_extension,
                    'building': building,
                    'floor': floor,
                    'file_path': os.path.join(root, file)
                })
    
    return jsonify({"csv_files": csv_files})




# 下載資料 【20250407】
@app.route('/download/<file_path>', methods=['GET', 'OPTIONS'])
def download_file(file_path: str):
    # print(f"收到下載請求：{file_path}")
    try:
        if file_path == "其他 區網(10)":
            file_path = os.path.join(f'{BASE_DIRECTORY}', '其他', f"{file_path}.csv")
            return send_file(    
                    file_path,
                    as_attachment=True,
                    download_name=os.path.basename(file_path),
                    mimetype="text/csv"
                )
        if file_path == '歲修':
            file_path = os.path.join(f'{BASE_DIRECTORY}', f"suixiu.csv")
            # 複製一份
            xlsx_path = os.path.join(f'{BASE_DIRECTORY}', '歲修_(Secutity C).xlsx')  # 可以改路徑

            try:
                from io import BytesIO
                df = pd.read_csv(file_path, encoding='utf-8-sig')
                # df.to_excel(xlsx_path, index=False)
                # print(f"✅ 已將 {file_path} 轉成 {xlsx_path}")
                
                output = BytesIO()
                df.to_excel(output, index=False, engine="openpyxl")
                output.seek(0)  # 把指標移回開頭

                return send_file(
                    output,
                    as_attachment=True,
                    download_name="歲修_(Security C).xlsx",  # 注意有副檔名
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as e:
                print(f"❌ 歲修 CSV 轉換失敗：{e}")
                return jsonify({"error": "轉換失敗"}), 500
        else:
            build_floor = file_path.split(' ')
            # 區網(42)，在最後加上去
            end_file = build_floor[1]
            total_file = build_floor[0]

            total_file = total_file.split('-')
            build = total_file[0]
            floor = total_file[1]

            file_path = os.path.join(f'{BASE_DIRECTORY}', f"{build}", f"{floor}", f"{file_path}.csv")
            return send_file(    
                    file_path,
                    as_attachment=True,
                    download_name=os.path.basename(file_path),
                    mimetype="text/csv"
                )



    except Exception as e:
        print(f"❌ 發生錯誤：{e}")
        return jsonify({"error": "下載錯誤"}), 500


    
@app.route('/downloadAllFiles', methods = ['GET'])
def downloadAllFiles():
    """
    建立IP表備份統整_(Security C).zip，結束之後會上拋刪除
    """
    temp_zip_path = os.path.join(tempfile.gettempdir(), "IP表備份統整_(Security C).zip")
    
    # 建立一個 zip
    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # 遍历文件夹中的所有文件，查找 CSV 文件并添加到 ZIP 包中
        for root, dirs, files in os.walk(BASE_DIRECTORY):
            for file in files:
                if file.endswith('.csv'):  # 仅压缩 CSV 文件
                    file_path = os.path.join(root, file)
                    # 临时存储过滤后的 CSV 数据
                    temp_file_path = os.path.join(tempfile.gettempdir(), file)
                        
                    with open(file_path, mode='r', newline='', encoding='utf-8-sig') as infile:
                        reader = csv.reader(infile)
                        rows = []
                        header = next(reader)  # 读取表头（假设有表头）
                        rows.append(header)  # 保留表头
                        # 读取每一行并检查 Internal_IP 是否为 '0'
                        for row in reader:
                            # 如果该行的所有值都是 '0'，则跳过该行
                            if row[0].strip() == '0':
                                continue  # 跳过该行
                            rows.append(row)
                        
                    # 写入过滤后的数据到新的临时 CSV 文件
                    with open(temp_file_path, mode='w', newline='', encoding='utf-8-sig') as outfile:
                        writer = csv.writer(outfile)
                        writer.writerows(rows)

                        
                    # 使用相对路径以便文件在 zip 中保持目录结构
                    arcname = os.path.relpath(file_path, BASE_DIRECTORY)
                    if "suixiu" in arcname:
                        arcname = arcname.replace("suixiu", "歲修")
                    zipf.write(temp_file_path, arcname=arcname)
                    os.remove(temp_file_path)
    
    # 检查 ZIP 文件是否成功创建
    if not os.path.exists(temp_zip_path):
        abort(404, description="ZIP file could not be created.")
    
    # 使用 send_file 返回压缩包，触发下载
    return send_file(temp_zip_path, as_attachment=True, download_name="IP表備份統整_(Security C).zip")




def update_for_simple(target_file, file_name_without_extension):
    try:
        os.makedirs(f"{file_name_without_extension}", exist_ok=True)
        # 這邊把舊檔案移進這個資料夾

        file_name = os.path.basename(target_file)

        print(f"target_folder: {target_file}, file_name_without_extension: {file_name_without_extension}")
        # 讀取原檔案並寫入新檔案
        with open(target_file, 'r', encoding='utf-8-sig') as src_file:
            content = src_file.read()

        # 在新資料夾內創建新的 CSV 檔案並寫入內容
        new_file_path = os.path.join(file_name_without_extension, f'{file_name}')
        with open(new_file_path, 'w', encoding='utf-8-sig') as dest_file:
            dest_file.write(content)
        # 取得目前的日期時間，並格式化為 yyyymmdd_hhmmss
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # 組合新的檔案名稱
        new_file_name = f"{timestamp}_{os.path.basename(file_name)}"
        new_file_path_with_timestamp = os.path.join(file_name_without_extension, new_file_name)
        os.rename(new_file_path, new_file_path_with_timestamp)

    except Exception as e:
        print(e)

def update_for_suixiu():
    # 檢查是否資料夾存在
    os.makedirs(f"{BASE_DIRECTORY}\\backup_suixiu", exist_ok=True)
    # 先複製一份到備份資料夾
    with open(f"{BASE_DIRECTORY}\\suixiu.csv", 'r', encoding='utf-8-sig') as src_file:
        content = src_file.read()
        new_file_path = os.path.join(f"{BASE_DIRECTORY}\\backup_suixiu", f"suixiu.csv")

    with open(new_file_path, 'w', encoding='utf-8-sig') as dest_file:
        dest_file.write(content)
    # 取得目前的日期時間，並格式化為 yyyymmdd_hhmmss

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 組合新的檔案名稱
    new_file_name = f"{timestamp}_suixiu.csv"


    new_file_path_with_timestamp = os.path.join(f"{BASE_DIRECTORY}\\backup_suixiu", new_file_name)
    
    os.rename(new_file_path, new_file_path_with_timestamp)
    print(f"{new_file_path} 改名成 {new_file_path_with_timestamp}")

    # 移動 uploaded_files\\suixiu.csv 到 BASE_DIRECTORY
    if os.path.exists(f"uploaded_files\\suixiu.csv"):
        try:
            shutil.move(f"uploaded_files\\suixiu.csv", f"{BASE_DIRECTORY}\\suixiu.csv")
            print(f"uploaded_files\\suixiu.csv 已移動到 {BASE_DIRECTORY}\\suixiu.csv")
        except Exception as e:
            print(f"移動 uploaded_files\\suixiu.csv 時發生錯誤: {e}")
    else:
        print(f"uploaded_files\\suixiu.csv 不存在")


@app.route('/upload', methods=['POST']) # type: ignore
def upload_files():

    if 'files' not in request.files:
        return jsonify({"error": "沒有檔案部分"}), 400

    files = request.files.getlist('files')
    if len(files) == 0:
        return jsonify({"error": "未選擇任何檔案"}), 400
    
    saved_files = []


    for file in files:
        if file and allowed_file(file.filename):
            # filename = file.filename
            # file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename)) # type: ignore
            # file_ext = filename.rsplit('.', 1)[1].lower() # type: ignore
            # saved_files.append(filename)
            
            filename = file.filename
            file_ext = filename.rsplit('.', 1)[1].lower() # type: ignore
            print("當前上傳副檔名為 : ", file_ext)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename) # type: ignore
            file.save(save_path)

            # ✅ 如果是 xlsx，轉成 csv（覆蓋變數）
            if file_ext == 'xlsx':
                try:
                    original_path = save_path  # 明確指定原始 xlsx 路徑
                    df = pd.read_excel(original_path)

                    csv_name = filename.rsplit('.', 1)[0] + ".csv"  # type: ignore
                    csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_name)
                    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
                    print(f"✅ 已將 {filename} 轉為 utf-8-sig CSV：{csv_name}")

                    # ✅ 刪除 .xlsx 原始檔案
                    os.remove(original_path)
                    print(f"🗑️  已刪除原始檔案：{original_path}")

                    # ✅ 更新後續處理變數
                    filename = csv_name
                    print("當前 filename 為: ", filename)
                    save_path = csv_path
                    print("當前 save_path 為: ", save_path)
                    file_ext = 'csv'

                except Exception as e:
                    print(f"❌ Excel 轉 CSV 失敗：{e}")


            saved_files.append(filename)


            # 除了歲修之外的處理方式
            try:
                if file.filename not in ["歲修_(Security C).csv", "歲修_(Security C).xlsx", 'suixiu.csv']:
                    print("======================================")
                    folder_name = filename.split(' ')[0]  # type: ignore
                    try:
                        folder_parts = folder_name.split('-')
                        folder_path = os.path.join('static', 'source', folder_parts[0], folder_parts[1])  # 組成資料夾路徑
                        print("確認投放的資料夾路徑【已排除特例】: ", folder_path)
                    except:
                        name, _ = os.path.splitext(filename) # type: ignore
                        if name:
                            name = name.replace("_(Security C)", "")
                        folder_path = os.path.join('static', 'source', f'{folder_name}', f"{name}")  # 組成資料夾路徑
                        print("確認投放的資料夾路徑【已排除特例】: ", folder_path)

                    os.makedirs(folder_path, exist_ok=True)
                    print("已確定備份資料夾【已排除特例】: ", folder_path)

                    file_ext = filename.rsplit('.', 1)[1].lower() # type: ignore
                    
                    try:
                        update_file_name = os.path.join(f"{UPLOAD_FOLDER}", filename.replace("_(Security C)", "")) # type: ignore
                        os.rename(f"{UPLOAD_FOLDER}\\{filename}", update_file_name)
                        print('已將上傳的檔案改名： ', update_file_name)
                    except:
                        print("檔名不須更改")

                    df = pd.read_csv(update_file_name) if file_ext == 'csv' else pd.read_excel(update_file_name)
                    # 認真處理 CSV 編碼錯誤問題

                    # 檢查是否有 File_Place 欄位
                    if 'File_Place' in df.columns:
                        # 取得 File_Place 欄位的第一個值
                        file_place_value = df['File_Place'].iloc[0]
                        # print(f"File_Place 第一個路徑: {file_place_value}")
                        check_old_path = rf"{BASE_DIRECTORY}\{file_place_value}"
                        file_name_without_extension, _ = os.path.splitext(check_old_path)
                        # print(file_name_without_extension)
                        target_folder = os.path.join(BASE_DIRECTORY, file_place_value)

                        # 這邊是把舊資料放入備份檔內
                        update_for_simple(target_folder, file_name_without_extension)

                        # 先移除放在 source 的原始資料
                        try:
                            os.remove(target_folder)
                        except Exception as e:
                            print(f"刪除檔案時發生錯誤: {e}")

                        try:
                            # 取得檔案所在的資料夾路徑
                            folder_path = os.path.dirname(target_folder)
                            print(f'開始從 {UPLOAD_FOLDER} 裡面複製一份資料進入 File_Place -> 轉移為 {target_folder}')
                            shutil.move(f"{update_file_name}", f"{target_folder}")
                            print(f"已改名過的檔案【含路徑】{update_file_name} 已搬遷至【含路徑】 {target_folder}")
                            print("======================================")

                        except Exception as e:
                            print(f"刪除檔案時發生錯誤: {e}")

                else:
                    print("======================================")
                    print("此處執行特例")
                    update_file_name = os.path.join(f"{UPLOAD_FOLDER}", filename) # type: ignore
                    os.rename(f"{update_file_name}", f'uploaded_files\\suixiu.csv')
                    try:
                        update_for_suixiu()
                        print("uploaded_files\\suixiu.csv 已轉移結束")
                        print("======================================")

                    except Exception as e:
                        print(e)
                    
            except Exception as e:
                print(f"處理檔案 {filename} 時發生錯誤: {e}")
            
            return jsonify({"message": "檔案成功上傳", "files": saved_files}), 200

        else:
            return jsonify({"error": "檔案不存在"}), 404





@app.route('/delete-file', methods=['POST'])
def delete_file():
    data = request.get_json()
    filename = data.get('filename')

    if not filename:
        return jsonify({"error": "未提供檔名"}), 400
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    print("======================================")
    file_name = os.path.basename(file_path)
    # 一開始一樣設置為 None
    closest_file = None

    if file_name not in ["歲修_(Security C).csv", "歲修_(Security C).xlsx", 'suixiu.csv', 'suixiu_(Security C).csv', '其他 區網(10).csv', '其他 區網(10)_(Security C).csv']:
        pattern = r"([A-Za-z0-9]+)-([A-Za-z0-9]+)"
        match = re.match(pattern, file_name)
        if match:
            unit, floor = match.group(1), match.group(2)
            print("unit: ", unit, "floor", floor)
            try:
                file_name = file_name.replace("_(Security C)", "")
            except Exception as e:
                print(e)
            os.remove(rf"{BASE_DIRECTORY}\{unit}\{floor}\{file_name}")
            print(rf"已刪除 {BASE_DIRECTORY}\{unit}\{floor}\{file_name}")
            # 去除附檔名
            name_without_extension, _ = os.path.splitext(file_name)
            print(f"name_without_extension【去除檔名】: {name_without_extension}")
            file_names = [f for f in os.listdir(os.path.join(f"{BASE_DIRECTORY}", f"{unit}", f'{floor}', f'{name_without_extension}'))]
            closest_file = rename_and_move_closest_file(file_names)
        # 顯示結果
        if closest_file:
            print(f"距離現在時間最近的檔案是: {closest_file}")
            folder_path = f"{BASE_DIRECTORY}\\{unit}\\{floor}\\{name_without_extension}"
            parent_folder = os.path.dirname(folder_path)
            print("輸出上一層的資料夾路徑: ", parent_folder)
            # 目標路徑：將檔案移動到上一層資料夾
            target_path = os.path.join(parent_folder, closest_file)
            # 移動檔案
            try:
                shutil.move(f"{folder_path}\\{closest_file}", target_path)
                print(f"檔案會已移動到備份資料夾: {target_path}")
                closest_file_name = closest_file[16:]
                # 處理更換後的路徑
                closest_file_name_path = os.path.join(f"{BASE_DIRECTORY}\\{unit}\\{floor}\\{closest_file}")
                print("轉移後的路徑檔案： ", closest_file_name_path)

                os.rename(closest_file_name_path, f"{BASE_DIRECTORY}\\{unit}\\{floor}\\{closest_file_name}")
                print(f"已經移動到 {BASE_DIRECTORY}\\{unit}\\{floor}\\{closest_file_name}")
                print("======================================")
            except Exception as e:
                print(f"移動檔案時發生錯誤: {e}")
        else:
            print("未找到檔案")

    if file_name in ["歲修_(Security C).csv", "歲修_(Security C).xlsx", 'suixiu.csv', 'suixiu_(Security C).csv']:
        file_names = [f for f in os.listdir(os.path.join(f"{BASE_DIRECTORY}", "backup_suixiu"))]
        closest_file = rename_and_move_closest_file(file_names)
        if closest_file:
            print(f"距離現在時間最近的檔案是: {closest_file}")
            os.rename(f"{BASE_DIRECTORY}\\backup_suixiu\\{closest_file}", f"{BASE_DIRECTORY}\\backup_suixiu\\suixiu.csv")
            shutil.move(f"{BASE_DIRECTORY}\\backup_suixiu\\suixiu.csv", f"{BASE_DIRECTORY}\\suixiu.csv")
            print(f"舊檔案已移動到: {BASE_DIRECTORY}\\suixiu.csv")
            print("======================================")
        else:
            print("檔案出錯，請檢察歲修檔案是否輸入正確！")

    if file_name in ['其他 區網(10).csv', '其他 區網(10)_(Security C).csv']:
        file_names = [f for f in os.listdir(os.path.join(f"{BASE_DIRECTORY}", "其他", '其他 區網(10)'))]
        closest_file = rename_and_move_closest_file(file_names)
        if closest_file:
            print(f"距離現在時間最近的檔案是: {closest_file}")
            os.rename(f"{BASE_DIRECTORY}\\其他\\其他 區網(10)\\{closest_file}", f"{BASE_DIRECTORY}\\其他\\其他 區網(10)\\其他 區網(10).csv")
            shutil.move(f"{BASE_DIRECTORY}\\其他\\其他 區網(10)\\其他 區網(10).csv", f"{BASE_DIRECTORY}\\其他\\其他 區網(10).csv")
            print(f"舊檔案已移動到: {BASE_DIRECTORY}\\其他\\其他 區網(10).csv")
            print("======================================")

    if file_name:
        return jsonify({"success": True}), 200

    else:
        return jsonify({"error": "檔案不存在"}), 404


@app.route('/backup_simple/<string:filename>', methods=['GET'])
def backup_simple(filename: str):
    try:
        title_parts = filename.split(' ')  
        title = title_parts[0].split('-')  
        unit = title[0]
        floor = title[1]
        path = f"{BASE_DIRECTORY}\\{unit}\\{floor}\\{filename}"
        file_names = [f for f in os.listdir(path)]
        try:
            if len(file_names) >= 1:
                closest_file = rename_and_move_closest_file(file_names)
                if closest_file:
                    print(closest_file)
                    try:
                        parent_directory = os.path.dirname(path)  
                        os.rename(f"{path}\\{closest_file}", f"{path}\\{filename}.csv")
                        shutil.move(f"{path}\\{filename}.csv", f"{parent_directory}\\{filename}.csv")
                        print(f"檔案已回溯: {filename}")
                    except Exception as e:
                        return jsonify({"message": "出現突發狀態"}), 404
                return jsonify({"message": "Status updated successfully"}), 200
            else:
                print("內部沒有檔案，無法拉取")
                return jsonify({"message": "出現突發狀態"}), 404

        except Exception as e:
            return jsonify({"message": "出現突發狀態"}), 404
        
        
    except Exception as e:
        return jsonify({"message": "出現突發狀態"}), 404
    

@app.route('/backup_another', methods=['GET'])
def backup_another():
    path = f"{BASE_DIRECTORY}\\其他\\其他 區網(10)"
    file_names = [f for f in os.listdir(path)]
    try:
        if len(file_names) >= 1:
            closest_file = rename_and_move_closest_file(file_names)
            if closest_file:
                print(closest_file)
                try:
                    parent_directory = os.path.dirname(path)  
                    os.rename(f"{path}\\{closest_file}", f"{path}\\其他 區網(10).csv")
                    shutil.move(f"{path}\\其他 區網(10).csv", f"{parent_directory}\\其他 區網(10).csv")
                    print(f"檔案已回溯: 其他 區網(10).csv")
                except Exception as e:
                    return jsonify({"message": "出現突發狀態"}), 404
            return jsonify({"message": "Status updated successfully"}), 200
        else:
            print("內部沒有檔案，無法拉取")
            return jsonify({"message": "出現突發狀態"}), 404

    except Exception as e:
        return jsonify({"message": "出現突發狀態"}), 404


@app.route('/backup_suixiu', methods=['GET'])
def backup_suixiu():
    path = f"{BASE_DIRECTORY}\\backup_suixiu"
    file_names = [f for f in os.listdir(path)]
    try:
        if len(file_names) >= 1:
            closest_file = rename_and_move_closest_file(file_names)
            if closest_file:
                print(closest_file)
                try:
                    parent_directory = os.path.dirname(path)  
                    os.rename(f"{path}\\{closest_file}", f"{path}\\suixiu.csv")
                    shutil.move(f"{path}\\suixiu.csv", f"{parent_directory}\\suixiu.csv")
                    print(f"檔案已回溯: suixiu.csv")
                except Exception as e:
                    return jsonify({"message": "出現突發狀態"}), 404
            return jsonify({"message": "Status updated successfully"}), 200
        else:
            print("內部沒有檔案，無法拉取")
            return jsonify({"message": "出現突發狀態"}), 404

    except Exception as e:
        return jsonify({"message": "出現突發狀態"}), 404


# =============================================== json 歲修過帳
# pass_dwon_ER = r"\\20220530-W03\Data\EAP_Health_level\source"
pass_dwon_ER = r"static\source"

def load_json_data():
    """從 JSON 檔案載入資料"""
    try:
        # 載入 ASEF1.json (使用 utf-8-sig 處理 BOM)
        asef1_data = {}
        if os.path.exists(f'{pass_dwon_ER}\\ASEF1.json'):
            with open(f'{pass_dwon_ER}\\ASEF1.json', 'r', encoding='utf-8-sig') as f:
                asef1_data = json.load(f)
        
        # 載入 ASEF3.json (使用 utf-8-sig 處理 BOM)
        asef3_data = {}
        if os.path.exists(f'{pass_dwon_ER}\\ASEF3.json'):
            with open(f'{pass_dwon_ER}\\ASEF3.json', 'r', encoding='utf-8-sig') as f:
                asef3_data = json.load(f)

        # 載入 ASEF5.json (如果存在的話)
        asef5_data = {}
        if os.path.exists(f'{pass_dwon_ER}\\ASEF5.json'):
            with open(f'{pass_dwon_ER}\\ASEF5.json', 'r', encoding='utf-8-sig') as f:
                asef5_data = json.load(f)
        else:
            # 如果 ASEF5.json 不存在，給空值
            asef5_data = {}
            
        return asef1_data, asef3_data, asef5_data
    except FileNotFoundError as e:
        print(f"JSON 檔案未找到: {e}")
        return {}, {}, {}
    except json.JSONDecodeError as e:
        print(f"JSON 格式錯誤: {e}")
        return {}, {}, {}
    except Exception as e:
        print(f"載入資料時發生錯誤: {e}")
        return {}, {}, {}

def save_json_data(filename, data):
    """儲存資料到 JSON 檔案"""
    try:
        with open(f'{pass_dwon_ER}\\{filename}.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"儲存 {pass_dwon_ER}\\{filename}.json 失敗: {e}")
        return False


@app.route('/api/data')
def get_data():
    """API 端點：返回原始 JSON 資料"""
    try:
        asef1_data, asef3_data, asef5_data = load_json_data()
        
        return jsonify({
            "asef1": asef1_data,
            "asef3": asef3_data,
            "asef5": asef5_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# GET - 取得特定檔案資料
@app.route('/api/<filename>')
def get_file_data(filename):
    """取得特定檔案的資料"""
    try:
        asef1_data, asef3_data, asef5_data = load_json_data()
        
        if filename.upper() == 'ASEF1':
            return jsonify(asef1_data)
        elif filename.upper() == 'ASEF3':
            return jsonify(asef3_data)
        elif filename.upper() == 'ASEF5':
            return jsonify(asef5_data)
        else:
            return jsonify({"error": "檔案不存在"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# POST - 新增分類
@app.route('/api/<filename>', methods=['POST'])
def add_category(filename):
    """新增分類到指定檔案"""
    try:
        data = request.get_json()
        category_id = data.get('category_id')
        
        if not category_id:
            return jsonify({"error": "缺少 category_id"}), 400
        
        asef1_data, asef3_data, asef5_data = load_json_data()
        
        if filename.upper() == 'ASEF1':
            if category_id in asef1_data:
                return jsonify({"error": "分類已存在"}), 400
            asef1_data[category_id] = {}
            success = save_json_data('ASEF1', asef1_data)
        elif filename.upper() == 'ASEF3':
            if category_id in asef3_data:
                return jsonify({"error": "分類已存在"}), 400
            asef3_data[category_id] = {}
            success = save_json_data('ASEF3', asef3_data)
        elif filename.upper() == 'ASEF5':
            if category_id in asef5_data:
                return jsonify({"error": "分類已存在"}), 400
            asef5_data[category_id] = {}
            success = save_json_data('ASEF5', asef5_data)
        else:
            return jsonify({"error": "檔案不存在"}), 404
        
        if success:
            return jsonify({"message": f"成功新增分類 {category_id}"})
        else:
            return jsonify({"error": "儲存失敗"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# DELETE - 刪除分類
@app.route('/api/<filename>/<category_id>', methods=['DELETE'])
def delete_category(filename, category_id):
    """刪除指定分類"""
    try:
        asef1_data, asef3_data, asef5_data = load_json_data()
        
        if filename.upper() == 'ASEF1':
            if category_id not in asef1_data:
                return jsonify({"error": "分類不存在"}), 404
            del asef1_data[category_id]
            success = save_json_data('ASEF1', asef1_data)
        elif filename.upper() == 'ASEF3':
            if category_id not in asef3_data:
                return jsonify({"error": "分類不存在"}), 404
            del asef3_data[category_id]
            success = save_json_data('ASEF3', asef3_data)
        elif filename.upper() == 'ASEF5':
            if category_id not in asef5_data:
                return jsonify({"error": "分類不存在"}), 404
            del asef5_data[category_id]
            success = save_json_data('ASEF5', asef5_data)
        else:
            return jsonify({"error": "檔案不存在"}), 404
        
        if success:
            return jsonify({"message": f"成功刪除分類 {category_id}"})
        else:
            return jsonify({"error": "儲存失敗"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# POST - 新增項目
@app.route('/api/<filename>/<category_id>', methods=['POST'])
def add_item(filename, category_id):
    """新增項目到指定分類"""
    try:
        data = request.get_json()
        item_code = data.get('item_code')
        item_value = data.get('item_value', '')
        
        if not item_code:
            return jsonify({"error": "缺少 item_code"}), 400
        
        asef1_data, asef3_data, asef5_data = load_json_data()
        
        if filename.upper() == 'ASEF1':
            if category_id not in asef1_data:
                return jsonify({"error": "分類不存在"}), 404
            if item_code in asef1_data[category_id]:
                return jsonify({"error": "項目已存在"}), 400
            asef1_data[category_id][item_code] = item_value
            success = save_json_data('ASEF1', asef1_data)
        elif filename.upper() == 'ASEF3':
            if category_id not in asef3_data:
                return jsonify({"error": "分類不存在"}), 404
            if item_code in asef3_data[category_id]:
                return jsonify({"error": "項目已存在"}), 400
            asef3_data[category_id][item_code] = item_value
            success = save_json_data('ASEF3', asef3_data)
        elif filename.upper() == 'ASEF5':
            if category_id not in asef5_data:
                return jsonify({"error": "分類不存在"}), 404
            if item_code in asef5_data[category_id]:
                return jsonify({"error": "項目已存在"}), 400
            asef5_data[category_id][item_code] = item_value
            success = save_json_data('ASEF5', asef5_data)
        else:
            return jsonify({"error": "檔案不存在"}), 404
        
        if success:
            return jsonify({"message": f"成功新增項目 {item_code}"})
        else:
            return jsonify({"error": "儲存失敗"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# PUT - 修改項目值
@app.route('/api/<filename>/<category_id>/<item_code>', methods=['PUT'])
def update_item(filename, category_id, item_code):
    """修改項目值"""
    try:
        data = request.get_json()
        new_value = data.get('item_value', '')
        
        asef1_data, asef3_data, asef5_data = load_json_data()
        
        if filename.upper() == 'ASEF1':
            if category_id not in asef1_data:
                return jsonify({"error": "分類不存在"}), 404
            if item_code not in asef1_data[category_id]:
                return jsonify({"error": "項目不存在"}), 404
            asef1_data[category_id][item_code] = new_value
            success = save_json_data('ASEF1', asef1_data)
        elif filename.upper() == 'ASEF3':
            if category_id not in asef3_data:
                return jsonify({"error": "分類不存在"}), 404
            if item_code not in asef3_data[category_id]:
                return jsonify({"error": "項目不存在"}), 404
            asef3_data[category_id][item_code] = new_value
            success = save_json_data('ASEF3', asef3_data)
        elif filename.upper() == 'ASEF5':
            if category_id not in asef5_data:
                return jsonify({"error": "分類不存在"}), 404
            if item_code not in asef5_data[category_id]:
                return jsonify({"error": "項目不存在"}), 404
            asef5_data[category_id][item_code] = new_value
            success = save_json_data('ASEF5', asef5_data)
        else:
            return jsonify({"error": "檔案不存在"}), 404
        
        if success:
            return jsonify({"message": f"成功修改項目 {item_code}"})
        else:
            return jsonify({"error": "儲存失敗"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# DELETE - 刪除項目
@app.route('/api/<filename>/<category_id>/<item_code>', methods=['DELETE'])
def delete_item(filename, category_id, item_code):
    """刪除項目"""
    try:
        asef1_data, asef3_data, asef5_data = load_json_data()
        
        if filename.upper() == 'ASEF1':
            if category_id not in asef1_data:
                return jsonify({"error": "分類不存在"}), 404
            if item_code not in asef1_data[category_id]:
                return jsonify({"error": "項目不存在"}), 404
            del asef1_data[category_id][item_code]
            success = save_json_data('ASEF1', asef1_data)
        elif filename.upper() == 'ASEF3':
            if category_id not in asef3_data:
                return jsonify({"error": "分類不存在"}), 404
            if item_code not in asef3_data[category_id]:
                return jsonify({"error": "項目不存在"}), 404
            del asef3_data[category_id][item_code]
            success = save_json_data('ASEF3', asef3_data)
        elif filename.upper() == 'ASEF5':
            if category_id not in asef5_data:
                return jsonify({"error": "分類不存在"}), 404
            if item_code not in asef5_data[category_id]:
                return jsonify({"error": "項目不存在"}), 404
            del asef5_data[category_id][item_code]
            success = save_json_data('ASEF5', asef5_data)
        else:
            return jsonify({"error": "檔案不存在"}), 404
        
        if success:
            return jsonify({"message": f"成功刪除項目 {item_code}"})
        else:
            return jsonify({"error": "儲存失敗"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500














if __name__ == '__main__':
    app.run()
    # serve(app, host='0.0.0.0', port=8081)