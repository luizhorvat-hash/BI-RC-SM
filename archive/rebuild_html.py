"""
rebuild_html.py — Reconstrói json-D e json-T no arrocha_dashboard_v7.html
a partir do CSV atualizado em C:/Dashboard/input/Tickets.csv
"""
import json, re, math
from pathlib import Path
from datetime import date, datetime, timedelta

import pandas as pd

# ── CAMINHOS ──────────────────────────────────────────────────────────────────
DASHBOARD_DIR = Path("C:/Dashboard")
CSV_PATH      = DASHBOARD_DIR / "input" / "Tickets.csv"
HTML_SRC      = DASHBOARD_DIR / "arrocha_dashboard_v7.html"
HTML_OUT      = DASHBOARD_DIR / "arrocha_dashboard_v7.html"   # sobrescreve

# ── LER CSV ───────────────────────────────────────────────────────────────────
def read_csv(path):
    for sep in [";", ","]:
        try:
            df = pd.read_csv(path, sep=sep, encoding="utf-8-sig", low_memory=False)
            if len(df.columns) > 3:
                return df
        except Exception:
            pass
    raise RuntimeError("Não foi possível ler o CSV.")

print("Lendo CSV...")
df = read_csv(CSV_PATH)
df.columns = [str(c).strip() for c in df.columns]

# ── NORMALIZAR CAMPOS ─────────────────────────────────────────────────────────
def col(name, default=""):
    return df[name] if name in df.columns else pd.Series([default]*len(df))

df["Severity"]  = col("Severity","unknown").fillna("unknown").astype(str).str.lower().str.strip()
df["Status"]    = col("Status","unknown").fillna("unknown").astype(str).str.lower().str.strip()
df["Priority"]  = col("Priority","P4").fillna("P4").astype(str).str.strip()
df["Project Name"] = col("Project Name","Unknown").fillna("Unknown").astype(str).str.strip()
df["Application"]  = col("Application","").fillna("").astype(str).str.strip()
df["Environment"]  = col("Environment","").fillna("").astype(str).str.strip().str.upper()
df["Root Cause Source"] = col("Root Cause Source","").fillna("").astype(str)
df["Root Cause Type"]   = col("Root Cause Type","").fillna("").astype(str)
df["Summary"]    = col("Summary","").fillna("").astype(str)
df["External ID"] = col("External ID","").fillna("").astype(str)
df["assigned"]   = col("assigned","").fillna("").astype(str)
df["Resolution SLA"] = pd.to_numeric(col("Resolution SLA"), errors="coerce")
df["Acknowledge SLA"] = pd.to_numeric(col("Acknowledge SLA"), errors="coerce")
df["Opening Date"] = pd.to_datetime(col("Opening Date"), errors="coerce")
df["Close Date"]   = pd.to_datetime(col("Close Date"),   errors="coerce")
df["Date of Resolution"] = pd.to_datetime(col("Date of Resolution"), errors="coerce")
df["Last Updated Date"]  = pd.to_datetime(col("Last Updated Date"),  errors="coerce")

# Normalizar severity
df.loc[df["Severity"]=="request_for_change","Severity"] = "change_request"
df.loc[df["Severity"]=="user request","Severity"]       = "user_request"

# Flags
CLOSED = {"closed","resolved","rejected"}
MY_BK  = {"acknowledged","assigned_for_analysis","assigned_for_dev",
           "waiting_for_prioritization","assigned_for_testing","pending_required_fields"}
CLI_BK = {"waiting_client_feedback","waiting_client_prd_inst","waiting_client_tests",
           "waiting_client_tst_inst","waiting_oracle_feedback"}

df["Is_Closed"] = df["Status"].isin(CLOSED)
df["Is_Open"]   = ~df["Is_Closed"]
df["BK_Owner"]  = df["Status"].apply(
    lambda s: "RC" if s in MY_BK else ("Client" if s in CLI_BK else "Other"))

today = pd.Timestamp(date.today())
df["Y_O"] = df["Opening Date"].dt.year
df["M_O"] = df["Opening Date"].dt.month
df["D_O"] = df["Opening Date"].dt.day
df["Y_C"] = df["Close Date"].dt.year
df["M_C"] = df["Close Date"].dt.month
df["D_C"] = df["Close Date"].dt.day
df["Days_BK"]  = (today - df["Opening Date"]).dt.days.fillna(0).clip(lower=0).astype(int)
df["Days_Upd"] = (today - df["Last Updated Date"]).dt.days.fillna(999).clip(lower=0).astype(int)

