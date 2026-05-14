#!/usr/bin/env python3
"""
smd_build.py — Pipeline de atualização do SMD Dashboard
Arrocha | 2026
"""

import os, sys, json, logging, re, math
import subprocess
from datetime import datetime, date, timedelta
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
import pandas as pd
import numpy as np
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
# (Mapeamentos agora carregados via smd_config.py -> smd_projects.json)

# ── UTILITÁRIOS DE TIMESHEET ──────────────────────────────────────────────────
def get_ts_path():
    """Busca o arquivo de timesheet nos locais padrão."""
    # Procura por qualquer arquivo que comece com TimesheetsCMSMonthly e termine com xls/xlsx
    search_dirs = [smd_config.INPUT_DIR, smd_config.DOWNLOADS_DIR]
    for d in search_dirs:
        if not d.exists(): continue
        for p in d.glob("TimesheetsCMSMonthly*"):
            if p.suffix.lower() in [".xlsx", ".xls"]:
                return p
    return None

def normalize_name(n):
    """Normaliza o nome do recurso removendo sufixos e espaços extras."""
    if not n: return ""
    n = str(n)
    # Remove sufixos como _PTN, _BR, etc.
    n = re.sub(r'_[A-Z]{2,3}$', '', n)
    return n.strip().lower()

def get_resource_grade_map():
    """Lê o arquivo Resource Level.xlsx e retorna um mapeamento de nomes para Career Grade."""
    res_path = smd_config.RESOURCE_LEVEL_FILE
    if not res_path.exists():
        log.warning(f"Arquivo de Resource Level não encontrado em {res_path}. Usando apenas correções manuais.")
        return smd_config.MANUAL_RESOURCE_FIXES

    try:
        import pandas as pd
        df = pd.read_excel(res_path)
        mapping = {}
        for _, r in df.iterrows():
            full_name = str(r.get("Name", "")).strip().lower()
            grade = str(r.get("Career Grade", "N/A")).strip()
            if full_name:
                mapping[full_name] = grade
                # Também mapeia pelo primeiro + último nome para maior flexibilidade
                parts = full_name.split()
                if len(parts) > 1:
                    short = f"{parts[0]} {parts[-1]}"
                    if short not in mapping: mapping[short] = grade
        
        # Adiciona mapeamentos manuais configurados
        mapping.update(smd_config.MANUAL_RESOURCE_FIXES)

        log.info(f"Carregados {len(mapping)} mapeamentos de Career Grade.")
        return mapping
    except Exception as e:
        log.error(f"Erro ao carregar Resource Level: {e}")
        return {}

def _read_timesheet_file(path, row_processor):
    """Lê um arquivo de timesheet (.xlsx ou .xls/xml) e chama row_processor para cada linha."""
    if path.suffix.lower() == ".xlsx":
        try:
            xl = pd.ExcelFile(path)
            sheet = 'Report' if 'Report' in xl.sheet_names else xl.sheet_names[0]
            df_ts = pd.read_excel(xl, sheet_name=sheet, header=None)
            for _, row in df_ts.iterrows():
                row_processor({idx: val for idx, val in enumerate(row)})
        except Exception as e:
            log.error(f"Erro XLSX: {path.name} — {e}")
    else:
        try:
            ns_tag = '{urn:schemas-microsoft-com:office:spreadsheet}'
            ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
            for event, elem in ET.iterparse(str(path), events=('end',)):
                if elem.tag == f'{ns_tag}Row':
                    cells = elem.findall(f'{ns_tag}Cell', ns)
                    row_data = {}; cur_idx = 1
                    for cell in cells:
                        idx_attr = cell.get(f'{ns_tag}Index')
                        if idx_attr: cur_idx = int(idx_attr)
                        d = cell.find(f'{ns_tag}Data', ns)
                        row_data[cur_idx] = d.text if d is not None else None
                        cur_idx += 1 + int(cell.get(f'{ns_tag}MergeAcross', 0))
                    row_processor(row_data)
                    elem.clear()
        except Exception as e:
            log.error(f"Erro XML: {path.name} — {e}")


