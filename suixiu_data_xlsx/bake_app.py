# import pandas as pd

# file_path = r"2026_自動化復機率回報_(Security C).xlsx"
# sheet_name = "妥善率(K18.K21.K25 不停電)"

# df = pd.read_excel(file_path, sheet_name=sheet_name)

# # 移除完全空白列
# df_valid = df.dropna(how="all")

# print("📊 工作表：", sheet_name)
# print("✅ 有效資料筆數：", len(df_valid))
# print("📐 欄位數：", len(df_valid.columns))
# print("🧾 欄位名稱：", list(df_valid.columns))
# print("=" * 80)

# print(df_valid)


import json
import os

JSON_PATHS = {
    "ASEF1": r"\\20220530-W03\data\EAP_Health_level\source\ASEF1.json",
    "ASEF3": r"\\20220530-W03\data\EAP_Health_level\source\ASEF3.json",
    "ASEF5": r"\\20220530-W03\data\EAP_Health_level\source\ASEF5.json",
}


def collect_status(obj):
    result = []
    if isinstance(obj, dict):
        for v in obj.values():
            result.extend(collect_status(v))
    elif isinstance(obj, list):
        for i in obj:
            result.extend(collect_status(i))
    elif isinstance(obj, str):
        result.append(obj.strip().upper())
    return result


def calc_v_percent(status_list):
    total = len(status_list)
    if total == 0:
        return 0.0
    v_cnt = sum(1 for s in status_list if s == "V")
    return round(v_cnt / total * 100, 2)


# ===== 只為了這三個變數 =====
ASEF1_ALL_V = None
ASEF3_ALL_V = None
ASEF5_ALL_V = None


for name, path in JSON_PATHS.items():
    if not os.path.exists(path):
        continue

    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    all_status = collect_status(data)
    all_v = calc_v_percent(all_status)

    if name == "ASEF1":
        ASEF1_ALL_V = all_v
    elif name == "ASEF3":
        ASEF3_ALL_V = all_v
    elif name == "ASEF5":
        ASEF5_ALL_V = all_v


# ===== 只做 print =====
print(f"ASEF1 ALL V% : {ASEF1_ALL_V}%")
print(f"ASEF3 ALL V% : {ASEF3_ALL_V}%")
print(f"ASEF5 ALL V% : {ASEF5_ALL_V}%")


