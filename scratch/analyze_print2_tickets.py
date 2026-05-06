import pandas as pd
from pathlib import Path

csv_path = Path("c:/Dashboard/input/tickets.csv")
if csv_path.exists():
    df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig', low_memory=False)
    if len(df.columns) < 5:
        df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig', low_memory=False)
    
    df.columns = [str(c).strip() for c in df.columns]
    
    # Tickets que o usuário listou no Print 2 (Mantis)
    target_tickets = [
        "106729", "106930", "107283", "107574", "107645", 
        "107762", "107994", "108150", "108334", "108667", "108708"
    ]
    
    # Garantir que Ticket é string
    df["Ticket"] = df["Ticket"].astype(str)
    
    # Filtrar os tickets alvo
    df_found = df[df["Ticket"].isin(target_tickets)].copy()
    
    print(f"--- ANÁLISE DOS TICKETS DO PRINT 2 (MANTIS) ---")
    print(f"{'TICKET':<10} {'ABERTURA':<20} {'FECHAMENTO':<20} {'MDs':<10}")
    print("-" * 65)
    
    for _, r in df_found.iterrows():
        print(f"{r['Ticket']:<10} {str(r['Opening Date']):<20} {str(r['Close Date']):<20} {str(r.get('MD\'s', '0')):<10}")

    # Ver se algum outro ticket da Chanel abriu em Fev
    chanel_mask = df["Project Name"].str.contains("CHANEL", case=False, na=False)
    df_chanel = df[chanel_mask].copy()
    df_chanel["Opening Date"] = pd.to_datetime(df_chanel["Opening Date"], errors="coerce")
    
    feb_opened = df_chanel[(df_chanel["Opening Date"].dt.month == 2) & (df_chanel["Opening Date"].dt.year == 2026)]
    print(f"\n--- TICKETS DA CHANEL QUE ABRIRAM EM FEV NO SISTEMA ---")
    print(feb_opened[["Ticket", "Opening Date", "MD's"]])
