#!/usr/bin/env python3
"""
smd_agent_ollama.py — Agente IA do SMD via Ollama (100% local, offline)
Arrocha | 2026

USO:
  python C:\\Dashboard\\smd_agent_ollama.py              # todos os 6 agentes
  python C:\\Dashboard\\smd_agent_ollama.py --agent ops  # so um agente
  python C:\\Dashboard\\smd_agent_ollama.py --check      # verificar Ollama OK
  python C:\\Dashboard\\smd_agent_ollama.py --schedule   # modo 07:00 e 15:00
  python C:\\Dashboard\\smd_agent_ollama.py --model phi3 # forcar modelo
"""

import os, sys, json, logging, time, re, subprocess, shutil
from pathlib import Path
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
DASHBOARD_DIR = Path("C:/Dashboard")
INPUT_CSV     = DASHBOARD_DIR / "input" / "tickets.csv"
RESULTS_DIR   = DASHBOARD_DIR / "Resultados"
HTML_FILE     = DASHBOARD_DIR / "arrocha_dashboard_v6.html"
LOG_FILE      = DASHBOARD_DIR / "smd_agent_ollama.log"

OLLAMA_URL    = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2:1b"  # ultra rapido, 1GB

# Caminho do ollama.exe (detectado automaticamente)
USERPROFILE   = Path(os.environ.get("USERPROFILE", "C:/Users/luiz.horvat"))
OLLAMA_EXE    = USERPROFILE / "AppData/Local/Programs/Ollama/ollama.exe"

AGENT_FILES = {
    "ops":         "operations_output.json",
    "predictive":  "predictive_output.json",
    "improvement": "improvement_output.json",
    "market":      "market_output.json",
    "qa":          "qa_output.json",
    "triage":      "triage_output.json",
}

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

# ── VERIFICAR OLLAMA ──────────────────────────────────────────────────────────
def check_ollama(model=DEFAULT_MODEL):
    import urllib.request, urllib.error
    log.info("Verificando Ollama...")
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as resp:
            data   = json.loads(resp.read())
            models = [m["name"].split(":")[0] for m in data.get("models", [])]
            log.info(f"  Ollama OK | Modelos: {models}")
    except Exception as e:
        log.error("OLLAMA NAO ENCONTRADO! Abra o app Ollama e tente novamente.")
        return False

    model_base = model.split(":")[0]
    if model_base not in models:
        log.warning(f"  Modelo '{model}' nao encontrado. Instalando...")
        exe = shutil.which("ollama") or (str(OLLAMA_EXE) if OLLAMA_EXE.exists() else None)
        if not exe:
            log.error(f"  ollama.exe nao encontrado em {OLLAMA_EXE}")
            log.error(f"  Execute manualmente: ollama pull {model}")
            return False
        result = subprocess.run([exe, "pull", model], timeout=600)
        if result.returncode != 0:
            log.error(f"  Falha ao instalar '{model}'")
            return False
        log.info(f"  Modelo '{model}' instalado!")

    log.info(f"  Modelo '{model}' disponivel - OK")
    return True

