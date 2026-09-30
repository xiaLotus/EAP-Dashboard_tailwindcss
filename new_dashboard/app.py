import json
import os
import re
import sys
from datetime import datetime

import pandas as pd
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from filelock import FileLock
from loguru import logger
from ldap3 import Server, Connection, ALL, NTLM  # type: ignore
from ldap3.core.exceptions import LDAPException, LDAPBindError  # type: ignore
import csv
from datetime import datetime
from shutil import move
import shutil
import sys
import time
from flask import Flask, jsonify, request, redirect, url_for, send_file, abort # type: ignore
from flask_cors import CORS # type: ignore
from collections import OrderedDict, defaultdict
import json
import os
import re
import pandas as pd # type: ignore
import tempfile
import zipfile
from ldap3 import Server, Connection, ALL, NTLM # type: ignore
from ldap3.core.exceptions import LDAPException, LDAPBindError # type: ignore
from waitress import serve


# =========================================================
# ⭐ 路徑設定（全部改為 CSV）
# =========================================================
CSV_FOLDER = r"csv"                     # 各網段 CSV 存放資料夾（原 db/）
LOG_CSV = "log.csv"                     # 修改紀錄（原 log.db）
log_path = "log.log"
status_path = "status.json"
STATE_DIR = os.path.join(os.getcwd(), "user_states")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # html 所在目錄

# 設置上傳檔案的資料夾
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploaded_files')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 允許的檔案擴展名
ALLOWED_EXTENSIONS = {'csv', 'xlsx'}

error_lose_csv = "D:\Data\EAP_Health_level\error_data\error_lose_machine.csv"
daily_json = "D:\Data\EAP_Health_level\error_data\Daily_error"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


os.makedirs(CSV_FOLDER, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)

CSV_ENCODING = "utf-8-sig"

# ⭐ 網段 CSV 欄位（順序固定）
DEVICE_COLUMNS = [
    "Internal_IP", "Machine_ID", "Local", "Device_Name",
    "TCP_Port", "COM_Port", "OS_Spec", "IP_Source",
    "Category", "Online_Test", "Set_Time", "Remark",
    "歲修", "File_Place", "所在區域(柱位)", "alive_or_dead", "是否派報"
]

# ⭐ 修改紀錄 CSV 欄位
AUDIT_COLUMNS = [
    "id", "time", "username", "site", "floor", "label",
    "ip", "field", "old_value", "new_value"
]

# ⭐ 全域搜尋用欄位
SEARCH_COLUMNS = [
    "Internal_IP", "Machine_ID", "Device_Name", "Local",
    "Category", "Remark", "alive_or_dead", 
]

# =========================================================
# ⭐ logger
# =========================================================
logger.remove()
logger.add(sys.stdout, level="INFO",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
logger.add(log_path, level="INFO", encoding="utf-8-sig", enqueue=True)

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "static"), static_url_path="/static")
CORS(app)


# =========================================================
# ⭐ 認證
# =========================================================
def authenticate_user(username, password):
    try:
        server = Server('ldap://KHADDC02.kh.asegroup.com', get_info=ALL)
        user = f'kh\\{username}'
        password = f'{password}'
        # conn = Connection(server, user=user, password=password, authentication=NTLM)
        logger.info(f"User {username} 成功降落！！！")
        return True
        # if conn.bind():
        #     return True
        # else:
        #     return False
    except Exception:
        return False


# =========================================================
# ⭐ 頁面路由（login / index / log）
# =========================================================
@app.route('/')
@app.route('/login')
@app.route('/login.html')
def page_login():
    return send_from_directory(BASE_DIR, 'login.html')


@app.route('/index')
@app.route('/index.html')
def page_index():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/log')
@app.route('/log.html')
def page_log():
    return send_from_directory(BASE_DIR, 'log.html')


# =========================================================
# ⭐ 登入 API
# =========================================================
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({"success": False, "message": "請輸入帳號密碼"}), 400

    if authenticate_user(username, password):
        return jsonify({"success": True, "username": username})

    logger.warning(f"{username} 登入失敗")
    return jsonify({"success": False, "message": "帳號或密碼錯誤"}), 401


# =========================================================
# ⭐ CSV 共用工具
# =========================================================
NA_TOKENS = {"nan", "NaN", "NAN", "None", "null", "NULL", "<NA>"}


def read_csv(path):
    """讀 CSV，所有欄位以字串處理，缺值 / nan 一律轉空字串"""
    df = pd.read_csv(path, dtype=str, encoding=CSV_ENCODING, keep_default_na=False)
    df = df.fillna("")
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]   # 去 BOM / 空白
    return df.replace(list(NA_TOKENS), "")


def write_csv(df, path):
    df.to_csv(path, index=False, encoding=CSV_ENCODING)


def parse_label(filename):
    """
    從檔名取出 label：
      K11-6F 區網(54).csv → 區網(54)
      其他 區網(10).csv    → 區網(10)
    """
    name = filename[:-4] if filename.lower().endswith('.csv') else filename
    parts = name.rsplit(' ', 1)
    return parts[1] if len(parts) == 2 else name


