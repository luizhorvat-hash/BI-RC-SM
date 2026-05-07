
import pandas as pd
import os

source_file = 'downloads/processed/Incidents_Chanel2026-05-07.csv'
# Testar com as configurações do smd_merge.py
try:
    df = pd.read_csv(source_file, sep=';', encoding='utf-8-sig', low_memory=False)
    print("Read with utf-8-sig success")
except:
    df = pd.read_csv(source_file, sep=';', encoding='latin-1', low_memory=False)
    print("Read with latin-1 success")

print("\nColunas do arquivo de origem:")
print(df.columns.tolist())

print("\nDados do ticket 112735 no DataFrame lido:")
row = df[df['Ticket'].astype(str) == '112735']
if not row.empty:
    print(row.iloc[0].to_dict())
else:
    print("Ticket 112735 não encontrado!")
