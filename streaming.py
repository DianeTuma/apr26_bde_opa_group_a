import pymongo
import websocket
import json
import requests
import os
import time

goal_market = "BTC-USDT"

# We fetch the exact environment variables defined in your docker-compose.yml
# If running outside Docker, it falls back to localhost
MONGO_URL = os.getenv("MONGO_URL", "mongodb://datascientest:dst123@localhost:27017/")
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Secure Mongo connection using the full URL string
client = pymongo.MongoClient(MONGO_URL)
db = client["crypto_db"] # we create a db in mongodb "crypto.."
collection = db["price_streaming"]


#for each market the url is like different.
#so we create a function which will adapt the url link for the market each time
#this function take the market name as parameter
def create_stream_url(symbol):
    clean_symbol = symbol.lower().replace("-", "")
    return f"wss://stream.binance.com:9443/ws/{clean_symbol}@kline_1m"

# generic data retrieval function
def clean_data(data_to_clean):
    return {
        "market": data_to_clean["k"]["s"],
        "timestamp_open": int(data_to_clean["k"]["t"]),
        "open": float(data_to_clean["k"]["o"]),
        "high": float(data_to_clean["k"]["h"]),
        "low": float(data_to_clean["k"]["l"]),
        "price": float(data_to_clean["k"]["c"]),
        "volume": float(data_to_clean["k"]["v"]),
        "timestamp_close": int(data_to_clean["k"]["T"])
    }


# Warm-up function to fetch historical data from Binance REST API before starting the stream
def warmup_database(symbol):
    print(f"[*] Warm-up: Fetching recent historical data for {symbol}...", flush=True)
    clean_symbol = symbol.upper().replace("-", "")
    
    # Call Binance public REST API to fetch the last 50 candles (1-minute interval)
    url = f"https://api.binance.com/api/v3/klines?symbol={clean_symbol}&interval=1m&limit=50"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            candles = response.json()
            inserted_count = 0
            
            for c in candles:
                # Binance REST API structure mapping:
                # 0: Open time, 1: Open, 2: High, 3: Low, 4: Close, 5: Volume, 6: Close time
                candle_doc = {
                    "market": clean_symbol,
                    "timestamp_open": int(c[0]),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "price": float(c[4]),
                    "volume": float(c[5]),
                    "timestamp_close": int(c[6])
                }
                
                # Use upsert to prevent duplicates if data already exists
                collection.update_one(
                    {
                        "market": candle_doc["market"], 
                        "timestamp_open": candle_doc["timestamp_open"]
                    },
                    {"$set": candle_doc},
                    upsert=True
                )
                inserted_count += 1
                
            print(f"[✓] Warm-up complete! {inserted_count} candles synced to MongoDB.", flush=True)
        else:
            print(f"[!] Warm-up failed (Binance API Error: {response.status_code}). Starting cold.", flush=True)
    except Exception as e:
        print(f"[!] Network error during warm-up: {e}. Starting cold.", flush=True)


# we define a function to take info flux of binance(streaming) and clean then if 
# there is a market.
def on_message(ws, message):
    evenement = json.loads(message)
    
    # we check if the structure is ok before continue
    if "k" in evenement:

        # now just store the kline if the close is also there 
        if evenement["k"]["x"]:  # Candle closed!
            data_clean = clean_data(evenement)
            
        # store the data in MongoDB
            # Use upsert at the place of insert_one to avoid duplicate candles on    reconnection
            collection.update_one(
                {
                    "market": data_clean["market"], 
                    "timestamp_open": data_clean["timestamp_open"]
                },
                {"$set": data_clean},
                upsert=True
            )
            
            # Fetch the last 50 candles to satisfy indicators requirement
            last_50_candles = list(collection.find().sort("timestamp_open", -1).limit(50))
            
            # Cold Start Protection. To make sure that we will have at least 50 candles
            # Thanks to warm-up, this condition is instantly bypassed from the very first live candle
            if len(last_50_candles) < 50:
                print(f"[*] Warming up database... ({len(last_50_candles)}/50 candles collected). Waiting for more data.", flush=True)
                return  # We stop here and don't call FastAPI yet
                
            # Put them back in chronological order
            last_50_candles.reverse()
            
            # Remove MongoDB internal IDs
            for candle in last_50_candles:
                candle.pop("_id", None)
                
            # Send the batch to FastAPI for prediction
            try:
                # Target the endpoint correctly using the API_URL variable
                response = requests.post(f"{API_URL}/predict", json=last_50_candles)
                if response.status_code == 200:
                    print("Prediction Signal:", response.json(), flush=True)
                else:
                    print(f"API returned error {response.status_code}: {response.text}", flush=True)
            except Exception as e:
                print(f"FastAPI offline or error: {e}", flush=True)

# Starting Point
# 1. Warm up the database to satisfy the 50-candle requirement instantly
warmup_database(goal_market)

# 2. we connect python with the streaming in Binance
url_finale = create_stream_url(goal_market)
print(f"[*] Connecting to Binance WebSocket live stream for {goal_market}...", flush=True)
ws = websocket.WebSocketApp(url_finale, on_message=on_message)
ws.run_forever()