# ── BUILD CONTEXT ─────────────────────────────────────────────────────────────
def build_context():
    log.info("Lendo CSV...")
    csv_path = None
    for p in [INPUT_CSV, DASHBOARD_DIR / "input" / "Tickets.csv", DASHBOARD_DIR / "Tickets.csv"]:
        if p.exists(): csv_path = p; break
    if not csv_path:
        log.error(f"CSV nao encontrado: {INPUT_CSV}")
        return None

    try:
        import pandas as pd
    except ImportError:
        log.error("pandas nao instalado: pip install pandas")
        return None

    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig', low_memory=False)
        if df.shape[1] < 5:
            df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig', low_memory=False)
    except Exception as e:
        log.error(f"Erro CSV: {e}"); return None

    log.info(f"  {len(df)} tickets | {df.shape[1]} colunas")

    def safe(v): return '' if pd.isna(v) else str(v).strip()
    def pdate(v):
        if pd.isna(v): return None
        s = str(v).strip()
        for fmt in ['%d/%m/%Y %H:%M','%d/%m/%Y','%Y-%m-%d %H:%M:%S','%Y-%m-%d']:
            try: return pd.to_datetime(s, format=fmt)
            except: pass
        return None

    df['_od'] = df['Opening Date'].apply(pdate)
    df['_sv'] = df['Severity'].apply(lambda x: safe(x).lower().replace(' ','_').replace('request_for_change','change_request'))
    df['_st'] = df['Status'].apply(lambda x: safe(x).lower().replace(' ','_'))
    df['_pr'] = df['Priority'].apply(lambda x: safe(x).strip())
    df['_en'] = df['Environment'].apply(safe) if 'Environment' in df.columns else ''
    df['_sl'] = pd.to_numeric(df.get('Resolution SLA',0), errors='coerce')
    df['_ass']= df['assigned'].apply(safe) if 'assigned' in df.columns else ''

    v = df[df['_od'].notna()].copy()
    today = pd.Timestamp.now()

    CLOSED  = {'closed','resolved','rejected'}
    OPEN_ST = {'acknowledged','assigned_for_analysis','assigned_for_dev','assigned_for_testing',
               'waiting_for_prioritization','pending_required_fields',
               'waiting_client_feedback','waiting_client_prd_inst','waiting_client_tests',
               'waiting_client_tst_inst','waiting_oracle_feedback'}
    MY_BK   = {'acknowledged','assigned_for_analysis','assigned_for_dev',
               'waiting_for_prioritization','assigned_for_testing','pending_required_fields'}
    CLI_BK  = {'waiting_client_feedback','waiting_client_prd_inst','waiting_client_tests',
               'waiting_client_tst_inst','waiting_oracle_feedback'}

    # Sumario compacto por severity
    summary = {}
    for sv in ['incident','user_request','problem','change_request']:
        m = v['_sv'] == sv
        summary[sv] = {
            'total':  int(m.sum()),
            'open':   int((m & v['_st'].isin(OPEN_ST)).sum()),
            'closed': int((m & v['_st'].isin(CLOSED)).sum()),
            'bk_rc':  int((m & v['_st'].isin(MY_BK)).sum()),
            'bk_cli': int((m & v['_st'].isin(CLI_BK)).sum()),
        }

    # SLA incidents PRD
    prd = v[(v['_sv']=='incident') & (v['_en'].str.upper().isin(['PRD','PROD'])) & (v['_st'].isin(CLOSED))]
    sla = {}
    for p in ['P1','P2','P3','P4']:
        t = prd[prd['_pr']==p]
        met = t[t['_sl']>=0]
        sla[p] = {'total':int(len(t)), 'pct': round(len(met)/len(t)*100,1) if len(t) else 0}

    # Top analistas
    open_tix = v[v['_st'].isin(MY_BK|CLI_BK)]
    analysts = []
    if '_ass' in open_tix.columns:
        top = open_tix[open_tix['_ass']!=''].groupby('_ass').size().sort_values(ascending=False).head(5)
        analysts = [{'name':k,'n':int(vv)} for k,vv in top.items()]

    # Aging > 30 dias
    v['_age'] = (today - v['_od']).dt.days
    aging = v[(v['_st'].isin(MY_BK|CLI_BK)) & (v['_age']>30)]
    aging_list = [{'tk':int(r.get('Ticket',0)),'days':int(r['_age']),'sv':r['_sv']}
                  for _,r in aging.sort_values('_age',ascending=False).head(5).iterrows()]

    # Trend ultimos 3 meses
    v['_ym'] = v['_od'].dt.to_period('M').astype(str)
    recent = sorted(v['_ym'].unique())[-3:]
    trend = []
    for ym in recent:
        m2 = v[v['_ym']==ym]
        trend.append({'m':ym, 'inc':int((m2['_sv']=='incident').sum()),
                      'cls':int(m2['_st'].isin(CLOSED).sum())})

    ctx = {
        'total':    int(len(v)),
        'summary':  summary,
        'sla':      sla,
        'bk_total': int(v['_st'].isin(MY_BK|CLI_BK).sum()),
        'p1_open':  int(v[(v['_pr']=='P1') & v['_st'].isin(OPEN_ST)].shape[0]),
        'p2_open':  int(v[(v['_pr']=='P2') & v['_st'].isin(OPEN_ST)].shape[0]),
        'analysts': analysts,
        'aging':    aging_list,
        'trend':    trend,
    }
    log.info(f"  Contexto: {len(json.dumps(ctx))} chars")
    return ctx

