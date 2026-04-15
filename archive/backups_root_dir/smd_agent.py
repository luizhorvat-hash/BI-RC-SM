"""
Service Management Dashboard — Agente Orquestrador v5
Usa Google Gemini API (GRATUITO) com suporte a 6 Agentes e Desacoplamento (data.js)

COMO OBTER A API KEY GRATUITA DO GEMINI:
1. Acesse: aistudio.google.com
2. Clique em "Get API Key" > "Create API key"
3. Copie a chave e salve em C:\Dashboard\api_key.txt

USO:
  python C:\Dashboard\smd_agent.py
  python C:\Dashboard\smd_agent.py --agent ops
  python C:\Dashboard\smd_agent.py --schedule
"""
import os, sys, json, logging, re, time
from datetime import datetime, date
from pathlib import Path
from logging.handlers import RotatingFileHandler

# ── CONFIGURACAO ──────────────────────────────────────────────────────────────
DASHBOARD_DIR = Path(r"C:/Dashboard")
INPUT_CSV     = DASHBOARD_DIR / "input" / "Tickets.csv"
RESULTS_DIR   = DASHBOARD_DIR / "Resultados"
LOG_FILE      = DASHBOARD_DIR / "smd_agent.log"

# Google Gemini — GRATUITO (1500 requests/dia)
GEMINI_MODEL = "gemini-2.0-flash-pro"
GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ── LOGGING ROTATIVO ──────────────────────────────────────────────────────────
_fh = RotatingFileHandler(LOG_FILE, maxBytes=500_000, backupCount=2, encoding="utf-8")
_fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
_ch = logging.StreamHandler(sys.stdout)
_ch.setFormatter(logging.Formatter("%(asctime)s[%(levelname)s] %(message)s"))
log = logging.getLogger("smd")
log.setLevel(logging.INFO)
log.addHandler(_fh)
log.addHandler(_ch)

# ── LER API KEY ───────────────────────────────────────────────────────────────
def get_api_key():
    key = os.environ.get("GEMINI_API_KEY")
    if key: return key
    key_file = DASHBOARD_DIR / "api_key.txt"
    if key_file.exists():
        for line in key_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    return ""

