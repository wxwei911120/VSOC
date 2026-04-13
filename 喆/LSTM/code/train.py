import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout
from keras.callbacks import EarlyStopping
from dateutil import parser
import re

# 前置作業：載入資料
csv_file_path = 'realcar.vehicle_data.csv'
df = pd.read_csv(csv_file_path, encoding='utf-8')

# 使用 'timestamp' 欄位來計算相鄰資料的時間差（秒）
df['Time_diff'] = df['timestamp'].diff() / 1000  # 將毫秒轉換為秒

# 使用 'vehicle_speed' 欄位來計算相鄰資料的速度差（km/h）
df['Speed_diff'] = df['vehicle_speed'].diff()

# 計算加速度：Speed_diff / Time_diff (km/h/s)
df['ACC'] = df['Speed_diff'] / df['Time_diff']

# 將第一筆 NaN 的 ACC 值設為 0（保留所有資料）
df['ACC'].fillna(0, inplace=True)

# 加入異常標籤
def classify_anomaly(row):
    """根據速度、加速度與引擎狀態標記不同的狀態"""
    if row['vehicle_speed'] == 0 and row['engine_rpm'] > 600:
        return '怠速'
    elif row['engine_coolant_temp'] >= 90 and row['engine_rpm'] > 600:
        return '冷卻水溫過高'
    elif row['vehicle_speed'] > 70 and row['ACC'] > 3:
        return '高速急加速'
    elif 40 < row['vehicle_speed'] <= 70 and row['ACC'] > 5:
        return '中度急加速'
    elif row['vehicle_speed'] >= 10 and row['ACC'] < -5:
        return '低速急煞車'
    elif row['vehicle_speed'] >= 107:
        return '超速(法規)'
    elif row['ACC'] < -12:
        return '緊急急煞車'
    elif row['vehicle_speed'] > 70 and row['ACC'] < -10:
        return '重度急煞車'
    elif 40 < row['vehicle_speed'] <= 70 and row['ACC'] < -8:
        return '中度急煞車'
    elif row['vehicle_speed'] < 40 and row['ACC'] < -5:
        return '輕度急煞車'
    else:
        return ''

# 應用標籤規則
df['anomaly'] = df.apply(classify_anomaly, axis=1)

# 移除 'Time_diff'、'Speed_diff' 和 'ACC' 欄位
df = df.drop(columns=['Time_diff', 'Speed_diff', 'ACC'])

# 儲存新的 DataFrame 至當前執行程式的資料夾中，檔名為 "vehicle_data_with_anomaly.csv"
output_file_path = "vehicle_data_with_anomaly.csv"
df.to_csv(output_file_path, index=False, encoding='utf-8-sig')

# 顯示儲存成功的訊息
print(f"新的CSV檔案已儲存至當前執行程式的資料夾中，檔名為: {output_file_path}")

# 需要訓練的欄位
columns_of_interest = [
    'battery', 'engine_rpm', 'vehicle_speed', 
    'air_flow_rate_maf', 'throttle_position', 
    'intake_air_temp', 'engine_coolant_temp'
]

# 定義模型參數
time_steps = 10
epochs = 50
batch_size = 32

# 為每個欄位建立一個獨立的模型
for column in columns_of_interest:
    print(f"Training model for: {column}")

    # 取出單一欄位進行訓練
    single_data = df[[column]]

    # 標準化資料
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(single_data)

    # 準備 LSTM 訓練資料
    X, y = [], []
    for i in range(time_steps, len(scaled_data)):
        X.append(scaled_data[i-time_steps:i])
        y.append(scaled_data[i])
    X, y = np.array(X), np.array(y)

    # 資料分割成訓練和測試集
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # 建立 LSTM 模型
    model = Sequential()
    model.add(LSTM(units=50, return_sequences=True, input_shape=(X_train.shape[1], X_train.shape[2])))
    model.add(Dropout(0.2))
    model.add(LSTM(units=50, return_sequences=False))
    model.add(Dropout(0.2))
    model.add(Dense(units=1))  # 單一輸出

    # 編譯模型
    model.compile(optimizer='adam', loss='mean_squared_error')

    # 使用 EarlyStopping 進行訓練
    early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)
    model.fit(X_train, y_train, validation_split=0.2, epochs=epochs, batch_size=batch_size, callbacks=[early_stop])

    # 保存模型
    model_filename = f"{column}_model.h5"
    model.save(model_filename)
    print(f"Model for {column} saved as {model_filename}")