def fmt_date(ts):
    if pd.isna(ts): return None
    return ts.strftime("%Y-%m-%d")

SEVS = ["incident","user_request","problem","change_request","internal"]

print(f"CSV lido: {len(df)} tickets | Anos: {sorted(df['Y_O'].dropna().unique().astype(int))}")

# ── JSON-T (raw rows — columnar) ───────────────────────────────────────────────
print("Construindo json-T...")
FIELDS = ["k","eid","pr","sv","st","op","res","cl","ap","en","su","upd",
          "ass","sl","rc","rct","rs","prj","y_o","m_o","d_o","y_c","m_c","d_c"]

rows_out = []
for _, r in df.iterrows():
    def sv(v):
        return None if pd.isna(v) else v
    def iv(v):
        try: return int(v) if not pd.isna(v) else None
        except: return None
    def fv(v):
        try:
            f = float(v)
            return None if math.isnan(f) else round(f, 2)
        except: return None

    row = [
        iv(r["Ticket"]),                    # k
        str(r["External ID"]) if r["External ID"] else None,  # eid
        str(r["Priority"]),                 # pr
        str(r["Severity"]),                 # sv
        str(r["Status"]),                   # st
        fmt_date(r["Opening Date"]),        # op
        fmt_date(r["Date of Resolution"]),  # res
        fmt_date(r["Close Date"]),          # cl
        str(r["Application"]),              # ap
        str(r["Environment"]),              # en
        str(r["Summary"])[:120],            # su (truncar a 120 chars)
        fmt_date(r["Last Updated Date"]),   # upd
        str(r["assigned"]),                 # ass
        fv(r["Acknowledge SLA"]),           # sl
        str(r["Root Cause Source"]),        # rc
        str(r["Root Cause Type"]),          # rct
        fv(r["Resolution SLA"]),            # rs
        str(r["Project Name"]),             # prj
        iv(r["Y_O"]), iv(r["M_O"]), iv(r["D_O"]),  # y_o m_o d_o
        iv(r["Y_C"]), iv(r["M_C"]), iv(r["D_C"]),  # y_c m_c d_c
    ]
    rows_out.append(row)

json_T = {"fields": FIELDS, "rows": rows_out}

# ── JSON-D ─────────────────────────────────────────────────────────────────────
print("Construindo json-D...")

# --- monthly & daily --------------------------------------------------------
monthly = {}
daily   = {}

for sev in SEVS:
    sub = df[df["Severity"]==sev]
    monthly[sev] = {}
    daily[sev]   = {}

    for _, r in sub.iterrows():
        tid = int(r["Ticket"]) if not pd.isna(r["Ticket"]) else None
        # Opening
        if not pd.isna(r["Y_O"]) and not pd.isna(r["M_O"]):
            yo, mo, do = int(r["Y_O"]), int(r["M_O"]), int(r["D_O"]) if not pd.isna(r["D_O"]) else 1
            mk = f"{yo}-{mo:02d}"
            if mk not in monthly[sev]:
                monthly[sev][mk] = {"opened":0,"closed":0,"o_ids":[],"c_ids":[]}
            monthly[sev][mk]["opened"] += 1
            if tid: monthly[sev][mk]["o_ids"].append(tid)
            # daily opened
            if mk not in daily[sev]:
                daily[sev][mk] = {"opened":{},"closed":{},"o_ids":{},"c_ids":{}}
            ds = str(do)
            daily[sev][mk]["opened"][ds] = daily[sev][mk]["opened"].get(ds,0) + 1
            if tid: daily[sev][mk]["o_ids"].setdefault(ds,[]).append(tid)

        # Closing
        if r["Is_Closed"] and not pd.isna(r["Y_C"]) and not pd.isna(r["M_C"]):
            yc, mc, dc = int(r["Y_C"]), int(r["M_C"]), int(r["D_C"]) if not pd.isna(r["D_C"]) else 1
            mk2 = f"{yc}-{mc:02d}"
            if mk2 not in monthly[sev]:
                monthly[sev][mk2] = {"opened":0,"closed":0,"o_ids":[],"c_ids":[]}
            monthly[sev][mk2]["closed"] += 1
            if tid: monthly[sev][mk2]["c_ids"].append(tid)
            # daily closed
            if mk2 not in daily[sev]:
                daily[sev][mk2] = {"opened":{},"closed":{},"o_ids":{},"c_ids":{}}
            ds2 = str(dc)
            daily[sev][mk2]["closed"][ds2] = daily[sev][mk2]["closed"].get(ds2,0) + 1
            if tid: daily[sev][mk2]["c_ids"].setdefault(ds2,[]).append(tid)