def parse_timesheet_unified(paths, tickets_df=None):
    """
    Versão unificada e otimizada de parsing de Timesheet.
    Aceita um Path único ou lista de Paths.
    Lê os arquivos e gera:
    1. Agregação por Projeto/Ano/Mês (Dashboard Tab)
    2. Agregação por Ticket ID (Visão Granular)
    """
    # Normalizar entrada para lista
    if isinstance(paths, Path):
        paths = [paths]
    elif paths is None:
        paths = []
    valid_paths = [p for p in paths if p and p.exists()]
    if not valid_paths:
        log.warning("Nenhum arquivo de timesheet válido para processar.")
        return {}, {}

    log.info(f"Iniciando parsing unificado de Timesheet: {len(valid_paths)} arquivo(s)...")
    import pandas as pd
    from collections import defaultdict
    import re

    # 1. Preparar mapas de apoio
    ticket_info_map = {}
    if tickets_df is not None:
        for _, r in tickets_df.iterrows():
            tk_raw = r.get('Ticket')
            if pd.isna(tk_raw): continue
            try:
                tk_id = str(int(pd.to_numeric(tk_raw, errors='coerce')))
                ticket_info_map[tk_id] = {
                    "pr": str(r.get('Priority', 'P4')).strip(),
                    "sv": str(r.get('Severity', 'incident')).strip(),
                    "prj": smd_config.TIMESHEET_PROJECT_MAP.get(str(r.get('Project Name', 'Other')).strip(), str(r.get('Project Name', 'Other')).strip()),
                    "st": str(r.get('Status', 'New')).strip(),
                    "iv": str(r.get('Invoice', '')).strip()
                }
            except: continue

    grade_map = get_resource_grade_map()

    # 2. Acumuladores
    acc_tab = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        "total_h": 0.0, "total_days": 0.0, "overtime_h": 0.0,
        "staff": defaultdict(float), "tasks": defaultdict(float), "subs":  defaultdict(float),
        "by_priority": defaultdict(lambda: {"md": 0.0, "tix": defaultdict(float)}),
        "by_sev_prio": defaultdict(lambda: defaultdict(lambda: {"md": 0.0, "tix": set()})),
        "weekly": defaultdict(float), "grades": defaultdict(float),
        "staff_detailed": defaultdict(lambda: {"h": 0.0, "d": 0.0, "sub": "", "grade": ""}),
    })))
    acc_gran = {}

    def process_row_unified(row_data):
        prj_ts = row_data.get(1, "") or ""
        task   = row_data.get(3, "") or ""
        staff  = row_data.get(6, "") or ""
        week_s = row_data.get(7, "") or ""
        sub    = row_data.get(23, "") or ""
        ref_col = str(row_data.get(19, ""))

        try:
            wk_h = float(row_data.get(21) or 0)
            if math.isnan(wk_h) or wk_h <= 0 or not prj_ts or not staff: return
        except: return

        prj_ts_clean = str(prj_ts).strip()
        dash_prj = smd_config.TIMESHEET_PROJECT_MAP.get(prj_ts_clean, prj_ts_clean)

        try:
            dt = datetime.fromisoformat(week_s[:10]) if isinstance(week_s, str) else week_s
            if pd.isnull(dt) or not isinstance(dt, (datetime, date)): return
        except: return

        s_norm = normalize_name(staff)
        grade = grade_map.get(s_norm, "N/A")

        search_text = f"{ref_col} {task}"
        ids_found = re.findall(r'(\d{4,7})', search_text)
        
        tid_match, t_meta = None, None
        if ids_found:
            for tid in ids_found:
                if tid in ticket_info_map:
                    tid_match = tid
                    t_meta = ticket_info_map[tid]
                    break

        day_indices = [9, 10, 11, 13, 14, 15, 17]
        for idx, i in enumerate(day_indices):
            h = row_data.get(i, 0)
            try:
                h = float(h or 0)
                if math.isnan(h) or h <= 0: continue
            except: continue
            
            day_date = dt + timedelta(days=idx)
            dy, dm = str(day_date.year), f"{day_date.month:02d}"
            dw, mk = f"{dy}-W{day_date.isocalendar()[1]:02d}", f"{dy}-{dm}"
            d_md = h / 8.0
            is_overtime = (i >= 15)

            for prj in [dash_prj, "Todos"]:
                b = acc_tab[prj][dy][dm]
                b["total_h"] += h; b["total_days"] += d_md
                if is_overtime: b["overtime_h"] += h
                b["staff"][staff] += h; b["tasks"][task] += h; b["subs"][sub] += h
                
                priority = t_meta["pr"] if t_meta else "N/A"
                severity = t_meta["sv"] if t_meta else "N/A"
                
                bp = b["by_priority"][priority]
                bp["md"] += d_md
                if tid_match:
                    bp["tix"][tid_match] += d_md
                    if severity != "N/A":
                        sp = b["by_sev_prio"][severity][priority]
                        sp["md"] += d_md; sp["tix"].add(tid_match)

                b["weekly"][dw] += h; b["grades"][grade] += d_md
                sd = b["staff_detailed"][staff]
                sd["h"] += h; sd["d"] += d_md; sd["sub"] = sub; sd["grade"] = grade

            if tid_match:
                if tid_match not in acc_gran:
                    acc_gran[tid_match] = {'prj': t_meta['prj'], 'sv': t_meta['sv'], 'pr': t_meta['pr'], 'st': t_meta['st'], 'iv': t_meta['iv'], 'periods': {}}
                p = acc_gran[tid_match]['periods'].setdefault(mk, {'h': 0, 'd': 0, 'staff': {}})
                p['h'] += h; p['d'] += d_md
                p['staff'][staff] = p['staff'].get(staff, 0) + h

    # Processar todos os arquivos (acumuladores compartilhados)
    for file_path in valid_paths:
        log.info(f"  Processando: {file_path.name}...")
        _read_timesheet_file(file_path, process_row_unified)

    result_tab = {}
    for prj, years in acc_tab.items():
        result_tab[prj] = {}
        for yr, months in years.items():
            result_tab[prj][yr] = {}
            for mo, b in months.items():
                headcount = len(b["staff"])
                top_staff = sorted([{"name": n, "h": round(h, 1)} for n, h in b["staff"].items()], key=lambda x: -x["h"])[:8]
                top_tasks = sorted([{"task": t, "h": round(h, 1)} for t, h in b["tasks"].items()], key=lambda x: -x["h"])[:8]
                by_sub = {s: round(h, 1) for s, h in sorted(b["subs"].items(), key=lambda x: -x[1])}
                by_priority = []
                for p_name, p_data in b["by_priority"].items():
                    by_priority.append({"name": p_name, "d": round(p_data["md"], 2), "tix": sorted([{"id": tid, "md": round(m, 2)} for tid, m in p_data["tix"].items()], key=lambda x: -x["md"])})
                by_priority.sort(key=lambda x: x["name"])
                by_sev_prio = {sv: {pr: {"md": round(d["md"], 2), "n": len(d["tix"])} for pr, d in prios.items()} for sv, prios in b["by_sev_prio"].items()}
                weekly = [{"week": w, "h": round(h, 1)} for w, h in sorted(b["weekly"].items())]
                by_grade = {g: round(d, 2) for g, d in sorted(b["grades"].items(), key=lambda x: -x[1])}
                grade_details = {}
                for name, d in b["staff_detailed"].items():
                    grade_details.setdefault(d["grade"], []).append({"name": name, "sub": d["sub"], "h": round(d["h"], 1), "d": round(d["d"], 2)})
                for g in grade_details: grade_details[g].sort(key=lambda x: -x["d"], reverse=True)
                result_tab[prj][yr][mo] = {
                    "total_h": round(b["total_h"], 1), "total_days": round(b["total_days"], 1), "overtime_h": round(b["overtime_h"], 1),
                    "headcount": headcount, "avg_h_per_staff": round(b["total_h"] / headcount, 1) if headcount else 0,
                    "top_staff": top_staff, "top_tasks": top_tasks, "by_subsidiary": by_sub, "by_career_grade": by_grade,
                    "grade_details": grade_details, "by_priority": by_priority, "by_sev_prio": by_sev_prio, "weekly": weekly,
                }
    log.info(f"Timesheet unificado: {len(result_tab)} projetos processados.")
    return result_tab, acc_gran

