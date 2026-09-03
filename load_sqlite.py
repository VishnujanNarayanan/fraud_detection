"""Load the PaySim transaction log into SQLite and run the project's aggregations.

The exploratory numbers in this project used to live only inside the notebook, which
made them impossible to reuse: the spreadsheet report and the dashboard would each
have had to recompute them and could drift apart. They now have one definition, in
`sql/aggregations.sql`, and everything downstream reads the results from here.

    python load_sqlite.py                 # build fraud.db, run queries, write CSVs
    python load_sqlite.py --skip-build    # re-run the queries against an existing db

Building reads the 471 MB CSV in chunks so peak memory stays well under a gigabyte.
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3

import pandas as pd

CSV = "Fraud.csv"
DB = "fraud.db"
SCHEMA = os.path.join("sql", "schema.sql")
QUERIES = os.path.join("sql", "aggregations.sql")
AGG_DIR = "app_data"

#: The identifier columns are deliberately absent -- see sql/schema.sql.
COLUMNS = ["step", "type", "amount", "oldbalanceOrg", "newbalanceOrig",
           "oldbalanceDest", "newbalanceDest", "isFraud", "isFlaggedFraud"]

CHUNK = 500_000


def split_named_queries(sql_text: str) -> dict[str, str]:
    """Split a .sql file into {name: statement} on its `-- name:` markers.

    Anything before the first marker is treated as a file header and dropped, so
    the queries file can carry an explanatory preamble.
    """
    parts = re.split(r"^--\s*name:\s*(\w+)\s*$", sql_text, flags=re.MULTILINE)
    return {parts[i]: parts[i + 1].strip() for i in range(1, len(parts) - 1, 2)}


def build(csv_path: str = CSV, db_path: str = DB) -> int:
    """Create the database from the CSV. Returns the row count loaded."""
    if not os.path.exists(csv_path):
        raise SystemExit(
            f"{csv_path} not found. Download it from Kaggle first -- see the README."
        )

    if os.path.exists(db_path):
        os.remove(db_path)

    con = sqlite3.connect(db_path)
    try:
        con.executescript(open(SCHEMA, encoding="utf8").read())
        rows = 0
        reader = pd.read_csv(csv_path, usecols=COLUMNS, chunksize=CHUNK)
        for chunk in reader:
            chunk[COLUMNS].to_sql("transactions", con, if_exists="append", index=False)
            rows += len(chunk)
            print(f"  loaded {rows:,} rows", end="\r", flush=True)
        con.commit()
        print(f"  loaded {rows:,} rows")
    finally:
        con.close()
    return rows


def run_queries(db_path: str = DB, sql_path: str = QUERIES) -> dict[str, pd.DataFrame]:
    """Run every named query in `sql_path` and return the results by name."""
    queries = split_named_queries(open(sql_path, encoding="utf8").read())
    con = sqlite3.connect(db_path)
    try:
        return {name: pd.read_sql_query(sql, con) for name, sql in queries.items()}
    finally:
        con.close()


def export(results: dict[str, pd.DataFrame], out_dir: str = AGG_DIR) -> list[str]:
    """Write each result to a small CSV the report and the dashboard can read."""
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name, df in results.items():
        path = os.path.join(out_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        written.append(path)
    return written


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-build", action="store_true",
                    help="reuse an existing fraud.db instead of rebuilding it")
    args = ap.parse_args()

    if not args.skip_build:
        print(f"Building {DB} from {CSV}")
        build()

    print(f"Running {QUERIES}")
    results = run_queries()
    for path in export(results):
        print(f"  wrote {path}")

    print()
    print(results["channel_mix"].to_string(index=False))


if __name__ == "__main__":
    main()
