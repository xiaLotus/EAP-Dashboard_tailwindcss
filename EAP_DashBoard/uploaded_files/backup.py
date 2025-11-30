
# # 讀取CSV檔案並返回處理過的數據    
# def read_csv_file_with_pandas(file_path):
#     """使用 pandas 讀取 CSV 檔案並返回處理過的數據"""
#     try:
#         # 讀取 CSV 檔案
#         df = pd.read_csv(file_path, encoding='utf-8-sig', dtype=str)

#         # 過濾掉 Internal_IP 為 '0' 的行
#         df = df[df['Internal_IP'] != '0']

#         df = df.fillna('')

#         # 選擇需要的列，並將每一行轉換為字典
#         data = df[['Internal_IP', 'Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port', 
#                    'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time', 'Remark', 
#                    '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']].to_dict(orient='records')

#         # 將欄位名稱轉換為需要的格式
#         for row in data:
#             row['ip'] = row.pop('Internal_IP')
#             row['machine_id'] = row.pop('Machine_ID')
#             row['local'] = row.pop('Local')
#             row['device_name'] = row.pop('Device_Name')
#             row['tcp_port'] = row.pop('TCP_Port')
#             row['com_port'] = row.pop('COM_Port')
#             row['os_spec'] = row.pop('OS_Spec')
#             row['ip_source'] = row.pop('IP_Source')
#             row['category'] = row.pop('Category')
#             row['online_test'] = row.pop('Online_Test')
#             row['set_time'] = row.pop('Set_Time')
#             row['remark'] = row.pop('Remark')
#             row['suixiu'] = row.pop('歲修')
#             row['File_Place'] = row.pop('File_Place')
#             row['Column_Position'] = row.pop('所在區域(柱位)')
#             row['status'] = row.pop('alive_or_dead')

#         return data

#     except Exception as e:
#         print(f"Error reading file: {e}")
#         return None


# # 針對更新 csv 原始表，比如 【K18-9F 區網(41)】 or【其他 區網(10)】
# def update_csv(filepath: str, ip: str, machine_id: str, local: str, device_name: str, tcp_port: str, com_port: str, 
#                 os_spec: str, ip_source: str, category: str, online_test: str, set_time: str, remark: str, 
#                 suixiu: str, file_place: str, Column_Position: str, status: str):
#     """針對更新 csv 原始表，比如 【K18-9F 區網(41)】 or【其他 區網(10)】"""
#     df = pd.read_csv(filepath, encoding='utf-8-sig', dtype=str)
#     df = df.apply(lambda x: x.fillna(''), axis=0)
#     # 確保 'Internal_IP' 列是字符串型，並將空值轉換為 NaN
#     df['Internal_IP'] = df['Internal_IP'].astype(str)
#     df['Machine_ID'] = df['Machine_ID'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Local'] = df['Local'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Device_Name'] = df['Device_Name'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['TCP_Port'] = df['TCP_Port'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['COM_Port'] = df['COM_Port'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['OS_Spec'] = df['OS_Spec'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['IP_Source'] = df['IP_Source'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Category'] = df['Category'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Online_Test'] = df['Online_Test'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Set_Time'] = df['Set_Time'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Remark'] = df['Remark'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['歲修'] = df['歲修'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['File_Place'] = df['File_Place'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['所在區域(柱位)'] = df['所在區域(柱位)'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['alive_or_dead'] = df['alive_or_dead'].apply(lambda x: str(x) if pd.notna(x) else '')
#     # 如果 IP 是 0.0.0.0，使用 Machine_ID 和 Device_Name 作為更新條件
#     if ip == "0.0.0.0":
#         df.loc[(df['Machine_ID'] == machine_id) & (df['Device_Name'] == device_name), 
#                ['Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port',
#                 'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time',
#                 'Remark', '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']] = \
#             [str(machine_id), str(local), str(device_name), str(tcp_port), str(com_port), str(os_spec), 
#              str(ip_source), str(category), str(online_test), str(set_time), str(remark), str(suixiu), 
#              str(file_place), str(Column_Position), str(status)]    
#     # 更新 IP 相對應的行`
#     else:
#         df.loc[df['Internal_IP'] == ip, ['Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port',
#                                             'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time',
#                                             'Remark', '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']] = \
#                 [str(machine_id), str(local), str(device_name), str(tcp_port), str(com_port), str(os_spec), 
#                 str(ip_source), str(category), str(online_test), str(set_time), str(remark), str(suixiu), 
#                 str(file_place), str(Column_Position), str(status)]

