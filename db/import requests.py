import asyncio
import socketio
import random
from datetime import datetime, timedelta
import json
import logging
import threading
import pytz
from tabulate import tabulate
from colorama import Fore, Style, init

init(autoreset=True)  # 初始化 colorama

class CustomFormatter(logging.Formatter):
    format_str = "%(asctime)s - %(levelname)s - %(message)s"

    FORMATS = {
        logging.DEBUG: Fore.CYAN + format_str + Style.RESET_ALL,
        logging.INFO: Fore.GREEN + format_str + Style.RESET_ALL,
        logging.WARNING: Fore.YELLOW + format_str + Style.RESET_ALL,
        logging.ERROR: Fore.RED + format_str + Style.RESET_ALL,
        logging.CRITICAL: Fore.RED + Style.BRIGHT + format_str + Style.RESET_ALL
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%Y-%m-%d %H:%M:%S")
        return formatter.format(record)

logger = logging.getLogger("VehicleDataLogger")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
ch.setFormatter(CustomFormatter())
logger.addHandler(ch)

sio = socketio.AsyncClient(logger=False, engineio_logger=False)
vehicle_data_storage = {}
is_running = True
send_data_event = asyncio.Event()

@sio.event
async def connect():
    logger.info("已連接到伺服器")

@sio.event
async def disconnect():
    logger.info("已從伺服器斷開連接")

@sio.event
def blockchainResult(data):
    result = json.loads(data)
    if result['success']:
        print(Fore.CYAN + "\n--- 區塊鏈交易結果 ---")
        
        # 計算最長的標籤長度
        max_label_length = max(len(label) for label in ["區塊 ID", "交易哈希", "區塊編號", "區塊哈希"])
        
        # 計算最長的值長度
        max_value_length = max(len(str(value)) for value in result.values() if isinstance(value, str))
        
        # 創建格式化字符串
        format_string = f"{{:<{max_label_length}}} : {{:<{max_value_length}}}"
        
        print(format_string.format("區塊 ID", result['blockId']))
        print(format_string.format("交易哈希", result['transactionHash']))
        print(format_string.format("區塊編號", result['blockNumber']))
        print(format_string.format("區塊哈希", result['blockHash']))
    else:
        logger.error(f"將數據存儲到區塊鏈時發生錯誤：{result['error']}")

def generate_vehicle_data():
    return {
        "datetime": datetime.now(pytz.UTC).isoformat(),
        "speed": random.randint(0, 200),
        "rpm": random.randint(0, 8000),
        "ect": random.randint(-50, 200),
        "iat": random.randint(-50, 200),
        "maf": random.randint(0, 1000),
        "map": random.randint(0, 500),
        "tps": random.randint(0, 100),
        "iaa": random.randint(0, 360),
        "el": random.randint(0, 100),
        "ftl": random.randint(0, 100),
        "gps": f"{random.uniform(-90, 90):.6f},{random.uniform(-180, 180):.6f}",
        "anomaly": "警告：高溫" if random.random() > 0.9 else ""
    }

async def connect_with_retry(max_retries=10, delay=5):
    for attempt in range(max_retries):
        try:
            await sio.connect('http://localhost:3000', transports=['websocket'])
            return True
        except Exception as e:
            logger.error(f"連接嘗試 {attempt + 1} 失敗：{str(e)}")
            if attempt < max_retries - 1:
                logger.info(f"{delay} 秒後重試...")
                await asyncio.sleep(delay)
            else:
                logger.error("達到最大重試次數。無法連接到伺服器。")
                return False

async def send_vehicle_data():
    while is_running:
        if send_data_event.is_set():
            vehicle_data = generate_vehicle_data()
            print(Fore.YELLOW + "\n--- 發送車輛數據 ---")
            print(tabulate(vehicle_data.items(), tablefmt="pretty"))
            
            try:
                result = await sio.call('vehicleData', vehicle_data, timeout=10)
                if result and result.get('success'):
                    timestamp = datetime.fromisoformat(vehicle_data['datetime'])
                    vehicle_data_storage[timestamp] = vehicle_data
                    logger.info(f"車輛數據已存儲，時間戳：{timestamp}")
                else:
                    logger.warning(f"發送數據失敗：{result.get('error', '未知錯誤')}")
            except Exception as e:
                logger.error(f"發送數據時發生錯誤：{str(e)}")
            
            await asyncio.sleep(5)
        else:
            await asyncio.sleep(1)

# 處理使用者輸入的函數
def user_input_handler():
    global is_running
    while is_running:
        command = input("輸入 'stop' 暫停發送數據，'start' 恢復發送，'query' 查詢數據，或 'exit' 退出程序: ").strip().lower()
        logger.info(f"接收到的命令: {command}")
        if command == 'stop':
            send_data_event.clear()
            print("數據發送已暫停")
        elif command == 'start':
            send_data_event.set()
            print("數據發送已恢復")
        elif command == 'query':
            query_data()
        elif command == 'exit':
            is_running = False
            send_data_event.set()  # 確保發送循環可以退出
            print("正在退出程序...")
        else:
            print("無效的命令")

# 解析日期時間字串
def parse_datetime(datetime_str):
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f"
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(datetime_str, fmt)
            return pytz.UTC.localize(dt)
        except ValueError:
            pass
    raise ValueError("無效的時間格式")

# 查詢數據
def query_data():
    while True:
        start_time = input("請輸入查詢開始時間 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD HH:MM:SS.mmmmmm): ")
        try:
            start_datetime = parse_datetime(start_time)
            break
        except ValueError:
            print("無效的時間格式，請重新輸入。")

    while True:
        end_time = input("請輸入查詢結束時間 (格式: YYYY-MM-DD HH:MM:SS 或 YYYY-MM-DD HH:MM:SS.mmmmmm): ")
        try:
            end_datetime = parse_datetime(end_time)
            if end_datetime < start_datetime:
                print("結束時間不能早於開始時間，請重新輸入。")
                continue
            break
        except ValueError:
            print("無效的時間格式，請重新輸入。")

    # 擴大查詢範圍，增加1秒的容差
    start_datetime -= timedelta(seconds=1)
    end_datetime += timedelta(seconds=1)

    filtered_data = {
        k: v for k, v in vehicle_data_storage.items()
        if start_datetime <= k <= end_datetime
    }

    if filtered_data:
        print(f"在 {start_time} 到 {end_time} 之間找到 {len(filtered_data)} 條記錄：")
        for timestamp, data in filtered_data.items():
            print(f"\n時間戳: {timestamp}")
            print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(f"在指定時間範圍內未找到數據")
    
    print(f"\n當前存儲的所有時間戳:")
    for timestamp in sorted(vehicle_data_storage.keys()):
        print(timestamp)

# 主協程函數
async def main():
    while True:
        if await connect_with_retry():
            send_data_event.set()  # 初始狀態為發送數據
            input_thread = threading.Thread(target=user_input_handler)
            input_thread.start()

            try:
                await send_vehicle_data()
            except Exception as e:
                logger.error(f"發送數據時發生錯誤：{str(e)}")
            finally:
                await sio.disconnect()
                input_thread.join()
        
        if not is_running:
            break
        
        logger.info("10秒後嘗試重新連接...")
        await asyncio.sleep(10)
    
    logger.info("程序已結束")

# 程序入口
if __name__ == "__main__":
    asyncio.run(main())