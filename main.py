from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import pandas as pd

from predict import make_prediction
from analytics import fetch_recent_data, calculate_key_metrics, engine

app = FastAPI(
    title="Crypto Bot API",
    description="API endpoints to serve historical metrics and model predictions",
    version="1.0.0"
)

#  Configure the middleware CORS to authorize all local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Autorise toutes les origines (indispensable pour Swagger/Docs)
    allow_credentials=True,
    allow_methods=["*"], # Autorise toutes les méthodes (GET, POST, etc.)
    allow_headers=["*"], # Autorise tous les headers
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the API of our Crypto Bot!"}

# Schema for one single candle
class KlineData(BaseModel):
    timestamp_open: int
    market: str
    open: float
    high: float
    low: float
    price: float
    volume: float

# Endpoint of Prediction

last_predictions = {}
@app.post("/predict")
def get_prediction(data: List[KlineData]):
    if not data:
        raise HTTPException(status_code=400, detail="The data list cannot be empty.")
        
    try:
        # Convert incoming JSON candles into a DataFrame
        market_name = data[0].market
        klines_dict = [kline.model_dump() for kline in data]
        df_live = pd.DataFrame(klines_dict)
        df_live['id'] = df_live.index
        
        # Send the DataFrame to predict.py
        result = make_prediction(df_live)
        
        # If predict.py caught an engineering error, reflect it cleanly
        if "error" in result:
            raise HTTPException(status_code=422, detail=result["error"])
        last_predictions[market_name] = result   

        return {
            "status": "Success",
            "prediction_data": result
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred during prediction: {str(e)}"
        )

@app.get("/stats")
def get_market_stats(days: int = Query(default=7, ge=1, le=30)):
    """
    Endpoint to retrieve key financial metrics for a specific number of past days.
    - **days**: Number of days of historical data to analyze (default: 7, min: 1, max: 30)
    """
    # Fetch recent raw data using the centralized engine
    df = fetch_recent_data(days=days, engine=engine)
    
    # Check if the database query returned an empty DataFrame or failed
    if df.empty:
        raise HTTPException(
            status_code=404, 
            detail=f"No market data found for the last {days} days."
        )
    
    # Calculate financial KPIs using the clean DataFrame
    metrics = calculate_key_metrics(df)
    metrics["history"] = df[['timestamp_open', 'price', 'volume']].to_dict(orient="records")
    
    # Return the results as a clean JSON response
    return metrics

@app.get("/latest-prediction")
def get_latest_prediction(market: str):
    """
    Endpoint dedicated to the Streamlit Dashboard. 
    It reads the latest prediction computed from the streaming flow.
    """
    if market not in last_predictions:
        raise HTTPException(status_code=404, detail="Market not supported.")
        
    return {
        "market": market,
        "latest_prediction": last_predictions[market]
    }
