"""
Análise profunda de tickets oncall para sugestões de melhoria.
"""
import pandas as pd
import json
from collections import Counter

CLIENT_CONFIG = {
    "Farmatodo": {"biz_start_utc": 11, "biz_end_utc": 23},
    "GDN":       {"biz_start_utc": 11, "biz_end_utc": 21},
    "Chanel":    {"biz_start_utc": 11, "biz_end_utc": 21},
}

def is_oncall(dt, cfg):
    if pd.isna(dt): return False
    if dt.weekday() >= 5: return True
    h = dt.hour
    return h < cfg["biz_start_utc"] or h >= cfg["biz_end_utc"]

df = pd.read_csv('c:/Dashboard/input/Tickets.csv', sep=';', encoding='utf-8-sig', low_memory=False)
df.columns = [c.strip() for c in df.columns]
df['Opening Date'] = pd.to_datetime(df['Opening Date'], errors='coerce')
df['Close Date']   = pd.to_datetime(df['Close Date'],   errors='coerce')
df['Severity']     = df['Severity'].fillna('').str.lower().str.strip()
df['Priority']     = df['Priority'].fillna('').str.strip()
df['Status']       = df['Status'].fillna('').str.lower().str.strip()
df['Application']  = df['Application'].fillna('N/A').str.strip()
df['Root Cause Type']   = df['Root Cause Type'].fillna('N/A').str.strip()
df['Root Cause Source'] = df['Root Cause Source'].fillna('N/A').str.strip()
df['Summary']      = df['Summary'].fillna('').str.strip()

CLOSED = {'closed', 'resolved', 'rejected'}

results = {}