# --- ym (year → months) -----------------------------------------------------
ym = {}
for sev in SEVS:
    for mk in monthly[sev]:
        y, m = mk.split("-")
        mi = int(m)
        if y not in ym:
            ym[y] = []
        if mi not in ym[y]:
            ym[y].append(mi)
for y in ym:
    ym[y] = sorted(ym[y])

# --- backlog ----------------------------------------------------------------
backlog = {}
for sev in SEVS:
    sub = df[(df["Severity"]==sev) & df["Is_Open"]]
    def top_tickets(s, max_t=500):
        out = []
        for _, r in s.nlargest(min(max_t,len(s)),"Days_BK").iterrows():
            out.append({
                "ticket":   int(r["Ticket"]) if not pd.isna(r["Ticket"]) else 0,
                "status":   str(r["Status"]),
                "days":     int(r["Days_BK"]),
                "days_upd": int(r["Days_Upd"]),
                "opened":   fmt_date(r["Opening Date"]) or "",
                "priority": str(r["Priority"]),
                "summary":  str(r["Summary"])[:60],
                "project":  str(r["Project Name"]),
            })
        return out

    rc_sub  = sub[sub["BK_Owner"]=="RC"]
    cli_sub = sub[sub["BK_Owner"]=="Client"]
    backlog[sev] = {
        "rc":  {"total": len(rc_sub),  "sem_upd": int((rc_sub["Days_Upd"]>7).sum()),  "tickets": top_tickets(rc_sub)},
        "client": {"total": len(cli_sub), "sem_upd": int((cli_sub["Days_Upd"]>7).sum()), "tickets": top_tickets(cli_sub)},
    }

# --- SLA --------------------------------------------------------------------
sla = {}
sla_df = df[(df["Severity"]=="incident") & (df["Environment"]=="PRD") &
            df["Is_Closed"] & df["Resolution SLA"].notna()].copy()
for pri, lim, tgt in [("P1",360,98),("P2",720,95),("P3",1920,95),("P4",2880,95)]:
    g = sla_df[sla_df["Priority"]==pri]
    if len(g)==0: continue
    met   = int((g["Resolution SLA"]>=0).sum())
    total = int(len(g))
    tix   = []
    for _, r in g.iterrows():
        tix.append({
            "tid": int(r["Ticket"]) if not pd.isna(r["Ticket"]) else 0,
            "rs":  round(float(r["Resolution SLA"]),1),
            "met": bool(r["Resolution SLA"]>=0),
            "op":  fmt_date(r["Opening Date"]) or "",
            "ap":  str(r["Application"])[:30],
            "s":   str(r["Summary"])[:50],
            "y":   int(r["Y_O"]) if not pd.isna(r["Y_O"]) else 0,
            "m":   int(r["M_O"]) if not pd.isna(r["M_O"]) else 0,
        })
    avg_rs = round(float(g["Resolution SLA"].mean()),1) if len(g)>0 else 0
    sla[pri] = {"total":total,"met":met,"not_met":total-met,
                "pct":round(met/total*100,1),"target":tgt,"lim_min":lim,
                "avg_actual":avg_rs,"tickets":tix}

# --- RC distribution --------------------------------------------------------
def rc_group(s):
    s = str(s).strip().lower()
    if s in ("client","client - rollout"): return "Client"
    if s == "rc":                          return "RC"
    if s in ("problem analysis","not identified"): return "Problem Analysis"
    if s == "oracle":                      return "Oracle"
    return "Outros"

