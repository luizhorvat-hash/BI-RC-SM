#!/usr/bin/env python3
"""
smd_build.py — Pipeline de atualização do SMD Dashboard
Arrocha | 2026
"""

import os, sys, json, logging, re, math, subprocess
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict
import xml.etree.ElementTree as ET
import pandas as pd
import smd_config
from smd_ai_engine import SMDAIEngine

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(smd_config.BASE_DIR / "smd_build.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ── AUXILIARES ───────────────────────────────────────────────────────────────
def normalize_project(name):
    """Normaliza o nome do projeto (primeira palavra, lowercase) para reconciliação."""
    if not name: return ""
    # Pega a primeira palavra, remove caracteres especiais e converte para lower
    first_word = re.sub(r'[^a-zA-Z0-9]', '', str(name).split()[0])
    return first_word.lower()

# ── PROCESSAMENTO DE TIMESHEET ────────────────────────────────────────────────
DE_PARA_PROJETOS = {
    "PARFOIS (PT) CMS 2025": "Parfois",
    "Farmatodo (PT) CMS 2024": "Farmatodo",
    "TATA (DE) CMS 2024": "Tata",
    "ARROCHA (MX) CMS 2025": "Farmacia Arrocha",
    "GDN (DE) CMS 2025": "GDN",
    "CHANEL (BR) CMS 2025": "Chanel"
}

# Mapeamento completo: nome no timesheet → projeto do dashboard
TIMESHEET_PROJECT_MAP = {
    # Chanel
    "CHANEL (BR) CMS 2024": "Chanel",
    "CHANEL (BR) CMS 2024 Change Requests": "Chanel",
    "CHANEL (BR) CMS 2025": "Chanel",
    "CHANEL (BR) Reforma Tributaria - Xstore": "Chanel",
    # Farmacia Arrocha
    "ARROCHA (MX) CMS 2025": "Farmacia Arrocha",
    "ARROCHA (MX) CMS 2025 Change Requests": "Farmacia Arrocha",
    "ARROCHA (MX) Improvements 2025": "Farmacia Arrocha",
    # Farmatodo
    "Farmatodo (PT) CMS 2024": "Farmatodo",
    "Farmatodo (PT) Agile 2024": "Farmatodo",
    "Farmatodo (PT) Improvements": "Farmatodo",
    "FARMATODO (PT) CMS 2024 Change Requests": "Farmatodo",
    "FARMATODO (PT) AR RWMS Implementation": "Farmatodo",
    # GDN
    "GDN (DE) CMS 2025": "GDN",
    # Parfois
    "PARFOIS (PT) 2025": "Parfois",
    "PARFOIS (PT) Apps Evolution 2026": "Parfois",
    "PARFOIS (PT) CMS 2025": "Parfois",
    "PARFOIS (PT) Consultoria Xstore 2026": "Parfois",
    "PARFOIS (PT) FIL Team 2025": "Parfois",
    "PARFOIS (PT) MOM Move to Cloud": "Parfois",
    "PARFOIS (PT) MOM Move to Cloud - RDT": "Parfois",
    "PARFOIS (PT) Pequenas Acoes 2025": "Parfois",
    "PARFOIS (PT) Pequenas Acoes 2026": "Parfois",
    "PARFOIS (PT) Stream MOM": "Parfois",
    "PARFOIS (PT) Waving 3.0": "Parfois",
    "RC (PT) PARFOIS": "Parfois",
    # Sonae RDF
    "SONAE (PT) CMS Planning 2023": "Sonae RDF",
    "SONAE (PT) MDM Genesis": "Sonae RDF",
    "SONAE (PT) Pequenas Acoes 2025": "Sonae RDF",
    "SONAE (PT) Pequenas Acoes 2026": "Sonae RDF",
    "SONAE (PT) Resource Assignment T&M 2025": "Sonae RDF",
    "SONAE (PT) Resource Assignment T&M 2026": "Sonae RDF",
    "SONAE (PT) SPLIT Maxmat Data Migration": "Sonae RDF",
    "SONAE (PT) SPLIT Maxmat MW 2025": "Sonae RDF",
    "SONAE (PT) Suporte MDM 2025": "Sonae RDF",
    "SONAE (PT) Suporte MDM 2026": "Sonae RDF",
    "SONAE (PT) Worten Darwin Migracao Vistex 2025": "Sonae RDF",
    "SONAE (PT) Worten Park Orders": "Sonae RDF",
    "SONAE (PT) Worten Receitas 2026": "Sonae RDF",
    "RC (PT) SONAE": "Sonae RDF",
    # Tata
    "TATA (DE) CMS 2024": "Tata",
    "TIA (MX) CMS 2025": "Tata",
    "Tata Tia (MX) TIA CMS 2021": "Tata",
}

# ── UTILITÁRIOS DE TIMESHEET ──────────────────────────────────────────────────
def get_ts_path():
    """Busca o arquivo de timesheet (.xlsx ou .xls) nos locais padrão."""
    for ext in [".xlsx", ".xls"]:
        p = smd_config.INPUT_DIR / f"TimesheetsCMSMonthly{ext}"
        if p.exists(): return p
        p = smd_config.DOWNLOADS_DIR / f"TimesheetsCMSMonthly{ext}"
        if p.exists(): return p
    return None

def parse_timesheet_tab(path):
    """
    Lê o timesheet e agrega por projeto-dashboard / ano / mês.
    Suporta .xls (XML 2003) e .xlsx (Pandas).
    """
    if not path or not path.exists():
        log.warning(f"Timesheet não encontrado.")
        return {}

    log.info(f"Gerando dados da aba Timesheet de {path.name}...")
    import pandas as pd
    from collections import defaultdict

    # acumuladores: [prj][year][month] → dicts
    acc = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        "total_h": 0.0, "total_days": 0.0, "overtime_h": 0.0,
        "staff": defaultdict(float),
        "tasks": defaultdict(float),
        "subs":  defaultdict(float),
        "sub_projects": defaultdict(float),
        "weekly": defaultdict(float),
    })))

    def process_row(row_data, acc):
        prj_ts = row_data.get(2, "") or ""
        task   = row_data.get(4, "") or ""
        staff  = row_data.get(7, "") or ""
        week_s = row_data.get(8, "") or ""
        sub    = row_data.get(24, "") or ""

        try:
            wk_h  = float(row_data.get(22) or 0)
            wk_d  = float(row_data.get(23) or 0)
            sat_h = float(row_data.get(14) or 0)
            sun_h = float(row_data.get(16) or 0)
            
            if math.isnan(wk_h): wk_h = 0
            if math.isnan(wk_d): wk_d = 0
            if math.isnan(sat_h): sat_h = 0
            if math.isnan(sun_h): sun_h = 0
        except (ValueError, TypeError):
            return

        if wk_h <= 0 or not prj_ts or not staff:
            return

        dash_prj = TIMESHEET_PROJECT_MAP.get(prj_ts)
        if not dash_prj:
            return

        try:
            if isinstance(week_s, str):
                dt = datetime.fromisoformat(week_s[:10])
            else:
                dt = week_s
            
            if pd.isnull(dt) or not isinstance(dt, (datetime, date)):
                return
                
            year  = str(dt.year)
            month = f"{dt.month:02d}"
            week_key = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
        except Exception:
            return

        for prj in [dash_prj, "Todos"]:
            b = acc[prj][year][month]
            b["total_h"]   += wk_h
            b["total_days"] += wk_d
            b["overtime_h"] += sat_h + sun_h
            b["staff"][staff]   += wk_h
            b["tasks"][task]    += wk_h
            b["subs"][sub]      += wk_h
            b["sub_projects"][prj_ts] += wk_h
            b["weekly"][week_key]     += wk_h

    # --- LEITURA DOS DADOS ---
    if path.suffix.lower() == ".xlsx":
        try:
            df_ts = pd.read_excel(path, header=None)
            for i, row in df_ts.iterrows():
                row_dict = {idx+1: val for idx, val in enumerate(row)}
                process_row(row_dict, acc)
        except Exception as e:
            log.error(f"Erro ao ler XLSX via Pandas: {e}")
            return {}
    else:
        # Tenta ler como XML Spreadsheet 2003
        try:
            ns_tag = '{urn:schemas-microsoft-com:office:spreadsheet}'
            ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
            context = ET.iterparse(str(path), events=('end',))
            for event, elem in context:
                if elem.tag == f'{ns_tag}Row':
                    cells_raw = elem.findall(f'{ns_tag}Cell', ns)
                    if not cells_raw:
                        elem.clear(); continue
                    row_data = {}
                    cur_idx = 1
                    for cell in cells_raw:
                        idx_attr = cell.get(f'{ns_tag}Index')
                        if idx_attr: cur_idx = int(idx_attr)
                        d = cell.find(f'{ns_tag}Data', ns)
                        row_data[cur_idx] = d.text if d is not None else None
                        cur_idx += 1 + int(cell.get(f'{ns_tag}MergeAcross', 0))
                    elem.clear()
                    process_row(row_data, acc)
        except Exception as e:
            log.warning(f"Parser XML falhou ({e}), tentando via Pandas/Openpyxl...")
            try:
                df = pd.read_excel(path, header=None)
                for _, row in df.iterrows():
                    row_data = {i+1: val for i, val in enumerate(row)}
                    process_row(row_data, acc)
            except Exception as e2:
                log.error(f"Falha total ao ler Timesheet: {e2}")
                return {}


    # Converter defaultdicts para dicts serializáveis
    result = {}
    for prj, years in acc.items():
        result[prj] = {}
        for yr, months in years.items():
            result[prj][yr] = {}
            for mo, b in months.items():
                headcount = len(b["staff"])
                top_staff = sorted(
                    [{"name": n, "h": round(h, 1)} for n, h in b["staff"].items()],
                    key=lambda x: -x["h"])[:8]
                top_tasks = sorted(
                    [{"task": t, "h": round(h, 1)} for t, h in b["tasks"].items()],
                    key=lambda x: -x["h"])[:8]
                by_sub = {s: round(h, 1) for s, h in sorted(b["subs"].items(), key=lambda x: -x[1])}
                sub_projects = sorted(
                    [{"name": n, "h": round(h, 1)} for n, h in b["sub_projects"].items()],
                    key=lambda x: -x["h"])[:10]
                weekly = [{"week": w, "h": round(h, 1)}
                          for w, h in sorted(b["weekly"].items())]

                avg_h = round(b["total_h"] / headcount, 1) if headcount else 0
                result[prj][yr][mo] = {
                    "total_h":    round(b["total_h"], 1),
                    "total_days": round(b["total_days"], 1),
                    "overtime_h": round(b["overtime_h"], 1),
                    "headcount":  headcount,
                    "avg_h_per_staff": avg_h,
                    "top_staff":  top_staff,
                    "top_tasks":  top_tasks,
                    "by_subsidiary": by_sub,
                    "sub_projects": sub_projects,
                    "weekly": weekly,
                }

    log.info(f"Aba Timesheet: {len(result)} projetos, anos={sorted({yr for p in result.values() for yr in p})}")
    return result

