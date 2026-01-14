from flask import Flask, jsonify, send_file, request
from flask_cors import CORS
import pandas as pd
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/timeline-data')
def get_timeline_data():
    # 讀取 CSV
    df_all = pd.read_csv('machine_status.csv')
    df_all['received_at'] = pd.to_datetime(df_all['received_at'])
    
    # 獲取時間範圍參數
    days = request.args.get('days', type=int)
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    
    # 記錄篩選範圍
    filter_start = None
    filter_end = None
    
    # 根據參數設定篩選範圍
    if start_date and end_date:
        # 自訂時間範圍
        filter_start = pd.to_datetime(start_date)
        filter_end = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    elif days:
        # 快速選擇（N天前到現在）
        filter_start = pd.Timestamp.now() - pd.Timedelta(days=days)
        filter_end = pd.Timestamp.now()
    else:
        # 預設24小時
        filter_start = pd.Timestamp.now() - pd.Timedelta(days=1)
        filter_end = pd.Timestamp.now()
    
    # 統一 station 名稱
    df_all['station'] = df_all['station'].str.replace('K21_8F', 'K21-8F')
    df_all = df_all.sort_values(['station', 'received_at'])
    
    # 建立狀態區間數據
    timeline_data = []
    
    for station in df_all['station'].unique():
        station_df = df_all[df_all['station'] == station].reset_index(drop=True)
        
        # 找出在範圍內的記錄
        in_range = station_df[
            (station_df['received_at'] >= filter_start) & 
            (station_df['received_at'] <= filter_end)
        ].reset_index(drop=True)
        
        if len(in_range) == 0:
            # 如果範圍內沒有記錄，找最後一筆早於範圍的記錄
            before_range = station_df[station_df['received_at'] < filter_start]
            if len(before_range) > 0:
                last_before = before_range.iloc[-1]
                # 用這個狀態填充整個範圍
                timeline_data.append({
                    'station': station,
                    'status': last_before['status'],
                    'start': filter_start.isoformat(),
                    'end': filter_end.isoformat(),
                    'duration_minutes': round((filter_end - filter_start).total_seconds() / 60, 2)
                })
            continue
        
        # 處理第一筆記錄之前的時間段
        first_record = in_range.iloc[0]
        if first_record['received_at'] > filter_start:
            # 找前一筆記錄的狀態
            before_range = station_df[station_df['received_at'] < filter_start]
            if len(before_range) > 0:
                last_before = before_range.iloc[-1]
                # 從範圍開始到第一筆記錄，使用前一個狀態
                timeline_data.append({
                    'station': station,
                    'status': last_before['status'],
                    'start': filter_start.isoformat(),
                    'end': first_record['received_at'].isoformat(),
                    'duration_minutes': round((first_record['received_at'] - filter_start).total_seconds() / 60, 2)
                })
        
        # 處理範圍內的記錄
        for i in range(len(in_range)):
            start_time = in_range.loc[i, 'received_at']
            status = in_range.loc[i, 'status']
            
            # 結束時間
            if i < len(in_range) - 1:
                end_time = in_range.loc[i + 1, 'received_at']
            else:
                # 最後一筆記錄：檢查是否有更晚的記錄
                after_records = station_df[station_df['received_at'] > start_time]
                if len(after_records) > 0:
                    end_time = min(after_records.iloc[0]['received_at'], filter_end)
                else:
                    end_time = filter_end
            
            # 確保不超出範圍
            if end_time > filter_end:
                end_time = filter_end
            
            timeline_data.append({
                'station': station,
                'status': status,
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'duration_minutes': round((end_time - start_time).total_seconds() / 60, 2)
            })
    
    return jsonify(timeline_data)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)