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
    res_path = smd_config.BASE_DIR / "DOcs" / "Resource Level.xlsx"
    if not res_path.exists():
        log.warning(f"Arquivo de Resource Level não encontrado em {res_path}")
        return {}

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
        # Mapeamentos manuais fornecidos pelo usuário para nomes divergentes no Timesheet
        manual_fixes = {
            "helder ferreira": "300",
            "joao pinto": "203",
            "bruno madaleno": "300",
            "nuno pereira": "101",
            "joao cunha goncalves": "202"
        }
        mapping.update(manual_fixes)

        log.info(f"Carregados {len(mapping)} mapeamentos de Career Grade (incluindo variações e correções manuais).")
        return mapping
    except Exception as e:
        log.error(f"Erro ao carregar Resource Level: {e}")
        return {}

def parse_timesheet_tab(path):
    """
    Lê o timesheet e agrega por projeto-dashboard / ano / mês.
    Suporta .xls (XML 2003) e .xlsx (Pandas).
    """
    if not path:
        log.warning(f"Timesheet não configurado ou não encontrado.")
        return {}
    if not path.exists():
        log.warning(f"Arquivo de timesheet {path} não existe.")
        return {}

    log.info(f"Gerando dados da aba Timesheet de {path.name}...")
    import pandas as pd
    from collections import defaultdict

    # acumuladores: [prj][year][month] → dicts
    grade_map = get_resource_grade_map()
    acc = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: {
        "total_h": 0.0, "total_days": 0.0, "overtime_h": 0.0,
        "staff": defaultdict(float),
        "tasks": defaultdict(float),
        "subs":  defaultdict(float),
        "sub_projects": defaultdict(float),
        "weekly": defaultdict(float),
        "grades": defaultdict(float),
        "staff_detailed": defaultdict(lambda: {"h": 0.0, "d": 0.0, "sub": "", "grade": ""}),
    })))

    def process_row(row_data, acc):
        prj_ts = row_data.get(1, "") or ""
        task   = row_data.get(3, "") or ""
        staff  = row_data.get(6, "") or ""
        week_s = row_data.get(7, "") or ""
        sub    = row_data.get(23, "") or ""

        try:
            wk_h  = float(row_data.get(21) or 0)
            wk_d  = float(row_data.get(22) or 0)
            sat_h = float(row_data.get(15) or 0)
            sun_h = float(row_data.get(17) or 0)
            
            if math.isnan(wk_h): wk_h = 0
            if math.isnan(wk_d): wk_d = 0
            if math.isnan(sat_h): sat_h = 0
            if math.isnan(sun_h): sun_h = 0
        except (ValueError, TypeError):
            return

        if wk_h <= 0 or not prj_ts or not staff:
            return

        prj_ts_clean = str(prj_ts).strip()
        dash_prj = TIMESHEET_PROJECT_MAP.get(prj_ts_clean, "Outros")

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

        # Busca Career Grade com normalização e fallback para nome curto
        s_norm = normalize_name(staff)
        grade = grade_map.get(s_norm)
        if not grade:
            parts = s_norm.split()
            if len(parts) > 1:
                grade = grade_map.get(f"{parts[0]} {parts[-1]}", "N/A")
            else:
                grade = "N/A"

        # Itera sobre os dias da semana (índices específicos devido a colunas vazias no CMS)
        day_indices = [9, 10, 11, 13, 14, 15, 17] # Seg, Ter, Qua, Qui, Sex, Sab, Dom
        for idx, i in enumerate(day_indices):
            h = row_data.get(i, 0)
            try:
                h = float(h or 0)
                if math.isnan(h) or h <= 0: continue
            except (ValueError, TypeError):
                continue
            
            day_offset = idx
            day_date = dt + timedelta(days=day_offset)
            
            d_year  = str(day_date.year)
            d_month = f"{day_date.month:02d}"
            d_week  = f"{day_date.year}-W{day_date.isocalendar()[1]:02d}"
            
            # MD proporcional (base 8h)
            d_md = h / 8.0
            is_overtime = (i >= 15) # Sábado (15) e Domingo (17)

            for prj in [dash_prj, "Todos"]:
                b = acc[prj][d_year][d_month]
                b["total_h"]    += h
                b["total_days"] += d_md
                if is_overtime:
                    b["overtime_h"] += h
                
                b["staff"][staff]   += h
                b["tasks"][task]    += h
                b["subs"][sub]      += h
                b["sub_projects"][prj_ts] += h
                b["weekly"][d_week]       += h
                b["grades"][grade]        += d_md
                
                # Detalhes do colaborador para o novo KPI
                sd = b["staff_detailed"][staff]
                sd["h"] += h
                sd["d"] += d_md
                if sub: sd["sub"] = sub
                sd["grade"] = grade

    # --- LEITURA DOS DADOS ---
    if path.suffix.lower() == ".xlsx":
        try:
            # Tenta localizar a aba de dados brutos 'Report'
            xl = pd.ExcelFile(path)
            sheet = 'Report' if 'Report' in xl.sheet_names else xl.sheet_names[0]
            log.info(f"Lendo aba '{sheet}' de {path.name}")
            df_ts = pd.read_excel(xl, sheet_name=sheet, header=None)
            for i, row in df_ts.iterrows():
                # No Pandas, row[0] é a primeira coluna. Nosso process_row espera 0-based agora se simplificarmos.
                # Mas para manter compatibilidade com o XML, vamos mapear idx direto.
                row_dict = {idx: val for idx, val in enumerate(row)}
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

                by_grade = {g: round(d, 2) for g, d in sorted(b["grades"].items(), key=lambda x: -x[1])}

                # Detalhes por grade para o novo KPI
                grade_details = {}
                for name, d in b["staff_detailed"].items():
                    g = d["grade"]
                    if g not in grade_details: grade_details[g] = []
                    grade_details[g].append({
                        "name": name, "sub": d["sub"], 
                        "h": round(d["h"], 1), "d": round(d["d"], 2)
                    })
                for g in grade_details:
                    grade_details[g].sort(key=lambda x: -x["d"], reverse=True)

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
                    "by_career_grade": by_grade,
                    "grade_details": grade_details,
                    "sub_projects": sub_projects,
                    "weekly": weekly,
                }

    log.info(f"Aba Timesheet: {len(result)} projetos, anos={sorted({yr for p in result.values() for yr in p})}")
    return result

