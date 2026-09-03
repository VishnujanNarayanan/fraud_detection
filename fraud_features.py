"""Feature engineering for the PaySim mobile-money fraud data.

Extracted from the notebook so it can be imported, tested and unpickled elsewhere.
While the transformer was defined in the notebook it belonged to `__main__`, which
meant `fraud_preprocessor.pkl` could only be loaded back by the notebook that wrote
it -- the artefact was unusable from any other process.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.preprocessing import OneHotEncoder, StandardScaler

__all__ = ["FraudPreprocessor"]


class FraudPreprocessor(BaseEstimator, TransformerMixin):
    """Feature engineering for the PaySim fraud data.

    Note on `fit`: an earlier version dropped PAYMENT / DEBIT / CASH_IN rows
    before fitting the encoder and the scaler, while `transform` kept them. That
    left the one-hot encoder knowing only two of the five channels, so the three
    dropped ones silently encoded as all-zeros and `always_nonfraud_type` — which
    is derived from those very columns — was identically 0 for every row. `fit`
    and `transform` now see the same distribution.
    """

    def __init__(self, log_transform=True):
        self.log_transform = log_transform
        self.ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        self.scaler = StandardScaler()
        self.numeric_features = [
            "amount", "oldbalanceOrg", "oldbalanceDest", "newbalanceDest"
        ]  # removed 'newbalanceOrig'
        self.categorical_features = ["type"]

    def fit(self, X, y=None):
        X_ = X.copy()

        # Fit encoder on transaction type
        self.ohe.fit(X_[['type']])

        # Fit scaler on numeric features
        self.scaler.fit(X_[self.numeric_features])
        return self

    def transform(self, X):
        X_ = X.copy()

        # --- Engineered balance features BEFORE dropping ---
        if 'newbalanceOrig' in X_.columns:
            X_['diff_orig'] = X_['oldbalanceOrg'] - X_['newbalanceOrig']
        else:
            X_['diff_orig'] = 0
        X_['diff_dest'] = X_['newbalanceDest'] - X_['oldbalanceDest']

        # --- Drop identifiers + leakage + redundant col ---
        X_.drop(columns=['nameOrig', 'nameDest', 'isFlaggedFraud', 'newbalanceOrig'],
                inplace=True, errors='ignore')

        # --- Time-based features from 'step' ---
        if 'step' in X_.columns:
            X_['hour'] = X_['step'] % 24
            X_['day_of_week'] = X_['step'] % 168
            # Cyclical encoding
            X_['hour_sin'] = np.sin(2 * np.pi * X_['hour'] / 24)
            X_['hour_cos'] = np.cos(2 * np.pi * X_['hour'] / 24)

        # --- One-hot encode transaction type ---
        type_encoded = self.ohe.transform(X_[['type']])
        type_encoded = pd.DataFrame(
            type_encoded,
            columns=self.ohe.get_feature_names_out(['type']),
            index=X_.index
        )
        X_ = pd.concat([X_.drop(columns=['type']), type_encoded], axis=1)

        # --- Always non-fraud type flag ---
        always_safe_types = ['PAYMENT', 'DEBIT', 'CASH_IN']
        X_['always_nonfraud_type'] = X_[type_encoded.columns].filter(
            regex="|".join(always_safe_types), axis=1
        ).sum(axis=1).clip(upper=1)

        # --- Log transform ---
        if self.log_transform and 'amount' in X_.columns:
            X_['log_amount'] = np.log1p(X_['amount'])

        # suspicious if money transferred but dest balance unchanged
        X_['suspicious_flag'] = (
            (X_['amount'] > 0) & (X_['newbalanceDest'] == X_['oldbalanceDest'])
        ).astype(int)

        # error flag for invalid balances
        X_['error_flag'] = (
            (X_['oldbalanceOrg'] < 0) |
            (X_['oldbalanceDest'] < 0) |
            (X_['newbalanceDest'] < 0)
        ).astype(int)

        # --- Scale numeric features ---
        X_[self.numeric_features] = self.scaler.transform(X_[self.numeric_features])

        return X_