#     # 檢查是否成功更新
#     if df[df['Internal_IP'] == ip].empty:
#         return jsonify({"error": "IP not found"}), 404

#     # 將更新後的數據寫回 CSV 文件
#     df.to_csv(filepath, index=False, encoding='utf-8-sig')

#     return None

# # 針對更新 其他表
# def update_another_csv(filepath: str, ip: str, machine_id: str, local: str, device_name: str, tcp_port: str, com_port: str, 
#                 os_spec: str, ip_source: str, category: str, online_test: str, set_time: str, remark: str, 
#                 suixiu: str, file_place: str, Column_Position: str, status: str):
#     df = pd.read_csv(filepath, encoding='utf-8-sig', dtype=str)
#     df = df.apply(lambda x: x.fillna(''), axis=0)
#     # 確保 'Internal_IP' 列是字符串型，並將空值轉換為 NaN
#     df['Internal_IP'] = df['Internal_IP'].astype(str)
#     df['Machine_ID'] = df['Machine_ID'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Local'] = df['Local'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Device_Name'] = df['Device_Name'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['TCP_Port'] = df['TCP_Port'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['COM_Port'] = df['COM_Port'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['OS_Spec'] = df['OS_Spec'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['IP_Source'] = df['IP_Source'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Category'] = df['Category'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Online_Test'] = df['Online_Test'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Set_Time'] = df['Set_Time'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['Remark'] = df['Remark'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['歲修'] = df['歲修'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['File_Place'] = df['File_Place'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['所在區域(柱位)'] = df['所在區域(柱位)'].apply(lambda x: str(x) if pd.notna(x) else '')
#     df['alive_or_dead'] = df['alive_or_dead'].apply(lambda x: str(x) if pd.notna(x) else '')
#                 # 檢查是否需要新增行
#     if df[(df['Device_Name'] == device_name)].empty:
#                 new_row = {
#                             'Internal_IP': str(ip),
#                             'Machine_ID': str(machine_id),
#                             'Local': str(local),
#                             'Device_Name': str(device_name),
#                             'TCP_Port': str(tcp_port),
#                             'COM_Port': str(com_port),
#                             'OS_Spec': str(os_spec),
#                             'IP_Source': str(ip_source),
#                             'Category': str(category),
#                             'Online_Test': str(online_test),
#                             'Set_Time': str(set_time),
#                             'Remark': str(remark),
#                             '歲修': str(suixiu),
#                             'File_Place': str(file_place),
#                             '所在區域(柱位)': str(Column_Position),
#                             'alive_or_dead': 'dead'
#                         }
#     df = pd.concat([df, pd.DataFrame([new_row], columns=df.columns)], ignore_index=True)
#     df.to_csv(filepath, index=False, encoding='utf-8-sig')

#     return jsonify({'其他: 10': 400})




# # 針對更新歲修原始表 suixiu.csv
# def suixiu_csv_update(suixiu_file_path: str, ip: str, machine_id: str, local: str, device_name: str, tcp_port: str, com_port: str, 
#                 os_spec: str, ip_source: str, category: str, online_test: str, set_time: str, remark: str, 
#                 suixiu: str, file_place: str, Column_Position: str, status: str, BASE_DIRECTORY):
#     """針對更新歲修原始表 suixiu.csv"""
#     if suixiu == 'Y':
#         suixiu_df = pd.read_csv(suixiu_file_path, encoding='utf-8-sig', dtype=str)
#         suixiu_df = suixiu_df.apply(lambda x: x.fillna(''), axis=0)
#         # 確保 'Internal_IP' 列是字符串型
#         suixiu_df['Internal_IP'] = suixiu_df['Internal_IP'].astype(str)

