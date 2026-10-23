from datetime import timedelta
from feast import Entity, FeatureView, Field, ValueType
from feast.infra.offline_stores.contrib.postgres_offline_store.postgres_source import PostgreSQLSource
from feast.types import Float32, Int64, String

# 1. Define the Entity as a String type
customer_entity = Entity(
    name="customer_id",
    value_type=ValueType.STRING,
    description="Unique customer identifier",
)

# 2. Map CustomerNo and filter out NULLs
ecommerce_source = PostgreSQLSource(
    name="ecommerce_transactions_source",
    query="""
        SELECT 
            CAST(TRUNC("CustomerNo") AS TEXT) AS customer_id,
            "Price" AS amount,
            "Quantity" AS quantity,
            "Date" AS event_timestamp,
            "Date" AS created_timestamp 
        FROM ecommerce_transactions
        WHERE "CustomerNo" IS NOT NULL
    """,
    timestamp_field="event_timestamp",
    created_timestamp_column="created_timestamp",
)

# 3. Define the Feature View
ecommerce_feature_view = FeatureView(
    name="ecommerce_features",
    entities=[customer_entity],
    ttl=timedelta(days=3650),
    schema=[
        Field(name="amount", dtype=Float32),
        Field(name="quantity", dtype=Int64),
    ],
    online=True,
    source=ecommerce_source,
)