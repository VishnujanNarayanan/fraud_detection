"""Streamlit dashboard over the fraud aggregates.

Built to be deployable on Streamlit Community Cloud, which rules out the 471 MB source
CSV: the app reads only the small tracked aggregates in app_data/ (written by
load_sqlite.py from sql/aggregations.sql) plus the figures the notebook already renders.
That keeps one definition of every number across the notebook, the spreadsheet and here.

    streamlit run app.py
"""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

AGG_DIR = "app_data"
FIG_DIR = "figures"

BLUE, ORANGE = "#2a78d6", "#eb6834"

st.set_page_config(page_title="Mobile-money fraud", page_icon="🔎", layout="wide")


@st.cache_data
def load(name: str) -> pd.DataFrame:
    path = os.path.join(AGG_DIR, f"{name}.csv")
    if not os.path.exists(path):
        st.error(f"{path} is missing. Run `python load_sqlite.py` to rebuild it.")
        st.stop()
    return pd.read_csv(path)


def headline() -> None:
    channels = load("channel_mix")
    rule = load("flagged_rule_effectiveness").iloc[0]

    total = int(channels["transactions"].sum())
    fraud = int(channels["fraud_cases"].sum())

    st.title("Where fraud hides in a mobile-money payment log")
    st.caption(
        "Every number below comes from `sql/aggregations.sql`, the same queries behind "
        "the notebook and the spreadsheet report."
    )

    a, b, c, d = st.columns(4)
    a.metric("Transactions", f"{total:,}")
    b.metric("Fraudulent", f"{fraud:,}", f"{100 * fraud / total:.3f}% of all rows")
    c.metric("Channels carrying fraud", int((channels["fraud_cases"] > 0).sum()),
             f"of {len(channels)}")
    d.metric("Caught by the built-in rule", f"{rule['fraud_caught_pct']:.2f}%",
             f"{int(rule['rule_alerts'])} alerts", delta_color="inverse")


def channel_section() -> None:
    df = load("channel_mix")
    st.subheader("Fraud is exclusive to two channels, not merely concentrated in them")
    left, right = st.columns([2, 3])
    with left:
        st.dataframe(
            df.style.format({"transactions": "{:,}", "fraud_cases": "{:,}",
                             "fraud_rate_pct": "{:.4f}%", "mean_amount": "{:,.0f}"}),
            hide_index=True, width="stretch",
        )
    with right:
        st.bar_chart(df.set_index("channel")["fraud_rate_pct"],
                     color=ORANGE, height=320,
                     y_label="Fraud rate (% of that channel)")
    st.caption(
        "Payment, debit and cash-in contain no fraud at all, so three of the five "
        "channels can be discarded before any model is fitted."
    )


def hour_section() -> None:
    hourly = load("fraud_by_hour")
    pivot = load("channel_hour").pivot_table(
        index="hour", columns="channel", values="fraud_rate_pct", aggfunc="sum")

    st.subheader("Time of day beats every raw column")
    peak = hourly.loc[hourly["fraud_rate_pct"].idxmax()]
    trough = hourly.loc[hourly["fraud_rate_pct"].idxmin()]
    st.markdown(
        f"Fraud holds steady around the clock while legitimate volume collapses "
        f"overnight, so the fraud rate swings from **{trough['fraud_rate_pct']:.3f}% "
        f"at {int(trough['hour']):02d}:00** to **{peak['fraud_rate_pct']:.1f}% at "
        f"{int(peak['hour']):02d}:00**."
    )

    by_channel = st.toggle("Split by channel", value=False)
    if by_channel:
        st.line_chart(pivot, height=340, y_label="Fraud rate (%)", x_label="Hour of day")
    else:
        st.line_chart(hourly.set_index("hour")["fraud_rate_pct"], color=ORANGE,
                      height=340, y_label="Fraud rate (%)", x_label="Hour of day")

    hour = st.slider("Inspect an hour", 0, 23, int(peak["hour"]))
    row = hourly.set_index("hour").loc[hour]
    a, b, c = st.columns(3)
    a.metric("Transactions in this hour", f"{int(row['transactions']):,}")
    b.metric("Fraud cases", f"{int(row['fraud_cases']):,}")
    c.metric("Fraud rate", f"{row['fraud_rate_pct']:.3f}%")


def signature_section() -> None:
    sig = load("balance_signature").set_index("class")
    amounts = load("amount_by_class").set_index("class")

    st.subheader("What separates a fraudulent transaction from a legitimate one")
    left, right = st.columns(2)
    with left:
        st.markdown("**The recipient's balance never moves**")
        st.bar_chart(sig["recipient_unchanged_pct"], color=BLUE, height=260,
                     y_label="% of the class")
        st.caption(
            "Money leaves the sender but the recipient balance does not change — an "
            "accounting impossibility in a real ledger, and the model's strongest "
            "single feature."
        )
    with right:
        st.markdown("**Fraudulent transactions are far larger**")
        st.dataframe(
            amounts.style.format({"transactions": "{:,}", "min_amount": "{:,.2f}",
                                  "mean_amount": "{:,.0f}", "max_amount": "{:,.0f}"}),
            width="stretch",
        )


def figures_section() -> None:
    st.subheader("Figures from the analysis")
    picks = {
        "Fraud rate by hour": "10-fraud-rate-by-hour.png",
        "Precision-recall curves": "13-precision-recall-curves.png",
        "Confusion matrix": "15-confusion-matrix.png",
        "Model coefficients": "14-model-coefficients.png",
    }
    available = {k: v for k, v in picks.items()
                 if os.path.exists(os.path.join(FIG_DIR, v))}
    if not available:
        st.info("No figures found. Run the notebook to regenerate `figures/`.")
        return
    choice = st.selectbox("Figure", list(available))
    st.image(os.path.join(FIG_DIR, available[choice]), width="stretch")


def main() -> None:
    headline()
    st.divider()
    channel_section()
    st.divider()
    hour_section()
    st.divider()
    signature_section()
    st.divider()
    figures_section()
    st.caption(
        "Data: PaySim synthetic mobile-money transaction log (CC BY-SA 4.0). "
        "Source: github.com/VishnujanNarayanan/fraud_detection"
    )


if __name__ == "__main__":
    main()