#         # 更新 歲修 表
#         if ip == "0.0.0.0":
#             suixiu_df.loc[(suixiu_df['Machine_ID'] == machine_id) & (suixiu_df['Device_Name'] == device_name), 
#                 ['Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port',
#                     'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time',
#                     'Remark', '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']] = \
#                 [str(machine_id), str(local), str(device_name), str(tcp_port), str(com_port), str(os_spec), 
#                 str(ip_source), str(category), str(online_test), str(set_time), str(remark), str(suixiu), 
#                 str(file_place), str(Column_Position), str(status)]    
#         # 更新 IP 相對應的行`
#         else:
#             suixiu_df.loc[suixiu_df['Internal_IP'] == ip, ['Machine_ID', 'Local', 'Device_Name', 'TCP_Port', 'COM_Port',
#                                                 'OS_Spec', 'IP_Source', 'Category', 'Online_Test', 'Set_Time',
#                                                 'Remark', '歲修', 'File_Place', '所在區域(柱位)', 'alive_or_dead']] = \
#                     [str(machine_id), str(local), str(device_name), str(tcp_port), str(com_port), str(os_spec), 
#                     str(ip_source), str(category), str(online_test), str(set_time), str(remark), str(suixiu), 
#                     str(file_place), str(Column_Position), str(status)]

#         # 檢查是否存在需要新增的行
#         if ip == "0.0.0.0":
#             # 檢查是否需要新增行
#             if suixiu_df[(suixiu_df['Machine_ID'] == machine_id) & (suixiu_df['Device_Name'] == device_name)].empty:
#                 new_row = {
#                             'Internal_IP': str(ip),
#                             'Machine_ID': str(machine_id),
#                             'Local': str(local),
#                             'Device_Name': str(device_name),
#                             'TCP_Port': str(tcp_port),
#                             'COM_Port': str(com_port),
#                             'OS_Spec': str(os_spec),
#                             'IP_Source': str(ip_source),
#                             'Category': str(category),
#                             'Online_Test': str(online_test),
#                             'Set_Time': str(set_time),
#                             'Remark': str(remark),
#                             '歲修': str(suixiu),
#                             'File_Place': str(file_place),
#                             '所在區域(柱位)': str(Column_Position),
#                             'alive_or_dead': 'dead'
#                         }
#                 suixiu_df = pd.concat([suixiu_df, pd.DataFrame([new_row], columns=suixiu_df.columns)], ignore_index=True)
#         else:
#             # 檢查 IP 相對應的行是否存在
#             if suixiu_df[suixiu_df['Internal_IP'] == ip].empty:
#                 new_row = {
#                             'Internal_IP': str(ip),
#                             'Machine_ID': str(machine_id),
#                             'Local': str(local),
#                             'Device_Name': str(device_name),
#                             'TCP_Port': str(tcp_port),
#                             'COM_Port': str(com_port),
#                             'OS_Spec': str(os_spec),
#                             'IP_Source': str(ip_source),
#                             'Category': str(category),
#                             'Online_Test': str(online_test),
#                             'Set_Time': str(set_time),
#                             'Remark': str(remark),
#                             '歲修': str(suixiu),
#                             'File_Place': str(file_place),
#                             '所在區域(柱位)': str(Column_Position),
#                             'alive_or_dead': 'dead' 
#                         }
#                 suixiu_df = pd.concat([suixiu_df, pd.DataFrame([new_row], columns=suixiu_df.columns)], ignore_index=True)


#         suixiu_df.to_csv(suixiu_file_path, index=False, encoding='utf-8-sig')

