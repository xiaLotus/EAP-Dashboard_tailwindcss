# import pandas as pd

# # 读取 XLS 文件
# xls_file = 'EAP PC_(Security B).xls'
# df = pd.read_excel(xls_file)

# # 保存为 CSV
# csv_file = 'EAP PC_(Security B).csv'
# df.to_csv(csv_file, index=False, encoding='utf-8-sig')

# print(f"✓ 转换完成！")
# print(f"原始文件: {xls_file}")
# print(f"输出文件: {csv_file}")
# print(f"\n数据信息:")
# print(f"总行数: {len(df)}")
# print(f"总列数: {len(df.columns)}")
# print(f"\n数据预览 (前5行):")
# print(df.head())

import pandas as pd

# 读取两个 CSV 文件
eap_file = 'EAP PC_(Security B).csv'
suixiu_file = 'suixiu.csv'

eap_df = pd.read_csv(eap_file)
suixiu_df = pd.read_csv(suixiu_file)

# 提取电脑名称列
eap_names = set(eap_df['電腦名稱'].dropna().astype(str).str.strip())
suixiu_names = set(suixiu_df['Device_Name'].dropna().astype(str).str.strip())

# 找出三种分类
only_in_eap = sorted(eap_names - suixiu_names)
only_in_suixiu = sorted(suixiu_names - eap_names)
common = sorted(eap_names & suixiu_names)

# 创建三个 CSV 文件
# 1. 只在 EAP 中的
eap_only_df = pd.DataFrame({
    '设备名称': only_in_eap,
    '备注': ['仅在EAP文件中'] * len(only_in_eap)
})
eap_only_df.to_csv('1_只在EAP中的设备.csv', index=False, encoding='utf-8-sig')

# 2. 只在 SUIXIU 中的
suixiu_only_df = pd.DataFrame({
    '设备名称': only_in_suixiu,
    '备注': ['仅在SUIXIU文件中'] * len(only_in_suixiu)
})
suixiu_only_df.to_csv('2_只在SUIXIU中的设备.csv', index=False, encoding='utf-8-sig')

# 3. 共有的
common_df = pd.DataFrame({
    '设备名称': common,
    '备注': ['两个文件都有'] * len(common)
})
common_df.to_csv('3_共有的设备.csv', index=False, encoding='utf-8-sig')

print(f"=== 分类统计 ===")
print(f"1. 只在 EAP 中的设备: {len(only_in_eap)} 台")
print(f"2. 只在 SUIXIU 中的设备: {len(only_in_suixiu)} 台")
print(f"3. 共有的设备: {len(common)} 台")
print(f"\n总计: {len(only_in_eap) + len(only_in_suixiu) + len(common)} 台")
print(f"\n✓ 已生成三个 CSV 文件")