# ── PROCESSAR CSV ─────────────────────────────────────────────────────────────
def build_context():
    log.info("Iniciando leitura do CSV...")
    csv_path = None
    for p in[INPUT_CSV, DASHBOARD_DIR / "Tickets.csv"]:
        if p.exists(): csv_path = p; break
    if not csv_path:
        log.error(f"CSV nao encontrado em {INPUT_CSV}")
        return None, None
    try:
        import pandas as pd
    except ImportError:
        log.error("pandas nao instalado. Execute: pip install pandas")
        return None, None
        
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig", low_memory=False)
    except Exception as e:
        try:
            df = pd.read_csv(csv_path, sep=",", encoding="utf-8-sig", low_memory=False)
        except Exception as e2:
            log.error(f"Falha total CSV: {e2}"); return None, None

    df.columns =[str(c).strip() for c in df.columns]

    try:
        df["Severity"]  = df.get("Severity",  "unknown").fillna("unknown").astype(str).str.lower().str.strip()
        df["Status"]    = df.get("Status",     "unknown").fillna("unknown").astype(str).str.lower().str.strip()
        df["Priority"]  = df.get("Priority",   "P4").fillna("P4").astype(str).str.strip()
        df["Project Name"] = df.get("Project Name", "Unknown").fillna("Unknown").astype(str).str.strip()
        df["Application"]  = df.get("Application",  "").fillna("").astype(str).str.strip()
        df["Environment"]  = df.get("Environment",  "").fillna("").astype(str).str.strip().str.upper()
        df["Root Cause Source"] = df.get("Root Cause Source", "").fillna("").astype(str)
        df["Summary"]   = df.get("Summary", "").fillna("").astype(str)
        df["Resolution SLA"] = pd.to_numeric(df.get("Resolution SLA", None), errors="coerce")
        df["Opening Date"] = pd.to_datetime(df.get("Opening Date"), errors="coerce")
        df["Close Date"]   = pd.to_datetime(df.get("Close Date"),   errors="coerce")
        df.loc[df["Severity"]=="request_for_change","Severity"] = "change_request"
    except Exception as e:
        log.error(f"Erro processando campos: {e}"); return None, None

    CLOSED = {"closed","resolved","rejected"}
    MY_BK  = {"acknowledged","assigned_for_analysis","assigned_for_dev","waiting_for_prioritization","assigned_for_testing","pending_required_fields"}
    CLI_BK = {"waiting_client_feedback","waiting_client_prd_inst","waiting_client_tests","waiting_client_tst_inst","waiting_oracle_feedback"}

    try:
        df["Is_Closed"] = df["Status"].isin(CLOSED)
        df["Is_Open"]   = ~df["Is_Closed"]
        df["BK_Owner"]  = df["Status"].apply(lambda s: "RC" if s in MY_BK else ("Client" if s in CLI_BK else "Other"))
        today = pd.Timestamp(date.today())
        df["Y_O"] = df["Opening Date"].dt.year
        df["M_O"] = df["Opening Date"].dt.month
        df["Y_C"] = df["Close Date"].dt.year
        df["M_C"] = df["Close Date"].dt.month
        df["Days_BK"] = (today - df["Opening Date"]).dt.days.fillna(0).clip(lower=0).astype(int)
    except Exception as e:
        log.error(f"Erro flags/datas: {e}"); return None, None

    sevs =["incident","user_request","problem","change_request","internal"]

    summary = {"total_registered": int(len(df)), "total_open": int(df["Is_Open"].sum())}
    try: summary["projects"] = sorted(df["Project Name"].dropna().unique().tolist())
    except: summary["projects"] =[]
    
    for sev in sevs:
        sub = df[df["Severity"]==sev]
        summary[sev] = {"registered":int(len(sub)),"closed":int(sub["Is_Closed"].sum()),"open":int(sub["Is_Open"].sum())}

    monthly = {}
    try:
        for sev in sevs:
            sub = df[df["Severity"]==sev]
            monthly[sev] = {}
            if len(sub)==0: continue
            
            # Extract IDs for caching
            for i, r in sub.iterrows():
                yo = r.get("Y_O"); mo = r.get("M_O")
                yc = r.get("Y_C"); mc = r.get("M_C")
                tid = str(r.get("Ticket",""))
                
                if pd.notna(yo) and pd.notna(mo):
                    k = f"{int(yo)}-{int(mo):02d}"
                    if k not in monthly[sev]: monthly[sev][k] = {"opened":0, "closed":0, "o_ids":[], "c_ids":[]}
                    monthly[sev][k]["opened"] += 1
                    monthly[sev][k]["o_ids"].append(tid)
                    
                if r["Is_Closed"] and pd.notna(yc) and pd.notna(mc):
                    k = f"{int(yc)}-{int(mc):02d}"
                    if k not in monthly[sev]: monthly[sev][k] = {"opened":0, "closed":0, "o_ids":[], "c_ids":[]}
                    monthly[sev][k]["closed"] += 1
                    monthly[sev][k]["c_ids"].append(tid)
                    
    except Exception as e:
        log.warning(f"Monthly erro: {e}")

    sla = {}
    try:
        sla_df = df[(df["Severity"]=="incident")&(df["Environment"]=="PRD")&df["Is_Closed"]&df["Resolution SLA"].notna()].copy()
        for pri,lim,tgt in[("P1",360,98),("P2",720,95),("P3",1920,95),("P4",2880,95)]:
            g = sla_df[sla_df["Priority"]==pri]
            if len(g)==0: continue
            met=int((g["Resolution SLA"]>=0).sum()); total=int(len(g))
            sla[pri]={"total":total,"met":met,"not_met":total-met,"pct":round(met/total*100,1),"target":tgt,"lim_min":lim,"avg_min":round(float(g["Resolution SLA"].mean()),1)}
    except Exception as e:
        pass

    backlog = {}
    try:
        for sev in sevs:
            sub = df[(df["Severity"]==sev)&df["Is_Open"]]
            def top(s):
                rows=[]
                for _,r in s.nlargest(min(500,len(s)),"Days_BK").iterrows(): # Aumentado para suportar tabelas grandes
                    rows.append({"ticket":str(r.get("Ticket","")),"status":str(r["Status"]),"days":int(r["Days_BK"]),"days_upd":int(r["Days_BK"]),"priority":str(r["Priority"]),"summary":str(r["Summary"])[:60],"project":str(r["Project Name"])})
                return rows
            rc=sub[sub["BK_Owner"]=="RC"]; cl=sub[sub["BK_Owner"]=="Client"]
            backlog[sev]={"rc":{"total":int(len(rc)),"aging_30d":int((rc["Days_BK"]>30).sum()),"tickets":top(rc)},"client":{"total":int(len(cl)),"aging_30d":int((cl["Days_BK"]>30).sum()),"tickets":top(cl)}}
    except Exception as e:
        pass

    rc_dist={}
    try:
        def rc_grp(s):
            s=str(s).strip().lower()
            if s in("client","client - rollout"): return "Client"
            if s=="rc": return "RC"
            if s in("problem analysis","not identified"): return "Problem Analysis"
            if s=="oracle": return "Oracle"
            return "Outros"

        for sev in sevs:
            sub=df[df["Severity"]==sev].copy(); total=len(sub)
            sub["RCG"]=sub["Root Cause Source"].apply(rc_grp)
            rc_dist[sev]={}
            for g, gg in sub.groupby("RCG"):
                ids = gg["Ticket"].astype(str).tolist()
                rc_dist[sev][str(g)] = {"count": int(len(gg)), "pct": round(len(gg)/total*100,1) if total>0 else 0, "ids": ids}
    except Exception as e:
        pass

    ctx={"generated_at":str(date.today()),"summary":summary,"monthly"