def scan_csv_files():
    """
    掃描 csv/ 資料夾，回傳 [{site, floor, label, path}, ...]
    目錄規則：
      csv/<site>/<floor>/<site>-<floor> 區網(N).csv   ← 正式檔（讀這個）
      csv/<site>/<site> 區網(N).csv                   ← 無樓層（例如 其他）
      csv/<site>/<floor>/<site>-<floor> 區網(N)/xxx.csv ← 時間戳備份，略過
    """
    results = []
    base = os.path.abspath(CSV_FOLDER)

    for root, dirs, files in os.walk(base):
        rel = os.path.relpath(root, base)
        parts = [] if rel == '.' else rel.split(os.sep)

        # 只接受 csv/<site>/ 或 csv/<site>/<floor>/ 兩層
        if len(parts) == 1:
            site, floor = parts[0], ''
        elif len(parts) == 2:
            site, floor = parts[0], parts[1]
        else:
            continue

        # 備份資料夾（名稱含 區網(...)）不當樓層
        if floor and '區網(' in floor:
            continue

        for f in files:
            if not f.lower().endswith('.csv'):
                continue
            # 時間戳備份檔（20251202_135104_xxx.csv）略過
            if re.match(r'^\d{8}_\d{6}_', f):
                continue
            results.append({
                'site': site,
                'floor': floor,
                'label': parse_label(f),
                'path': os.path.join(root, f),
            })

    return results


def status_key(site, floor, label):
    """status.json 的 key：K11-6F 區網(54) / 其他 區網(10)"""
    return f"{site}-{floor} {label}" if floor else f"{site} {label}"


def get_csv_path(site, floor, label=None):
    """根據 site/floor/label 回傳對應的 CSV 檔路徑"""
    logger.debug(f"🔍 搜尋 CSV: site={site}, floor={floor}, label={label}")

    for info in scan_csv_files():
        if info['site'] != site or info['floor'] != (floor or ''):
            continue
        if label and info['label'] != label:
            continue
        return info['path']

    logger.warning(f"  ❌ 未找到匹配的 CSV")
    return None


# =========================================================
# ⭐ 網段清單（Sidebar）
# =========================================================
@app.route('/api/db_list')
def api_db_list():
    result = {}
    username = request.args.get('username', '')

    def natural(text):
        return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)', text or '')]

    for info in sorted(scan_csv_files(),
                       key=lambda x: (natural(x['site']), natural(x['floor']), natural(x['label']))):
        result.setdefault(info['site'], {}).setdefault(info['floor'], []).append({'label': info['label']})

    logger.info(f"{username} 正在進入網頁，正在拉取Sidebar資訊")
    return jsonify(result)


# =========================================================
# ⭐ 查詢單一網段
# =========================================================
@app.route('/api/devices')
def api_devices():
    site = request.args.get('site')
    floor = request.args.get('floor')
    username = request.args.get('username', '')
    label = request.args.get('label', '')

    floor = floor or ''
    if not site or not label:
        logger.warning(f"⚠️ 缺少參數 | user={username}")
        return jsonify({"error": "missing site or label"}), 400

    logger.success(f"{username} 正在查詢 {site}-{floor} {label}")

    csv_path = get_csv_path(site, floor, label)
    if not csv_path or not os.path.exists(csv_path):
        logger.warning(f"❌ CSV不存在")
        return jsonify([])

    try:
        with FileLock(csv_path + ".lock", timeout=10):
            df = read_csv(csv_path)

        logger.success(f"{username} 已查詢到 {label}")

        stats = {}
        try:
            if os.path.exists(status_path):
                with open(status_path, "r", encoding="utf-8-sig") as f:
                    status_data = json.load(f)
                stats = status_data.get(status_key(site, floor, label), {})
        except Exception:
            logger.error(f"{site}-{floor}找不到資料")

        return jsonify({
            "devices": df.to_dict(orient='records'),
            "stats": stats,
        })

    except Exception as e:
        logger.error(f"異常處理：user={username} 的 {label}，error={str(e)}")
        return jsonify({"error": str(e)}), 500


# =========================================================
# ⭐ 修改紀錄（log.csv）
# =========================================================
def read_audit_df():
    if not os.path.exists(LOG_CSV):
        return pd.DataFrame(columns=AUDIT_COLUMNS)
    df = read_csv(LOG_CSV)
    for c in AUDIT_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[AUDIT_COLUMNS]


def write_audit_log(username, site, floor, label, ip, changes):
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with FileLock(LOG_CSV + ".lock", timeout=10):
            df = read_audit_df()

            try:
                next_id = int(pd.to_numeric(df["id"], errors="coerce").max()) + 1
            except Exception:
                next_id = 1
            if pd.isna(next_id):
                next_id = 1

            new_rows = []
            for c in changes:
                try:
                    if "→" not in c or ":" not in c:
                        continue
                    field, values = c.split(":", 1)
                    old_val, new_val = values.split("→", 1)

                    new_rows.append({
                        "id": next_id,
                        "time": now,
                        "username": username,
                        "site": site,
                        "floor": floor,
                        "label": label,
                        "ip": ip,
                        "field": field.strip(),
                        "old_value": old_val.strip(),
                        "new_value": new_val.strip(),
                    })
                    next_id += 1
                except Exception as e:
                    logger.error(f"⚠️ audit 單筆寫入失敗 | {c} | error={e}")

            if new_rows:
                df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                write_csv(df, LOG_CSV)

        logger.success(f"{username} 已修正 IP={ip} ")

    except Exception as e:
        logger.error(f"🔥 log.csv 寫入失敗: {e}")