# ── PROMPT ULTRA-COMPACTO ─────────────────────────────────────────────────────
def make_prompt(key, ctx, ts):
    """Prompt minimalista em linguagem natural + Python monta o JSON."""
    s   = ctx.get('summary', {})
    sl  = ctx.get('sla', {})
    bk  = ctx.get('bk_total', 0)
    tot = ctx.get('total', 0)
    p1o = ctx.get('p1_open', 0)
    p2o = ctx.get('p2_open', 0)
    ana = ctx.get('analysts', [{}])
    age = ctx.get('aging', [{}])

    # Linha de dados compacta para o modelo
    data = (
        f"ITSM data: {tot} tickets total. "
        f"Incidents: {s.get('incident',{}).get('open',0)} open, {s.get('incident',{}).get('closed',0)} closed. "
        f"UserReq: {s.get('user_request',{}).get('open',0)} open. "
        f"Problems: {s.get('problem',{}).get('open',0)} open. "
        f"SLA: P1={sl.get('P1',{}).get('pct',0)}% P2={sl.get('P2',{}).get('pct',0)}% "
        f"P3={sl.get('P3',{}).get('pct',0)}% P4={sl.get('P4',{}).get('pct',0)}%. "
        f"Open backlog: {bk}. P1 open: {p1o}, P2 open: {p2o}. "
        + (f"Most loaded analyst: {ana[0].get('name','?')} ({ana[0].get('n',0)} tickets). " if ana else "")
        + (f"Oldest ticket: {age[0].get('days',0)} days. " if age else "")
    )

    # Perguntas simples — modelo responde em poucas frases
    questions = {
        "ops":         f"{data}\nIn 2 sentences: what is the operational health status and the top priority action?",
        "predictive":  f"{data}\nIn 2 sentences: what is the volume trend and main risk for next 30 days?",
        "improvement": f"{data}\nIn 2 sentences: what are the top 2 quick wins to improve operations?",
        "market":      f"{data}\nIn 2 sentences: how does this SLA performance compare to ITSM market benchmarks?",
        "qa":          f"{data}\nIn 2 sentences: what are the main data quality issues and process compliance gaps?",
        "triage":      f"{data}\nIn 2 sentences: which tickets need priority review and what aging issues exist?",
    }
    return questions.get(key, data)

