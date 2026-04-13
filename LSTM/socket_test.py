from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from flask_cors import CORS
from pymongo import MongoClient
from bson import json_util
import time
import json

app = Flask(__name__)
# 修改 CORS 配置
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
# 修改 SocketIO 配置
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
# MongoDB 連接

client = MongoClient('mongodb://lab5f.usalab.org:27087')
db = client.admin
db_vehicle = client['vehicle']
collection_vehicle = db_vehicle['VIN_1FMZK02147GA90077']

def create_data_route(field_name):
    def get_field_data():
        try:
            # 可選的過濾參數
            speed = request.args.get('speed')
            rpm = request.args.get('rpm')

            # 構建查詢條件
            query = {}
            if speed:
                query['SPD(km/h)'] = float(speed)
            if rpm:
                query['RPM(Rpm)'] = float(rpm)

            # 設置投影，只返回需要的字段
            projection = {'DateTime': 1, field_name: 1, '_id': 0}

            # 執行查詢
            data = list(collection_vehicle.find(
                query,
                projection
            ).sort('DateTime', 1))

            # 如果沒有找到數據
            if not data:
                return jsonify({"message": "No data found", "data": []}), 404

            # 將結果轉換為 JSON 並返回
            return json.loads(json_util.dumps(data))

        except ValueError as e:
            return jsonify({"error": "Invalid parameter format"}), 400
        except Exception as e:
            app.logger.error(f"An error occurred: {str(e)}")
            return jsonify({"error": "An internal server error occurred"}), 500

    # 為每個字段設置一個唯一的端點名稱
    get_field_data.__name__ = f'get_{field_name.lower().replace(" ", "_")}_data'
    return get_field_data

# 為每個欄位創建路由
fields = [
    'vehicle_speed', 'datetime', 'altitude', 'battery', 
    'engine_rpm', 'air_flow_rate_maf', 'throttle_position', 'intake_air_temp', 
    'engine_coolant_temp', 'cardata'
]

for field in fields:
    app.add_url_rule(
        f'/api/{field}',
        view_func=create_data_route(field),
        methods=['GET']
    )
    
@app.route('/api/cluster_overview', methods=['GET'])
def get_cluster_overview():
    server_status = db.command("serverStatus")
    uptime_seconds = server_status['uptime']
    weeks, remainder = divmod(uptime_seconds, 7 * 24 * 3600)
    days, remainder = divmod(remainder, 24 * 3600)
    hours, _ = divmod(remainder, 3600)
    
    uptime_str = f"{weeks}W {days}D {hours}H" if weeks else f"{days}D {hours}H"

    connection_info = f"{client.address[0]}:{client.address[1]}"
    Set_name = connection_info
    
    return jsonify({
        'Set Name': Set_name,
        'Server Uptime': uptime_str,
        'MongoDB Version': server_status['version'],
        'Replica Set Status': 'Healthy' if server_status.get('repl', {}).get('ismaster', False) else 'Not Primary'
    })

@app.route('/api/ops_counters', methods=['GET'])
def get_ops_counters():
    server_status = db.command("serverStatus")
    return jsonify(server_status['opcounters'])

@app.route('/api/requests_per_second', methods=['GET'])
def get_requests_per_second():
    server_status = db.command("serverStatus")
    network_info = server_status.get('network', {})
    return jsonify({
        'reads': network_info.get('numRequests', 0),
        'writes': network_info.get('bytesOut', 0) / 1024  # Convert to KB
    })

@app.route('/api/wiredtiger_stats', methods=['GET'])
def get_wiredtiger_stats():
    server_status = db.command("serverStatus")
    wt_stats = server_status.get('wiredTiger', {})
    return jsonify({
        'WT - Concurrent Tickets': wt_stats.get('concurrentTransactions', {}),
        'WT - Cache': {
            'Used': wt_stats.get('cache', {}).get('bytes currently in the cache', 0),
            'Dirty': wt_stats.get('cache', {}).get('tracked dirty bytes in the cache', 0),
            'Read into': wt_stats.get('cache', {}).get('bytes read into cache', 0)
        }
    })

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

def get_monitoring_data():
    server_status = db.command("serverStatus")
    network_info = server_status.get('network', {})
    wt_stats = server_status.get('wiredTiger', {})
    
    data = {
        'timestamp': time.time(),
        'ops_counters': server_status['opcounters'],
        'requests_per_second': {
            'reads': network_info.get('numRequests', 0),
            'writes': network_info.get('bytesOut', 0) / 1024  # Convert to KB
        },
        'wiredtiger_stats': {
            'WT - Concurrent Tickets': wt_stats.get('concurrentTransactions', {}),
            'WT - Cache': {
                'Used': wt_stats.get('cache', {}).get('bytes currently in the cache', 0),
                'Dirty': wt_stats.get('cache', {}).get('tracked dirty bytes in the cache', 0),
                'Read into': wt_stats.get('cache', {}).get('bytes read into cache', 0)
            }
        }
    }
    return data

def background_task():
    while True:
        monitoring_data = get_monitoring_data()
        # 確保數據可以正確序列化
        json_data = json.dumps(monitoring_data, default=json_util.default)
        socketio.emit('monitoring_update', json.loads(json_data))
        time.sleep(1)  # 每秒發送一次更新

if __name__ == '__main__':
    from threading import Thread
    Thread(target=background_task).start()
    # 修改運行配置
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)