#     elif suixiu in ["N", ""] :
#         suixiu_file_path = f'{BASE_DIRECTORY}\suixiu.csv'
#         suixiu_df = pd.read_csv(suixiu_file_path, encoding='utf-8-sig')
#         suixiu_df = suixiu_df.apply(lambda x: x.fillna(''), axis=0)
#         # 確保 'Internal_IP' 列是字符串型
#         suixiu_df['Internal_IP'] = suixiu_df['Internal_IP'].astype(str)
#         if ip == "0.0.0.0":
#             suixiu_df = suixiu_df[~((suixiu_df['Machine_ID'] == machine_id) & (suixiu_df['Device_Name'] == device_name))]
#             suixiu_df['alive_or_dead'] = 'dead'
#         else:
#             suixiu_df = suixiu_df[suixiu_df['Internal_IP'] != ip]
#         suixiu_df.to_csv(suixiu_file_path, index=False, encoding='utf-8-sig')
    
#     return None



# def update_for_simple(target_file, file_name_without_extension):
#     try:
#         os.makedirs(f"{file_name_without_extension}", exist_ok=True)
#         # 這邊把舊檔案移進這個資料夾

#         file_name = os.path.basename(target_file)

#         # print(f"target_folder: {target_file}, file_name_without_extension: {file_name_without_extension}")
#         # 讀取原檔案並寫入新檔案
#         with open(target_file, 'r', encoding='utf-8') as src_file:
#             content = src_file.read()

#         # 在新資料夾內創建新的 CSV 檔案並寫入內容
#         new_file_path = os.path.join(file_name_without_extension, f'{file_name}')
#         with open(new_file_path, 'w', encoding='utf-8') as dest_file:
#             dest_file.write(content)
#         # 取得目前的日期時間，並格式化為 yyyymmdd_hhmmss
#         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#         # 組合新的檔案名稱
#         new_file_name = f"{timestamp}_{os.path.basename(file_name)}"
#         new_file_path_with_timestamp = os.path.join(file_name_without_extension, new_file_name)
#         os.rename(new_file_path, new_file_path_with_timestamp)

#     except Exception as e:
#         print(e)

# def update_for_suixiu():
#     # 檢查是否資料夾存在
#     os.makedirs(f"{BASE_DIRECTORY}\\backup_suixiu", exist_ok=True)
#     # 先複製一份到備份資料夾
#     with open(f"{BASE_DIRECTORY}\\suixiu.csv", 'r', encoding='utf-8') as src_file:
#         content = src_file.read()
#         new_file_path = os.path.join(f"{BASE_DIRECTORY}\\backup_suixiu", f"suixiu.csv")

#     with open(new_file_path, 'w', encoding='utf-8') as dest_file:
#         dest_file.write(content)
#     # 取得目前的日期時間，並格式化為 yyyymmdd_hhmmss

#     timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
#     # 組合新的檔案名稱
#     new_file_name = f"{timestamp}_suixiu.csv"


#     new_file_path_with_timestamp = os.path.join(f"{BASE_DIRECTORY}\\backup_suixiu", new_file_name)
    
#     os.rename(new_file_path, new_file_path_with_timestamp)
#     print(f"{new_file_path} 改名成 {new_file_path_with_timestamp}")

#     # 移動 uploaded_files\\suixiu.csv 到 BASE_DIRECTORY
#     if os.path.exists(f"uploaded_files\\suixiu.csv"):
#         try:
#             shutil.move(f"uploaded_files\\suixiu.csv", f"{BASE_DIRECTORY}\\suixiu.csv")
#             print(f"uploaded_files\\suixiu.csv 已移動到 {BASE_DIRECTORY}\\suixiu.csv")
#         except Exception as e:
#             print(f"移動 uploaded_files\\suixiu.csv 時發生錯誤: {e}")
#     else:
#         print(f"uploaded_files\\suixiu.csv 不存在")


# @app.route('/upload', methods=['POST'])
# def upload_files():
#     if 'files' not in request.files:
#         return jsonify({"error": "沒有檔案部分"}), 400

#     files = request.files.getlist('files')

#     if len(files) == 0:
#         return jsonify({"error": "未選擇任何檔案"}), 400

#     saved_files = []

