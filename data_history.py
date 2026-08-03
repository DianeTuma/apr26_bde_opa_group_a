import datetime
from binance.client import Client
import pandas as pd
import pymongo

# # we connect to MongoDB with the  credentials in the course
client_mongo = pymongo.MongoClient("mongodb://datascientest:dst123@localhost:27017/")
db = client_mongo["crypto_db"]
collection = db["data_history"]

# we define a generic fonction to fetch and clean historical data for a market
def fetch_and_clean_history(symbol, start_date, end_date):
    
    client_binance = Client() # we connect to binance without credentials
    
    clean_symbol = symbol.lower().replace("-", "") # we clean the market name
    
    
    # here we define inputs for the klines to be take (market name, intervall of kline
    #start and end date)
    klines = client_binance.get_historical_klines(
        symbol=clean_symbol,
        interval=Client.KLINE_INTERVAL_1MINUTE,
        start_str=str(start_date),
        end_str=str(end_date)
    )
    
    # we convert the data to extract (klines) in dataframe for a quick clean
    df = pd.DataFrame(klines, columns=[
        'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 
        'Close Time', 'Quote Asset Volume', 'Number of Trades', 
        'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore'
    ])
    
    # because we have to have the same data structure like for the streaming for the ML
    #we create a new dataframe df_clean and just choose from df the attribut we are interested for by converting them by the way
    df_clean = pd.DataFrame()
    df_clean['market'] = [clean_symbol] * len(df)
    df_clean['timestamp_open'] = df['Open Time'].astype(int)
    df_clean['open'] = df['Open'].astype(float)
    df_clean['high'] = df['High'].astype(float)
    df_clean['low'] = df['Low'].astype(float)
    df_clean['price_close'] = df['Close'].astype(float)
    df_clean['volume'] = df['Volume'].astype(float)
    df_clean['timestamp_close'] = df['Close Time'].astype(int)
    
    # to insert it in MongoDB we record to dict
    records = df_clean.to_dict(orient='records')
    
    if records:
        collection.insert_many(records)
    
# let start
end = datetime.datetime.now() # from now
start = end - datetime.timedelta(days=90) # back to the 3 last Month
    
fetch_and_clean_history("BTC-USDT", start, end)