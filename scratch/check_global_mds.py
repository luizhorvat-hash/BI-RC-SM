import pandas as pd
from pathlib import Path

csv_path = Path("c:/Dashboard/input/tickets.csv")
if csv_path.exists():
    df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig', low_memory=False)
    if len(df.columns) < 5:
        df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig', low_memory=False)
    
    df.columns = [str(c).strip() for c in df.columns]
    
    md_col = "MD's"
    if md_col in df.columns:
        # Convert to numeric to count non-zeros
        df["MD_num"] = pd.to_numeric(df[md_col].astype(str).str.replace(",", "."), errors="coerce").fillna(0)
        filled = df[df["MD_num"] > 0]
        print(f"Total tickets with MD's > 0: {len(filled)}")
        print("Breakdown by Project Name:")
        print(filled["Project Name"].value_counts())
    else:
        print("MD's column not found")
