import csv
from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # ✅ 允許跨來源（保險）

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 原本既有的 JSON
K11_JSON_PATH = os.path.join(BASE_DIR, "K11.json")
K22_JSON_PATH = os.path.join(BASE_DIR, "K22.json")

# 🔹 新增：異常紀錄 JSON
RECORD_JSON_PATH = os.path.join(BASE_DIR, "abnormal_records.json")
HOURLY_RATE_CSV_PATH = os.path.join(BASE_DIR, "hourly_rate.csv")

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
# ⏰ 每小時妥善率 API
# =========================
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
        data = read_csv_data(HOURLY_RATE_CSV_PATH, limit=15)
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


def read_csv_data(filepath, limit=15):
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



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)