import pandas as pd
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("C:/Dashboard")
TICKETS_CSV = BASE_DIR / "input" / "tickets.csv"
OUTPUT = BASE_DIR / "scratch" / "_oncall_tmp.json"

def main():
    if not TICKETS_CSV.exists():
        return
    
    df = pd.read_csv(TICKETS_CSV, sep=';', encoding='utf-8-sig')
    df['Opening Date'] = pd.to_datetime(df['Opening Date'], errors='coerce')
    
    oncall_tix = []
    for _, r in df.dropna(subset=['Opening Date']).iterrows():
        dt = r['Opening Date']
        is_weekend = dt.weekday() >= 5
        is_night = dt.hour < 8 or dt.hour > 18 # Horário comercial simplificado 08-18h
        
        if is_weekend or is_night:
            oncall_tix.append(int(r['Ticket']))
            
    res = {
        "count": len(oncall_tix),
        "pct": round(len(oncall_tix) / len(df) * 100, 1) if len(df) > 0 else 0,
        "ids": oncall_tix[:500] # Limite para o dashboard
    }
    
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(res), encoding='utf-8')
    print(f"On-call processado: {len(oncall_tix)} tickets.")

if __name__ == "__main__":
    main()
