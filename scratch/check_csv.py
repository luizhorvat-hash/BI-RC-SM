import pandas as pd
import numpy as np

try:
    df = pd.read_csv(r'c:\Dashboard\input\tickets.csv', sep=';', encoding='utf-8-sig', low_memory=False)
    print(f"Total rows: {len(df)}")
    print(f"Columns: {df.columns.tolist()}")
    
    if 'Problem' in df.columns:
        print(f"With Problem: {df['Problem'].notna().sum()}")
        print("Sample Problem values:", df['Problem'].dropna().unique()[:5])
    else:
        print("Column 'Problem' NOT FOUND")
        
    if "MD's" in df.columns:
        mds = pd.to_numeric(df["MD's"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        print(f"MDs > 0: {(mds > 0).sum()}")
        print(f"Total MD sum: {mds.sum()}")
    else:
        print("Column 'MD's' NOT FOUND")

except Exception as e:
    print(f"Error: {e}")
