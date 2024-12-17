import sys
# 更換
package_path = r".\python-3.9.12\Lib\site-packages"
if package_path not in sys.path:
    sys.path.append(package_path)
from flask import Flask, jsonify, request
from flask_cors import CORS
import csv
import os

app = Flask(__name__)
CORS(app)  # 啟用跨域請求

@app.get("/menu-items")
def get_menu_items():
    sidebarlist = ['K11', 'K25']
    return [{"name": f"{sidebarlist[i]}"} for i in range(len(sidebarlist))]



@app.get("/card-data/<string:location>")
def get_card_data(location: str):
    # 構建文件路徑
    filepath = f"source/K11/K11-8F.csv"

    # 初始化數據結構
    data = []
    try:
        # 檢查文件是否存在
        if not os.path.exists(filepath):
            return jsonify({"error": f"File not found: {filepath}"}), 404

        # 打開文件並讀取內容
        with open(filepath, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)  # 使用 DictReader 確保標題行對應字典鍵
            print("CSV file headers:", csv_reader.fieldnames)  # 打印 CSV 標題行
            for row in csv_reader:
                ip = row['ip']
                status = row['status']
                data.append({"ip": ip, "status": status})
        

    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500

    # 返回數據
    print(data)
    return jsonify(data)


@app.post("/update-status/<string:ip>")
def update_status(ip: str):
    try:

        location = request.json.get('location')  # 假設前端傳遞 location
        print(location)
        filepath = f"source/{location}/{location}-8F.csv"  # 正確構建文件路徑
        # filepath = f"source/K11/K11-8F.csv"
        data = []
        updated = False

        # 讀取 CSV 文件
        with open(filepath, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if row["ip"] == ip:
                    row["status"] = request.json.get("status")  # 更新狀態
                    updated = True
                data.append(row)

        # 如果沒有找到 IP，返回錯誤
        if not updated:
            return jsonify({"error": "IP not found"}), 404

        # 將更新後的數據寫回文件
        with open(filepath, 'w', encoding='utf-8', newline='') as file:
            fieldnames = ["ip", "status"]
            csv_writer = csv.DictWriter(file, fieldnames=fieldnames)
            csv_writer.writeheader()
            csv_writer.writerows(data)

        return jsonify({"message": "Status updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(debug=True)
