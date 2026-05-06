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
    
    df_chanel["Opening Date"] = pd.to_datetime(df_chanel["Opening Date"], errors="coerce")
    df_chanel["Close Date"] = pd.to_datetime(df_chanel["Close Date"], errors="coerce")
    
    # Analyze February 2026
    month = 2
    year = 2026
    
    # Tickets opened in Feb
    opened_in_feb = df_chanel[(df_chanel["Opening Date"].dt.month == month) & (df_chanel["Opening Date"].dt.year == year)]
    
    # Tickets closed in Feb but opened BEFORE Feb
    backlog_closed_in_feb = df_chanel[(df_chanel["Close Date"].dt.month == month) & (df_chanel["Close Date"].dt.year == year) & (df_chanel["Opening Date"] < pd.Timestamp(year, month, 1))]
    
    # Tickets STILL OPEN in Feb (opened before)
    still_open_in_feb = df_chanel[(df_chanel["Opening Date"] < pd.Timestamp(year, month, 1)) & ((df_chanel["Close Date"].isna()) | (df_chanel["Close Date"] > pd.Timestamp(year, month, 28)))]

    print(f"--- ANÁLISE FEVEREIRO 2026 (CHANEL) ---")
    print(f"Tickets Abertos em Fev: {len(opened_in_feb)}")
    print(f"Tickets de Backlog FINALIZADOS em Fev: {len(backlog_closed_in_feb)}")
    print(f"Tickets de Backlog que CONTINUARAM ABERTOS em Fev: {len(still_open_in_feb)}")
    
    if not backlog_closed_in_feb.empty:
        print("\nSamples of Backlog tickets finished in Feb:")
        print(backlog_closed_in_feb[["Ticket", "Opening Date", "Close Date", "MD's"]].head(10))