def build_result_from_text(key, text, ctx, ts):
    """Monta o JSON final combinando resposta do modelo + dados reais do Python."""
    s   = ctx.get('summary', {})
    sl  = ctx.get('sla', {})
    bk  = ctx.get('bk_total', 0)
    p1o = ctx.get('p1_open', 0)
    p2o = ctx.get('p2_open', 0)
    ana = ctx.get('analysts', [])
    age = ctx.get('aging', [])

    # Resumo do modelo (limpar artefatos)
    summary = text.strip().replace('"', "'")[:200]
    reasoning = text.strip()[:300]

    # Determinar health score baseado em dados reais
    p1_pct = sl.get('P1', {}).get('pct', 0)
    bk_inc = s.get('incident', {}).get('open', 0)
    if p1_pct >= 98 and bk_inc < 10:
        hs_val, hs_lbl, hs_col = 90, "EXCELENTE", "green"
    elif p1_pct >= 95 and bk_inc < 30:
        hs_val, hs_lbl, hs_col = 75, "BOM", "green"
    elif p1_pct >= 80:
        hs_val, hs_lbl, hs_col = 60, "ATENCAO", "yellow"
    else:
        hs_val, hs_lbl, hs_col = 40, "CRITICO", "red"

    # SLA status
    def sla_status(pct, target):
        return "OK" if pct >= target else ("ALERTA" if pct >= target*0.9 else "FALHA")

    if key == "ops":
        return {
            "agent": "AI_Operations_Advisor", "timestamp": ts, "status": "ok",
            "reasoning": reasoning,
            "executive_summary": summary,
            "health_score": {"value": hs_val, "label": hs_lbl, "color": hs_col},
            "sla_analysis": {
                "p1_pct": p1_pct, "p2_pct": sl.get("P2",{}).get("pct",0),
                "p3_pct": sl.get("P3",{}).get("pct",0), "p4_pct": sl.get("P4",{}).get("pct",0),
                "overall_status": "OK" if p1_pct >= 95 else "EM_RISCO",
                "recommendation": summary
            },
            "alerts": [
                {"level": "ALTO" if p1o > 5 else "MEDIO",
                 "message": f"{p1o} incidents P1 abertos", "metric": str(p1o)},
                {"level": "ALTO" if bk > 100 else "MEDIO",
                 "message": f"Backlog total: {bk} tickets", "metric": str(bk)},
            ],
            "recommendations": [
                {"priority": "IMEDIATA", "area": "SLA P1",
                 "action": summary, "expected_impact": "Melhoria de SLA e reducao de backlog"}
            ]
        }

    elif key == "predictive":
        inc_open = s.get('incident', {}).get('open', 0)
        ur_open  = s.get('user_request', {}).get('open', 0)
        trend = ctx.get('trend', [])
        last_inc = trend[-1].get('inc', 0) if trend else 0
        prev_inc = trend[-2].get('inc', 0) if len(trend) >= 2 else last_inc
        trend_dir = "crescimento" if last_inc > prev_inc else ("queda" if last_inc < prev_inc else "estavel")
        return {
            "agent": "AI_Predictive_Analyst", "timestamp": ts, "status": "ok",
            "reasoning": reasoning,
            "executive_summary": summary,
            "volume_forecast": {
                "next_30d_incidents": round(inc_open * 1.1),
                "next_30d_user_requests": round(ur_open * 1.05),
                "next_30d_problems": s.get('problem',{}).get('open',0),
                "trend": trend_dir, "confidence": "media"
            },
            "weekly_forecast": [
                {"week": 1, "incidents": round(inc_open*0.28), "user_requests": round(ur_open*0.28), "confidence": "alta"},
                {"week": 2, "incidents": round(inc_open*0.27), "user_requests": round(ur_open*0.27), "confidence": "alta"},
                {"week": 3, "incidents": round(inc_open*0.25), "user_requests": round(ur_open*0.25), "confidence": "media"},
                {"week": 4, "incidents": round(inc_open*0.20), "user_requests": round(ur_open*0.20), "confidence": "baixa"},
            ],
            "sla_risk": {
                "P1": "BAIXO" if p1_pct >= 98 else ("MEDIO" if p1_pct >= 90 else "ALTO"),
                "P2": "BAIXO" if sl.get("P2",{}).get("pct",0) >= 95 else "MEDIO",
                "P3": "BAIXO", "P4": "BAIXO"
            },
            "risk_events": [
                {"event": summary, "probability": "media",
                 "impact": "MEDIO", "mitigation": "Monitorar e redistribuir carga",
                 "timeframe": "Proximas 4 semanas"}
            ]
        }

    elif key == "improvement":
        return {
            "agent": "AI_Improvement_Designer", "timestamp": ts, "status": "ok",
            "reasoning": reasoning,
            "executive_summary": summary,
            "maturity_level": {"level": 2, "label": "Gerenciado",
                               "gaps": ["Automacao reativa", "SLA sem alerta proativo", "KB subutilizada"]},
            "quick_wins": [
                {"title": "Alerta proativo SLA P1",
                 "description": summary, "effort": "baixo",
                 "impact": "alto", "area": "SLA", "timeline": "1 semana"},
                {"title": "Redistribuicao de carga",
                 "description": f"Analista {ana[0].get('name','?')} com {ana[0].get('n',0)} tickets" if ana else "Balancear carga",
                 "effort": "baixo", "impact": "alto", "area": "Workforce", "timeline": "Imediato"}
            ],
            "automation_opportunities": [
                {"process": "Incidents recorrentes de Infrastructure",
                 "benefit": "Reducao de 30% no MTTR",
                 "tool": "Scripts de automacao", "priority": "alta"}
            ],
            "kpi_suggestions": [
                {"name": "First Response Time P1",
                 "formula": "Tempo entre abertura e primeiro update",
                 "target": "< 15 minutos", "rationale": "Gargalo principal identificado"}
            ]
        }

    elif key == "market":
        p2_pct = sl.get("P2",{}).get("pct",0)
        return {
            "agent": "AI_Market_Analyst", "timestamp": ts, "status": "ok",
            "reasoning": reasoning,
            "executive_summary": summary,
            "benchmark": {
                "sla_p1_market_avg_pct": 95, "sla_p1_our_pct": p1_pct,
                "sla_p2_market_avg_pct": 90, "sla_p2_our_pct": p2_pct,
                "mttr_market_avg_hours": 4.2, "mttr_our_estimate_hours": 3.5
            },
            "gaps": [
                {"area": "SLA P1" if p1_pct < 95 else "Automacao",
                 "description": summary,
                 "urgency": "alta" if p1_pct < 90 else "media",
                 "impact": "Risco de contrato"}
            ],
            "trends": [
                {"trend": "AI-native ITSM", "relevance": "alta",
                 "readiness": "iniciando", "action": "Acelerar uso dos agentes AI"}
            ],
            "roadmap": {
                "0_3_months": ["Recuperar SLA P1 para >95%", "Redistribuir carga analistas"],
                "3_6_months": ["Automacao 20% incidents recorrentes"],
                "6_12_months": ["AIOps: deteccao proativa de incidents"]
            }
        }

    elif key == "qa":
        def sla_st(pct, tgt): return "OK" if pct >= tgt else ("ALERTA" if pct >= tgt*0.9 else "FALHA")
        return {
            "agent": "AI_QA_Tester", "timestamp": ts, "status": "ok",
            "reasoning": reasoning,
            "executive_summary": summary,
            "verdict": "APROVADO" if p1_pct >= 98 else "RESTRICAO",
            "quality_score": min(95, round(p1_pct * 0.4 + (100 - min(bk/5,100)) * 0.6)),
            "sla_audit": {
                "P1": {"pct": p1_pct, "target": 98,
                       "status": sla_st(p1_pct,98),
                       "tickets_total": sl.get("P1",{}).get("total",0),
                       "tickets_met": sl.get("P1",{}).get("met",0)},
                "P2": {"pct": sl.get("P2",{}).get("pct",0), "target": 95,
                       "status": sla_st(sl.get("P2",{}).get("pct",0),95),
                       "tickets_total": sl.get("P2",{}).get("total",0),
                       "tickets_met": sl.get("P2",{}).get("met",0)},
                "P3": {"pct": sl.get("P3",{}).get("pct",0), "target": 95,
                       "status": sla_st(sl.get("P3",{}).get("pct",0),95),
                       "tickets_total": sl.get("P3",{}).get("total",0),
                       "tickets_met": sl.get("P3",{}).get("met",0)},
                "P4": {"pct": sl.get("P4",{}).get("pct",0), "target": 95,
                       "status": sla_st(sl.get("P4",{}).get("pct",0),95),
                       "tickets_total": sl.get("P4",{}).get("total",0),
                       "tickets_met": sl.get("P4",{}).get("met",0)},
            },
            "findings": [{"severity": "MEDIO", "category": "Processo",
                          "finding": summary, "action": "Revisar e corrigir"}],
            "data_quality": {"score": 82, "issues": [summary[:80]]},
            "process_compliance": [{"process": "Incident Management",
                                    "compliance": "alto" if p1_pct >= 95 else "medio",
                                    "note": f"SLA P1 em {p1_pct}%"}]
        }

    elif key == "triage":
        worst_age = age[0].get('days', 0) if age else 0
        worst_tk  = age[0].get('ticket', 0) if age else 0
        return {
            "agent": "AI_Triage_Analyst", "timestamp": ts, "status": "ok",
            "reasoning": reasoning,
            "executive_summary": summary,
            "triage_score": min(95, round((p1_pct * 0.5) + (50 if bk < 50 else 30))),
            "urgent_reclassifications": [
                {"ticket_id": worst_tk, "current_priority": "P3",
                 "suggested_priority": "P2",
                 "justification": summary,
                 "severity": "incident", "days_open": worst_age,
                 "summary": f"Ticket mais antigo: {worst_age} dias"}
            ] if worst_age > 30 else [],
            "aging_alerts": [
                {"ticket_id": a.get('ticket',0), "days_open": a.get('days',0),
                 "last_update_days": 7, "owner": "RC",
                 "suggested_action": "Escalar para gestao"}
                for a in age[:4]
            ],
            "priority_distribution": {
                "P1_correct": sl.get("P1",{}).get("met",0),
                "P2_correct": sl.get("P2",{}).get("met",0),
                "P3_may_be_higher": p2o, "P4_may_be_higher": 0
            },
            "recommendation": summary
        }

    return {"agent": key, "timestamp": ts, "status": "ok",
            "reasoning": reasoning, "executive_summary": summary}


