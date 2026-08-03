import datetime
import time
from binance.client import Client
import pandas as pd
from sqlalchemy import create_engine, text

# POSTGRESQL CONFIGURATION
DATABASE_URL = "postgresql://daniel:datascientest@localhost:5432/crypto_db"
engine = create_engine(DATABASE_URL)

def setup_database():
    """Ensures the table exists and sets up the unique constraint to prevent duplicates."""
    with engine.begin() as conn:
        # 1. Create table if it doesn't exist
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS data_history (
                id SERIAL PRIMARY KEY,
                market VARCHAR(20),
                timestamp_open BIGINT,
                open FLOAT,
                high FLOAT,
                low FLOAT,
                price FLOAT,
                volume FLOAT,
                timestamp_close BIGINT
            );
        """))
        
    # 2. Add unique constraint (handled in a separate block to catch 'already exists' exception)
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                ALTER TABLE data_history 
                ADD CONSTRAINT unique_market_timestamp UNIQUE (market, timestamp_open);
            """))
            print("[*] Database constraint verified/created successfully.")
    except Exception as e:
        if "already exists" in str(e):
            print("[*] Unique constraint already exists. Skipping.")
        else:
            print(f"[Warning] Could not verify/create database constraint: {e}")

def get_row_count():
    """Returns the total number of rows currently in the data_history table."""
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM data_history;")).scalar()
    return result

def save_data_upsert(df_clean):
    """Inserts rows or updates them if a timestamp conflict occurs (UPSERT pattern)."""
    if df_clean.empty:
        return
        
    query = text("""
        INSERT INTO data_history (market, timestamp_open, open, high, low, price, volume, timestamp_close)
        VALUES (:market, :timestamp_open, :open, :high, :low, :price, :volume, :timestamp_close)
        ON CONFLICT (market, timestamp_open) 
        DO UPDATE SET 
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            price = EXCLUDED.price,
            volume = EXCLUDED.volume,
            timestamp_close = EXCLUDED.timestamp_close;
    """)
    
    records = df_clean.to_dict(orient='records')
    with engine.begin() as conn:
        conn.execute(query, records)

def fetch_and_clean(symbol, start_ms, end_ms, is_historical=False):
    """Fetches klines from Binance API, formats them into a DataFrame, and stores them in PostgreSQL."""
    client_binance = Client()
    binance_symbol = symbol.upper().replace("-", "")
    
    # Define 30-day chunks in milliseconds for safe historical downloads to protect memory
    chunk_size_ms = 30 * 24 * 60 * 60 * 1000 if is_historical else (end_ms - start_ms)
    current_start = start_ms

    while current_start < end_ms:
        current_end = min(current_start + chunk_size_ms, end_ms)
        
        try:
            klines = client_binance.get_historical_klines(
                symbol=binance_symbol,
                interval=Client.KLINE_INTERVAL_1MINUTE,
                start_str=str(current_start),
                end_str=str(current_end)
            )
            
            if not klines:
                current_start = current_end
                continue

            df = pd.DataFrame(klines, columns=[
                'Open Time', 'Open', 'High', 'Low', 'Close', 'Volume', 
                'Close Time', 'Quote Asset Volume', 'Number of Trades', 
                'Taker Buy Base Asset Volume', 'Taker Buy Quote Asset Volume', 'Ignore'
            ])
            
            df_clean = pd.DataFrame()
            df_clean['market'] = [binance_symbol] * len(df)
            df_clean['timestamp_open'] = df['Open Time'].astype(int)
            df_clean['open'] = df['Open'].astype(float)
            df_clean['high'] = df['High'].astype(float)
            df_clean['low'] = df['Low'].astype(float)
            df_clean['price'] = df['Close'].astype(float)
            df_clean['volume'] = df['Volume'].astype(float)
            df_clean['timestamp_close'] = df['Close Time'].astype(int)
            
            # Secure database storage using UPSERT
            save_data_upsert(df_clean)
            print(f"    [OK] Processed {len(df_clean)} rows (Inserted/Updated).")
            
            # Polite pause to respect Binance API rate limits during heavy historical fetches
            if is_historical:
                time.sleep(0.5)
            
        except Exception as e:
            print(f"    [Error] Failed to process data chunk: {e}")
        
        current_start = current_end

if __name__ == "__main__":
    # 1. Initialize database schema & constraints
    setup_database()
    
    # 2. Check the current status of the database table
    total_rows = get_row_count()
    print(f"[*] Current row count in database: {total_rows}")
    
    target_market = "BTC-USDT"
    end_dt = datetime.datetime.now(datetime.timezone.utc)
    
    if total_rows == 0:
        # --- MODE 1: INITIAL HISTORICAL LOAD (Triggered only if database is completely empty) ---
        print("[*] DATABASE EMPTY: Triggering 180-day historical data load...")
        start_dt = end_dt - datetime.timedelta(days=180)
        
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)
        
        fetch_and_clean(target_market, start_ms, end_ms, is_historical=True)
        print("[*] Historical data load complete!")
    else:
        # --- MODE 2: CONTINUOUS INGESTION (Triggered by your every-15-minute Crontab) ---
        print("[*] INCREMENTAL RUN: Fetching data from the last 20 minutes...")
        
        # We look back 20 minutes instead of 15 to establish an overlap buffer. 
        # The database UPSERT constraint will seamlessly handle overlaps and filter duplicates.
        start_dt = end_dt - datetime.timedelta(minutes=20)
        
        start_ms = int(start_dt.timestamp() * 1000)
        end_ms = int(end_dt.timestamp() * 1000)
        
        fetch_and_clean(target_market, start_ms, end_ms, is_historical=False)