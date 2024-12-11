import sys
# 更換
package_path = r".\python-3.9.12\Lib\site-packages"
if package_path not in sys.path:
    sys.path.append(package_path)
from flask import Flask, jsonify
from flask_cors import CORS


app = Flask(__name__)
CORS(app)  # 啟用跨域請求

@app.get("/menu-items")
def get_menu_items():
    return [{"name": f"Menu Item {i + 1}"} for i in range(50)]

@app.get("/card-data/<int:card_number>")
def get_card_data(card_number: int):
    statuses = ["Active", "Inactive", "Error", "Pending"]
    data = []
    for i in range(4):
        table = []
        for j in range(15):
            ip = f"192.168.{card_number}.{i * 15 + j + 1}"
            status = statuses[j % len(statuses)]
            table.append({"ip": ip, "status": status})
        data.append(table)
    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)