# =========================================================
# ⭐ 更新設備
# =========================================================
@app.route('/api/update_device', methods=['POST'])
def update_device():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "沒有收到 JSON"}), 400

        username = data.get('username', '')
        label = data.get('label', '')

        ip = data.get("Internal_IP")
        if not ip:
            return jsonify({"success": False, "error": "缺少 Internal_IP"}), 400

        site = data.get('site')
        floor = data.get('floor') or ''
        if not site or not label:
            return jsonify({"success": False, "error": "缺少 site 或 label"}), 400

        logger.info(f"接收到來自{username} 的更改資訊如下：{json.dumps(data, ensure_ascii=False)}")

        csv_path = get_csv_path(site, floor, label)
        if not csv_path or not os.path.exists(csv_path):
            logger.warning(f"❌ {site}-{floor} 的CSV不存在")
            return jsonify({"success": False, "error": "找不到資料檔"}), 404

        with FileLock(csv_path + ".lock", timeout=10):
            df = read_csv(csv_path)

            mask = df["Internal_IP"] == ip
            if not mask.any():
                return jsonify({"success": False, "error": "找不到該設備"}), 404

            idx = df.index[mask][0]
            old_data = df.loc[idx].to_dict()
            csv_columns = list(df.columns)

            def safe_col(names):
                for n in names:
                    if n in csv_columns:
                        return n
                return None

            col_area = safe_col(["所在區域(柱位)", "所在區域", "區域"])
            col_maint = safe_col(["歲修"])
            col_tcp = safe_col(["TCP_Port"])
            col_com = safe_col(["COM_Port"])

            AREA_KEYS = ["所在區域(柱位)", "所在區域 (柱位)", "所在區域", "區域"]
            area_key = next((k for k in AREA_KEYS if k in data), None)

            updates = {}

            def add_field(col, key):
                """只更新 payload 有帶的欄位；沒帶的保持原值"""
                if not col or col not in csv_columns or key not in data:
                    return
                new_value = data.get(key)
                new_value = "" if new_value is None else str(new_value)
                old_value = str(old_data.get(col, ""))
                if new_value != old_value:
                    updates[col] = new_value

            add_field("Machine_ID", "Machine_ID")
            add_field("Device_Name", "Device_Name")
            add_field("Local", "Local")
            add_field(col_area, area_key)
            add_field(col_tcp, "TCP_Port")
            add_field(col_com, "COM_Port")
            add_field("OS_Spec", "OS_Spec")
            add_field("IP_Source", "IP_Source")
            add_field("Category", "Category")
            add_field("Online_Test", "Online_Test")
            add_field("Set_Time", "Set_Time")
            add_field(col_maint, "歲修")
            add_field("alive_or_dead", "alive_or_dead")
            add_field("Remark", "Remark")
            add_field("是否派報", "是否派報")

            if not updates:
                logger.warning(f"⚠️ 無欄位更新 | user={username} | ip={ip}")
                return jsonify({"success": False, "error": "沒有可更新欄位"})

            for col, val in updates.items():
                df.at[idx, col] = val

            write_csv(df, csv_path)
            new_data = df.loc[idx].to_dict()

        changes = []
        for k in new_data.keys():
            old_val = str(old_data.get(k, ""))
            new_val = str(new_data.get(k, ""))
            if old_val != new_val:
                changes.append(f"{k}: {old_val} → {new_val}")

        if changes:
            logger.info(f"{username} IP={ip} 欄位變更共{len(changes)}項")
            for i, c in enumerate(changes, 1):
                logger.info(f"[{i}] {c}")
            write_audit_log(username, site, floor, label, ip, changes)

        invalidate_search_cache()

        logger.success(f"{username}修改{label}的IP={ip}")
        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"🔥 修改失敗 | user={locals().get('username','')} | error={str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500