def parse_timesheet(path, tickets_df):
    """Lê o arquivo XLS (XML) de timesheet e gera mapeamento granular D.timesheet."""
    if not path.exists():
        log.warning(f"Arquivo de timesheet não encontrado: {path}")
        return {}

    log.info(f"Processando timesheet estrito (ID-based) de {path}...")
    import pandas as pd
    try:
        # Mapa de tickets {id: {sv, pr, prj}}
        ticket_map = {}
        for _, r in tickets_df.iterrows():
            tk_raw = r.get('Ticket')
            if pd.isna(tk_raw): continue
            tk_id = str(int(pd.to_numeric(tk_raw, errors='coerce')))
            ticket_map[tk_id] = {
                'sv': str(r.get('Severity', 'incident')).lower().replace(' ', '_'),
                'prj': str(r.get('Project Name', 'Other')).strip()
            }

        ts_final = {} # { tid: { prj, sv, months: { "Y-M": hours }, staff: { name: hours } } }
        ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
        stats = {"match_ticket": 0, "ignored": 0}

        def process_ts_row(row_data):
            nonlocal stats
            try:
                hc = row_data.get(22)
                dc = row_data.get(23)
                hours = float(hc) if hc and not pd.isnull(hc) else 0
                days  = float(dc) if dc and not pd.isnull(dc) else 0
                
                if math.isnan(hours): hours = 0
                if math.isnan(days): days = 0
                
                if hours <= 0 and days <= 0: return

                staff_name = row_data.get(7, "Unknown")
                desc_col   = str(row_data.get(4, ""))
                ref_col    = str(row_data.get(20, ""))
                week_iso   = str(row_data.get(8, ""))
                
                # 1. Match Ticket ID (Regra Estrita)
                tid_col    = str(row_data.get(3, ""))
                search_text = f"{tid_col} {desc_col} {ref_col}"
                ids_found = re.findall(r'(\d{4,7})', search_text)
                
                t_meta = None
                tid_match = None
                if ids_found:
                    for tid in ids_found:
                        if tid in ticket_map:
                            t_meta = ticket_map[tid]
                            tid_match = tid
                            break
                
                if not t_meta:
                    stats["ignored"] += 1
                    return

                # 2. Determinar Período (Ano-Mes)
                try: 
                    # Trata tanto string ISO quanto objeto datetime do pandas
                    if isinstance(week_iso, str):
                        dt = datetime.fromisoformat(week_iso[:19])
                    else:
                        dt = week_iso
                    mk = f"{dt.year}-{dt.month:02d}"
                except: 
                    mk = datetime.now().strftime("%Y-%m")

                # 3. Agrupar
                if tid_match not in ts_final:
                    ts_final[tid_match] = {
                        'prj': t_meta['prj'],
                        'sv': t_meta['sv'],
                        'periods': {}
                    }
                
                entry = ts_final[tid_match]
                if mk not in entry['periods']:
                    entry['periods'][mk] = {'h': 0, 'd': 0, 'staff': {}}
                
                p = entry['periods'][mk]
                p['h'] += hours
                p['d'] += days
                p['staff'][staff_name] = p['staff'].get(staff_name, 0) + hours
                stats["match_ticket"] += 1
            except: pass

        # --- LEITURA DOS DADOS ---
        if path.suffix.lower() == ".xlsx":
            try:
                df_ts = pd.read_excel(path, header=None)
                for _, row in df_ts.iterrows():
                    process_ts_row({idx+1: val for idx, val in enumerate(row)})
                log.info(f"Timesheet XLSX concluído: {len(ts_final)} tickets vinculados. Status: {stats}")
            except Exception as e:
                log.error(f"Erro ao ler XLSX: {e}")
                return {}
        else:
            # Tenta ler como XML
            try:
                context = ET.iterparse(str(path), events=('end',))
                for event, elem in context:
                    if elem.tag == '{urn:schemas-microsoft-com:office:spreadsheet}Row':
                        cells_raw = elem.findall('{urn:schemas-microsoft-com:office:spreadsheet}Cell', ns)
                        if not cells_raw:
                            elem.clear(); continue
                        
                        row_data = {}
                        current_idx = 1
                        for cell in cells_raw:
                            idx_attr = cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                            if idx_attr: current_idx = int(idx_attr)
                            data_elem = cell.find('{urn:schemas-microsoft-com:office:spreadsheet}Data', ns)
                            row_data[current_idx] = data_elem.text if data_elem is not None else None
                            current_idx += 1 + int(cell.get('{urn:schemas-microsoft-com:office:spreadsheet}MergeAcross', 0))
                        
                        process_ts_row(row_data)
                        elem.clear()
                log.info(f"Timesheet concluído: {len(ts_final)} tickets vinculados. Status: {stats}")
            except Exception as e:
                log.error(f"Erro ao processar timesheet: {e}")
                return {}

        return ts_final
    except Exception as e:
        log.error(f"Erro ao processar timesheet granular: {e}")
        return {}

