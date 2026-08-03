import pandas as pd
import pandas_ta as ta
import joblib

# We load the exact model and scaler trained in our notebook
model = joblib.load('crypto_model.joblib')
scaler = joblib.load('crypto_scaler.joblib')

# we also define the here the fonction we use for the feature Engineering
# so that the streaming data can also use them
def prepare_realtime_data(raw_candles_df):
    """
    Takes the latest raw candles from Binance API, computes indicators, 
    and returns the very last row for prediction.
    """
    df_feat = raw_candles_df.copy()
    
    # We apply the EXACT same indicators as the training pipeline
    df_feat['ema_20'] = ta.ema(df_feat['price'], length=20)
    df_feat['ema_50'] = ta.ema(df_feat['price'], length=50)
    
    macd = ta.macd(df_feat['price'], fast=12, slow=26, signal=9)
    df_feat = pd.concat([df_feat, macd], axis=1)
    
    bbands = ta.bbands(df_feat['price'], length=20, std=2)
    df_feat = pd.concat([df_feat, bbands], axis=1)
    
    # FIX: If your model strictly expects columns ending in '_2.0_2.0', 
    # we manually map the standard pandas_ta names to match your notebook's state.
    rename_mapping = {
        'BBL_20_2.0': 'BBL_20_2.0_2.0',
        'BBM_20_2.0': 'BBM_20_2.0_2.0',
        'BBU_20_2.0': 'BBU_20_2.0_2.0',
        'BBB_20_2.0': 'BBB_20_2.0_2.0',
        'BBP_20_2.0': 'BBP_20_2.0_2.0'
    }
    df_feat = df_feat.rename(columns=rename_mapping)
    
    df_feat['atr'] = ta.atr(df_feat['high'], df_feat['low'], df_feat['price'], length=14)
    df_feat['rsi'] = ta.rsi(df_feat['price'], length=14)
    
    df_feat['returns'] = df_feat['price'].pct_change()
    df_feat['vol_momentum'] = df_feat['volume'] / df_feat['volume'].rolling(window=5).mean()
    
    # Drop NaNs but keep the structure
    df_feat = df_feat.dropna().reset_index(drop=True)
    
    # We only care about the LATEST candle (the present moment) to make a prediction
    latest_candle = df_feat.tail(1)
    return latest_candle

FEATURES_LIST = [
    'id',
    'open', 
    'high', 
    'low', 
    'price', 
    'volume', 
    'ema_20', 
    'ema_50', 
    'MACD_12_26_9', 
    'MACDh_12_26_9', 
    'MACDs_12_26_9', 
    'BBL_20_2.0_2.0', 
    'BBM_20_2.0_2.0', 
    'BBU_20_2.0_2.0', 
    'BBB_20_2.0_2.0', 
    'BBP_20_2.0_2.0', 
    'atr', 
    'rsi', 
    'returns', 
    'vol_momentum'
]

def make_prediction(raw_candles_df):
    """Main function to be called by FastAPI endpoint."""
    latest_features = prepare_realtime_data(raw_candles_df)
    
    if latest_features.empty:
        return {"error": "Not enough data to compute indicators"}
        
    try:
        X_live = latest_features[FEATURES_LIST]
    except KeyError as e:
        return {"error": f"Missing feature column in real-time data: {e}"}
    
    # Scale live data using the SAVED scaler
    X_live_scaled = scaler.transform(X_live)
    
    # Predict
    prediction = int(model.predict(X_live_scaled)[0])
    buy_probability = float(model.predict_proba(X_live_scaled)[0][1])
    
    
    # Apply your 65% filter logic directly for the API response
    CONFIDENCE_THRESHOLD = 0.65
    action = "BUY" if (prediction == 1 and buy_probability > CONFIDENCE_THRESHOLD) else "HOLD/SELL"
    
    return {
        "market": latest_features['market'].values[0],
        "timestamp": str(latest_features['timestamp_open'].values[0]),
        "raw_prediction": prediction,
        "buy_probability": round(buy_probability, 4),
        "recommended_action": action
    }