# =========================================================
# ⭐ 修改紀錄查詢
# =========================================================
@app.route('/api/audit_logs')
def get_audit_logs():
    try:
        with FileLock(LOG_CSV + ".lock", timeout=10):
            df = read_audit_df()

        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        df = df.sort_values("id", ascending=False).head(500)
        return jsonify(df.to_dict(orient="records"))

    except Exception as e:
        logger.error(f"🔥 audit 查詢失敗: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/audit_logs/search')
def search_audit_logs():
    try:
        query = request.args.get("q", "").strip()
        if not query:
            return jsonify([])

        with FileLock(LOG_CSV + ".lock", timeout=10):
            df = read_audit_df()

        cols = ["username", "site", "floor", "label", "ip", "field", "old_value", "new_value"]
        mask = pd.Series(False, index=df.index)
        for c in cols:
            mask |= df[c].astype(str).str.contains(query, case=False, regex=False, na=False)

        df = df[mask].copy()
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        df = df.sort_values("id", ascending=False).head(500)
        return jsonify(df.to_dict(orient="records"))

    except Exception as e:
        logger.error(f"🔥 搜尋失敗: {e}")
        return jsonify({"error": str(e)}), 500


# =========================================================
# ⭐ 使用者狀態
# =========================================================
@app.route('/api/save_user_state', methods=['POST'])
def save_user_state():
    try:
        data = request.get_json(silent=True)
        if not data:
            return jsonify({"success": False, "error": "no json received"}), 400

        username = data.get("username")
        state = data.get("state")
        if not username:
            return jsonify({"success": False, "error": "missing username"}), 400

        file_path = os.path.join(STATE_DIR, f"{username}.json")

        with FileLock(file_path + ".lock", timeout=5):
            old_data = {}
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        old_data = json.load(f)
                except Exception:
                    old_data = {}

            old_data.update(state or {})

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(old_data, f, ensure_ascii=False, indent=2)

        logger.info(f"username: {username} save_user_state 的狀態儲存")
        return jsonify({"success": True})

    except Exception as e:
        logger.error(f"🔥 state儲存失敗: {e}")
        return jsonify({"success": False, "error": str(e)})


@app.route('/api/get_user_state')
def get_user_state():
    try:
        username = request.args.get("username")
        if not username:
            return jsonify({})

        file_path = os.path.join(STATE_DIR, f"{username}.json")
        if not os.path.exists(file_path):
            return jsonify({})

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        logger.info(f"{username} 正在讀取上輪狀態點擊紀錄")
        return jsonify(data)

    except Exception as e:
        logger.error(f"🔥 上輪狀態點擊紀錄讀取失敗: {e}")
        return jsonify({})


# =========================================================
# ⭐ 新增網段
# =========================================================
@app.route('/api/add_network', methods=['POST'])
def add_network():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"message": "沒有收到 JSON"}), 400

    site = (data.get('site') or '').upper()
    floor = (data.get('floor') or '').upper()
    subnet1 = data.get('subnet1')
    subnet2 = data.get('subnet2')
    username = data.get('username')

    eap_count = int(data.get('eapCount', 0))
    eqp_count = int(data.get('eqpCount', 0))
    switch_count = int(data.get('switchCount', 0))

    if not floor.endswith('F'):
        floor = ''.join(filter(str.isdigit, floor)) + 'F'

    if not site or not floor or subnet1 is None or subnet2 is None:
        return jsonify({"message": "缺少必要欄位"}), 400

    try:
        subnet1 = int(subnet1)
        subnet2 = int(subnet2)
    except Exception:
        return jsonify({"message": "網段格式錯誤"}), 400

    total = eap_count + eqp_count + switch_count
    if total != 254:
        return jsonify({"message": f"分類總數需為254，目前為{total}"}), 400

    csv_name = f"{site}-{floor} 區網({subnet2}).csv"
    csv_dir = os.path.join(CSV_FOLDER, site, floor)
    os.makedirs(csv_dir, exist_ok=True)
    csv_path = os.path.join(csv_dir, csv_name)

    if os.path.exists(csv_path):
        return jsonify({"message": "CSV已存在"}), 400

    try:
        local = f"{site}-{floor}"
        file_place = f"{site}\\{floor}\\{csv_name}"

        rows = []
        current = 1
        for category, count in (("EAP", eap_count), ("EQP", eqp_count), ("Switch", switch_count)):
            for _ in range(count):
                rows.append({
                    "Internal_IP": f"172.{subnet1}.{subnet2}.{current}",
                    "Machine_ID": "",
                    "Local": local,
                    "Device_Name": "",
                    "TCP_Port": "",
                    "COM_Port": "",
                    "OS_Spec": "",
                    "IP_Source": "",
                    "Category": category,
                    "Online_Test": "",
                    "Set_Time": "",
                    "Remark": "",
                    "歲修": "",
                    "File_Place": file_place,
                    "所在區域(柱位)": "",
                    "alive_or_dead": "alive" if current == 1 else "dead",
                    "是否派報": "alive" if current == 1 else "dead"
                })
                current += 1

        df = pd.DataFrame(rows, columns=DEVICE_COLUMNS)
        with FileLock(csv_path + ".lock", timeout=10):
            write_csv(df, csv_path)

        logger.info(f"{username} 已建立 {csv_name} 這個新CSV,為 {site}-{floor}，為 172.{subnet1}.{subnet2}.1,預計 EAP數量: {eap_count},EQP數量:{eqp_count},Switch數量:{switch_count}")

        invalidate_search_cache()

        return jsonify({
            "message": "CSV建立成功",
            "db_name": csv_name,
            "total_ips": 254,
        })

    except Exception as e:
        return jsonify({"message": "建立失敗", "error": str(e)}), 500


