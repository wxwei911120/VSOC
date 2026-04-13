import pandas as pd

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
