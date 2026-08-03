import datetime
from sqlalchemy import create_engine, text

# Database configuration
DATABASE_URL = "postgresql://daniel:datascientest@localhost:5432/crypto_db"
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        # 1. Get the total number of rows
        total_rows = conn.execute(text("SELECT COUNT(*) FROM data_history;")).scalar()
        print(f"📊 Total rows in 'data_history': {total_rows:,}")
        
        if total_rows > 0:
            # 2. Get the latest 5 entries to check recent timestamps
            print("\n🕒 Latest 5 entries:")
            query = text("""
                SELECT market, timestamp_open, price, volume 
                FROM data_history 
                ORDER BY timestamp_open DESC 
                LIMIT 5;
            """)
            results = conn.execute(query).fetchall()
            
            for row in results:
                # Convert millisecond timestamp to human-readable format
                readable_time = datetime.datetime.fromtimestamp(row[1] / 1000, tz=datetime.timezone.utc)
                print(f"   - [{row[0]}] {readable_time} | Price: ${row[2]:,.2f} | Vol: {row[3]:.4f}")
        else:
            print("❌ The table is empty.")

except Exception as e:
    print(f"❌ Connection failed: {e}")