#     for file in files:
#         if file and allowed_file(file.filename):
#             filename = file.filename
#             file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

#             file_ext = filename.rsplit('.', 1)[1].lower()
#             saved_files.append(filename)
#             # 檢查資料夾是否存在
#             try:
#                 if file.filename not in ["歲修_(Security C).csv", "歲修_(Security C).xlsx", 'suixiu.csv']:
#                     # 1. 提取資料夾名稱部分，這裡假設我們只需要 'K18-10F'
#                     folder_name = filename.split(' ')[0]  # 取得檔案名中的 'K18-10F' 部分
#                     print("folder_name: ", folder_name)

#                     # 2. 用 "-" 分割 'K18-10F'，並組合成 'K18\\10F' 格式
#                     folder_parts = folder_name.split('-')
#                     folder_path = os.path.join('static', 'source', folder_parts[0], folder_parts[1])  # 組成資料夾路徑
#                     # 3. 檢查資料夾是否存在，如果不存在則創建
#                     if not os.path.exists(folder_path):
#                         try:
#                             os.makedirs(folder_path)  # 創建資料夾
#                             print(f"資料夾 {folder_path} 已創建。")
#                         except Exception as e:
#                             print(f"創建資料夾時發生錯誤: {e}")
#                     else:
#                         print(f"資料夾 {folder_path} 已經存在。")
#             except Exception as e:
#                 print(e)

#             try:
#                 if file.filename not in ["歲修_(Security C).csv", "歲修_(Security C).xlsx", 'suixiu.csv']:
#                     # print(f"檔案名稱 {filename} 符合條件，可以進一步處理")

#                     if file_ext == 'csv':
#                         df = pd.read_csv(f"{UPLOAD_FOLDER}\{filename}")
#                     elif file_ext == 'xlsx':
#                         df = pd.read_excel(f"{UPLOAD_FOLDER}\{filename}")

#                     # 檢查是否有 File_Place 欄位
#                     if 'File_Place' in df.columns:
#                         # 取得 File_Place 欄位的第一個值
#                         file_place_value = df['File_Place'].iloc[0]
#                         # print(f"File_Place 第一個路徑: {file_place_value}")
#                         check_old_path = f"{BASE_DIRECTORY}\{file_place_value}"
#                         file_name_without_extension, _ = os.path.splitext(check_old_path)
#                         # print(file_name_without_extension)
#                         target_folder = os.path.join(BASE_DIRECTORY, file_place_value)
#                         update_for_simple(target_folder, file_name_without_extension)
#                         # print(target_folder, filename)


#                         try:
#                             os.remove(target_folder)
#                         except Exception as e:
#                             print(f"刪除檔案時發生錯誤: {e}")
#                         # 轉移file資料
#                         try:
#                             # 取得檔案所在的資料夾路徑
#                             folder_path = os.path.dirname(target_folder)
#                             print('複製一份資料進入 File_Place -> 轉移')
#                             shutil.move(f"uploaded_files\\{filename}", f"{folder_path}\\{filename}")
#                             print(f"檔案 {filename} 已經從 uploaded_files\\{filename} 移動到 {folder_path}\\{filename}")

                            

#                         except Exception as e:
#                             print(f"刪除檔案時發生錯誤: {e}")



#                     else:
#                         print("檔案中找不到 'File_Place' 欄位")
#                 else:
#                     if file.filename in ["歲修_(Security C).csv", "歲修_(Security C).xlsx", 'suixiu.csv']:
#                         os.rename(f"uploaded_files\\{file.filename}", f'uploaded_files\\suixiu.csv')
#                         try:
#                             print("傳入並更新")
#                             update_for_suixiu()
#                             # os.remove(f'uploaded_files\\suixiu.csv')
                
#                         except Exception as e:
#                             print(e)

#             except Exception as e:
#                 print(f"處理檔案 {filename} 時發生錯誤: {e}")
#                 pass

#         else:
#             return jsonify({"error": f"檔案 {file.filename} 不允許的檔案類型"}), 400

#     return jsonify({"message": "檔案成功上傳", "files": saved_files}), 200






