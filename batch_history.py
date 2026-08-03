import requests
import pymongo


goal_market = "BTC-USDT"

#  Connect to Mongodb
client = pymongo.MongoClient("mongodb://datascientest:dst123@localhost:27017/")
db = client["crypto_db"]
collection = db["historical_price"] # we range it in the same place

# we define a generic function to create the URL for the historical data
def create_history_url(symbol):
    clean_symbol = symbol.lower().replace("-", "")
    # we ask the 900 last linie in a intervall of 1 min
    return f"https://api.binance.com/api/v3/klines?symbol={clean_symbol.upper()}&interval=1m&limit=900"

# here we clean the data
def clean_data_history(kline, market_name):
    file_clean = {
        "market": market_name.upper().replace("-", ""),
        "timestamp_open": int(kline[0]),
        "open": float(kline[1]), # price at open
        "high": float(kline[2]),# high price
        "low": float(kline[3]),# low price
        "price": float(kline[4]),      # Close price
        "volume": float(kline[5]),  # Volume
        "timestamp_close": int(kline[6])  
    }
    return file_clean

# let start

url_api = create_history_url(goal_market)

# we send the requet and take the answer back
answer= requests.get(url_api)
kline_liste = answer.json() 
print(kline_liste)

#because it is historical data , we have to clean and save each of the kline in the data
counter = 0
for k in kline_liste:
    data_clean = clean_data_history(k, goal_market)
    collection.insert_one(data_clean)
    counter += 1



