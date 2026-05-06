import pandas as pd
from pathlib import Path

csv_path = Path("c:/Dashboard/input/tickets.csv")
if csv_path.exists():
    df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig', low_memory=False)
    if len(df.columns) < 5:
        df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig', low_memory=False)
    
    df.columns = [str(c).strip() for c in df.columns]
    
    # Filter for Chanel
    # Need to handle potential mapping in CSV if it was already mapped
    chanel_mask = df["Project Name"].str.contains("CHANEL", case=False, na=False)
    df_chanel = df[chanel_mask].copy()
    
    df_chanel["Close Date"] = pd.to_datetime(df_chanel["Close Date"], errors="coerce")
    
    # Filter for 2026
    df_chanel_2026 = df_chanel[df_chanel["Close Date"].dt.year == 2026].copy()
    
    print(f"Total Chanel tickets closed in 2026: {len(df_chanel_2026)}")
    
    if not df_chanel_2026.empty:
        df_chanel_2026["Month"] = df_chanel_2026["Close Date"].dt.month
        # Check MD's field
        md_col = "MD's" if "MD's" in df_chanel_2026.columns else None
        if md_col:
            summary = df_chanel_2026.groupby("Month")[md_col].sum()
            print("MD's sum by month (Closed Date):")
            print(summary)
            
            # Look at a few rows
            print("\nSample rows:")
            print(df_chanel_2026[["Ticket", "Status", "Close Date", md_col]].head(10))
        else:
            print("Column 'MD's' NOT found in CSV")
