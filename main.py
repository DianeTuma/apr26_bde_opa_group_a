from fastapi import FastAPI, HTTPException, Query, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List
import pandas as pd
from datetime import datetime, timedelta
import jwt

# Prometheus Instrumentation
from prometheus_fastapi_instrumentator import Instrumentator

from predict import make_prediction
from analytics import fetch_recent_data, calculate_key_metrics, engine

app = FastAPI(
    title="Crypto Bot API",
    description="API endpoints with JWT Authentication, RBAC, Prometheus Metrics, and Model Predictions",
    version="2.0.0"
)

#  Configure the middleware CORS to authorize all local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Autorise toutes les origines (indispensable pour Swagger/Docs)
    allow_credentials=True,
    allow_methods=["*"], # Autorise toutes les méthodes (GET, POST, etc.)
    allow_headers=["*"], # Autorise tous les headers
)

# Automatically measures HTTP latency, request counts, and error rates
instrumentator = Instrumentator().instrument(app)

@app.on_event("startup")
async def startup_prometheus():
    # Expose public /metrics endpoint for Prometheus scraping
    instrumentator.expose(app)

SECRET_KEY = "SUPER_SECRET_KEY_FOR_DEMO_PRESENTATION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Mock database with 3 user roles: admin, trader, viewer
USERS_DB = {
    "alice_admin": {
        "username": "alice_admin",
        "password": "adminpassword123",
        "role": "admin",
    },
    "bob_trader": {
        "username": "bob_trader",
        "password": "traderpassword123",
        "role": "trader",
    },
    "charlie_viewer": {
        "username": "charlie_viewer",
        "password": "viewerpassword123",
        "role": "viewer",
    },
}

def create_access_token(data: dict) -> str:
    """Creates a signed JWT token containing the user identity and role."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def require_roles(allowed_roles: List[str]):
    """Dependency that verifies the JWT token and checks the user role."""
    def role_checker(token: str = Depends(oauth2_scheme)) -> dict:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_role: str = payload.get("role")
            username: str = payload.get("sub")

            if not user_role or not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token data."
                )

            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Allowed roles: {allowed_roles}"
                )

            return payload
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token."
            )

    return role_checker


@app.post("/token", tags=["Authentication"])
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login endpoint to obtain JWT Token for Swagger UI or API clients."""
    user = USERS_DB.get(form_data.username)
    if not user or user["password"] != form_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect username or password."
        )

    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"]
    }

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

@app.post("/admin/retrain")
def trigger_retrain(current_user: dict = Depends(require_roles(["admin"]))):
    """
    Model retraining management endpoint.
    STRICTLY RESERVED TO ROLE: 'admin'.
    """
    return {
        "status": "Success",
        "message": "Random Forest model retraining started.",
        "triggered_by": current_user["sub"]
    }