rc_dist = {}
for sev in SEVS:
    sub   = df[df["Severity"]==sev].copy()
    total = len(sub)
    sub["RCG"] = sub["Root Cause Source"].apply(rc_group)
    rc_dist[sev] = {}
    for g, gg in sub.groupby("RCG"):
        ids = gg["Ticket"].dropna().astype(int).tolist()
        rc_dist[sev][str(g)] = {"count":int(len(gg)),
                                 "pct": round(len(gg)/total*100,1) if total>0 else 0,
                                 "ids": ids}

# --- summary ----------------------------------------------------------------
summary = {"total_registered": int(len(df)), "total_open": int(df["Is_Open"].sum())}
try: summary["projects"] = sorted(df["Project Name"].dropna().unique().tolist())
except: summary["projects"] = []
for sev in SEVS:
    sub = df[df["Severity"]==sev]
    summary[sev] = {"registered":int(len(sub)),"closed":int(sub["Is_Closed"].sum()),
                    "open":int(sub["Is_Open"].sum())}

# --- comp (comparação mês atual vs mês anterior) ----------------------------
cur_y = today.year; cur_m = today.month
prev_m = cur_m - 1 if cur_m > 1 else 12
prev_y = cur_y    if cur_m > 1 else cur_y - 1
cur_mk  = f"{cur_y}-{cur_m:02d}"
prev_mk = f"{prev_y}-{prev_m:02d}"

comp = {}
for sev in SEVS:
    md = monthly.get(sev, {})
    cur_ab  = md.get(cur_mk,  {}).get("opened", 0)
    prev_ab = md.get(prev_mk, {}).get("opened", 0)
    cur_cl  = md.get(cur_mk,  {}).get("closed", 0)
    prev_cl = md.get(prev_mk, {}).get("closed", 0)
    def var_pct(c, p):
        if p == 0: return None
        return round((c - p) / p * 100, 1)
    comp[sev] = {
        "ab": {"cur": cur_ab,  "prev": prev_ab, "var": var_pct(cur_ab, prev_ab)},
        "cl": {"cur": cur_cl,  "prev": prev_cl, "var": var_pct(cur_cl, prev_cl)},
    }

# --- attention --------------------------------------------------------------
attention = []
for sev in SEVS:
    bk = backlog[sev]
    for owner in ["rc","client"]:
        aging = sum(1 for t in bk[owner]["tickets"] if t["days"]>30)
        if aging > 0:
            worst = max((t["days"] for t in bk[owner]["tickets"] if t["days"]>30), default=0)
            attention.append({
                "type": "backlog_aging", "severity": sev, "owner": owner,
                "count": aging, "worst": worst,
                "msg": f"{aging} ticket(s) {sev} ({owner.upper()}) ha +30 dias (pior: {worst}d)"
            })

# --- projects ---------------------------------------------------------------
projects = sorted(df["Project Name"].dropna().unique().tolist())

# ── MONTAR json-D ─────────────────────────────────────────────────────────────
json_D = {
    "monthly":  monthly,
    "daily":    daily,
    "backlog":  backlog,
    "sla":      sla,
    "rc":       rc_dist,
    "summary":  summary,
    "comp":     comp,
    "ym":       ym,
    "attention": attention,
    "projects": projects,
}

print(f"json-D: {len(projects)} projetos | ym: {ym}")
print(f"json-T: {len(rows_out)} rows")

# ── INJETAR NO HTML ───────────────────────────────────────────────────────────
print("Injetando dados no HTML...")

with open(HTML_SRC, encoding="utf-8") as f:
    html = f.read()

# Substituir json-D
html = re.sub(
    r'(<script type="application/json" id="json-D">).*?(</script>)',
    lambda m: m.group(1) + json.dumps(json_D, ensure_ascii=False, separators=(',',':')) + m.group(2),
    html, flags=re.DOTALL
)

# Substituir json-T
html = re.sub(
    r'(<script type="application/json" id="json-T">).*?(</script>)',
    lambda m: m.group(1) + json.dumps(json_T, ensure_ascii=False, separators=(',',':')) + m.group(2),
    html, flags=re.DOTALL
)

with open(HTML_OUT, "w", encoding="utf-8") as f:
    f.write(html)

size_mb = HTML_OUT.stat().st_size / 1_048_576
print(f"✓ HTML gerado: {HTML_OUT} ({size_mb:.1f} MB)")
print("Abra o arquivo no browser para validar.")
