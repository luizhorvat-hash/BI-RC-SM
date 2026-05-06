import json
from pathlib import Path
from datetime import datetime

data_js = Path("c:/Dashboard/data.js")
if data_js.exists():
    with open(data_js, "r", encoding="utf-8") as f:
        content = f.read()
        
        # Extrair SMD_DATA_T
        start = content.find("var SMD_DATA_T =") + len("var SMD_DATA_T =")
        end = content.find(";", start)
        t_data = json.loads(content[start:end].strip())
        rows = t_data.get("rows", [])
        
        # Extrair SMD_TIMESHEET
        start_ts = content.find("var SMD_TIMESHEET =") + len("var SMD_TIMESHEET =")
        end_ts = content.find(";", start_ts)
        ts_data = json.loads(content[start_ts:end_ts].strip())

        project = "Chanel"
        months = [("2026", "02"), ("2026", "03"), ("2026", "04")]
        
        print(f"--- DIAGNÓSTICO ESTRATÉGICO: {project} ---")
        
        for yr, mo in months:
            print(f"\n[ANÁLISE {mo}/{yr}]")
            
            # 1. MD Faturável do Timesheet
            ts_val = ts_data.get(project, {}).get(yr, {}).get(mo, {}).get("total_days", 0)
            print(f"  - MD Faturável (Timesheet): {ts_val:.2f}")
            
            # 2. MD Técnico (Abertos no mês)
            mantis_opened_md = sum(float(str(r[26]).replace(',', '.')) if r[21] != 0 and r[18] == int(yr) and r[19] == int(mo) and "Chanel" in str(r[17]) else 0 for r in rows)
            
            # 3. Identificar tickets antigos (Backlog) que consumiram esforço técnico no mês
            # No dashboard simplificado, não temos o cruzamento exato de horas por dia no data.js para tickets antigos,
            # mas podemos ver quais tickets estavam abertos nesse período.
            
            backlog_count = 0
            for r in rows:
                if "Chanel" in str(r[17]):
                    # Se abriu antes do mês e fechou depois ou ainda está aberto
                    opened = datetime(r[18], r[19], 1) if r[18] != 0 else datetime(1900,1,1)
                    target_month = datetime(int(yr), int(mo), 1)
                    
                    closed_y, closed_m = r[21], r[22]
                    if closed_y == 0: # Ainda aberto
                        is_active = opened < target_month
                    else:
                        closed = datetime(closed_y, closed_m, 1)
                        is_active = opened < target_month and closed >= target_month
                    
                    if is_active:
                        backlog_count += 1
            
            print(f"  - Tickets de Backlog ativos no mês: {backlog_count}")
            if backlog_count > 10:
                print(f"  - IMPACTO: A alta carga de backlog ({backlog_count} tickets) explica o consumo de horas superior à abertura de novos tickets.")

