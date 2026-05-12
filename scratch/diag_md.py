import pandas as pd
import numpy as np

try:
    df = pd.read_csv('input/tickets.csv', sep=';', encoding='utf-8-sig', low_memory=False)
    # Tenta identificar a coluna MD's (pode ter variações de encoding)
    md_cols = [c for c in df.columns if 'MD' in c]
    print(f"Colunas encontradas com 'MD': {md_cols}")
    
    for col in md_cols:
        # Converte para numérico, tratando vírgulas se necessário
        vals = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        greater_zero = (vals > 0).sum()
        total_val = vals.sum()
        print(f"Coluna: {col} | Tickets > 0: {greater_zero} | Soma Total: {total_val}")

except Exception as e:
    print(f"Erro: {e}")
