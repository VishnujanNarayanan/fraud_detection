"""Tests for the SQL layer.

These run the project's real schema.sql and aggregations.sql -- not copies -- against a
small in-memory database, so a query that stops parsing or silently changes shape fails
here rather than in a report someone has already sent on.
"""

import sqlite3

import pandas as pd
import pytest

from load_sqlite import split_named_queries

SCHEMA = "sql/schema.sql"
QUERIES = "sql/aggregations.sql"

EXPECTED_QUERIES = {"channel_mix", "fraud_by_hour", "amount_by_class",
                    "balance_signature", "flagged_rule_effectiveness", "channel_hour"}


@pytest.fixture
def con():
    """An in-memory database on the real schema, with a handful of known rows."""
    con = sqlite3.connect(":memory:")
    with open(SCHEMA, encoding="utf8") as fh:
        con.executescript(fh.read())

    rows = [
        # step, type, amount, oldOrg, newOrig, oldDest, newDest, isFraud, isFlagged
        (5,  "TRANSFER", 900.0, 900.0, 0.0,   0.0,  0.0,   1, 1),  # fraud, dest unmoved
        (5,  "TRANSFER", 100.0, 500.0, 400.0, 10.0, 110.0, 0, 0),
        (5,  "CASH_OUT", 800.0, 800.0, 0.0,   0.0,  0.0,   1, 0),  # fraud, dest unmoved
        (19, "CASH_OUT", 50.0,  200.0, 150.0, 20.0, 70.0,  0, 0),
        (19, "PAYMENT",  20.0,  100.0, 80.0,  0.0,  0.0,   0, 0),
        (19, "CASH_IN",  30.0,  60.0,  90.0,  40.0, 10.0,  0, 0),
        (19, "DEBIT",    10.0,  40.0,  30.0,  5.0,  15.0,  0, 0),
    ]
    con.executemany("INSERT INTO transactions VALUES (?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    yield con
    con.close()


@pytest.fixture
def queries():
    with open(QUERIES, encoding="utf8") as fh:
        return split_named_queries(fh.read())


def test_every_expected_query_is_present(queries):
    assert set(queries) == EXPECTED_QUERIES


def test_every_query_runs_and_returns_rows(con, queries):
    """A query that stops parsing, or returns nothing, is a broken report."""
    for name, sql in queries.items():
        df = pd.read_sql_query(sql, con)
        assert not df.empty, f"{name} returned no rows"


def test_channel_mix_counts_fraud_per_channel(con, queries):
    df = pd.read_sql_query(queries["channel_mix"], con).set_index("channel")
    assert df.loc["TRANSFER", "fraud_cases"] == 1
    assert df.loc["CASH_OUT", "fraud_cases"] == 1
    assert df.loc["PAYMENT", "fraud_cases"] == 0
    assert df["transactions"].sum() == 7
    assert df.loc["TRANSFER", "fraud_rate_pct"] == pytest.approx(50.0)


def test_fraud_by_hour_uses_clock_hour_not_raw_step(con, queries):
    """step counts hours since the simulation began, so step % 24 is the clock hour."""
    df = pd.read_sql_query(queries["fraud_by_hour"], con).set_index("hour")
    assert set(df.index) == {5, 19}
    assert df.loc[5, "fraud_cases"] == 2
    assert df.loc[19, "fraud_cases"] == 0


def test_balance_signature_counts_unmoved_recipient_balances(con, queries):
    df = pd.read_sql_query(queries["balance_signature"], con).set_index("class")
    assert df.loc["Fraudulent", "recipient_unchanged"] == 2
    assert df.loc["Fraudulent", "recipient_unchanged_pct"] == pytest.approx(100.0)
    assert df.loc["Legitimate", "recipient_unchanged"] == 1  # the PAYMENT row


def test_flagged_rule_effectiveness(con, queries):
    row = pd.read_sql_query(queries["flagged_rule_effectiveness"], con).iloc[0]
    assert row["rule_alerts"] == 1
    assert row["rule_true_positives"] == 1
    assert row["fraud_cases"] == 2
    assert row["fraud_caught_pct"] == pytest.approx(50.0)


def test_channel_hour_covers_only_the_two_fraud_channels(con, queries):
    df = pd.read_sql_query(queries["channel_hour"], con)
    assert set(df["channel"]) == {"TRANSFER", "CASH_OUT"}


def test_split_named_queries_drops_the_file_header():
    text = "-- a preamble\n-- name: one\nSELECT 1;\n-- name: two\nSELECT 2;\n"
    assert split_named_queries(text) == {"one": "SELECT 1;", "two": "SELECT 2;"}