def parse_timesheet(path, tickets_df):
    """Lê o arquivo XLS (XML) de timesheet e gera mapeamento granular D.timesheet."""
    if not path:
        log.warning("Caminho de timesheet não fornecido.")
        return {}
    if not path.exists():
        log.warning(f"Arquivo de timesheet não encontrado: {path}")
        return {}

    log.info(f"Processando timesheet estrito (ID-based) de {path}...")
    import pandas as pd
    try:
        # Usar header=4 para pegar os nomes das colunas reais (Row 4)
        df_ts = pd.read_excel(path, sheet_name='Report', header=4)
        
        # Mapa de tickets {id: {sv, pr, prj}}
        ticket_map = {}
        for _, r in tickets_df.iterrows():
            tk_raw = r.get('Ticket')
            if pd.isna(tk_raw): continue
            tk_id = str(int(pd.to_numeric(tk_raw, errors='coerce')))
            ticket_map[tk_id] = {
                'sv': str(r.get('Severity', 'incident')).lower().replace(' ', '_'),
                'prj': TIMESHEET_PROJECT_MAP.get(str(r.get('Project Name', 'Other')).strip(), str(r.get('Project Name', 'Other')).strip()),
                'pr': str(r.get('Priority', 'P4')).strip(),
                'st': str(r.get('Status', 'New')).strip(),
                'iv': str(r.get('Invoice', '')).strip()
            }

        ts_final = {} # { tid: { prj, sv, pr, iv, months: { "Y-M": hours }, staff: { name: hours } } }
        ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
        stats = {"match_ticket": 0, "ignored": 0}

        def process_ts_row(row_data):
            nonlocal stats
            try:
                # Acessar colunas por posição física (0-based)
                # 1=Project, 6=Staff, 7=Week, 19=Ticket(Comments), 21=Hours, 22=Days
                try:
                    # Garantir que row_data seja uma Series para usar iloc
                    if not isinstance(row_data, pd.Series):
                        row_data = pd.Series(row_data)
                        
                    hc = row_data.iloc[21]
                    dc = row_data.iloc[22]
                    hours = float(hc) if hc is not None and not pd.isnull(hc) else 0
                    days  = float(dc) if dc is not None and not pd.isnull(dc) else 0
                    
                    if math.isnan(hours): hours = 0
                    if math.isnan(days): days = 0
                    
                    if hours <= 0 and days <= 0: return

                    staff_name = str(row_data.iloc[6]) if not pd.isnull(row_data.iloc[6]) else "Unknown"
                    desc_col   = str(row_data.iloc[3]) if not pd.isnull(row_data.iloc[3]) else ""
                    ref_col    = str(row_data.iloc[19]) if not pd.isnull(row_data.iloc[19]) else ""
                    week_val   = row_data.iloc[7]
                    
                    # 1. Match Ticket ID (Coluna 19 contém o ID no campo Comments)
                    tid_col    = str(row_data.iloc[19]) if not pd.isnull(row_data.iloc[19]) else ""
                    search_text = f"{tid_col} {desc_col}"
                    ids_found = re.findall(r'(\d{4,7})', search_text)
                except Exception as ex:
                    # Se der erro de índice em alguma linha malformada, apenas ignora
                    return
                
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
                    dt = week_val
                    mk = f"{dt.year}-{dt.month:02d}"
                except: 
                    mk = datetime.now().strftime("%Y-%m")

                # 3. Agrupar
                if tid_match not in ts_final:
                    ts_final[tid_match] = {
                        'prj': t_meta['prj'],
                        'sv': t_meta['sv'],
                        'pr': t_meta['pr'],
                        'st': t_meta['st'],
                        'iv': t_meta['iv'],
                        'periods': {}
                    }
                
                entry = ts_final[tid_match]
                if mk not in entry['periods']:
                    entry['periods'][mk] = {'h': 0, 'd': 0, 'staff': {}}
                
                p = entry['periods'][mk]
                p['h'] += hours
                p['d'] += (hours / 8.0) # Força consistência com a regra de 8h/MD
                p['staff'][staff_name] = p['staff'].get(staff_name, 0) + hours
                stats["match_ticket"] += 1
            except: pass

        # --- PROCESSAMENTO ---
        # df_ts já foi carregado com header=4 (nomes de colunas na Row 4)
        for _, row in df_ts.iterrows():
            process_ts_row(row)

        log.info(f"Timesheet granular concluído: {len(ts_final)} tickets vinculados. Status: {stats}")
        return ts_final

    except Exception as e:
        log.error(f"Falha ao processar timesheet: {e}")
        return {}

        return ts_final
    except Exception as e:
        log.error(f"Erro ao processar timesheet granular: {e}")
        return {}

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
            TIMESHEET_PROJECT_MAP.get(str(r.get("Project Name", "Desconhecido")).strip(), str(r.get("Project Name", "Desconhecido")).strip()),
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
                    "priority": str(r.get("Priority", "N/A")), "summary": str(r.get("Summary", f"Ticket {tk_id}"))[:60], "project": str(r.get("Project Name", "Desconhecido"))
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
        if "Root Cause Source" in sub.columns:
            sub["RCG"] = sub["Root Cause Source"].apply(rc_group)
            for g, gg in sub.groupby("RCG"):
                rc_dist[sv][str(g)] = {"count":int(len(gg)), "pct":round(len(gg)/len(sub)*100,1), "ids":gg["Ticket"].dropna().astype(int).tolist()}
        else:
            rc_dist[sv] = {"N/A": {"count": int(len(sub)), "pct": 100.0, "ids": sub["Ticket"].dropna().astype(int).tolist()}}

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
         "ym": {y:sorted(list(m)) for y,m in ym.items()}, "projects": summary["projects"], "timesheet": timesheet,
         "generated_at": today.strftime("%Y-%m-%d %H:%M"), "mttr_stats": mttr_stats,
         "problems": problems_idx, "staff": staff_data}
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
    parser.add_argument("--no-agents", action="store_true", help="Pular execução da IA")
    parser.add_argument("--csv", type=str, help="Caminho para arquivo CSV customizado (ex: DOcs/Chanel.csv)")
    args = parser.parse_args()
    
    run_pipeline(skip_agents=args.no_agents, csv_override=args.csv)
