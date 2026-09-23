from __future__ import annotations

import pytest

from data.synthetic_generator import generate_transactions
from analysis.graph_builder import build_graph_from_transactions


@pytest.fixture
def sample_df():
    return generate_transactions(seed=42, num_transactions=100, num_clients=80)


@pytest.fixture
def sample_graph(sample_df):
    return build_graph_from_transactions(sample_df)
