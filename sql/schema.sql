-- Schema for the PaySim mobile-money transaction log.
--
-- The two identifier columns (nameOrig, nameDest) are not loaded: they hold ~6.3M
-- distinct values each, carry no signal, and triple the size of the database.
--
-- Column meanings are the dataset authors' own -- see Data Dictionary.txt.

DROP TABLE IF EXISTS transactions;

CREATE TABLE transactions (
    step            INTEGER NOT NULL,  -- hours since the start of the simulation
    type            TEXT    NOT NULL,  -- CASH_IN, CASH_OUT, DEBIT, PAYMENT, TRANSFER
    amount          REAL    NOT NULL,
    oldbalanceOrg   REAL    NOT NULL,  -- sender balance before
    newbalanceOrig  REAL    NOT NULL,  -- sender balance after
    oldbalanceDest  REAL    NOT NULL,  -- recipient balance before
    newbalanceDest  REAL    NOT NULL,  -- recipient balance after
    isFraud         INTEGER NOT NULL,  -- ground truth
    isFlaggedFraud  INTEGER NOT NULL   -- the simulated business rule's own verdict
);

-- Every aggregation below filters or groups on one of these three.
CREATE INDEX idx_transactions_type   ON transactions (type);
CREATE INDEX idx_transactions_fraud  ON transactions (isFraud);
CREATE INDEX idx_transactions_hour   ON transactions (step % 24);