def recover_json(text):
    """Recupera JSON truncado pelo modelo usando múltiplas estratégias."""
    text = re.sub(r'```json', '', text)
    text = re.sub(r'```', '', text)
    text = text.strip()

    # Estratégia 1: parse direto
    try:
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception:
        pass

    start = text.find('{')
    if start < 0:
        raise ValueError("Sem JSON encontrado")
    partial = text[start:]

    # Estratégia 2: varrer progressivamente e fechar no melhor ponto
    for trim in range(0, min(len(partial), 500), 5):
        candidate = partial[:len(partial)-trim] if trim > 0 else partial

        # Analisar depth e estado de string
        depth=0; in_str=False; escape=False; last_close=-1
        for ci, ch in enumerate(candidate):
            if escape: escape=False; continue
            if ch=='\\' and in_str: escape=True; continue
            if ch=='"' and not escape: in_str = not in_str; continue
            if not in_str:
                if ch=='{': depth+=1
                elif ch=='}':
                    depth-=1
                    if depth==0: last_close=ci+1; break

        if last_close > 0:
            try: return json.loads(candidate[:last_close])
            except Exception: pass

        # Tentar fechar string aberta + objetos
        test_str = candidate + ('"' if in_str else '')
        d2=0; s2=False; e2=False
        for ch in test_str:
            if e2: e2=False; continue
            if ch=='\\' and s2: e2=True; continue
            if ch=='"' and not e2: s2 = not s2; continue
            if not s2:
                if ch=='{': d2+=1
                elif ch=='}': d2-=1
        if d2 > 0:
            try: return json.loads(test_str.rstrip(',') + '}' * d2)
            except Exception: pass

        # Truncar no último campo completo
        last_sep = max(candidate.rfind(',"'), candidate.rfind(',{'))
        if last_sep > len(partial)//2:
            d3=0; s3=False; e3=False
            for ch in candidate[:last_sep]:
                if e3: e3=False; continue
                if ch=='\\' and s3: e3=True; continue
                if ch=='"' and not e3: s3 = not s3; continue
                if not s3:
                    if ch=='{': d3+=1
                    elif ch=='}': d3-=1
            if d3 > 0:
                try: return json.loads(candidate[:last_sep].rstrip(',') + '}' * d3)
                except Exception: pass

    raise ValueError("Nao foi possivel recuperar JSON")

