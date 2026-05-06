import pandas as pd
from pathlib import Path

csv_path = Path("c:/Dashboard/input/tickets.csv")
if csv_path.exists():
    df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig', low_memory=False)
    if len(df.columns) < 5:
        df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig', low_memory=False)
    
    df.columns = [str(c).strip() for c in df.columns]
    
    # Filter for Chanel
    chanel_mask = df["Project Name"].str.contains("CHANEL", case=False, na=False)
    df_chanel = df[chanel_mask].copy()
    
    # Check if MD's has any non-null values
    md_col = "MD's"
    if md_col in df_chanel.columns:
        valid_mds = df_chanel[df_chanel[md_col].notna()]
        print(f"Chanel tickets with MD's filled: {len(valid_mds)}")
        if not valid_mds.empty:
            print(valid_mds[["Ticket", "Status", "Close Date", md_col]].head(20))
    else:
        print("MD's column not found")
