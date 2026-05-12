import pandas as pd
import numpy as np
from pathlib import Path

CURRENT = Path(r'c:\Dashboard\input\tickets.csv')
BACKUP = Path(r'c:\Dashboard\input\backups\tickets_20260430_090123.csv')
OUTPUT = Path(r'c:\Dashboard\input\tickets.csv')

def recover():
    print(f"Lendo arquivo atual: {CURRENT}")
    df_cur = pd.read_csv(CURRENT, sep=';', encoding='utf-8-sig', low_memory=False)
    df_cur['_priority'] = 1
    
    print(f"Lendo backup de recuperação: {BACKUP}")
    df_bak = pd.read_csv(BACKUP, sep=';', encoding='utf-8-sig', low_memory=False)
    df_bak['_priority'] = 2
    
    merged = pd.concat([df_cur, df_bak], ignore_index=True)
    
    # Coalesce logic
    merged = merged.replace(r'^\s*$', np.nan, regex=True)
    
    # Sort: Current first
    merged['Ticket'] = merged['Ticket'].astype(str).str.lstrip('0')
    merged = merged.sort_values(['_priority'], ascending=[True])
    
    print("Consolidando dados...")
    final = merged.groupby('Ticket', as_index=False, sort=False).first()
    
    # Cleanup
    if '_priority' in final.columns:
        final = final.drop(columns=['_priority'])
    
    print(f"Salvando resultado em: {OUTPUT}")
    final.to_csv(OUTPUT, sep=';', encoding='utf-8-sig', index=False)
    print("Recuperação concluída!")

if __name__ == "__main__":
    recover()
