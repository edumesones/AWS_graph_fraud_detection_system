from __future__ import annotations

import pandas as pd

from data.synthetic_generator import generate_transactions


def test_reproducibility():
    df1 = generate_transactions(seed=123, num_transactions=200)
    df2 = generate_transactions(seed=123, num_transactions=200)
    assert df1.equals(df2)


def test_dataframe_structure():
    df = generate_transactions(seed=1, num_transactions=50)
    required = {
        "transaction_id",
        "origin_id",
        "destination_id",
        "amount",
        "timestamp",
        "description",
        "is_fraudulent",
        "fraud_type",
        "risk_score",
    }
    assert required.issubset(df.columns)


def test_amounts_positive_and_bounded():
    df = generate_transactions(seed=2, num_transactions=200)
    assert (df["amount"] > 0).all()
    assert df["amount"].max() <= 1_000_000.0


def test_fraud_percentage_reasonable():
    df = generate_transactions(seed=3, num_transactions=500)
    frac = float(df["is_fraudulent"].mean())
    assert 0.01 <= frac <= 0.5