for prj, cfg in CLIENT_CONFIG.items():
    inc = df[(df['Project Name'] == prj) & (df['Severity'] == 'incident') & df['Opening Date'].notna()].copy()
    inc['is_oncall'] = inc['Opening Date'].apply(lambda d: is_oncall(d, cfg))
    inc['is_weekend'] = inc['Opening Date'].dt.weekday >= 5
    inc['hour_utc']   = inc['Opening Date'].dt.hour
    inc['weekday']    = inc['Opening Date'].dt.weekday
    inc['ym']         = inc['Opening Date'].dt.strftime('%Y-%m')

    oc  = inc[inc['is_oncall']]
    non = inc[~inc['is_oncall']]

    print(f"\n{'='*60}")
    print(f"PROJETO: {prj} — {len(oc)} oncall / {len(inc)} total ({round(len(oc)/len(inc)*100,1)}%)")
    print(f"{'='*60}")

    # 1. TICKETS REPETIDOS (mesma Application + Root Cause Type, oncall)
    print("\n[1] TOP APLICAÇÕES EM ONCALL:")
    app_oc = oc['Application'].value_counts().head(8)
    app_tot = inc['Application'].value_counts()
    for app, cnt in app_oc.items():
        tot = app_tot.get(app, 0)
        pct_oc = round(cnt/tot*100) if tot else 0
        print(f"   {app}: {cnt} oncall / {tot} total ({pct_oc}% oncall)")

    print("\n[2] TOP ROOT CAUSE TYPES EM ONCALL:")
    rct_oc = oc['Root Cause Type'].value_counts().head(6)
    rct_tot = inc['Root Cause Type'].value_counts()
    for rct, cnt in rct_oc.items():
        tot = rct_tot.get(rct, 0)
        pct = round(cnt/tot*100) if tot else 0
        print(f"   {rct}: {cnt} oncall / {tot} total ({pct}% oncall)")

    print("\n[3] ROOT CAUSE SOURCE EM ONCALL:")
    rcs_oc = oc['Root Cause Source'].value_counts().head(6)
    for rcs, cnt in rcs_oc.items():
        pct = round(cnt/len(oc)*100)
        print(f"   {rcs}: {cnt} ({pct}%)")

    # 2. RECORRÊNCIA: mesma aplicação com >3 tickets oncall
    print("\n[4] APLICAÇÕES COM >5 TICKETS ONCALL (recorrência):")
    recur = oc.groupby('Application').size()
    recur_high = recur[recur > 5].sort_values(ascending=False)
    for app, cnt in recur_high.items():
        if app == 'N/A': continue
        # Ver se há padrão de horário
        app_hours = oc[oc['Application']==app]['hour_utc'].value_counts().head(3)
        print(f"   {app}: {cnt} tickets oncall | horas UTC mais frequentes: {list(app_hours.index)}")

    # 3. PADRÃO DE HORÁRIO: quando exatamente acontecem
    print("\n[5] DISTRIBUIÇÃO HORÁRIA ONCALL (UTC):")
    h_dist = oc['hour_utc'].value_counts().sort_index()
    for h, cnt in h_dist.items():
        bar = '█' * min(cnt // max(1, len(oc)//40), 20)
        print(f"   {h:02d}:00  {cnt:4d}  {bar}")

    # 4. PADRÃO DIA DA SEMANA
    wd_names = ['Seg','Ter','Qua','Qui','Sex','Sab','Dom']
    print("\n[6] ONCALL POR DIA DA SEMANA:")
    for wd in range(7):
        cnt = (oc['weekday'] == wd).sum()
        pct = round(cnt/len(oc)*100) if len(oc) else 0
        print(f"   {wd_names[wd]}: {cnt} ({pct}%)")

    # 5. P1 ONCALL — são repetidos?
    p1_oc = oc[oc['Priority'] == 'P1']
    print(f"\n[7] P1 ONCALL: {len(p1_oc)} tickets")
    if len(p1_oc):
        print("   Top aplicações P1 oncall:")
        for app, cnt in p1_oc['Application'].value_counts().head(5).items():
            print(f"     {app}: {cnt}")
        print("   Top root causes P1 oncall:")
        for rct, cnt in p1_oc['Root Cause Type'].value_counts().head(5).items():
            print(f"     {rct}: {cnt}")

    # 6. TEMPO DE RESOLUÇÃO oncall vs business hours
    inc['dtc'] = (inc['Close Date'] - inc['Opening Date']).dt.total_seconds() / 3600
    inc_closed = inc[inc['Status'].isin(CLOSED) & inc['dtc'].notna() & (inc['dtc'] >= 0)]
    oc_closed  = inc_closed[inc_closed['is_oncall']]
    bh_closed  = inc_closed[~inc_closed['is_oncall']]
    if len(oc_closed) and len(bh_closed):
        print(f"\n[8] MTTR MÉDIO:")
        print(f"   On-Call:         {round(oc_closed['dtc'].median(),1)}h mediano | {round(oc_closed['dtc'].mean(),1)}h média")
        print(f"   Horário Comercial: {round(bh_closed['dtc'].median(),1)}h mediano | {round(bh_closed['dtc'].mean(),1)}h média")
        if len(oc_closed[oc_closed['Priority']=='P1']) and len(bh_closed[bh_closed['Priority']=='P1']):
            print(f"   P1 On-Call MTTR:    {round(oc_closed[oc_closed['Priority']=='P1']['dtc'].median(),1)}h mediano")
            print(f"   P1 Business MTTR:   {round(bh_closed[bh_closed['Priority']=='P1']['dtc'].median(),1)}h mediano")

    # 7. TENDÊNCIA: melhorou ou piorou?
    print(f"\n[9] TENDÊNCIA ONCALL (últimos 6 meses):")
    recent = oc[oc['Opening Date'] >= pd.Timestamp.now() - pd.Timedelta(days=180)]
    by_mo = recent.groupby('ym').size().sort_index()
    for ym, cnt in by_mo.items():
        tot_mo = inc[inc['ym']==ym].shape[0]
        pct = round(cnt/tot_mo*100) if tot_mo else 0
        print(f"   {ym}: {cnt} oncall / {tot_mo} total ({pct}%)")

print("\nFIM DA ANÁLISE")
