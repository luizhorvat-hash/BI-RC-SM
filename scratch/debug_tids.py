import pandas as pd
import sys
import os
import json
import re

sys.path.append(os.getcwd())
import smd_config
from smd_build import parse_timesheet, process_tickets_data

D, T, df_raw = process_tickets_data()
xls_path = smd_config.DOWNLOADS_DIR / "TimesheetsCMSMonthly.xls"
ts_data = parse_timesheet(xls_path, df_raw)

# Encontra entradas que NÃO começam com TS- (ou seja, são IDs de ticket)
matched_tids = [k for k in ts_data.keys() if not k.startswith("TS-")]

print(f"Total de tickets vinculados por ID: {len(matched_tids)}")

for k in matched_tids[:10]:
    v = ts_data[k]
    print(f"Ticket: {k} | Project: '{v['prj']}' | Sev: '{v['sv']}' | Hours: {v['h']}")

if not matched_tids:
    print("ALERTA: NENHUM ticket foi vinculado por ID direto.")
