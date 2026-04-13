from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS
from pymongo import MongoClient
from bson import json_util
import time
import json

app = Flask(__name__)
# 修改 CORS 配置
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}}, supports_credentials=True)
# 修改 SocketIO 配置
socketio = SocketIO(app, cors_allowed_origins="http://localhost:5173", async_mode='threading')
# MongoDB 連接
client = MongoClient('mongodb://lab5f.usalab.org:27087')
db = client.admin

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
    ops_counters = server_status['opcounters']
    print('OpsCounters response:', ops_counters)
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

# 新增的 monitoring_data 端點
@app.route('/api/monitoring_data', methods=['GET'])
def get_monitoring_data_api():
    return jsonify(get_monitoring_data())

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