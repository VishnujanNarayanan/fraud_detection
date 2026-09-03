"""Contract tests for the aggregates the report and the dashboard read.

app.py and make_report.py both consume app_data/*.csv by column name. Those files are
generated, but they are tracked -- the dashboard is deployed without the source CSV and
cannot rebuild them -- so a rename in sql/aggregations.sql would break both consumers
silently. These tests pin the contract.
"""

import os

import pandas as pd
import pytest

AGG_DIR = "app_data"

EXPECTED_COLUMNS = {
    "channel_mix": ["channel", "transactions", "fraud_cases", "fraud_rate_pct", "mean_amount"],
    "fraud_by_hour": ["hour", "transactions", "fraud_cases", "fraud_rate_pct"],
    "amount_by_class": ["class", "transactions", "min_amount", "mean_amount", "max_amount"],
    "balance_signature": ["class", "transactions", "recipient_unchanged",
                          "recipient_unchanged_pct"],
    "flagged_rule_effectiveness": ["rule_alerts", "rule_true_positives", "fraud_cases",
                                   "fraud_caught_pct"],
    "channel_hour": ["channel", "hour", "transactions", "fraud_cases", "fraud_rate_pct"],
}


@pytest.mark.parametrize("name,columns", EXPECTED_COLUMNS.items())
def test_aggregate_exists_with_expected_columns(name, columns):
    path = os.path.join(AGG_DIR, f"{name}.csv")
    assert os.path.exists(path), f"{path} is missing -- run `python load_sqlite.py`"
    df = pd.read_csv(path)
    assert list(df.columns) == columns
    assert not df.empty


def test_channel_mix_totals_are_internally_consistent():
    df = pd.read_csv(os.path.join(AGG_DIR, "channel_mix.csv"))
    # the published headline figures for this dataset
    assert df["transactions"].sum() == 6_362_620
    assert df["fraud_cases"].sum() == 8_213
    # fraud_rate_pct must agree with the counts it was derived from
    derived = 100 * df["fraud_cases"] / df["transactions"]
    assert (derived - df["fraud_rate_pct"]).abs().max() < 1e-3


def test_only_transfer_and_cash_out_carry_fraud():
    df = pd.read_csv(os.path.join(AGG_DIR, "channel_mix.csv"))
    carrying = set(df.loc[df["fraud_cases"] > 0, "channel"])
    assert carrying == {"TRANSFER", "CASH_OUT"}


def test_hourly_aggregate_covers_a_full_day():
    df = pd.read_csv(os.path.join(AGG_DIR, "fraud_by_hour.csv"))
    assert sorted(df["hour"]) == list(range(24))
    assert df["transactions"].sum() == 6_362_620


def test_fraud_is_likelier_when_the_recipient_balance_never_moves():
    df = pd.read_csv(os.path.join(AGG_DIR, "balance_signature.csv")).set_index("class")
    assert (df.loc["Fraudulent", "recipient_unchanged_pct"]
            > df.loc["Legitimate", "recipient_unchanged_pct"])
