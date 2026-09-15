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

# =========================================================
# ⭐ 路徑設定（全部改為 CSV）
# =========================================================
CSV_FOLDER = r"csv"                     # 各網段 CSV 存放資料夾（原 db/）
LOG_CSV = "log.csv"                     # 修改紀錄（原 log.db）
log_path = "log.log"
status_path = "status.json"
STATE_DIR = os.path.join(os.getcwd(), "user_states")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # html 所在目錄

os.makedirs(CSV_FOLDER, exist_ok=True)
os.makedirs(STATE_DIR, exist_ok=True)

CSV_ENCODING = "utf-8-sig"

# ⭐ 網段 CSV 欄位（順序固定）
DEVICE_COLUMNS = [
    "Internal_IP", "Machine_ID", "Local", "Device_Name",
    "TCP_Port", "COM_Port", "OS_Spec", "IP_Source",
    "Category", "Online_Test", "Set_Time", "Remark",
    "歲修", "File_Place", "所在區域(柱位)", "alive_or_dead",
]

# ⭐ 修改紀錄 CSV 欄位
AUDIT_COLUMNS = [
    "id", "time", "username", "site", "floor", "label",
    "ip", "field", "old_value", "new_value",
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)