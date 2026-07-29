<h1 align="center">Fraud Detection on Mobile-Money Transactions</h1>

<p align="center">
  Detecting fraudulent transfers in 6.36M PaySim mobile-money transactions, where fraud is
  1 row in 775 — and showing why the ROC-AUC everyone reports for this dataset is misleading.
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white">
  <img alt="pandas" src="https://img.shields.io/badge/pandas-2.3-150458?logo=pandas&logoColor=white">
  <img alt="scikit-learn" src="https://img.shields.io/badge/scikit--learn-1.7-F7931E?logo=scikitlearn&logoColor=white">
  <img alt="matplotlib" src="https://img.shields.io/badge/matplotlib-3.10-11557C">
  <img alt="Licence" src="https://img.shields.io/badge/licence-MIT-green">
</p>

---

## Results

<p align="center"><img src="figures/10-fraud-rate-by-hour.png" width="88%"></p>

Fraud runs at a near-constant ~342 cases an hour while legitimate volume collapses overnight.
The result is a 422× swing in fraud rate between 05:00 (22.3%) and 19:00 (0.053%) — the
strongest single signal in the dataset, and one no raw column exposes.

<p align="center"><img src="figures/13-precision-recall-curves.png" width="88%"></p>

Precision-recall separates the three models; ROC does not. Average precision falls from
**0.744** (all engineered features) to **0.018** (amount alone) against **0.0013** for a
random classifier.

<p align="center"><img src="figures/15-confusion-matrix.png" width="88%"></p>

The cost of 95.4% recall at the default threshold: 40,637 false positives, so only 1 alert
in 27 is real.

| Model | ROC-AUC | Avg precision | Precision | Recall | F1 |
|---|---|---|---|---|---|
| Amount only (baseline) | 0.7870 | 0.0184 | 0.0027 | 0.7243 | 0.0054 |
| **All engineered features** | **0.9947** | **0.7440** | 0.0371 | 0.9537 | 0.0715 |
| Reduced feature set | 0.9946 | 0.7355 | 0.0361 | 0.9556 | 0.0696 |

Logistic regression, `class_weight="balanced"`, scored on a held-out 20% split
(1,272,524 transactions, 1,643 fraudulent). All 15 figures are in [`figures/`](figures/).

## Dataset

**PaySim** — an agent-based simulation of mobile-money transactions calibrated on a real
African mobile-money service, published as
[Synthetic Financial Datasets For Fraud Detection](https://www.kaggle.com/datasets/ealaxi/paysim1)
(Lopez-Rojas et al.), licensed **CC BY-SA 4.0**.

| | |
|---|---|
| Rows × columns | 6,362,620 × 11 |
| File | `Fraud.csv`, 471 MB |
| Period | 743 hourly steps ≈ 31 simulated days |
| Target | `isFraud` — 8,213 positives (0.129%) |
| Missing values | none |

The CSV is **not in this repo** (it is gitignored). Download it from the Kaggle link above
and place `Fraud.csv` in the repository root. Column definitions are in
[`Data Dictionary.txt`](Data%20Dictionary.txt).

## Approach

1. **Load** — read with the `pyarrow` engine and drop the two high-cardinality identifier
   columns (`nameOrig`, `nameDest`) at parse time. Takes the 471 MB read from ~30s to under 2s.
2. **Explore** — 11 figures covering class imbalance, channel mix, amount and balance
   distributions by class, correlation structure, hour-of-day fraud rate, and the
   balance-update signature. Chi-square (type vs fraud) and Mann–Whitney U (amount) both
   return p < 1e-300.
3. **Engineer** — `diff_orig` / `diff_dest` (balance movements), `suspicious_flag` (money
   left the sender but the recipient balance never moved), cyclical hour encodings,
   one-hot channel dummies, and `log_amount`. `newbalanceOrig` is dropped for perfect
   collinearity with `oldbalanceOrg` (r = 1.00).
4. **Model** — three logistic-regression variants (amount-only baseline, all engineered
   features, reduced set) fitted on 5.09M rows in float32 to stay inside 7 GB of RAM.
5. **Evaluate** — ROC and precision-recall curves, standardised coefficients, and a
   confusion matrix at the 0.50 threshold.

## Installation and usage

```bash
git clone https://github.com/VishnujanNarayanan/fraud_detection.git
cd fraud_detection

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Place Fraud.csv (from Kaggle) in the repository root, then:
jupyter notebook Fraud_Detection_Model.ipynb
```

To regenerate every figure in `figures/` non-interactively (~70s end to end):

```bash
python3 -c "
import nbformat as nbf
from nbclient import NotebookClient
nb = nbf.read('Fraud_Detection_Model.ipynb', as_version=4)
NotebookClient(nb, timeout=2400, resources={'metadata': {'path': '.'}}).execute()
nbf.write(nb, 'Fraud_Detection_Model.ipynb')
"
```

## Project structure

```
.
├── Fraud_Detection_Model.ipynb   # the analysis: EDA -> features -> 3 models -> 15 figures
├── viz_style.py                  # shared matplotlib style: palette, rcParams, tick formatters
├── figures/                      # 15 PNGs at 1600x1000, written by the notebook
├── Data Dictionary.txt           # column definitions from the dataset authors
├── requirements.txt              # runtime dependencies
├── Fraud.csv                     # NOT in git - download from Kaggle
└── fraud_preprocessor.pkl        # NOT in git - written by the notebook
```

## Findings

- **Fraud is exclusive to two channels, not merely concentrated in them.** All 8,213 fraud
  cases are `TRANSFER` (0.769% of transfers) or `CASH_OUT` (0.184%). `PAYMENT`, `DEBIT` and
  `CASH_IN` contain zero fraud across 3.6M rows, so three of five channels can be discarded
  before modelling.
- **Time of day beats every raw column.** Fraud volume is flat at ~342 cases/hour around the
  clock while legitimate traffic swings 500× (1,241 transactions at 04:00 against 647,814 at
  19:00). That alone drives the fraud rate from 0.053% to 22.3%.
- **The strongest engineered feature is an accounting impossibility.** In 49.6% of fraudulent
  transactions money leaves the sender but the recipient's balance never changes, against
  36.4% of legitimate ones. It carries the second-largest positive coefficient in the model.
- **ROC-AUC is the wrong metric here and hides a 40× difference.** The amount-only baseline
  scores a respectable-looking 0.787 ROC-AUC but only 0.018 average precision — barely
  distinguishable from random once the 1.27M easy negatives stop counting. Reporting ROC-AUC
  alone on this dataset would make a near-useless model look defensible.
- **Two engineered features are provably dead.** `error_flag` is identically 0 (PaySim
  contains no negative balances at all) and its fitted coefficient is exactly 0.000;
  `always_nonfraud_type` is an exact linear combination of the three never-fraud channel
  dummies. Both are dropped from the reduced model at no measurable cost (AP 0.7440 → 0.7355).
- **The dataset's own rule catches almost nothing.** `isFlaggedFraud` fires on 16 transactions.
  All 16 are genuine fraud, but that is 0.19% of the 8,213 cases present.

## Licence

[MIT](LICENSE). The PaySim dataset is separately licensed CC BY-SA 4.0 by its authors.
