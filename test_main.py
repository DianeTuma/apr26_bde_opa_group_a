import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import pandas as pd

# On importe l'application , la mémoire globale et la fonction de sécurité
from main import app, last_predictions , create_access_token

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    """
    Génère un faux token Admin valide pour toutes les requêtes de test
    et l'injecte dans le client via les headers par défaut.
    """
    # Crée un vrai JWT signé avec la SECRET_KEY pour contourner require_roles
    admin_token = create_access_token(data={"sub": "diane_admin", "role": "admin"})
    client.headers.update({"Authorization": f"Bearer {admin_token}"})
    yield
    client.headers.pop("Authorization", None)

@pytest.fixture(autouse=True)
def reset_predictions():
    """Vide la mémoire globale avant chaque test pour repartir à zéro."""
    last_predictions.clear()
    yield


# TEST ROUTE RACINE (GET /)
def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]


#  TESTS ROUTE DE PREDICTION (POST /predict) - Utilisée par le Streaming
@patch("main.make_prediction")  #  On intercepte l'appel pour éviter de charger joblib/scipy
def test_predict_endpoint_success(mock_make_prediction):
    # On définit ce que la fonction simulée doit renvoyer
    mock_make_prediction.return_value = {"decision": "BUY", "confidence": 0.92}
    
    # On prépare une fausse bougie au format attendu par Pydantic (KlineData)
    payload = [
        {
            "timestamp_open": 1718534400,
            "market": "BTCUSDT",
            "open": 65000.0,
            "high": 66000.0,
            "low": 64500.0,
            "price": 65800.0,
            "volume": 120.5
        }
    ]
    
    response = client.post("/predict", json=payload)
    
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "Success"
    assert json_data["prediction_data"]["decision"] == "BUY"
    
    # On vérifie que la variable globale a bien mémorisé le résultat pour Streamlit
    assert "BTCUSDT" in last_predictions
    assert last_predictions["BTCUSDT"]["decision"] == "BUY"

def test_predict_endpoint_empty_payload():
    """Vérifie que l'API renvoie un code 400 si la liste de bougies est vide."""
    response = client.post("/predict", json=[])
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]



# TESTS ROUTE HISTORIQUE (GET /stats) - Utilisée par le Dashboard
@patch("main.fetch_recent_data")
@patch("main.calculate_key_metrics")
def test_get_stats_success(mock_calculate, mock_fetch):
    """Simule un cas où PostgreSQL renvoie des données et l'API calcule les KPIs."""
    # On simule un DataFrame non vide renvoyé par Postgres
    mock_fetch.return_value = pd.DataFrame([{
        "timestamp_open": 1718534400, "price": 65000.0, "volume": 10.0
    }])
    # On simule le dictionnaire calculé par analytics.py
    mock_calculate.return_value = {"max_price": 65000.0, "vwap": 65000.0, "status": "OK"}
    
    response = client.get("/stats?days=7")
    
    assert response.status_code == 200
    data = response.json()
    assert "max_price" in data
    assert "history" in data

def test_get_stats_validation_error():
    """Vérifie que l'API bloque via un code 422 si les jours dépassent 30 (ge=1, le=30)."""
    response = client.get("/stats?days=45")
    assert response.status_code == 422



# TESTS ROUTE LATEST PREDICTION (GET /latest-prediction) - Pour Streamlit
def test_get_latest_prediction_not_found():
    """Renvoie une erreur 404 si le marché n'a encore reçu aucun streaming."""
    response = client.get("/latest-prediction?market=ETHUSDT")
    assert response.status_code == 404

def test_get_latest_prediction_success():
    """Vérifie que la route lit correctement la variable globale."""
    # On injecte manuellement une valeur dans le dictionnaire pour le test
    last_predictions["BTCUSDT"] = {"decision": "SELL", "confidence": 0.65}
    
    response = client.get("/latest-prediction?market=BTCUSDT")
    
    assert response.status_code == 200
    data = response.json()
    assert data["market"] == "BTCUSDT"
    assert data["latest_prediction"]["decision"] == "SELL"