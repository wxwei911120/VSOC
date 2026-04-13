import asyncio
import socketio
import random
from datetime import datetime
import json
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

sio = socketio.AsyncClient(logger=True, engineio_logger=True)

@sio.event
async def connect():
    logging.info("Connected to server")

@sio.event
async def disconnect():
    logging.info("Disconnected from server")

@sio.event
def blockchainResult(data):
    if data['success']:
        logging.info(f"Transaction successful with hash: {data['transactionHash']}")
        logging.info(f"Block number: {data['blockNumber']}")
        logging.info(f"Block hash: {data['blockHash']}")
    else:
        logging.error(f"Error storing data on blockchain: {data['error']}")
    
    sio.eio.create_event().set()

def generate_vehicle_data():
    return {
        "datetime": datetime.now().isoformat(),
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
        "gps": f"{random.uniform(-90, 90)},{random.uniform(-180, 180)}",
        "anomaly": "Warning: High temperature" if random.random() > 0.9 else ""
    }

async def connect_with_retry(max_retries=5, delay=5):
    for attempt in range(max_retries):
        try:
            await sio.connect('http://localhost:3000', transports=['websocket'])
            return
        except Exception as e:
            logging.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                logging.info(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                logging.error("Max retries reached. Could not connect to server.")
                raise

async def main():
    try:
        await connect_with_retry()
        
        while True:
            try:
                vehicle_data = generate_vehicle_data()
                logging.info(f"Sending vehicle data: {json.dumps(vehicle_data, indent=2)}")
                await sio.emit('vehicleData', vehicle_data)
                
                try:
                    await asyncio.wait_for(sio.eio.create_event().wait(), timeout=30.0)
                except asyncio.TimeoutError:
                    logging.warning("Timeout waiting for blockchain result")
                
                await asyncio.sleep(5)
            except Exception as e:
                logging.error(f"Error in main loop: {str(e)}")
                await asyncio.sleep(5)
    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
    finally:
        await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(main())