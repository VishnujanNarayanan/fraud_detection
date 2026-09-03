-- The exploratory aggregations behind the project's findings, as SQL.
--
-- Each query is named by a `-- name:` marker so load_sqlite.py can run them
-- individually and hand each result back as a DataFrame. Keeping them here
-- rather than inline in the notebook means the numbers in the report, the
-- spreadsheet and the dashboard all come from one definition.

-- name: channel_mix
-- Volume, fraud count and fraud rate for every transaction channel.
SELECT
    type                                             AS channel,
    COUNT(*)                                         AS transactions,
    SUM(isFraud)                                     AS fraud_cases,
    ROUND(100.0 * SUM(isFraud) / COUNT(*), 4)        AS fraud_rate_pct,
    ROUND(AVG(amount), 2)                            AS mean_amount
FROM transactions
GROUP BY type
ORDER BY fraud_cases DESC, transactions DESC;

-- name: fraud_by_hour
-- Fraud rate against hour of the simulated day. `step` counts hours, so
-- step % 24 recovers the clock hour. This is the strongest signal in the data.
SELECT
    step % 24                                        AS hour,
    COUNT(*)                                         AS transactions,
    SUM(isFraud)                                     AS fraud_cases,
    ROUND(100.0 * SUM(isFraud) / COUNT(*), 4)        AS fraud_rate_pct
FROM transactions
GROUP BY step % 24
ORDER BY hour;

-- name: amount_by_class
-- How far apart the two classes sit on transaction size.
SELECT
    CASE isFraud WHEN 1 THEN 'Fraudulent' ELSE 'Legitimate' END AS class,
    COUNT(*)                                         AS transactions,
    ROUND(MIN(amount), 2)                            AS min_amount,
    ROUND(AVG(amount), 2)                            AS mean_amount,
    ROUND(MAX(amount), 2)                            AS max_amount
FROM transactions
GROUP BY isFraud
ORDER BY isFraud;

-- name: balance_signature
-- The accounting impossibility that turned out to be the model's best feature:
-- money leaves the sender but the recipient's balance never moves.
SELECT
    CASE isFraud WHEN 1 THEN 'Fraudulent' ELSE 'Legitimate' END AS class,
    COUNT(*)                                         AS transactions,
    SUM(CASE WHEN amount > 0 AND newbalanceDest = oldbalanceDest
             THEN 1 ELSE 0 END)                      AS recipient_unchanged,
    ROUND(100.0 * SUM(CASE WHEN amount > 0 AND newbalanceDest = oldbalanceDest
             THEN 1 ELSE 0 END) / COUNT(*), 2)       AS recipient_unchanged_pct
FROM transactions
GROUP BY isFraud
ORDER BY isFraud;

-- name: flagged_rule_effectiveness
-- What the dataset's own built-in fraud rule actually catches.
SELECT
    SUM(isFlaggedFraud)                              AS rule_alerts,
    SUM(CASE WHEN isFlaggedFraud = 1 AND isFraud = 1 THEN 1 ELSE 0 END) AS rule_true_positives,
    SUM(isFraud)                                     AS fraud_cases,
    ROUND(100.0 * SUM(CASE WHEN isFlaggedFraud = 1 AND isFraud = 1 THEN 1 ELSE 0 END)
          / SUM(isFraud), 3)                         AS fraud_caught_pct
FROM transactions;
