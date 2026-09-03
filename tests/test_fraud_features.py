"""Tests for the feature-engineering transformer.

Every fixture here is synthetic and tiny. The real 471 MB CSV is not in the repo and
must never be a test dependency -- CI has to be able to run on a clean checkout.
"""

import numpy as np
import pandas as pd
import pytest

from fraud_features import FraudPreprocessor

CHANNELS = ["TRANSFER", "CASH_OUT", "PAYMENT", "DEBIT", "CASH_IN"]


@pytest.fixture
def raw():
    """Ten rows covering all five channels and both balance behaviours."""
    return pd.DataFrame({
        "step": [1, 5, 24, 25, 48, 49, 72, 73, 96, 97],
        "type": CHANNELS + CHANNELS,
        "amount": [100.0, 250.0, 30.0, 5.0, 75.0, 900.0, 12.0, 8.0, 60.0, 40.0],
        "oldbalanceOrg": [1000.0, 500.0, 80.0, 20.0, 300.0, 2000.0, 50.0, 30.0, 90.0, 70.0],
        "newbalanceOrig": [900.0, 250.0, 50.0, 15.0, 225.0, 1100.0, 38.0, 22.0, 30.0, 30.0],
        "oldbalanceDest": [0.0, 700.0, 10.0, 5.0, 0.0, 400.0, 60.0, 15.0, 25.0, 0.0],
        # rows 0, 4 and 9 leave the recipient balance untouched
        "newbalanceDest": [0.0, 950.0, 40.0, 10.0, 0.0, 1300.0, 72.0, 23.0, 85.0, 0.0],
        "isFlaggedFraud": [0] * 10,
    })


@pytest.fixture
def fitted(raw):
    return FraudPreprocessor().fit(raw)


def test_fit_returns_self(raw):
    pre = FraudPreprocessor()
    assert pre.fit(raw) is pre


def test_balance_differences(fitted, raw):
    out = fitted.transform(raw)
    expected_orig = raw["oldbalanceOrg"] - raw["newbalanceOrig"]
    expected_dest = raw["newbalanceDest"] - raw["oldbalanceDest"]
    assert np.allclose(out["diff_orig"], expected_orig)
    assert np.allclose(out["diff_dest"], expected_dest)


def test_suspicious_flag_marks_unmoved_recipient_balance(fitted, raw):
    """Money left the sender but the recipient balance never changed."""
    out = fitted.transform(raw)
    assert out["suspicious_flag"].tolist() == [1, 0, 0, 0, 1, 0, 0, 0, 0, 1]


def test_redundant_and_leaking_columns_are_dropped(fitted, raw):
    out = fitted.transform(raw)
    for column in ("newbalanceOrig", "isFlaggedFraud", "type"):
        assert column not in out.columns


def test_one_hot_covers_every_channel_even_a_rare_one(raw):
    """Regression test for the encoder-fitted-on-a-subset bug.

    An earlier version fitted the encoder on a filtered frame, so channels missing
    from the fit encoded as all-zeros at transform time and always_nonfraud_type --
    derived from those very columns -- was identically 0 for every row.
    """
    pre = FraudPreprocessor().fit(raw)
    out = pre.transform(raw)
    for channel in CHANNELS:
        assert f"type_{channel}" in out.columns
    # every row belongs to exactly one channel
    assert (out[[f"type_{c}" for c in CHANNELS]].sum(axis=1) == 1).all()


def test_always_nonfraud_type_flags_the_three_safe_channels(fitted, raw):
    out = fitted.transform(raw)
    safe = raw["type"].isin(["PAYMENT", "DEBIT", "CASH_IN"]).astype(int)
    assert out["always_nonfraud_type"].tolist() == safe.tolist()
    assert out["always_nonfraud_type"].max() <= 1


def test_cyclical_hour_encoding(fitted, raw):
    out = fitted.transform(raw)
    hours = raw["step"] % 24
    assert np.allclose(out["hour_sin"], np.sin(2 * np.pi * hours / 24))
    assert np.allclose(out["hour_cos"], np.cos(2 * np.pi * hours / 24))
    # sin^2 + cos^2 == 1 for every row, whatever the hour
    assert np.allclose(out["hour_sin"] ** 2 + out["hour_cos"] ** 2, 1.0)


def test_log_amount(fitted, raw):
    out = fitted.transform(raw)
    assert np.allclose(out["log_amount"], np.log1p(raw["amount"]))


def test_log_transform_can_be_disabled(raw):
    out = FraudPreprocessor(log_transform=False).fit(raw).transform(raw)
    assert "log_amount" not in out.columns


def test_error_flag_is_zero_without_negative_balances(fitted, raw):
    """PaySim contains no negative balances, so this feature is constant on it."""
    out = fitted.transform(raw)
    assert out["error_flag"].sum() == 0


def test_error_flag_fires_on_a_negative_balance(raw):
    dirty = raw.copy()
    dirty.loc[0, "oldbalanceDest"] = -1.0
    out = FraudPreprocessor().fit(dirty).transform(dirty)
    assert out.loc[0, "error_flag"] == 1


def test_numeric_features_are_scaled(fitted, raw):
    out = fitted.transform(raw)
    for column in fitted.numeric_features:
        assert abs(out[column].mean()) < 1e-9


def test_transform_is_deterministic(fitted, raw):
    a = fitted.transform(raw)
    b = fitted.transform(raw)
    pd.testing.assert_frame_equal(a, b)


def test_transform_does_not_mutate_its_input(fitted, raw):
    before = raw.copy()
    fitted.transform(raw)
    pd.testing.assert_frame_equal(raw, before)


def test_output_is_all_numeric(fitted, raw):
    """The design matrix goes straight into a model, so nothing may stay categorical."""
    out = fitted.transform(raw)
    assert all(np.issubdtype(dtype, np.number) for dtype in out.dtypes)
    assert not out.isnull().values.any()
