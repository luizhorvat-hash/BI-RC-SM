import pandas as pd
import os

print("--- DIAGNÓSTICO TICKETS.CSV ---")
if os.path.exists('input/tickets.csv'):
    try:
        df = pd.read_csv('input/tickets.csv', sep=';', encoding='utf-8-sig', low_memory=False)
        print(f"Total de tickets: {len(df)}")
        print(f"Projetos: {df['Project Name'].unique()}")
    except Exception as e:
        print(f"Erro ao ler tickets.csv: {e}")
else:
    print("tickets.csv não encontrado em input/")

print("\n--- DIAGNÓSTICO TIMESHEET ---")
ts_path = 'input/TimesheetsCMSMonthly.xls'
if os.path.exists(ts_path):
    try:
        # Tenta ler as primeiras 5 linhas para ver a estrutura
        df_ts = pd.read_excel(ts_path, header=None)
        print(f"Total de linhas no Timesheet: {len(df_ts)}")
        print("Primeiras 2 linhas do Timesheet (amostra de colunas):")
        print(df_ts.head(2).to_string())
    except Exception as e:
        print(f"Erro ao ler Timesheet: {e}")
else:
    print("Timesheet não encontrado em input/")
