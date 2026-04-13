import requests
import pandas as pd  # 引入 pandas 庫來處理數據

# 設置 API 基礎 URL
BASE_URL = "http://localhost:5000/api"

# 測試 HTTP API 並保存數據為 CSV
def test_http_api():
    fields = [
        "vehicle_speed", "datetime", "altitude", "battery", 
        "engine_rpm", "air_flow_rate_maf", "throttle_position", "intake_air_temp", 
        "engine_coolant_temp", "cardata"
    ]

    for field in fields:
        endpoint = f"{BASE_URL}/{field}"
        
        # 測試無參數請求
        response = requests.get(endpoint)
        print(f"Testing {field} :", response.status_code)

        if response.status_code == 200:
            data = response.json()
            # 檢查數據是否為空
            if data:
                # 將 JSON 數據轉換為 DataFrame
                df = pd.DataFrame(data)
                
                # 設置 CSV 檔案名稱
                csv_file = f"{field.replace('/', '_')}.csv"
                
                # 將 DataFrame 保存為 CSV 檔案
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                print(f"Data saved to {csv_file}")
            else:
                print(f"No data found for {field}")
        print()

if __name__ == "__main__":
    print("Testing HTTP API...")
    test_http_api()

##import pandas as pd

# 定義CSV檔案的路徑
file_paths = [
    "vehicle_speed.csv",
    "datetime.csv",
    "altitude.csv",
    "battery.csv",
    "engine_rpm.csv",
    "engine_coolant_temp.csv",
    "cardata.csv",
    "air_flow_rate_maf.csv",
    "throttle_position.csv",
    "intake_air_temp.csv"
]

# 讀取CSV檔案並在時間欄位上合併
dfs = [pd.read_csv(file_path) for file_path in file_paths]

# 假設時間欄位是每個CSV的第一欄
merged_df = dfs[0]
for df in dfs[1:]:
    merged_df = pd.merge(merged_df, df, on=merged_df.columns[0])

# 儲存合併後的資料為新的CSV檔案
output_path = "realcar.vehicle_data.csv"
merged_df.to_csv(output_path, index=False)