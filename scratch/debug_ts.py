import pandas as pd
import sys
import os
import json
from pathlib import Path
import re
from datetime import datetime

# Adiciona o diretório base para importar smd_config e smd_ai_engine
sys.path.append(os.getcwd())
import smd_config

from smd_build import parse_timesheet, process_tickets_data

print("--- INICIANDO DEBUG TIMESHEET ---")

# 1. Carrega os tickets
D, T, df_raw = process_tickets_data()
if df_raw is None:
    print("ERRO: Falha ao processar tickets.")
    sys.exit(1)

# 2. Executa a extração do timesheet
xls_path = smd_config.DOWNLOADS_DIR / "TimesheetsCMSMonthly.xls"
ts_data = parse_timesheet(xls_path, df_raw)

print(f"Total de entries no timesheet: {len(ts_data)}")

# 3. Analisa as 10 primeiras entradas
count = 0
for k, v in ts_data.items():
    print(f"Key: {k} | Project: '{v['prj']}' | Severity: '{v['sv']}' | Hours: {v['h']}")
    count += 1
    if count >= 10: break

print("--- FIM DO DEBUG ---")