# ── PROCESSAMENTO DE TICKETS ──────────────────────────────────────────────────
def process_tickets_data():
    """Lê o CSV e gera as estruturas D e T robustas."""
    if not smd_config.TICKETS_CSV.exists():
        log.error(f"CSV não encontrado: {smd_config.TICKETS_CSV}")
        return None, None, None

    log.info(f"Processando tickets de {smd_config.TICKETS_CSV}...")
    try:
        df = pd.read_csv(smd_config.TICKETS_CSV, sep=';', encoding='utf-8-sig', low_memory=False)
        if len(df.columns) < 5:
             df = pd.read_csv(smd_config.TICKETS_CSV, sep=',', encoding='utf-8-sig', low_memory=False)
        log.info(f"Colunas detectadas no CSV: {df.columns.tolist()}")
    except Exception as e:
        log.error(f"Falha ao ler CSV: {e}")
        return None, None, None

    df.columns = [str(c).strip() for c in df.columns]
    def col(name, default=""):
        return df[name] if name in df.columns else pd.Series([default]*len(df))

    df["Severity"]  = col("Severity","unknown").fillna("unknown").astype(str).str.lower().str.strip()
    df["Status"]    = col("Status","unknown").fillna("unknown").astype(str).str.lower().str.strip()
    df["Priority"]  = col("Priority","P4").fillna("P4").astype(str).str.strip()
    df["Project Name"] = col("Project Name","Unknown").fillna("Unknown").astype(str).str.strip()
    
    ts_cols = ["Opening Date", "Close Date", "Date of Resolution", "Last Updated Date"]
    for c in ts_cols:
        df[c] = pd.to_datetime(col(c), errors="coerce", format="ISO8601")
        mask = df[c].isna() & col(c).notna()
        if mask.any():
            df.loc[mask, c] = pd.to_datetime(df.loc[mask, c].fillna(col(c)), errors="coerce", dayfirst=True)

    valid_dates = df["Opening Date"].dropna()
    if not valid_dates.empty:
        log.info(f"Range de dados: {valid_dates.min().strftime('%d/%m/%Y')} até {valid_dates.max().strftime('%d/%m/%Y')}")
    log.info(f"Total de tickets carregados: {len(df)}")

    CLOSED = {"closed","resolved","rejected"}
    MY_BK  = {"acknowledged","assigned_for_analysis","assigned_for_dev","waiting_for_prioritization","assigned_for_testing","pending_required_fields"}
    CLI_BK = {"waiting_client_feedback","waiting_client_prd_inst","waiting_client_tests","waiting_client_tst_inst","waiting_oracle_feedback"}
    
    df["Is_Closed"] = df["Status"].isin(CLOSED)
    df["Is_Open"]   = ~df["Is_Closed"]
    df["BK_Owner"]  = df["Status"].apply(lambda s: "RC" if s in MY_BK else ("Client" if s in CLI_BK else "Other"))
    
    today = datetime.now()
    df["Days_BK"]  = (today - df["Opening Date"]).dt.days.fillna(0).astype(int)
    df["Days_Upd"] = (today - df["Last Updated Date"]).dt.days.fillna(999).astype(int)

    def fmt_date(ts):
        return ts.strftime("%Y-%m-%d") if pd.notnull(ts) else ""

    SEVS = ["incident","user_request","problem","change_request","internal"]
    TF   = ["k","eid","pr","sv","st","op","res","cl","ap","en","su","upd","ass","sl","rc","rct","rs","prj","y_o","m_o","d_o","y_c","m_c","d_c","sev"]

    rows_out = []; idx_out = {}
    monthly  = {sv: {} for sv in SEVS}; daily = {sv: {} for sv in SEVS}; ym = defaultdict(set)

    for _, r in df.iterrows():
        tk = int(pd.to_numeric(r["Ticket"], errors="coerce") or 0)
        sv = r["Severity"] if r["Severity"] in SEVS else "internal"
        if r["Severity"] == "request_for_change": sv = "change_request"
        if r["Severity"] == "user request": sv = "user_request"
        
        sl_ack = pd.to_numeric(r.get("Acknowledge SLA"), errors="coerce")
        sl_res = pd.to_numeric(r.get("Resolution SLA"), errors="coerce")
        
        row = [
            tk, str(r.get("External ID", "")), str(r["Priority"]), sv, str(r["Status"]),
            fmt_date(r["Opening Date"]), fmt_date(r["Date of Resolution"]), fmt_date(r["Close Date"]),
            str(r.get("Application", "N/A")) if pd.notna(r.get("Application")) else "N/A", str(r.get("Environment", "N/A")).upper(),
            str(r.get("Summary", ""))[:120], fmt_date(r["Last Updated Date"]),
            str(r.get("assigned", "")), float(sl_ack) if pd.notna(sl_ack) else None,
            str(r.get("Root Cause Source", "N/A")) if pd.notna(r.get("Root Cause Source")) else "N/A", 
            str(r.get("Root Cause Type", "N/A")) if pd.notna(r.get("Root Cause Type")) else "N/A",
            float(sl_res) if pd.notna(sl_res) else None, str(r["Project Name"]),
            int(r["Opening Date"].year) if pd.notnull(r["Opening Date"]) else 0,
            int(r["Opening Date"].month) if pd.notnull(r["Opening Date"]) else 0,
            int(r["Opening Date"].day) if pd.notnull(r["Opening Date"]) else 0,
            int(r["Close Date"].year) if pd.notnull(r["Close Date"]) else 0,
            int(r["Close Date"].month) if pd.notnull(r["Close Date"]) else 0,
            int(r["Close Date"].day) if pd.notnull(r["Close Date"]) else 0,
            str(r["Severity"]).lower()
        ]
        idx_out[str(tk)] = len(rows_out)
        rows_out.append(row)

        if pd.notnull(r["Opening Date"]):
            yo, mo, do = r["Opening Date"].year, r["Opening Date"].month, r["Opening Date"].day
            mk = f"{yo}-{mo:02d}"
            ym[str(yo)].add(mo)
            if mk not in monthly[sv]: monthly[sv][mk] = {"opened":0,"closed":0,"o_ids":[],"c_ids":[]}
            monthly[sv][mk]["opened"] += 1
            monthly[sv][mk]["o_ids"].append(tk)
            if mk not in daily[sv]: daily[sv][mk] = {"opened":{},"closed":{},"o_ids":{},"c_ids":{}}
            ds = str(do)
            daily[sv][mk]["opened"][ds] = daily[sv][mk]["opened"].get(ds,0) + 1
            daily[sv][mk]["o_ids"].setdefault(ds,[]).append(tk)

        if r["Is_Closed"] and pd.notnull(r["Close Date"]):
            yc, mc, dc = r["Close Date"].year, r["Close Date"].month, r["Close Date"].day
            mkc = f"{yc}-{mc:02d}"
            if mkc not in monthly[sv]: monthly[sv][mkc] = {"opened":0,"closed":0,"o_ids":[],"c_ids":[]}
            monthly[sv][mkc]["closed"] += 1
            monthly[sv][mkc]["c_ids"].append(tk)
            if mkc not in daily[sv]: daily[sv][mkc] = {"opened":{},"closed":{},"o_ids":{},"c_ids":{}}
            ds2 = str(dc)
            daily[sv][mkc]["closed"][ds2] = daily[sv][mkc]["closed"].get(ds2,0) + 1
            daily[sv][mkc]["c_ids"].setdefault(ds2,[]).append(tk)

    backlog = {sv: {"rc": {"total": 0, "tickets": []}, "client": {"total": 0, "tickets": []}} for sv in SEVS}
    for sv in SEVS:
        sub = df[(df["Severity"]==sv) & df["Is_Open"]]
        for _, r in sub.iterrows():
            tk_id = int(pd.to_numeric(r["Ticket"], errors="coerce") or 0)
            owner = "rc" if r["BK_Owner"] == "RC" else ("client" if r["BK_Owner"] == "Client" else None)
            if owner:
                backlog[sv][owner]["total"] += 1
                backlog[sv][owner]["tickets"].append({
                    "ticket": tk_id, "status": str(r["Status"]), "days": int(r["Days_BK"]),
                    "days_upd": int(r["Days_Upd"]), "opened": fmt_date(r["Opening Date"]),
                    "priority": str(r["Priority"]), "summary": str(r["Summary"])[:60], "project": str(r["Project Name"])
                })
        for owner in ["rc","client"]: backlog[sv][owner]["tickets"].sort(key=lambda x: x["days"], reverse=True)

    sla = {}
    env_mask = df["Environment"].astype(str).str.upper().str.strip().isin(["PRD", "PRODUÇÃO", "PROD"])
    sla_df = df[(df["Severity"]=="incident") & env_mask & df["Is_Closed"] & df["Resolution SLA"].notna() & df["Opening Date"].notna()].copy()
    log.info(f"Tickets elegíveis para SLA (Incident+PRD+Closed): {len(sla_df)}")
    for pri, lim, tgt in [("P1",360,98),("P2",720,95),("P3",1920,95),("P4",2880,95)]:
        g = sla_df[sla_df["Priority"]==pri]
        if len(g) == 0: continue
        met = int((g["Resolution SLA"] > 0).sum())
        total = len(g)
        tix = []
        for _, r in g.iterrows():
            tix.append({
                "tid": int(r["Ticket"]), "rs": round(float(r["Resolution SLA"]),1),
                "met": 1 if r["Resolution SLA"] > 0 else 0, "op": fmt_date(r["Opening Date"]),
                "ap": str(r.get("Application", "N/A"))[:30], "s": str(r.get("Summary", ""))[:50],
                "y": int(r["Close Date"].year) if pd.notnull(r["Close Date"]) else int(r["Opening Date"].year),
                "m": int(r["Close Date"].month) if pd.notnull(r["Close Date"]) else int(r["Opening Date"].month),
                "prj": str(r["Project Name"])
            })
        sla[pri] = {"total":total,"met":met,"not_met":total-met, "pct":round(met/total*100,1),
                    "target":tgt,"lim_min":lim,"avg_actual":round(float(g["Resolution SLA"].mean()),1),"tickets":tix}

    def rc_group(s):
        s = str(s).strip().lower()
        if s in ("client","client - rollout"): return "Client"
        if s == "rc": return "RC"
        if s in ("problem analysis","not identified"): return "Problem Analysis"
        if s == "oracle": return "Oracle"
        return "Outros"

    rc_dist = {sv: {} for sv in SEVS}
    for sv in SEVS:
        sub = df[df["Severity"]==sv].copy()
        if len(sub) == 0: continue
        sub["RCG"] = sub["Root Cause Source"].apply(rc_group)
        for g, gg in sub.groupby("RCG"):
            rc_dist[sv][str(g)] = {"count":int(len(gg)), "pct":round(len(gg)/len(sub)*100,1), "ids":gg["Ticket"].dropna().astype(int).tolist()}

    summary = {"total_registered": int(len(df)), "total_open": int(df["Is_Open"].sum()), "projects": sorted(df["Project Name"].dropna().unique().tolist())}
    for sv in SEVS:
        sub = df[df["Severity"]==sv]
        summary[sv] = {"registered":len(sub), "closed":int(sub["Is_Closed"].sum()), "open":int(sub["Is_Open"].sum())}

    cur_y, cur_m = today.year, today.month
    prev_m = cur_m - 1 if cur_m > 1 else 12
    prev_y = cur_y if cur_m > 1 else cur_y - 1
    cur_mk, prev_mk = f"{cur_y}-{cur_m:02d}", f"{prev_y}-{prev_m:02d}"
    comp = {sv: {
        "ab": {"cur": monthly[sv].get(cur_mk,{}).get("opened",0), "prev": monthly[sv].get(prev_mk,{}).get("opened",0)},
        "cl": {"cur": monthly[sv].get(cur_mk,{}).get("closed",0), "prev": monthly[sv].get(prev_mk,{}).get("closed",0)}
    } for sv in SEVS}
    for sv in SEVS:
        for k in ["ab","cl"]:
            cur, prev = comp[sv][k]["cur"], comp[sv][k]["prev"]
            comp[sv][k]["var"] = round((cur-prev)/prev*100,1) if prev>0 else None

    ts_path = get_ts_path()
    timesheet = parse_timesheet(ts_path, df)

    mttr_stats = {}
    inc_df = df[df["Severity"] == "incident"].copy()
    inc_closed = inc_df[inc_df["Is_Closed"] & inc_df["Close Date"].notna()].copy()
    for pri in ["P1", "P2", "P3", "P4"]:
        g = inc_closed[inc_closed["Priority"] == pri]
        if len(g) > 0:
            durations = (g["Close Date"] - g["Opening Date"]).dt.total_seconds() / 3600
            durations = durations[durations >= 0]
            if len(durations) > 0:
                mttr_stats[pri] = {"median": round(float(durations.median()), 1), "mean": round(float(durations.mean()), 1),
                                   "std": round(float(durations.std()), 1) if len(durations) > 1 else 0, "count": int(len(durations)),
                                   "bench": smd_config.MTTR_BENCHMARK_H.get(pri, 0)}

    D = {"monthly": monthly, "daily": daily, "backlog": backlog, "sla": sla, "rc": rc_dist, "summary": summary, "comp": comp, 
         "ym": {y:sorted(list(m)) for y,m in ym.items()}, "projects": summary["projects"], "timesheet": timesheet, 
         "generated_at": today.strftime("%Y-%m-%d %H:%M"), "mttr_stats": mttr_stats}
    T = {"fields": TF, "rows": rows_out, "idx": idx_out}
    return D, T, df

