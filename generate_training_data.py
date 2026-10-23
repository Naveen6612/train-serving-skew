import pandas as pd
from datetime import datetime
from feast import FeatureStore

# Point Feast to your feature_repo directory
store = FeatureStore(repo_path="feature_store/feature_repo")

# 1. Define your entity dataframe with customer IDs and event timestamps
entity_df = pd.DataFrame(
    {
        "customer_id": ["13069", "13070"],
        "event_timestamp": [
            datetime(2019, 12, 9, 0, 0, 0),
            datetime(2019, 12, 9, 0, 0, 0),
        ],
        "purchased_again": [1, 0] 
    }
)

# 2. Pull point-in-time historical features from PostgreSQL via Feast
training_data = store.get_historical_features(
    entity_df=entity_df,
    features=[
        "ecommerce_features:amount",
        "ecommerce_features:quantity",
    ],
).to_df()

print(training_data.head())
training_data.csv = training_data.to_csv("training_data.csv", index=False)
print("Training data successfully generated and saved to training_data.csv!")