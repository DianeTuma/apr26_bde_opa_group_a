from sqlalchemy import create_engine , text
import pandas as pd
import datetime
import logging

#  Configure logging to track production errors
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Secure database engine creation
DATABASE_URL = "postgresql://daniel:datascientest@pg_container:5432/crypto_db"
engine = create_engine(DATABASE_URL)

def fetch_recent_data(days: int, engine) -> pd.DataFrame:
    """Safely retrieves recent historical data based on the latest available record in DB."""
    try:
        with engine.connect() as conn:
            # 1. Find the absolute latest timestamp existing in the database
            latest_timestamp_ms = conn.execute(
                text("SELECT MAX(timestamp_open) FROM data_history;")
            ).scalar()
            
        # Safety check if the database is completely empty
        if not latest_timestamp_ms:
            logger.warning("Database is completely empty.")
            return pd.DataFrame()

        # 2. Subtract the number of days from this maximum timestamp
        # 1 day = 24 * 60 * 60 * 1000 milliseconds
        ms_per_day = 24 * 60 * 60 * 1000
        start_timestamp_ms = latest_timestamp_ms - (days * ms_per_day)

        # 3. Query the data
        query = text("""
            SELECT * FROM data_history 
            WHERE timestamp_open >= :start_timestamp
            ORDER BY timestamp_open ASC;
        """)
        
        df = pd.read_sql(query, engine, params={"start_timestamp": start_timestamp_ms})
        logger.info(f"Successfully fetched {len(df)} rows for the last {days} days.")
        return df

    except Exception as e:
        logger.error(f"Error fetching data from database: {e}")
        return pd.DataFrame()

def calculate_key_metrics(df: pd.DataFrame) -> dict:
    """Calculates financial KPIs and gracefully handles empty DataFrames."""
    # Safety check: if no data is available for the period (e.g., pipeline down or exchange gap)
    if df.empty:
        return {
            "max_price": 0.0,
            "min_price": 0.0,
            "total_volume": 0.0,
            "performance_pct": 0.0,      
            "vwap": 0.0,        
            "green_candles_pct": 0.0,  
            "average_volatility_pct": 0.0,   
            "status": "No data available"
        }
    
    # Calculate metrics and convert to native Python types for FastAPI JSON serialization
    return {
        # max_price: The highest price reached during the selected timeframe
        "max_price": float(df['high'].max()),
        
        # min_price: The lowest price reached during the selected timeframe
        "min_price": float(df['low'].min()),
        
        # total_volume: Cumulative asset volume traded over the entire period
        "total_volume": float(df['volume'].sum()),
        
        # performance_pct: Total asset return rate (growth/decline) from the start to the end of the period
        "performance_pct": float(((df['price'].iloc[-1] - df['open'].iloc[0]) / df['open'].iloc[0]) * 100),      
        
        # vwap: Volume Weighted Average Price. Reflects the true average execution price based on trade volume
        "vwap": float((df['price'] * df['volume']).sum() / df['volume'].sum()),        
        
        # green_candles_pct: Market sentiment ratio. Percentage of candles that closed higher than they opened
        "green_candles_pct": float(((df['price'] > df['open']).sum() / len(df)) * 100),  
        
        # average_volatility_pct: Average price amplitude (High vs Low) per candle, tracking current market turbulence
        "average_volatility_pct": float((((df['high'] - df['low']) / df['low']) * 100).mean()),
        
        "status": "OK"
    }