# =========================================================
# ⭐ 刪除網段
# =========================================================
@app.route('/api/delete_network', methods=['POST'])
def delete_network():
    data = request.get_json(silent=True) or {}

    site = (data.get('site') or '').upper()
    floor = (data.get('floor') or '').upper()
    label = data.get('label', '')
    username = data.get('username', '')

    if not site or not label:
        return jsonify({"success": False, "message": "缺少 site 或 label"}), 400

    csv_path = get_csv_path(site, floor, label)
    if not csv_path or not os.path.exists(csv_path):
        return jsonify({"success": False, "message": "找不到資料檔"}), 404

    try:
        with FileLock(csv_path + ".lock", timeout=10):
            os.remove(csv_path)

        logger.warning(f"{username} {site}-{floor} {label} 的CSV刪除")
        invalidate_search_cache()

        return jsonify({"success": True, "message": "刪除成功"})

    except Exception as e:
        logger.error(f"🔥 刪除失敗 | {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# =========================================================
# ⭐ 全域搜尋（記憶體快取，取代 search.db）
# =========================================================
_search_cache = {"df": None}


def invalidate_search_cache():
    _search_cache["df"] = None
    logger.info("🗑️ 搜尋快取已清除，下次搜尋將重建")


def build_search_df():
    if _search_cache["df"] is not None:
        return _search_cache["df"]

    frames = []
    for info in scan_csv_files():
        csv_path = info['path']
        try:
            with FileLock(csv_path + ".lock", timeout=10):
                df = read_csv(csv_path)

            for c in SEARCH_COLUMNS:
                if c not in df.columns:
                    df[c] = ""
            df = df[SEARCH_COLUMNS].copy()
            df["site"] = info['site']
            df["floor"] = info['floor']
            df["label"] = info['label']
            frames.append(df)
        except Exception as e:
            logger.error(f"合併失敗 {csv_path} | {e}")

    if frames:
        merged = pd.concat(frames, ignore_index=True)
    else:
        merged = pd.DataFrame(columns=SEARCH_COLUMNS + ["site", "floor", "label"])

    _search_cache["df"] = merged
    logger.success("🚀 搜尋快取建立完成")
    return merged


@app.route('/api/search_all_devices')
def search_all_devices():
    keyword = request.args.get('q', '').strip()
    if not keyword:
        return jsonify([])

    df = build_search_df()

    mask = pd.Series(False, index=df.index)
    for c in df.columns:
        mask |= df[c].astype(str).str.contains(keyword, case=False, regex=False, na=False)

    return jsonify(df[mask].head(500).to_dict(orient="records"))


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
    return jsonify({"success": True, "message": "登入成功!"})
    
    # if authenticate_user(username, password):
    #     return jsonify({"success": True, "message": "登入成功!"})
    # else:
    #     return jsonify({"success": False, "message": "帳號或密碼錯誤，請重新輸入"})





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




# =============================================== json 歲修過帳
pass_dwon_ER = 'D:\Data\EAP_Health_level\source'
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
            print(f"新增 filename: {filename}, category_id: {category_id} 分類成功")
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
            print(f"移除 filename: {filename}, category_id: {category_id} 分類成功")
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
            print(f"新增 filename: {filename}, category_id: {category_id}, item_value: {item_value} 成功")
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
            print(f"修改 filename: {filename}, category_id: {category_id}, item_code: {item_code}, new_value: {new_value}")
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
            print(f"刪除 filename: {filename}, category_id: {category_id}, item_code: {item_code} 成功")
            return jsonify({"message": f"成功刪除項目 {item_code}"})
        else:
            return jsonify({"error": "儲存失敗"}), 500
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# def _safe_read_csv_index(file_path):
#     try:
#         if not os.path.exists(file_path):
#             return []
#         df = pd.read_csv(file_path, encoding='utf-8-sig')
#         # 欄位重新命名
#         df = df.rename(columns={
#             "時間": "timestamp",
#             "IP 位址": "ip", 
#             "設備 ID": "machine_id",
#             "設備類型": "device_type",
#             "位置": "location"
#         })
#         # 只保留需要的欄位並轉為 list of dict
#         result = df[["timestamp", "ip", "machine_id", "device_type", "location"]].to_dict(orient='records')
#         result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
#         return result
#     except Exception as e:
#         print(f"讀取 CSV 錯誤 [{file_path}]: {e}")
#         return []


# 修改 _safe_read_csv_index，增加欄位檢查
def _safe_read_csv_index(file_path):
    try:
        if not os.path.exists(file_path):
            return []
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        
        # 欄位重新命名
        df = df.rename(columns={
            "時間": "timestamp",
            "IP 位址": "ip", 
            "設備 ID": "machine_id",
            "設備類型": "device_type",
            "位置": "location"
        })
        
        # ✅ 只選取「存在的欄位」，避免 KeyError
        required_cols = ["timestamp", "ip", "machine_id", "device_type", "location"]
        available_cols = [col for col in required_cols if col in df.columns]
        
        if not available_cols:
            return []
            
        result = df[available_cols].to_dict(orient='records')
        result.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return result
    except Exception as e:
        print(f"讀取 CSV 錯誤 [{file_path}]: {e}")
        return []



# @app.route("/api/get_csv_data_all_index")
# def get_csv_data_all_index():
#     """讀取所有 CSV 檔案資料並回傳 JSON"""
#     base_path = r"\\KHA3CIMSEN1\Data\EAP_Health_level\alarm_store"
    
#     data = {
#         "EAP": _safe_read_csv_index(os.path.join(base_path, 'EAP_Loss.csv')),
#         "EQP": _safe_read_csv_index(os.path.join(base_path, 'EQP_Loss.csv')),
#         "Switch": _safe_read_csv_index(os.path.join(base_path, 'Switch_Loss.csv')),
#     }
#     return jsonify(data)

@app.route("/api/get_csv_data_all_index")
def get_csv_data_all_index():
    try:
        base_path = r"\\KHA3CIMSEN1\Data\EAP_Health_level\alarm_store"

        eap = _safe_read_csv_index(os.path.join(base_path, 'EAP_Loss.csv'))
        eqp = _safe_read_csv_index(os.path.join(base_path, 'EQP_Loss.csv'))
        switch = _safe_read_csv_index(os.path.join(base_path, 'Switch_Loss.csv'))

        return jsonify({
            "EAP": eap,
            "EQP": eqp,
            "Switch": switch
        })

    except Exception as e:
        print(f"❌ API 錯誤: {e}")
        return jsonify({"error": str(e)}), 500

# =========================
# ⏰ 每小時妥善率 API
# =========================
HOURLY_RATE_CSV_PATH = r"\\20220530-W03\data\EAP_Health_level\source\hourly_rate.csv"
# 原本既有的 JSON
K11_JSON_PATH = r"\\20220530-W03\data\EAP_Health_level\source\K11.json"
K22_JSON_PATH = r"\\20220530-W03\data\EAP_Health_level\source\K22.json"
RECORD_JSON_PATH = r"\\20220530-W03\data\EAP_Health_level\source\abnormal_records.json"

@app.route("/api/hourly_rate", methods=["GET"])
def get_hourly_rate():
    """
    獲取每小時妥善率數據（從CSV讀取）
    返回最新15筆記錄
    """
    if not os.path.exists(HOURLY_RATE_CSV_PATH):
        return jsonify({
            "status": "error",
            "message": "CSV文件不存在",
            "k11": [],
            "k22": [],
            "timestamps": []
        }), 404
    
    try:
        data = read_csv_data(HOURLY_RATE_CSV_PATH, limit=17)
        return jsonify(data)
    except Exception as e:
        print(f"❌ 讀取CSV失敗: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "k11": [],
            "k22": [],
            "timestamps": []
        }), 500