# @app.route('/delete-file', methods=['POST'])
# def delete_file():
#     data = request.get_json()
#     filename = data.get('filename')

#     if not filename:
#         return jsonify({"error": "未提供檔名"}), 400

#     print('要刪掉取消的檔案了。')
#     file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
#     print("file_path: ", file_path)
#     file_name = os.path.basename(file_path)
#     print("要取消上傳的檔案： ", file_name)
#     # 使用正則表達式來提取 K11 和 3F
#     pattern = r"([A-Za-z0-9]+)-([A-Za-z0-9]+)"
#     match = re.match(pattern, file_name)

#     if file_name not in ["歲修_(Security C).csv", "歲修_(Security C).xlsx", 'suixiu.csv', 'suixiu_(Security C).csv', '其他 區網(10).csv']:
#         if match:
#             unit = match.group(1)  # 例如 K11
#             floor = match.group(2)  # 例如 3F
#             print(f"提取到的部分：{unit}, {floor}")
#             print(f"完整檔案名稱：{file_name}")
#         else:
#             print("檔案名稱不符合預期的格式")

#         os.remove(f"{BASE_DIRECTORY}\{unit}\{floor}\{file_name}")
#         # 去除附檔名
#         name_without_extension, _ = os.path.splitext(file_name)
#         # shutil.move(f"uploaded_files\\{filename}", f"{folder_path}\\{filename}")
#         file_names = [f for f in os.listdir(os.path.join(f"{BASE_DIRECTORY}", f"{unit}", f'{floor}', f'{name_without_extension}'))]
#         # print(file_names)
#         # 取得目前時間
#         current_time = datetime.now()

#         # 變數初始化
#         closest_file = None
#         closest_time_diff = None

#         # 逐一處理每個檔案
#         for file_name in file_names:
#             # 確保檔案名稱符合預期格式 (以日期時間開頭)
#             if len(file_name) >= 15 and file_name[8] == '_':  # 假設檔案名稱至少有 15 字元並包含時間戳記
#                 # 提取檔案名稱中的時間戳記部分 (例如 "20250322_181611")
#                 timestamp_str = file_name[:15]  # 取前 15 字元，包含 "YYYYMMDD_HHMMSS"

#                 try:
#                     # 轉換時間戳記為 datetime 物件
#                     file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
#                     # 計算與現在時間的時間差
#                     time_diff = abs(current_time - file_time)
                    
#                     # 如果這是目前找到的最接近的檔案，則更新
#                     if closest_time_diff is None or time_diff < closest_time_diff:
#                         closest_time_diff = time_diff
#                         closest_file = file_name
#                 except ValueError:
#                     # 如果時間戳記格式不正確，跳過該檔案
#                     continue

#         # 顯示結果
#         if closest_file:
#             print(f"距離現在時間最近的檔案是: {closest_file}")
#             folder_path = f"{BASE_DIRECTORY}\\{unit}\\{floor}\\{name_without_extension}"
#             parent_folder = os.path.dirname(folder_path)
#             print(parent_folder)
#             # 目標路徑：將檔案移動到上一層資料夾
#             target_path = os.path.join(parent_folder, closest_file)
#             # 移動檔案
#             try:
#                 shutil.move(f"{folder_path}\\{closest_file}", target_path)
#                 print(f"檔案已移動到: {target_path}")
#                 closest_file_name = closest_file[16:]
#                 # 處理更換後的路徑
#                 closest_file_name_path = os.path.join(f"{BASE_DIRECTORY}\\{unit}\\{floor}\\{closest_file}")
#                 print(closest_file_name_path)

#                 os.rename(closest_file_name_path, f"{BASE_DIRECTORY}\\{unit}\\{floor}\\{closest_file_name}")
#             except Exception as e:
#                 print(f"移動檔案時發生錯誤: {e}")
#         else:
#             print("未找到檔案")

