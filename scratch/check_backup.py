import pandas as pd
import sys

file = sys.argv[1]
try:
    df = pd.read_csv(file, sep=';', encoding='utf-8-sig', low_memory=False)
    mds = pd.to_numeric(df["MD's"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
    print(f"File: {file}")
    print(f"Total rows: {len(df)}")
    print(f"MDs > 0: {(mds > 0).sum()}")
    print(f"Problems linked: {df['Problem'].notna().sum()}")
except Exception as e:
    print(f"Error {file}: {e}")
