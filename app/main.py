from feast import FeatureStore
from fastapi import FastAPI, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import os
from app.database import engine, check_database

app = FastAPI(
    title="Train Skew Serve API",
    description="REST API for ecommerce transaction data",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "message": "Train Skew Serve API is running",
        "docs": "/docs",
    }


@app.get("/health/db")
def database_health():
    try:
        connected = check_database()
        return {"database": "connected" if connected else "unavailable"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Could not connect to PostgreSQL",
        )


@app.get("/transactions")
def get_transactions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    query = text("""
        SELECT
            "TransactionNo",
            "Date",
            "ProductNo",
            "ProductName",
            "Price",
            "Quantity",
            "CustomerNo",
            "Country"
        FROM ecommerce_transactions
        ORDER BY "Date" DESC
        LIMIT :limit OFFSET :offset
    """)

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                query,
                {"limit": limit, "offset": offset},
            ).mappings().all()

        return {
            "count": len(rows),
            "limit": limit,
            "offset": offset,
            "data": [dict(row) for row in rows],
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch transactions",
        )


@app.get("/customers/{customer_no}/transactions")
def get_customer_transactions(
    customer_no: float,
    limit: int = Query(default=20, ge=1, le=100),
):
    query = text("""
        SELECT
            "TransactionNo",
            "Date",
            "ProductNo",
            "ProductName",
            "Price",
            "Quantity",
            "CustomerNo",
            "Country"
        FROM ecommerce_transactions
        WHERE "CustomerNo" = :customer_no
        ORDER BY "Date" DESC
        LIMIT :limit
    """)

    try:
        with engine.connect() as connection:
            rows = connection.execute(
                query,
                {"customer_no": customer_no, "limit": limit},
            ).mappings().all()

        return {
            "customer_no": customer_no,
            "count": len(rows),
            "data": [dict(row) for row in rows],
        }

    except SQLAlchemyError:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch customer transactions",
        )


# Initialize Feast Feature Store pointing to your feature_repo directory
REPO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../feature_store/feature_repo"))
store = FeatureStore(repo_path=REPO_PATH)
@app.get("/features/{customer_id}")
async def get_customer_features(customer_id: str):
    try:
        feature_refs = [
            "ecommerce_features:amount",
            "ecommerce_features:quantity",
        ]
        
        entity_rows = [{"customer_id": customer_id}]
        online_response = store.get_online_features(
            features=feature_refs,
            entity_rows=entity_rows
        )
        
        result = online_response.to_dict()
        
        if not result.get("customer_id") or result["customer_id"][0] is None:
            raise HTTPException(status_code=404, detail=f"Customer ID {customer_id} not found in online store.")
            
        return {
            "customer_id": result["customer_id"][0],
            "features": {
                "amount": result["amount"][0],
                "quantity": result["quantity"][0]
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 