#     if file_name in ["歲修_(Security C).csv", "歲修_(Security C).xlsx", 'suixiu.csv', 'suixiu_(Security C).csv']:
#         file_names = [f for f in os.listdir(os.path.join(f"{BASE_DIRECTORY}", "backup_suixiu"))]
#         print("file_names -> ", file_names)
#         # os.remove(f"{BASE_DIRECTORY}\\suixiu.csv")
#         # 取得目前時間
#         current_time = datetime.now()

#         # 變數初始化
#         closest_file = None
#         closest_time_diff = None

#         # 逐一處理每個檔案
#         for file_name in file_names:
#             # 確保檔案名稱符合預期格式 (以日期時間開頭)
#             if len(file_name) >= 15 and file_name[8] == '_':  # 假設檔案名稱至少有 15 字元並包含時間戳記
#                 # 提取檔案名稱中的時間戳記部分 (例如 "20250322_181611")
#                 timestamp_str = file_name[:15]  # 取前 15 字元，包含 "YYYYMMDD_HHMMSS"

#                 try:
#                     # 轉換時間戳記為 datetime 物件
#                     file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
#                     # 計算與現在時間的時間差
#                     time_diff = abs(current_time - file_time)
                    
#                     # 如果這是目前找到的最接近的檔案，則更新
#                     if closest_time_diff is None or time_diff < closest_time_diff:
#                         closest_time_diff = time_diff
#                         closest_file = file_name
#                 except ValueError:
#                     # 如果時間戳記格式不正確，跳過該檔案
#                     continue
#         if closest_file:
#             print(f"距離現在時間最近的檔案是: {closest_file}")
#             os.rename(f"{BASE_DIRECTORY}\\backup_suixiu\\{closest_file}", f"{BASE_DIRECTORY}\\backup_suixiu\\suixiu.csv")
#             shutil.move(f"{BASE_DIRECTORY}\\backup_suixiu\\suixiu.csv", f"{BASE_DIRECTORY}\\suixiu.csv")
       


#     if file_name in ['其他 區網(10).csv']:
#         file_names = [f for f in os.listdir(os.path.join(f"{BASE_DIRECTORY}", "其他", '其他 區網(10)'))]
#         print("file_names -> ", file_names)
#         # os.remove(f"{BASE_DIRECTORY}\\suixiu.csv")
#         # 取得目前時間
#         current_time = datetime.now()

#         # 變數初始化
#         closest_file = None
#         closest_time_diff = None

#         # 逐一處理每個檔案
#         for file_name in file_names:
#             # 確保檔案名稱符合預期格式 (以日期時間開頭)
#             if len(file_name) >= 15 and file_name[8] == '_':  # 假設檔案名稱至少有 15 字元並包含時間戳記
#                 # 提取檔案名稱中的時間戳記部分 (例如 "20250322_181611")
#                 timestamp_str = file_name[:15]  # 取前 15 字元，包含 "YYYYMMDD_HHMMSS"

#                 try:
#                     # 轉換時間戳記為 datetime 物件
#                     file_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
#                     # 計算與現在時間的時間差
#                     time_diff = abs(current_time - file_time)
                    
#                     # 如果這是目前找到的最接近的檔案，則更新
#                     if closest_time_diff is None or time_diff < closest_time_diff:
#                         closest_time_diff = time_diff
#                         closest_file = file_name
#                 except ValueError:
#                     # 如果時間戳記格式不正確，跳過該檔案
#                     continue
#         if closest_file:
#             print(f"距離現在時間最近的檔案是: {closest_file}")
#             os.rename(f"{BASE_DIRECTORY}\\其他\\其他 區網(10)\\{closest_file}", f"{BASE_DIRECTORY}\\其他\\其他 區網(10)\\其他 區網(10).csv")
#             shutil.move(f"{BASE_DIRECTORY}\\其他\\其他 區網(10)\\其他 區網(10).csv", f"{BASE_DIRECTORY}\\其他\\其他 區網(10).csv")

#     if file_name:
#         return jsonify({"success": True}), 200

#     else:
#         return jsonify({"error": "檔案不存在"}), 404