def read_csv_data(filepath, limit=17):
    """
    從CSV文件讀取最新的N筆記錄
    
    Args:
        filepath: CSV文件路徑
        limit: 要讀取的記錄數量
        
    Returns:
        dict: 包含k11, k22, timestamps的字典
    """
    k11_rates = []
    k22_rates = []
    timestamps = []
    
    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            all_rows = list(reader)
            
            # 獲取最新的limit筆記錄
            recent_rows = all_rows[-limit:] if len(all_rows) > limit else all_rows
            
            for row in recent_rows:
                timestamps.append(row['時間戳記'])
                k11_rates.append(float(row['K11妥善率(%)']))
                k22_rates.append(float(row['K22妥善率(%)']))
        
        return {
            "k11": k11_rates,
            "k22": k22_rates,
            "timestamps": timestamps
        }
    except KeyError as e:
        print(f"❌ CSV欄位錯誤: {e}")
        raise Exception(f"CSV格式錯誤，缺少欄位: {e}")
    except ValueError as e:
        print(f"❌ 數據格式錯誤: {e}")
        raise Exception(f"數據格式錯誤: {e}")
    except Exception as e:
        print(f"❌ 讀取CSV錯誤: {e}")
        raise


# =========================
# 讀取 K11
# =========================
@app.route("/api/k11")
def get_k11():
    if not os.path.exists(K11_JSON_PATH):
        return jsonify({"error": "K11.json 不存在"}), 404

    with open(K11_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify(data)


# =========================
# 讀取 K22
# =========================
@app.route("/api/k22")
def get_k22():
    if not os.path.exists(K22_JSON_PATH):
        return jsonify({"error": "K22.json 不存在"}), 404

    with open(K22_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    return jsonify(data)

# =========================
# 🔹 儲存 K11 數據
# =========================
@app.route("/api/save_k11", methods=["POST"])
def save_k11():
    """
    儲存修改後的 K11 數據
    """
    try:
        data = request.json

        # 寫入檔案
        with open(K11_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"✅ 已儲存 K11 數據")

        return jsonify({
            "status": "ok",
            "message": "K11 數據儲存成功"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# =========================
# 🔹 儲存 K22 數據
# =========================
@app.route("/api/save_k22", methods=["POST"])
def save_k22():
    """
    儲存修改後的 K22 數據
    """
    try:
        data = request.json

        # 寫入檔案
        with open(K22_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print(f"✅ 已儲存 K22 數據")

        return jsonify({
            "status": "ok",
            "message": "K22 數據儲存成功"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# =========================
# 🔹 載入異常紀錄（頁面初始化）
# =========================
@app.route("/api/load_records", methods=["GET"])
def load_records():
    if not os.path.exists(RECORD_JSON_PATH):
        # 尚未有資料，回空陣列
        return jsonify({
            "records": []
        })

    try:
        with open(RECORD_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        return jsonify({
            "records": data.get("records", [])
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# =========================
# 🔹 儲存異常紀錄（覆蓋寫入）
# =========================
@app.route("/api/save_records", methods=["POST"])
def save_records():
    data = request.json or {}
    records = data.get("records", [])

    payload = {
        "updated_at": datetime.now().isoformat(),
        "records": records
    }

    try:
        with open(RECORD_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        print(f"✅ 已儲存 {len(records)} 筆異常紀錄")

        return jsonify({
            "status": "ok",
            "count": len(records)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# =========================
# 🔹 刪除單筆異常紀錄
# =========================
@app.route("/api/delete_record/<int:index>", methods=["DELETE"])
def delete_record(index):
    """
    刪除指定索引的紀錄
    """
    if not os.path.exists(RECORD_JSON_PATH):
        return jsonify({
            "status": "error",
            "message": "找不到紀錄檔案"
        }), 404

    try:
        # 讀取現有資料
        with open(RECORD_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        records = data.get("records", [])

        # 檢查索引是否有效
        if index < 0 or index >= len(records):
            return jsonify({
                "status": "error",
                "message": f"無效的索引: {index}"
            }), 400

        # 刪除指定索引的紀錄
        deleted_record = records.pop(index)

        # 更新資料
        payload = {
            "updated_at": datetime.now().isoformat(),
            "records": records
        }

        # 寫回檔案
        with open(RECORD_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        print(f"✅ 已刪除第 {index} 筆紀錄")

        return jsonify({
            "status": "ok",
            "deleted_index": index,
            "deleted_record": deleted_record,
            "remaining_count": len(records)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# =========================
# 🔹 批量刪除異常紀錄
# =========================
@app.route("/api/delete_records", methods=["POST"])
def delete_records():
    """
    批量刪除指定索引的紀錄
    接收 JSON: {"indices": [0, 2, 5]}
    """
    if not os.path.exists(RECORD_JSON_PATH):
        return jsonify({
            "status": "error",
            "message": "找不到紀錄檔案"
        }), 404

    data = request.json or {}
    indices = data.get("indices", [])

    if not indices:
        return jsonify({
            "status": "error",
            "message": "未提供要刪除的索引"
        }), 400

    try:
        # 讀取現有資料
        with open(RECORD_JSON_PATH, "r", encoding="utf-8") as f:
            file_data = json.load(f)

        records = file_data.get("records", [])

        # 排序索引（由大到小），避免刪除時索引錯亂
        indices_sorted = sorted(set(indices), reverse=True)

        deleted_count = 0
        for idx in indices_sorted:
            if 0 <= idx < len(records):
                records.pop(idx)
                deleted_count += 1

        # 更新資料
        payload = {
            "updated_at": datetime.now().isoformat(),
            "records": records
        }

        # 寫回檔案
        with open(RECORD_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        print(f"✅ 已批量刪除 {deleted_count} 筆紀錄")

        return jsonify({
            "status": "ok",
            "deleted_count": deleted_count,
            "remaining_count": len(records)
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500



# 🔹 F1 / F3（同樣寫法）
HOURLY_RATE_F_CSV_PATH = r"\\20220530-W03\data\EAP_Health_level\source\hourly_rate_r.csv"


@app.route("/api/hourly_rate_f", methods=["GET"])
def get_hourly_rate_f():
    """
    獲取每小時妥善率數據（F1 / F3）
    """
    if not os.path.exists(HOURLY_RATE_F_CSV_PATH):
        return jsonify({
            "status": "error",
            "message": "CSV文件不存在",
            "f1": [],
            "f3": [],
            "timestamps": []
        }), 404

    try:
        data = read_csv_data_f(HOURLY_RATE_F_CSV_PATH, limit=15)
        return jsonify(data)
    except Exception as e:
        print(f"❌ 讀取 F CSV 失敗: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "f1": [],
            "f3": [],
            "timestamps": []
        }), 500


def read_csv_data_f(filepath, limit=15):
    f1_rates = []
    f3_rates = []
    timestamps = []

    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        recent = rows[-limit:] if len(rows) > limit else rows

        for row in recent:
            timestamps.append(row["時間戳記"])
            f1_rates.append(float(row["F1妥善率(%)"]))
            f3_rates.append(float(row["F3妥善率(%)"]))

    return {
        "f1": f1_rates,
        "f3": f3_rates,
        "timestamps": timestamps
    }






DEAD_JSON_DIR = r"D:\網頁\EAP_DashBoard\static\source\dead_json"
import glob

@app.route('/api/get_dead_history', methods=['GET'])
def get_dead_history():
    """
    讀取 static/source/dead_json/ 下所有 dead_*.json
    回傳格式：
    {
        "2026-05-07": [ { "電腦名稱": "...", "count": 38, "當下時間": "..." }, ... ],
        "2026-05-08": [ ... ],
        ...
    }
    按日期升冪排序
    """
    result = {}
 
    pattern = os.path.join(DEAD_JSON_DIR, "dead_*.json")
    files   = sorted(glob.glob(pattern))   # 升冪 = 最舊在前
 
    for filepath in files:
        filename = os.path.basename(filepath)               # dead_2026-05-07.json
        date_str = filename.replace("dead_", "").replace(".json", "")  # 2026-05-07
 
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            result[date_str] = data
        except Exception as e:
            print(f"[WARN] 讀取 {filename} 失敗: {e}")
            result[date_str] = []
 
    return jsonify(result)



import datetime as _dt

# ── Timeline ──────────────────────────────────────────────────────────────
CSV_PATH = r'status_change_log.csv'

_cache = None

def rows():
    global _cache
    if _cache is None:
        with open(CSV_PATH, encoding='utf-8-sig') as f:
            _cache = list(csv.DictReader(f))
    return _cache

def ipg(ip):  return '.'.join(ip.split('.')[:2])
def ips3(ip): return '.'.join(ip.split('.')[:3])
def ipk(ip):
    try: return tuple(int(x) for x in ip.split('.'))
    except: return (999,)*4


@app.route('/api/tl/subnet_stats')
def tl_subnet_stats():
    try:
        ip_events = defaultdict(list)
        for r in rows():
            ip = r['IP']
            if len(ip.split('.')) == 4:
                ip_events[ip].append((r['時間'], r['新狀態'], r['設備類型']))

        subnet_stats = defaultdict(lambda: {'alive':0,'dead':0,'total':0,'types':set()})
        for ip, evs in ip_events.items():
            evs.sort()
            last_status = evs[-1][1]
            subnet = ips3(ip)
            subnet_stats[subnet]['total'] += 1
            subnet_stats[subnet][last_status] += 1
            subnet_stats[subnet]['types'].add(evs[-1][2])

        result = []
        for s, st in sorted(subnet_stats.items(),
                             key=lambda x: tuple(int(n) for n in x[0].split('.'))):
            result.append({
                'subnet': s,
                'alive':  st['alive'],
                'dead':   st['dead'],
                'total':  st['total'],
                'types':  list(st['types']),
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tl/subnet_grid')
def tl_subnet_grid():
    try:
        subnet = request.args.get('subnet', '')
        if not subnet:
            return jsonify({'error': 'subnet required'}), 400

        all_times = sorted(r['時間'] for r in rows())
        tmin, tmax = all_times[0], all_times[-1]

        ip_ev, ip_meta = defaultdict(list), {}
        for r in rows():
            parts = r['IP'].split('.')
            if len(parts) == 4 and '.'.join(parts[:3]) == subnet:
                ip_ev[r['IP']].append({
                    't':   r['時間'],
                    'old': r['舊狀態'],
                    'new': r['新狀態'],
                })
                if r['IP'] not in ip_meta:
                    ip_meta[r['IP']] = {
                        'tp':  r['設備類型'],
                        'mid': r['Machine_ID'],
                        'dn':  r['Device_Name'],
                    }

        # 只回傳有資料的 IP（移除空的）
        devs = []
        for oct in range(1, 255):
            ip  = f'{subnet}.{oct}'
            evs = sorted(ip_ev.get(ip, []), key=lambda e: e['t'])
            if not evs:
                continue   # 沒有任何事件 → 跳過

            segs = []
            if evs[0]['t'] > tmin:
                segs.append({'s': tmin, 'e': evs[0]['t'], 'v': evs[0]['old']})
            for i, ev in enumerate(evs):
                segs.append({
                    's': ev['t'],
                    'e': evs[i+1]['t'] if i+1 < len(evs) else tmax,
                    'v': ev['new'],
                })
            meta = ip_meta[ip]
            devs.append({
                'ip':  ip,
                'oct': oct,
                'tp':  meta['tp'],
                'mid': meta['mid'],
                'dn':  meta['dn'],
                'segs': segs,
            })

        return jsonify({'devs': devs, 'tmin': tmin, 'tmax': tmax, 'subnet': subnet})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/tl/data')
def tl_data():
    try:
        dtype  = request.args.get('type', '')
        gfilt  = request.args.get('group', '')
        prefix = request.args.get('prefix', '')
        chonly = request.args.get('changed_only', '1') == '1'

        ip_cnt = defaultdict(int)
        for r in rows(): ip_cnt[r['IP']] += 1

        ip_ev, ip_meta = defaultdict(list), {}
        for r in rows():
            ip = r['IP']
            if dtype  and r['設備類型'] != dtype:           continue
            if gfilt  and ipg(ip) != gfilt:                 continue
            if prefix and not ip.startswith(prefix + '.'):  continue
            if chonly and ip_cnt[ip] <= 1:                   continue
            ip_ev[ip].append((r['時間'], r['新狀態']))
            if ip not in ip_meta:
                ip_meta[ip] = (r['設備類型'], r['Machine_ID'], r['Device_Name'])

        devs, times = [], []
        for ip, evs in ip_ev.items():
            evs.sort()
            times += [e[0] for e in evs]
            segs = [
                {'s': evs[i][0], 'e': evs[i+1][0] if i+1 < len(evs) else None, 'v': evs[i][1]}
                for i in range(len(evs))
            ]
            tp, mid, dn = ip_meta[ip]
            devs.append({
                'ip': ip, 'g': ipg(ip), 'sub': ips3(ip),
                'tp': tp, 'mid': mid, 'dn': dn, 'segs': segs,
            })

        devs.sort(key=lambda d: (ipg(d['ip']), ips3(d['ip']), ipk(d['ip'])))
        return jsonify({
            'devs': devs,
            'tmin': min(times) if times else '',
            'tmax': max(times) if times else '',
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────────────────────────────────
STATUS_CHANGE_LOG = r'status_change_log.csv'

@app.route('/api/building_floor_status')
def building_floor_status():
    try:
        rows = []
        with open(STATUS_CHANGE_LOG, encoding='utf-8-sig') as f:
            rows = list(csv.DictReader(f))
 
        ip_latest = {}
        for r in rows:
            ip = r['IP']
            if ip not in ip_latest or r['時間'] > ip_latest[ip]['時間']:
                ip_latest[ip] = r
 
        from collections import defaultdict
        bld_floor = defaultdict(lambda: defaultdict(lambda: {
            'alive': 0, 'dead': 0, 'subnets': set()
        }))
 
        def subnet3(ip):
            p = ip.split('.')
            return '.'.join(p[:3]) if len(p) == 4 else ''
 
        for r in ip_latest.values():
            bld, fl, st = r['棟別'], r['樓層'], r['新狀態']
            if bld == '歲修':
                continue
            if st in ('alive', 'dead'):
                bld_floor[bld][fl][st] += 1
                sn = subnet3(r['IP'])
                if sn:
                    bld_floor[bld][fl]['subnets'].add(sn)
 
        BLD_ORDER = ['K11', 'K18', 'K21', 'K22', 'K25', '其他']
 
        def floor_sort_key(name):
            n = ''.join(filter(str.isdigit, name))
            return int(n) if n else 999
 
        def subnet_label(sns):
            octets = []
            for s in sns:
                p = s.split('.')
                if len(p) == 3:
                    octets.append(int(p[2]))
            return sorted(octets)
 
        result = []
        for bld in BLD_ORDER:
            if bld not in bld_floor:
                continue
            floors = []
            for fl, cnt in sorted(bld_floor[bld].items(), key=lambda x: floor_sort_key(x[0])):
                prefix = ''
                for sn in cnt['subnets']:
                    p = sn.split('.')
                    if len(p) == 3:
                        prefix = p[0] + '.' + p[1]
                        break
                floors.append({
                    'name':          fl,
                    'alive':         cnt['alive'],
                    'dead':          cnt['dead'],
                    'subnets':       subnet_label(cnt['subnets']),
                    'subnet_prefix': prefix,
                })
            result.append({'id': bld, 'floors': floors})
 
        return jsonify({
            'buildings':  result,
            'updated_at': _dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500





if __name__ == '__main__':
    app.run(debug=True, port=5000)