# ── PROCESSAMENTO DE TICKETS ──────────────────────────────────────────────────
def process_tickets_data(csv_override=None):
    """Lê o CSV e gera as estruturas D e T robustas."""
    csv_path = Path(csv_override) if csv_override else smd_config.TICKETS_CSV
    if not csv_path.exists():
        log.error(f"CSV não encontrado: {csv_path}")
        return None, None, None

    log.info(f"Processando tickets de {csv_path}...")
    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig', low_memory=False)
        if len(df.columns) < 5:
             df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig', low_memory=False)
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
    
    date_cols = ["Opening Date", "Date of Resolution", "Close Date", "Last Updated Date"]
    for col_name in date_cols:
        if col_name in df.columns:
            # Converte garantindo que formatos DD/MM/YYYY (comuns no Mantis) sejam priorizados,
            # mas mantendo suporte a YYYY-MM-DD (comuns no histórico).
            d_ser = df[col_name].astype(str).replace(['nan', 'NaT', 'None', ''], np.nan)
            
            # Estratégia de conversão robusta:
            # 1. Tenta formato ISO (YYYY-MM-DD) primeiro, que é inequívoco.
            v_iso = pd.to_datetime(d_ser, format='ISO8601', errors='coerce')
            
            # 2. Tenta formatos com dia primeiro apenas para o que não é ISO
            # Para evitar UserWarning, passamos apenas as linhas que falharam no ISO
            failed_iso = v_iso.isna() & d_ser.notna()
            if failed_iso.any():
                v_df = pd.to_datetime(d_ser[failed_iso], dayfirst=True, errors='coerce')
                df[col_name] = v_iso.fillna(v_df)
            else:
                df[col_name] = v_iso
            
    # Auditando se ainda restam NaT em Opening Date (não deveriam para tickets válidos)
    nats = df["Opening Date"].isna().sum()
    if nats > 0:
        log.warning(f"Aviso: {nats} tickets com 'Opening Date' inválido após conversão.")

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
    df["Days_Upd"] = (today - df["Last Updated Date"]).dt.days.fillna(-1).astype(int)

    def fmt_date(ts):
        return ts.strftime("%Y-%m-%d") if pd.notnull(ts) else ""

    SEVS = ["incident","user_request","problem","change_request","internal"]
    # pid=Problem ID; md=MDs reais; co=Country; ca=Closed Admin; svl=Service Line.
    # Sempre adicionar AO FINAL para preservar índices existentes em _TF.indexOf().
    TF   = ["k","eid","pr","sv","st","op","res","cl","ap","en","su","upd","ass","sl","rc","rct","rs","prj","y_o","m_o","d_o","y_c","m_c","d_c","sev","pid","md","co","ca","svl"]

    rows_out = []; idx_out = {}
    monthly  = {sv: {} for sv in SEVS}; daily = {sv: {} for sv in SEVS}; ym = defaultdict(set)

    for _, r in df.iterrows():
        tk = int(pd.to_numeric(r["Ticket"], errors="coerce") or 0)
        sv = r["Severity"] if r["Severity"] in SEVS else "internal"
        if r["Severity"] == "request_for_change": sv = "change_request"
        if r["Severity"] == "user request": sv = "user_request"
        
        sl_ack = pd.to_numeric(r.get("Acknowledge SLA"), errors="coerce")
        sl_res = pd.to_numeric(r.get("Resolution SLA"), errors="coerce")

        # Parent Problem ID — normalizado (CSV mistura "84849" e "0084849" e float 84849.0)
        pid_raw = r.get("Problem")
        pid = ""
        if pd.notna(pid_raw) and str(pid_raw).strip() != "":
            try:
                # Remove decimais de float (.0)
                pid_val = int(float(str(pid_raw).replace(",", ".").strip()))
                pid = str(pid_val).lstrip("0")
            except:
                pid = str(pid_raw).strip().lstrip("0")

        # MDs reais — CSV usa vírgula decimal pt-BR
        md_raw = r.get("MD's")
        try:
            md_val = float(str(md_raw).strip().replace(",", ".")) if pd.notna(md_raw) and str(md_raw).strip() != "" else 0.0
        except (ValueError, TypeError):
            md_val = 0.0

        row = [
            tk, str(r.get("External ID", "")), str(r.get("Priority", "N/A")), sv, str(r.get("Status", "N/A")),
            fmt_date(r.get("Opening Date")), fmt_date(r.get("Date of Resolution")), fmt_date(r.get("Close Date")),
            str(r.get("Application", "N/A")), str(r.get("Environment", "N/A")).upper(),
            str(r.get("Summary", f"Ticket {tk}"))[:120], fmt_date(r.get("Last Updated Date", r.get("Opening Date"))),
            str(r.get("assigned", "")), float(sl_ack) if pd.notna(sl_ack) else None,
            str(r.get("Root Cause Source", "N/A")),
            str(r.get("Root Cause Type", "N/A")),
            float(sl_res) if pd.notna(sl_res) else None, 
            smd_config.TIMESHEET_PROJECT_MAP.get(str(r.get("Project Name", "Desconhecido")).strip(), str(r.get("Project Name", "Desconhecido")).strip()),
            int(r["Opening Date"].year) if pd.notnull(r.get("Opening Date")) else 0,
            int(r["Opening Date"].month) if pd.notnull(r.get("Opening Date")) else 0,
            int(r["Opening Date"].day) if pd.notnull(r.get("Opening Date")) else 0,
            int(r["Close Date"].year) if pd.notnull(r.get("Close Date")) else 0,
            int(r["Close Date"].month) if pd.notnull(r.get("Close Date")) else 0,
            int(r["Close Date"].day) if pd.notnull(r.get("Close Date")) else 0,
            str(r.get("Severity", "internal")).lower(),
            pid, md_val,
            (str(r.get("Country")).strip() if pd.notna(r.get("Country")) else ""),
            (str(r.get("Closed Admin")).strip().upper() if pd.notna(r.get("Closed Admin")) else ""),
            (str(r.get("Service Line")).strip() if pd.notna(r.get("Service Line")) else "")
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
                    "ticket": tk_id, "status": str(r.get("Status", "N/A")), "days": int(r.get("Days_BK", 0)),
                    "days_upd": int(r.get("Days_Upd", 0)), "opened": fmt_date(r.get("Opening Date")),
                    "priority": str(r.get("Priority", "N/A")), "summary": str(r.get("Summary", f"Ticket {tk_id}"))[:60], 
                    "project": str(r.get("Project Name", "Desconhecido")),
                    "env": str(r.get("Environment", "N/A")).upper()
                })
        for owner in ["rc","client"]: backlog[sv][owner]["tickets"].sort(key=lambda x: x["days"], reverse=True)

    sla = {}
    env_mask = df["Environment"].astype(str).str.upper().str.strip().isin(["PRD", "PRODUÇÃO", "PROD"])
    sla_df = df[(df["Severity"]=="incident") & env_mask & df["Is_Closed"] & df["Resolution SLA"].notna() & df["Opening Date"].notna()].copy()
    log.info(f"Tickets elegíveis para SLA (Incident+PRD+Closed): {len(sla_df)}")
    for pri, lim, tgt in [("P1",360,98),("P2",720,95),("P3",1920,95),("P4",2880,95)]:
        g = sla_df[sla_df["Priority"]==pri]
        if len(g) == 0: continue
        met = int((g["Resolution SLA"] >= 0).sum())
        total = len(g)
        tix = []
        for _, r in g.iterrows():
            tix.append({
                "tid": int(r["Ticket"]), "rs": round(float(r["Resolution SLA"]),1),
                "met": 1 if r["Resolution SLA"] >= 0 else 0, "op": fmt_date(r["Opening Date"]),
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
        if "Root Cause Source" in sub.columns:
            sub["RCG"] = sub["Root Cause Source"].apply(rc_group)
            for g, gg in sub.groupby("RCG"):
                rc_dist[sv][str(g)] = {"count":int(len(gg)), "pct":round(len(gg)/len(sub)*100,1), "ids":gg["Ticket"].dropna().astype(int).tolist()}
        else:
            rc_dist[sv] = {"N/A": {"count": int(len(sub)), "pct": 100.0, "ids": sub["Ticket"].dropna().astype(int).tolist()}}

    summary = {"total_registered": int(len(df)), "total_open": int(df["Is_Open"].sum()), "projects": sorted(list(set(smd_config.TIMESHEET_PROJECT_MAP.get(str(p).strip(), str(p).strip()) for p in df["Project Name"].dropna().unique())))}
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

    # --- STAFF PERFORMANCE ---
    staff_data = {}
    # Produtividade: Tickets fechados (por quem fechou)
    closed_mask = df["Is_Closed"] & df["Closed Admin"].notna()
    for admin, g in df[closed_mask].groupby("Closed Admin"):
        admin = str(admin).strip().upper()
        if admin not in staff_data: staff_data[admin] = {"closed": 0, "open": 0, "projects": set(), "sevs": defaultdict(int)}
        staff_data[admin]["closed"] += len(g)
        for _, r in g.iterrows():
            staff_data[admin]["projects"].add(r["Project Name"])
            staff_data[admin]["sevs"][r["Severity"]] += 1

    # --- MONTHLY ANALYSIS (Budget vs Volume) ---
    # Necessário para o Resumo Executivo (ROI e Capacidade Preventiva)
    monthly_analysis = {}
    projects_list = ["Todos"] + sorted(df["Project Name"].dropna().unique().tolist())
    for prj in projects_list:
        monthly_analysis[prj] = {}
        df_p = df if prj == "Todos" else df[df["Project Name"] == prj]
        if df_p.empty: continue
        
        # Agrupar abertos e fechados por mês
        df_p_o = df_p[df_p["Opening Date"].notna()].copy()
        df_p_o["y_m"] = df_p_o["Opening Date"].dt.strftime("%Y-%m")
        df_p_c = df_p[df_p["Is_Closed"] & df_p["Close Date"].notna()].copy()
        df_p_c["y_m"] = df_p_c["Close Date"].dt.strftime("%Y-%m")
        
        all_months = sorted(list(set(df_p_o["y_m"].unique().tolist() + df_p_c["y_m"].unique().tolist())))
        for mk in all_months:
            opened = len(df_p_o[df_p_o["y_m"] == mk])
            closed = len(df_p_c[df_p_c["y_m"] == mk])
            monthly_analysis[prj][mk] = {"open": int(opened), "closed": int(closed)}
            
    # Carga: Tickets abertos (por quem está atribuído)
    open_mask = df["Is_Open"] & df["assigned"].notna()
    for assigned, g in df[open_mask].groupby("assigned"):
        assigned = str(assigned).strip().upper()
        if assigned not in staff_data: staff_data[assigned] = {"closed": 0, "open": 0, "projects": set(), "sevs": defaultdict(int)}
        staff_data[assigned]["open"] += len(g)
        for _, r in g.iterrows():
            staff_data[assigned]["projects"].add(r["Project Name"])
            staff_data[assigned]["sevs"][r["Severity"]] += 1
            
    # Converter sets para listas para JSON
    for s in staff_data:
        staff_data[s]["projects"] = sorted(list(staff_data[s]["projects"]))
        staff_data[s]["sevs"] = dict(staff_data[s]["sevs"])

    # Problem Management index — pré-computa para o frontend não varrer _ROWS.
    # Estrutura: D.problems[pid_normalizado] = {ticket, self_md, status, app, priority,
    # prj, is_open, opening, incidents:[{ticket, md, pri, app, status, prj}, ...]}
    fi_pid = TF.index("pid"); fi_md = TF.index("md")
    fi_sv  = TF.index("sv");  fi_st = TF.index("st"); fi_pr = TF.index("pr")
    fi_ap  = TF.index("ap");  fi_prj = TF.index("prj"); fi_k = TF.index("k")
    fi_op  = TF.index("op")
    OPEN_STATUSES_NEG = {"closed", "resolved", "rejected"}
    problems_idx = {}
    for row in rows_out:
        if row[fi_sv] == "problem":
            pid_self = str(row[fi_k]).lstrip("0") or str(row[fi_k])
            problems_idx[pid_self] = {
                "ticket": str(row[fi_k]), "self_md": row[fi_md],
                "status": row[fi_st], "app": row[fi_ap], "priority": row[fi_pr],
                "prj": row[fi_prj], "opening": row[fi_op],
                "is_open": row[fi_st] not in OPEN_STATUSES_NEG,
                "incidents": []
            }
    for row in rows_out:
        if row[fi_sv] == "incident" and row[fi_pid]:
            pid = str(row[fi_pid]).lstrip("0")
            if pid in problems_idx:
                problems_idx[pid]["incidents"].append({
                    "ticket": str(row[fi_k]), "md": row[fi_md], "pri": row[fi_pr],
                    "app": row[fi_ap], "status": row[fi_st], "prj": row[fi_prj]
                })
    log.info(f"Problem index: {len(problems_idx)} problems, "
             f"{sum(len(p['incidents']) for p in problems_idx.values())} incidents linkados")

    D = {"monthly": monthly, "daily": daily, "backlog": backlog, "sla": sla, "rc": rc_dist, "summary": summary, "comp": comp,
         "ym": {y:sorted(list(m)) for y,m in ym.items()}, "projects": summary["projects"],
         "generated_at": today.strftime("%Y-%m-%d %H:%M"), "mttr_stats": mttr_stats,
         "problems": problems_idx, "staff": staff_data, "monthly_analysis": monthly_analysis}
    T = {"fields": TF, "rows": rows_out, "idx": idx_out}
    return D, T, df

def check_ai_availability():
    """Verifica se o provedor de IA configurado está respondendo."""
    provider = smd_config.DEFAULT_AI_PROVIDER
    if provider == "ollama":
        import urllib.request
        try:
            # Tenta um GET simples no endpoint do Ollama
            # Se a URL não termina em /api/generate, ajustamos para checar tags
            check_url = smd_config.OLLAMA_URL.split("/api/")[0] + "/api/tags"
            with urllib.request.urlopen(check_url, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False
    elif provider in ["gemini", "anthropic"]:
        # Para cloud, assumimos que se tem a chave, está disponível (ou falhará no run)
        key = smd_config.GEMINI_API_KEY if provider == "gemini" else smd_config.ANTHROPIC_API_KEY
        return bool(key)
    return False

# ── TIMESHEET HISTÓRICO (COLD DATA) ──────────────────────────────────────────────

def build_timesheet_history():
    """
    Processa todos os .xlsx em 'TS historico/' e gera timesheet_history.json.
    Deve ser executado uma única vez (ou quando os dados históricos mudarem).
    """
    hist_dir = smd_config.TS_HISTORY_DIR
    if not hist_dir.exists():
        log.error(f"Diretório não encontrado: {hist_dir}")
        return False

    files = sorted([f for f in hist_dir.iterdir() if f.suffix.lower() in ('.xlsx', '.xls') and f.is_file()])
    if not files:
        log.error(f"Nenhum arquivo .xlsx/.xls encontrado em {hist_dir}")
        return False

    log.info("=" * 60)
    log.info("BUILD TIMESHEET HISTÓRICO")
    log.info(f"Diretório: {hist_dir}")
    log.info(f"Arquivos encontrados: {len(files)}")
    for f in files:
        log.info(f"  - {f.name} ({f.stat().st_size // 1024}kb)")
    log.info("=" * 60)

    # Carregar tickets.csv para metadados (prioridade, severidade, projeto)
    _, _, df_raw = process_tickets_data()

    # Processar todos os arquivos históricos com acumuladores compartilhados
    hist_tab, hist_gran = parse_timesheet_unified(files, df_raw)

    if not hist_tab:
        log.error("Nenhum dado processado dos arquivos históricos.")
        return False

    # Salvar cache
    cache = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_files": [f.name for f in files],
        "tab": hist_tab,
        "granular": hist_gran
    }
    cache_path = smd_config.TS_HISTORY_CACHE
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    size_kb = cache_path.stat().st_size // 1024

    # Estatísticas
    n_projects = len([k for k in hist_tab if k != "Todos"])
    n_tickets = len(hist_gran)
    log.info(f"Cache histórico salvo: {cache_path} ({size_kb}kb)")
    log.info(f"  Projetos: {n_projects} | Tickets com lançamento: {n_tickets}")
    log.info("Build histórico concluído.")
    return True


def load_timesheet_history():
    """Carrega o cache de timesheet histórico. Retorna (tab, granular) ou (None, None)."""
    cache_path = smd_config.TS_HISTORY_CACHE
    if not cache_path.exists():
        return None, None

    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
        n_files = len(cache.get("source_files", []))
        log.info(f"Cache histórico carregado: {cache['generated_at']} | {n_files} arquivo(s) fonte")
        return cache["tab"], cache["granular"]
    except Exception as e:
        log.error(f"Erro ao carregar cache histórico: {e}")
        return None, None


def merge_timesheet_data(hist_tab, hist_gran, cur_tab, cur_gran):
    """
    Combina dados históricos (cold) com dados do mês corrente (hot).
    Não há sobreposição de meses entre os dois conjuntos.
    Em caso de colisão, o dado corrente prevalece.
    """
    import copy

    # Tab: deep merge por projeto → ano → mês
    merged_tab = copy.deepcopy(hist_tab)
    for prj, years in cur_tab.items():
        if prj not in merged_tab:
            merged_tab[prj] = years
        else:
            for yr, months in years.items():
                if yr not in merged_tab[prj]:
                    merged_tab[prj][yr] = months
                else:
                    merged_tab[prj][yr].update(months)

    # Granular: merge por ticket_id, combinando periods
    merged_gran = copy.deepcopy(hist_gran)
    for tid, data in cur_gran.items():
        if tid not in merged_gran:
            merged_gran[tid] = data
        else:
            # Combinar periods (sem sobreposição de meses)
            merged_gran[tid]['periods'].update(data['periods'])
            # Atualizar status (corrente é mais recente)
            merged_gran[tid]['st'] = data['st']

    return merged_tab, merged_gran


def run_pipeline(skip_agents=False, csv_override=None):
    """Executa a pipeline completa: Tickets -> AI -> Timesheet -> data.js"""
    log.info("=" * 60)
    log.info(f"SMD DASHBOARD BUILD — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    log.info("=" * 60)
    D, T, df_raw = process_tickets_data(csv_override)
    if not D or df_raw is None: return
    
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
        if not check_ai_availability():
            log.warning(f"Provedor de IA ({smd_config.DEFAULT_AI_PROVIDER}) não está acessível. Pulando agentes.")
            skip_agents = True
            
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
    
    # Timesheet: Processar mês corrente + integrar histórico
    ts_path = get_ts_path()
    timesheet_tab, timesheet_granular = parse_timesheet_unified(ts_path, df_raw)

    # Merge com dados históricos pré-computados (se existirem)
    hist_tab, hist_gran = load_timesheet_history()
    if hist_tab is not None:
        timesheet_tab, timesheet_granular = merge_timesheet_data(
            hist_tab, hist_gran, timesheet_tab, timesheet_granular
        )
        log.info("Dados históricos de timesheet integrados ao build.")

    D["timesheet"] = timesheet_granular
    
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
    parser.add_argument("--no-agents", action="store_true", help="Pular execução da IA")
    parser.add_argument("--csv", type=str, help="Caminho para arquivo CSV customizado (ex: DOcs/Chanel.csv)")
    parser.add_argument("--build-history", action="store_true", help="Processar timesheets históricos e gerar cache")
    args = parser.parse_args()

    if args.build_history:
        build_timesheet_history()
    else:
        run_pipeline(skip_agents=args.no_agents, csv_override=args.csv)