def run_pipeline(skip_agents=False):
    log.info("=" * 60)
    log.info(f"SMD DASHBOARD BUILD — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    log.info("=" * 60)
    D, T, df_raw = process_tickets_data()
    if D is None: return
    ai_insights = {}
    if skip_agents and smd_config.DATA_JS.exists():
        try:
            content = smd_config.DATA_JS.read_text(encoding="utf-8")
            for line in content.splitlines():
                if line.startswith("var AI_INSIGHTS ="):
                    json_str = line.replace("var AI_INSIGHTS =", "").strip().rstrip(";")
                    loaded = json.loads(json_str)
                    if loaded and "Todos" in loaded:
                        ai_insights = loaded
                    elif loaded:
                        ai_insights = {"Todos": loaded}
                    break
        except Exception:
            pass
    if not skip_agents:
        try:
            engine = SMDAIEngine()
            projects = ["Todos"] + sorted(df_raw["Project Name"].dropna().unique().tolist())
            for prj in projects:
                if prj == "Todos":
                    df_prj = df_raw.copy()
                else:
                    df_prj = df_raw[df_raw["Project Name"] == prj].copy()
                
                if df_prj.empty: continue
                ctx = engine.build_context_data(df_prj)
                ai_insights[prj] = {}
                
                for agent in ["ops", "predictive", "improvement", "market", "qa", "triage"]:
                    try: 
                        res = engine.run_agent(agent, ctx)
                        ai_insights[prj][agent] = res
                    except Exception as e: 
                        log.error(f"Falha no agente {agent} ({prj}): {e}")
        except Exception as ge: 
            log.error(f"Erro geral no motor de IA: {ge}")
    
    # Timesheet por projeto/ano/mês (aba dedicada)
    ts_path = get_ts_path()
    timesheet_tab = parse_timesheet_tab(ts_path)
    
    # Restauração do KPI de Oncall
    oncall_data = {}
    try:
        log.info("Processando dados de On-call...")
        subprocess.run([sys.executable, str(smd_config.BASE_DIR / "scratch" / "gen_oncall.py")], 
                       capture_output=True, text=True, check=True)
        oncall_file = smd_config.BASE_DIR / "scratch" / "_oncall_tmp.json"
        if oncall_file.exists():
            oncall_data = json.loads(oncall_file.read_text(encoding="utf-8"))
    except Exception as oe:
        log.error(f"Erro ao processar On-call: {oe}")

    log.info(f"Salvando data.js...")
    content = [f"var SMD_DATA_D = {json.dumps(D, ensure_ascii=False, separators=(',',':'))};",
               f"var SMD_DATA_T = {json.dumps(T, ensure_ascii=False, separators=(',',':'))};",
               f"var AI_INSIGHTS = {json.dumps(ai_insights, ensure_ascii=False, separators=(',',':'))};",
               f"var SMD_TIMESHEET = {json.dumps(timesheet_tab, ensure_ascii=False, separators=(',',':'))};",
               f"var SMD_ONCALL = {json.dumps(oncall_data, ensure_ascii=False, separators=(',',':'))};"]
    smd_config.DATA_JS.write_text("\n".join(content), encoding="utf-8")
    log.info("Build concluído.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-agents", action="store_true")
    run_pipeline(skip_agents=parser.parse_args().no_agents)
