import pandas as pd
import os

def get_suixiu_y_from_folder(folder_path, output_file="all_suixiu_Y.csv"):
    """
    撈取指定資料夾下所有 CSV 檔案中，歲修=Y 的資料，合併寫入同一個 all_suixiu_Y.csv
    :param folder_path: 資料夾路徑
    :param output_file: 合併輸出檔案 (固定 all_suixiu_Y.csv)
    """
    all_data = []

    if not os.path.exists(folder_path):
        print(f"⚠️ 找不到路徑: {folder_path}")
        return

    csv_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".csv")]

    if not csv_files:
        print(f"⚠️ 在 {folder_path} 找不到 CSV 檔案")
        return

    for file in csv_files:
        file_path = os.path.join(folder_path, file)
        try:
            df = pd.read_csv(file_path, encoding="utf-8-sig")
        except UnicodeDecodeError:
            df = pd.read_csv(file_path, encoding="big5", errors="ignore") # type: ignore

        if "歲修" not in df.columns:
            continue

        df["歲修"] = df["歲修"].astype(str).str.upper().str.strip()
        df_y = df[df["歲修"] == "Y"].copy()

        if not df_y.empty:
            all_data.append(df_y)

    if all_data:
        result = pd.concat(all_data, ignore_index=True)

        new_count = len(result)  # 這次處理到的筆數

        # 如果 all_suixiu_Y.csv 已存在，就讀取舊的再合併
        if os.path.exists(output_file):
            old = pd.read_csv(output_file, encoding="utf-8-sig")
            old_count = len(old)
            result = pd.concat([old, result], ignore_index=True)
        else:
            old_count = 0

        result.to_csv(output_file, index=False, encoding="utf-8-sig")

        added_count = len(result) - old_count
        print(f"✅ 已更新 {output_file}，新增 {added_count} 筆，總共 {len(result)} 筆資料")
    else:
        print("⚠️ 沒有找到任何 歲修=Y 的資料")


# 使用範例
if __name__ == "__main__":
    root_path = r"C:\Users\K18251\Desktop\K18\source\其他"  # 這邊換路徑
    get_suixiu_y_from_folder(root_path, output_file="all_suixiu_Y.csv")


# import pandas as pd

# def update_all_suixiu(file_path, output_file=None):
#     """
#     把整份 CSV 裡的 歲修 欄位全部改成 Y
#     :param file_path: 原始 CSV 檔案
#     :param output_file: 輸出檔案，若為 None 則覆蓋原檔
#     """
#     # 讀取檔案
#     df = pd.read_csv(file_path, encoding="utf-8-sig")
    
#     # 將歲修欄位全部設為 Y
#     df["歲修"] = "Y"
    
#     # 輸出
#     if output_file is None:
#         output_file = file_path
    
#     df.to_csv(output_file, index=False, encoding="utf-8-sig")
#     print(f"✅ 已將所有『歲修』欄位更新為 Y，輸出檔案：{output_file}")

# # 使用範例
# if __name__ == "__main__":
#     file_path = r"C:\Users\K18251\Desktop\K18\source\其他\其他 區網(10).csv"
#     update_all_suixiu(file_path, output_file="其他 區網(10)_updated.csv")