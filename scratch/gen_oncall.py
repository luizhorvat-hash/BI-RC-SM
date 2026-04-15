"""
Computa estatísticas de on-call por projeto/mês para a aba de Incidents.
On-call = ticket aberto fora do horário comercial do país do cliente (UTC).

Horários comerciais locais: Seg-Sex 08:00-18:00
  Brasil   (UTC-3): 11:00-21:00 UTC
  Argentina(UTC-3): 11:00-21:00 UTC
  Venezuela(UTC-4): 12:00-22:00 UTC
  Colombia (UTC-5): 13:00-23:00 UTC

Farmatodo: janela combinada (qualquer país aberto) = 11:00-23:00 UTC Seg-Sex
GDN:       Argentina → 11:00-21:00 UTC Seg-Sex
Chanel:    Brasil    → 11:00-21:00 UTC Seg-Sex
"""
import pandas as pd
import json
import re
from datetime import datetime
from pathlib import Path

# --- Config por projeto ---
CLIENT_CONFIG = {
    "Farmatodo": {
        "countries": ["Venezuela (UTC-4)", "Argentina (UTC-3)", "Colombia (UTC-5)"],
        "biz_start_utc": 11,   # Argentina abre às 08:00 → UTC 11:00
        "biz_end_utc":   23,   # Colombia fecha às 18:00 → UTC 23:00
        "note": "Seg-Sex 08:00-18:00 em qualquer um dos países"
    },
    "GDN": {
        "countries": ["Argentina (UTC-3)"],
        "biz_start_utc": 11,
        "biz_end_utc":   21,
        "note": "Seg-Sex 08:00-18:00 Argentina"
    },
    "Chanel": {
        "countries": ["Brasil (UTC-3)"],
        "biz_start_utc": 11,
        "biz_end_utc":   21,
        "note": "Seg-Sex 08:00-18:00 Brasil"
    },
}

def is_oncall(dt, cfg):
    """Retorna True se o datetime UTC está fora do horário comercial."""
    if pd.isna(dt):
        return False
    # Fim de semana
    if dt.weekday() >= 5:
        return True
    h = dt.hour
    return h < cfg["biz_start_utc"] or h >= cfg["biz_end_utc"]

# --- Ler CSV ---
df = pd.read_csv('c:/Dashboard/input/Tickets.csv', sep=';', encoding='utf-8-sig', low_memory=False)
df.columns = [c.strip() for c in df.columns]
df['Opening Date'] = pd.to_datetime(df['Opening Date'], errors='coerce')
df['Severity'] = df['Severity'].fillna('').str.lower().str.strip()
df['Priority'] = df['Priority'].fillna('').str.strip()
df['Status']   = df['Status'].fillna('').str.lower().str.strip()
df['Project Name'] = df['Project Name'].fillna('').str.strip()

CLOSED = {'closed', 'resolved', 'rejected'}

oncall_data = {}

for prj, cfg in CLIENT_CONFIG.items():
    inc = df[(df['Project Name'] == prj) & (df['Severity'] == 'incident')].copy()
    inc = inc[inc['Opening Date'].notna()]

    if inc.empty:
        continue

    inc['is_oncall']  = inc['Opening Date'].apply(lambda d: is_oncall(d, cfg))
    inc['ym']         = inc['Opening Date'].dt.strftime('%Y-%m')
    inc['year']       = inc['Opening Date'].dt.year
    inc['weekday']    = inc['Opening Date'].dt.weekday
    inc['hour_utc']   = inc['Opening Date'].dt.hour
    inc['is_weekend'] = inc['weekday'] >= 5

    total       = len(inc)
    total_oc    = int(inc['is_oncall'].sum())
    total_wkend = int(inc['is_weekend'].sum())
    total_night = int((inc['is_oncall'] & ~inc['is_weekend']).sum())

    # Por mês
    by_month = {}
    for ym, g in inc.groupby('ym'):
        oc = int(g['is_oncall'].sum())
        tot = len(g)
        by_month[ym] = {
            'oncall': oc,
            'total': tot,
            'pct': round(oc / tot * 100, 1) if tot else 0,
            'weekend': int(g['is_weekend'].sum()),
            'night_weekday': int((g['is_oncall'] & ~g['is_weekend']).sum()),
        }

    # Por prioridade
    by_priority = {}
    for pri, g in inc.groupby('Priority'):
        oc = int(g['is_oncall'].sum())
        tot = len(g)
        by_priority[str(pri)] = {
            'oncall': oc,
            'total': tot,
            'pct': round(oc / tot * 100, 1) if tot else 0,
        }

    # Distribuição por hora UTC (para chart)
    hour_dist = inc[inc['is_oncall']]['hour_utc'].value_counts().sort_index()
    hour_chart = [{'h': int(h), 'count': int(c)} for h, c in hour_dist.items()]

    # Por dia da semana
    weekday_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom']
    by_weekday = {}
    for wd, g in inc.groupby('weekday'):
        oc = int(g['is_oncall'].sum())
        by_weekday[weekday_names[wd]] = {
            'oncall': oc,
            'total': len(g),
        }

    oncall_data[prj] = {
        'total_incidents': total,
        'total_oncall': total_oc,
        'pct_oncall': round(total_oc / total * 100, 1) if total else 0,
        'total_weekend': total_wkend,
        'total_night_weekday': total_night,
        'countries': cfg['countries'],
        'business_hours_note': cfg['note'],
        'biz_start_utc': cfg['biz_start_utc'],
        'biz_end_utc': cfg['biz_end_utc'],
        'by_month': by_month,
        'by_priority': by_priority,
        'hour_distribution': hour_chart,
        'by_weekday': by_weekday,
    }
    print(f"{prj}: {total} incidents, {total_oc} oncall ({oncall_data[prj]['pct_oncall']}%) | weekend={total_wkend} night-weekday={total_night}")
    print(f"  by_priority: { {k: v['pct'] for k,v in by_priority.items()} }")

# Salvar para step 2
with open('c:/Dashboard/scratch/_oncall_tmp.json', 'w', encoding='utf-8') as f:
    json.dump(oncall_data, f, ensure_ascii=False, indent=2)
print("DONE — saved to scratch/_oncall_tmp.json")