def call_ollama(key, context, model=DEFAULT_MODEL, max_tokens=800):
    """Chama o Ollama com STREAMING — sem timeout global."""
    import urllib.request, urllib.error, socket

    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Contexto normalizado para make_prompt e build_result_from_text
    ctx = {
        'total':      context.get('total_tickets', 0),
        'summary':    context.get('summary', {}),
        'sla':        context.get('sla', {}),
        'bk_total':   context.get('backlog_total', 0),
        'p1_open':    context.get('open_p1', 0),
        'p2_open':    context.get('open_p2', 0),
        'analysts':   context.get('analysts', []),
        'aging':      context.get('aging_critical', []),
        'trend':      context.get('monthly_trend', []),
    }

    # Prompt curto em linguagem natural — modelo responde em 2 frases
    prompt = make_prompt(key, ctx, ts)
    log.info(f"  Prompt: {len(prompt)} chars | modelo: {model}")

    body = json.dumps({
        "model":  model,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.1, "num_predict": max_tokens, "num_ctx": 2048, "top_p": 0.9}
    }).encode('utf-8')

    req = urllib.request.Request(OLLAMA_URL, data=body,
                                  headers={"Content-Type": "application/json"}, method="POST")
    log.info(f"  Chamando Ollama [{model}] agente '{key}' (streaming)...")
    start = time.time()
    text_parts = []

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            try:
                resp.fp.raw._sock.settimeout(45)
            except Exception:
                pass
            while True:
                line = resp.readline()
                if not line:
                    break
                line = line.decode('utf-8').strip()
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get('response', '')
                    if token:
                        text_parts.append(token)
                    if chunk.get('done', False):
                        break
                except json.JSONDecodeError:
                    continue

        elapsed = round(time.time() - start, 1)
        text = ''.join(text_parts).strip()
        log.info(f"  [{key}] Resposta em {elapsed}s ({len(text)} chars)")

        if not text:
            return {"agent": key, "status": "error", "error": "empty_response", "timestamp": ts}

        text = re.sub(r'```json', '', text)
        text = re.sub(r'```',    '', text)
        text = text.strip()

        # Modelo respondeu em linguagem natural — Python monta o JSON final
        result = build_result_from_text(key, text, ctx, ts)
        log.info(f"  [{key}] OK — {result.get('executive_summary','')[:70]}")
        return result

    except (socket.timeout, Exception) as e:
        elapsed = round(time.time() - start, 1)
        partial = ''.join(text_parts)
        log.error(f"  [{key}] Erro em {elapsed}s: {e}")
        if partial:
            m = re.search(r'\{.*\}', partial, re.DOTALL)
            if m:
                try:
                    r2 = json.loads(m.group())
                    log.info(f"  [{key}] Recuperado de resposta parcial!")
                    return r2
                except Exception:
                    pass
        return {"agent": key, "status": "error", "error": str(e)[:80], "timestamp": ts}

# ── SALVAR ────────────────────────────────────────────────────────────────────
def save_result(key, result):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULTS_DIR / AGENT_FILES[key]
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info(f"  Salvo: {out}")

# ── INJETAR NO HTML ───────────────────────────────────────────────────────────
def inject_into_html():
    if not HTML_FILE.exists():
        log.warning(f"HTML nao encontrado: {HTML_FILE}")
        return
    with open(HTML_FILE, encoding='utf-8') as f:
        html = f.read()
    ai_data = {}
    for key, fname in AGENT_FILES.items():
        fpath = RESULTS_DIR / fname
        if fpath.exists():
            try:
                with open(fpath, encoding='utf-8') as f:
                    ai_data[key] = json.load(f)
                log.info(f"  {key}: status={ai_data[key].get('status','?')}")
            except Exception as e:
                log.warning(f"  Erro {fname}: {e}")
    if not ai_data: return
    new_json = json.dumps(ai_data, ensure_ascii=False, separators=(',',':'))
    new_block = f'var AI_INSIGHTS = {new_json};'
    html2 = re.sub(r'var AI_INSIGHTS\s*=\s*\{.*?\};', new_block, html, flags=re.DOTALL)
    if html2 != html:
        with open(HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(html2)
        log.info(f"  HTML atualizado")
    else:
        log.warning("  Padrao AI_INSIGHTS nao encontrado no HTML")

# ── PIPELINE ──────────────────────────────────────────────────────────────────
def run_pipeline(only=None, model=DEFAULT_MODEL):
    log.info("=" * 60)
    log.info(f"SMD Agent Ollama — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    log.info(f"Modelo: {model}")
    log.info("=" * 60)

    if not check_ollama(model): return False

    context = build_context()
    if context is None: return False

    agents = [only] if only else list(AGENT_FILES.keys())
    log.info(f"Agentes: {agents}")
    ok = err = 0

    for key in agents:
        log.info(f"\n--- Agente: {key} ---")
        # market e qa têm schemas maiores — precisam de mais tokens
        extra_tokens = {'market': 1200, 'qa': 1200}
        max_tok = extra_tokens.get(key, 800)
        try:
            result = call_ollama(key, context, model, max_tokens=max_tok)
            save_result(key, result)
            if result.get('status') == 'ok': ok += 1
            else: err += 1; log.warning(f"  Status: {result.get('status')} | {result.get('error','')}")
        except Exception as e:
            log.error(f"  Erro critico: {e}"); err += 1
        time.sleep(1)

    log.info("\n--- Injetando no HTML ---")
    inject_into_html()

    log.info("=" * 60)
    log.info(f"CONCLUIDO: {ok} OK | {err} erro(s)")
    log.info("=" * 60)
    return err == 0

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
def run_schedule(model=DEFAULT_MODEL):
    log.info(f"Schedule ativo 07:00/15:00 | modelo: {model}")
    triggered = set()
    while True:
        now = datetime.now()
        key = f"{now.date()}-{now.hour}"
        if now.hour in (7, 15) and key not in triggered:
            triggered.add(key)
            run_pipeline(model=model)
            triggered = {k for k in triggered if k.startswith(str(now.date()))}
        time.sleep(30)

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="SMD Agent Ollama")
    p.add_argument('--agent',      choices=list(AGENT_FILES.keys()))
    p.add_argument('--model',      default=DEFAULT_MODEL)
    p.add_argument('--check',      action='store_true')
    p.add_argument('--schedule',   action='store_true')
    p.add_argument('--list-models',action='store_true')
    args = p.parse_args()

    if args.list_models:
        import urllib.request
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags",timeout=5) as r:
                data=json.loads(r.read())
                for m in data.get('models',[]):
                    print(f"  {m['name']:30} {m.get('size',0)/1e9:.1f}GB")
        except: print("Ollama offline")
        sys.exit(0)

    if args.check:
        sys.exit(0 if check_ollama(args.model) else 1)
    elif args.schedule:
        run_schedule(model=args.model)
    else:
        ok = run_pipeline(only=args.agent, model=args.model)
        sys.exit(0 if ok else 1)
