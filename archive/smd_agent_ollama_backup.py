#!/usr/bin/env python3
"""
smd_agent_ollama.py — Agente de IA do SMD via Ollama (100% local, offline)
Arrocha | 2026

Modelo recomendado: llama3.2 (4GB) ou mistral (4GB) ou phi3 (2GB)

INSTALAÇÃO (uma vez só):
  1. Baixar Ollama: https://ollama.com/download (Windows)
  2. Instalar e abrir o Ollama
  3. No terminal: ollama pull llama3.2
  4. Pronto — sem API key, sem internet, sem custo

USO:
  python C:\\Dashboard\\smd_agent_ollama.py              # todos os 6 agentes
  python C:\\Dashboard\\smd_agent_ollama.py --agent ops  # só um agente
  python C:\\Dashboard\\smd_agent_ollama.py --check      # verificar Ollama OK
  python C:\\Dashboard\\smd_agent_ollama.py --schedule   # modo 07:00 e 15:00
  python C:\\Dashboard\\smd_agent_ollama.py --model phi3 # usar modelo diferente

MODELOS RECOMENDADOS (em ordem de qualidade vs tamanho):
  llama3.2   — 4GB  — melhor qualidade, requer 8GB RAM
  mistral    — 4GB  — boa qualidade, rápido
  phi3       — 2GB  — menor, funciona com 4GB RAM
  llama3.2:1b— 1GB  — ultra leve, qualidade menor
"""

import os, sys, json, logging, time, re, subprocess
from pathlib import Path
from datetime import datetime

# ── CONFIGURAÇÃO ──────────────────────────────────────────────────────────────
DASHBOARD_DIR = Path("C:/Dashboard")
INPUT_CSV     = DASHBOARD_DIR / "input" / "tickets.csv"
RESULTS_DIR   = DASHBOARD_DIR / "Resultados"
HTML_FILE     = DASHBOARD_DIR / "arrocha_dashboard_v6.html"
LOG_FILE      = DASHBOARD_DIR / "smd_agent_ollama.log"

OLLAMA_URL    = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"   # trocar para "mistral" ou "phi3" se preferir

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
    """Verifica se Ollama está rodando e o modelo está disponível."""
    import urllib.request, urllib.error
    log.info("Verificando Ollama...")

    # 1. Ollama está rodando?
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as resp:
            data = json.loads(resp.read())
            models = [m["name"].split(":")[0] for m in data.get("models", [])]
            log.info(f"  Ollama OK | Modelos instalados: {models}")
    except Exception as e:
        log.error("=" * 55)
        log.error("OLLAMA NAO ENCONTRADO!")
        log.error("1. Baixe em: https://ollama.com/download")
        log.error("2. Instale e abra o Ollama")
        log.error("3. No terminal execute: ollama pull llama3.2")
        log.error("4. Execute este script novamente")
        log.error("=" * 55)
        return False

    # 2. Modelo está disponível?
    model_base = model.split(":")[0]
    if model_base not in models:
        log.warning(f"  Modelo '{model}' nao encontrado. Instalando...")
        log.info(f"  Executando: ollama pull {model}")
        try:
            result = subprocess.run(
                ["ollama", "pull", model],
                capture_output=False, timeout=300
            )
            if result.returncode == 0:
                log.info(f"  Modelo '{model}' instalado com sucesso!")
            else:
                log.error(f"  Falha ao instalar '{model}'")
                return False
        except Exception as e:
            log.error(f"  Erro ao instalar modelo: {e}")
            log.error(f"  Execute manualmente: ollama pull {model}")
            return False

    log.info(f"  Modelo '{model}' disponivel - OK")
    return True

# ── BUILD CONTEXT ─────────────────────────────────────────────────────────────
def build_context():
    """Lê o CSV e constrói o contexto para os agentes."""
    log.info("Lendo dados do CSV...")

    csv_path = None
    for p in [INPUT_CSV, DASHBOARD_DIR / "Tickets.csv", DASHBOARD_DIR / "input" / "Tickets.csv"]:
        if p.exists():
            csv_path = p
            break

    if not csv_path:
        log.error(f"CSV nao encontrado. Coloque em: {INPUT_CSV}")
        return None

    log.info(f"CSV: {csv_path}")

    try:
        import pandas as pd
    except ImportError:
        log.error("pandas nao instalado. Execute: pip install pandas")
        return None

    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig', low_memory=False)
        if df.shape[1] < 5:
            df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig', low_memory=False)
    except Exception as e:
        log.error(f"Erro ao ler CSV: {e}")
        return None

    log.info(f"  {len(df)} tickets | {df.shape[1]} colunas")

    def safe(v):
        return '' if pd.isna(v) else str(v).strip()

    def parse_date(v):
        if pd.isna(v): return None
        s = str(v).strip()
        for fmt in ['%d/%m/%Y %H:%M','%d/%m/%Y','%Y-%m-%d %H:%M:%S','%Y-%m-%d']:
            try: return pd.to_datetime(s, format=fmt)
            except: pass
        return None

    df['_od'] = df['Opening Date'].apply(parse_date)
    df['_cd'] = df['Close Date'].apply(parse_date) if 'Close Date' in df.columns else None
    df['_sv'] = df['Severity'].apply(lambda x: safe(x).lower().replace(' ','_').replace('request_for_change','change_request'))
    df['_st'] = df['Status'].apply(lambda x: safe(x).lower().replace(' ','_'))
    df['_pr'] = df['Priority'].apply(lambda x: safe(x).strip())
    df['_en'] = df['Environment'].apply(safe) if 'Environment' in df.columns else ''
    df['_sl'] = pd.to_numeric(df.get('Resolution SLA', 0), errors='coerce')
    df['_ass']= df['assigned'].apply(safe) if 'assigned' in df.columns else ''
    df['_prj']= df['Project Name'].apply(safe) if 'Project Name' in df.columns else ''
    df['_rc'] = df['Root Cause Source'].apply(safe) if 'Root Cause Source' in df.columns else ''

    valid = df[df['_od'].notna()].copy()
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
    SEVS    = ['incident','user_request','problem','change_request','internal']

    # Sumário por severidade
    summary = {}
    for sv in SEVS:
        mask = valid['_sv'] == sv
        summary[sv] = {
            'total':      int(mask.sum()),
            'closed':     int((mask & valid['_st'].isin(CLOSED)).sum()),
            'open':       int((mask & valid['_st'].isin(OPEN_ST)).sum()),
            'backlog_rc': int((mask & valid['_st'].isin(MY_BK)).sum()),
            'backlog_cli':int((mask & valid['_st'].isin(CLI_BK)).sum()),
        }

    # SLA por prioridade (incidents PRD)
    prd_inc = valid[(valid['_sv']=='incident') & (valid['_en'].str.upper().isin(['PRD','PROD','PRODUCTION'])) & (valid['_st'].isin(CLOSED))]
    sla = {}
    for p in ['P1','P2','P3','P4']:
        tix = prd_inc[prd_inc['_pr']==p]
        met = tix[tix['_sl']>=0]
        sla[p] = {
            'total':   int(len(tix)),
            'met':     int(len(met)),
            'not_met': int(len(tix)-len(met)),
            'pct':     round(len(met)/len(tix)*100,1) if len(tix)>0 else 0
        }

    # Analistas com mais tickets assignados
    open_tix = valid[valid['_st'].isin(MY_BK | CLI_BK)]
    analyst_load = open_tix[open_tix['_ass']!=''].groupby('_ass').size().sort_values(ascending=False).head(10)
    analysts = [{'name':k,'tickets':int(v)} for k,v in analyst_load.items()]

    # Aging — tickets abertos há mais de X dias
    valid['_age'] = (today - valid['_od']).dt.days
    aging_30 = valid[(valid['_st'].isin(MY_BK | CLI_BK)) & (valid['_age']>30)]
    aging_critical = [
        {'ticket': int(r['Ticket']) if pd.notna(r.get('Ticket')) else 0,
         'days': int(r['_age']),
         'sv': r['_sv'], 'st': r['_st'],
         'summary': str(r.get('Summary',''))[:80]}
        for _, r in aging_30.sort_values('_age',ascending=False).head(10).iterrows()
    ]

    # Root cause distribution
    rc_dist = valid[valid['_rc']!=''].groupby(['_sv','_rc']).size().reset_index(name='count')
    rc_summary = {}
    for sv in SEVS:
        top = rc_dist[rc_dist['_sv']==sv].sort_values('count',ascending=False).head(5)
        rc_summary[sv] = [{'rc':r['_rc'],'count':int(r['count'])} for _,r in top.iterrows()]

    # Monthly trend (últimos 6 meses)
    valid['_ym'] = valid['_od'].dt.to_period('M').astype(str)
    recent_6m = sorted(valid['_ym'].unique())[-6:]
    monthly_trend = []
    for ym in recent_6m:
        m = valid[valid['_ym']==ym]
        monthly_trend.append({
            'month': ym,
            'incident':     int((m['_sv']=='incident').sum()),
            'user_request': int((m['_sv']=='user_request').sum()),
            'problem':      int((m['_sv']=='problem').sum()),
            'closed':       int(m['_st'].isin(CLOSED).sum()),
        })

    # Projetos
    projects = sorted(valid['_prj'].unique().tolist()) if '_prj' in valid.columns else []

    context = {
        'timestamp':    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'total_tickets': int(len(valid)),
        'projects':     projects[:20],  # limitar para não explodir o prompt
        'summary':      summary,
        'sla':          sla,
        'analysts':     analysts,
        'aging_critical': aging_critical,
        'rc_distribution': rc_summary,
        'monthly_trend':   monthly_trend,
        'backlog_total':   int(valid['_st'].isin(MY_BK | CLI_BK).sum()),
        'open_p1':         int(valid[(valid['_pr']=='P1') & valid['_st'].isin(OPEN_ST)].shape[0]),
        'open_p2':         int(valid[(valid['_pr']=='P2') & valid['_st'].isin(OPEN_ST)].shape[0]),
    }

    log.info(f"  Contexto: {len(json.dumps(context))//1024}kb")
    return context

# ── PROMPTS DOS AGENTES ────────────────────────────────────────────────────────
def get_prompt(key, data_json, ts):
    base = (
        "Voce e um especialista ITSM senior. Analise os dados e retorne APENAS JSON valido.\n"
        "REGRAS CRITICAS:\n"
        "- Retorne SOMENTE o JSON, sem texto antes ou depois\n"
        "- Sem markdown, sem ```json, sem explicacoes\n"
        "- Todos os campos do schema devem estar presentes\n"
        "- Numeros devem ser numeros (nao strings)\n"
        "- Use os dados reais fornecidos, nao invente valores\n\n"
        f"DADOS ITSM:\n{data_json}\n\n"
    )

    schemas = {
        "ops": (
            'Analise saude operacional. Retorne exatamente este JSON (substitua os valores):\n'
            '{"agent":"AI_Operations_Advisor","timestamp":"' + ts + '","status":"ok",'
            '"reasoning":"explique em 2-3 frases como chegou as conclusoes",'
            '"executive_summary":"resumo executivo em 1 frase",'
            '"health_score":{"value":75,"label":"BOM","color":"green"},'
            '"sla_analysis":{"p1_pct":0,"p2_pct":0,"p3_pct":0,"p4_pct":0,'
            '"overall_status":"EM_RISCO","recommendation":"acao recomendada"},'
            '"alerts":[{"level":"ALTO","message":"descricao do alerta","metric":"valor"}],'
            '"recommendations":[{"priority":"IMEDIATA","area":"SLA",'
            '"action":"acao especifica","expected_impact":"impacto esperado"}]}'
        ),
        "predictive": (
            'Analise tendencias e faca previsoes. Retorne exatamente este JSON:\n'
            '{"agent":"AI_Predictive_Analyst","timestamp":"' + ts + '","status":"ok",'
            '"reasoning":"explique a logica da previsao",'
            '"executive_summary":"resumo da previsao",'
            '"volume_forecast":{"next_30d_incidents":0,"next_30d_user_requests":0,'
            '"next_30d_problems":0,"trend":"crescimento","confidence":"media"},'
            '"weekly_forecast":['
            '{"week":1,"incidents":0,"user_requests":0,"confidence":"alta"},'
            '{"week":2,"incidents":0,"user_requests":0,"confidence":"alta"},'
            '{"week":3,"incidents":0,"user_requests":0,"confidence":"media"},'
            '{"week":4,"incidents":0,"user_requests":0,"confidence":"baixa"}],'
            '"sla_risk":{"P1":"ALTO","P2":"MEDIO","P3":"BAIXO","P4":"BAIXO"},'
            '"risk_events":[{"event":"descricao","probability":"alta",'
            '"impact":"ALTO","mitigation":"acao","timeframe":"prazo"}]}'
        ),
        "improvement": (
            'Identifique oportunidades de melhoria. Retorne exatamente este JSON:\n'
            '{"agent":"AI_Improvement_Designer","timestamp":"' + ts + '","status":"ok",'
            '"reasoning":"explique os principais gaps identificados",'
            '"executive_summary":"resumo das melhorias",'
            '"maturity_level":{"level":2,"label":"Gerenciado",'
            '"gaps":["gap1","gap2","gap3"]},'
            '"quick_wins":[{"title":"titulo","description":"descricao",'
            '"effort":"baixo","impact":"alto","area":"area","timeline":"prazo"}],'
            '"automation_opportunities":[{"process":"processo",'
            '"benefit":"beneficio","tool":"ferramenta","priority":"alta"}],'
            '"kpi_suggestions":[{"name":"nome","formula":"formula",'
            '"target":"meta","rationale":"justificativa"}]}'
        ),
        "market": (
            'Compare com benchmarks ITSM de mercado. Retorne exatamente este JSON:\n'
            '{"agent":"AI_Market_Analyst","timestamp":"' + ts + '","status":"ok",'
            '"reasoning":"explique a comparacao com o mercado",'
            '"executive_summary":"posicionamento vs mercado",'
            '"benchmark":{"sla_p1_market_avg_pct":95,"sla_p1_our_pct":0,'
            '"sla_p2_market_avg_pct":90,"sla_p2_our_pct":0,'
            '"mttr_market_avg_hours":4.2,"mttr_our_estimate_hours":0},'
            '"gaps":[{"area":"area","description":"descricao",'
            '"urgency":"alta","impact":"impacto"}],'
            '"trends":[{"trend":"tendencia","relevance":"alta",'
            '"readiness":"iniciando","action":"acao recomendada"}],'
            '"roadmap":{"0_3_months":["acao1","acao2"],'
            '"3_6_months":["acao1"],"6_12_months":["acao1"]}}'
        ),
        "qa": (
            'Audite qualidade dos dados e processos ITIL. Retorne exatamente este JSON:\n'
            '{"agent":"AI_QA_Tester","timestamp":"' + ts + '","status":"ok",'
            '"reasoning":"explique os principais problemas encontrados",'
            '"executive_summary":"resumo da auditoria",'
            '"verdict":"RESTRICAO",'
            '"quality_score":78,'
            '"sla_audit":{'
            '"P1":{"pct":0,"target":98,"status":"FALHA","tickets_total":0,"tickets_met":0},'
            '"P2":{"pct":0,"target":95,"status":"OK","tickets_total":0,"tickets_met":0},'
            '"P3":{"pct":0,"target":95,"status":"OK","tickets_total":0,"tickets_met":0},'
            '"P4":{"pct":0,"target":95,"status":"OK","tickets_total":0,"tickets_met":0}},'
            '"findings":[{"severity":"ALTO","category":"Dados",'
            '"finding":"descricao do problema","action":"acao corretiva"}],'
            '"data_quality":{"score":78,"issues":["issue1","issue2"]},'
            '"process_compliance":[{"process":"Incident Management",'
            '"compliance":"medio","note":"observacao"}]}'
        ),
        "triage": (
            'Analise prioridades e aging dos tickets. Retorne exatamente este JSON:\n'
            '{"agent":"AI_Triage_Analyst","timestamp":"' + ts + '","status":"ok",'
            '"reasoning":"explique os criterios de triagem usados",'
            '"executive_summary":"resumo da triagem",'
            '"triage_score":71,'
            '"urgent_reclassifications":[{"ticket_id":0,'
            '"current_priority":"P3","suggested_priority":"P1",'
            '"justification":"motivo","severity":"incident",'
            '"days_open":0,"summary":"resumo do ticket"}],'
            '"aging_alerts":[{"ticket_id":0,"days_open":0,'
            '"last_update_days":0,"owner":"RC",'
            '"suggested_action":"acao recomendada"}],'
            '"priority_distribution":{"P1_correct":0,"P2_correct":0,'
            '"P3_may_be_higher":0,"P4_may_be_higher":0},'
            '"recommendation":"recomendacao geral"}'
        ),
    }

    return base + schemas.get(key, '')

# ── CHAMAR OLLAMA ─────────────────────────────────────────────────────────────
def call_ollama(key, context, model=DEFAULT_MODEL):
    """Chama o Ollama local e retorna o JSON do agente."""
    import urllib.request, urllib.error

    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    data_json = json.dumps(context, ensure_ascii=False)

    # Limitar contexto se muito grande
    if len(data_json) > 8000:
        ctx_slim = {
            'timestamp':      context['timestamp'],
            'total_tickets':  context['total_tickets'],
            'summary':        context['summary'],
            'sla':            context['sla'],
            'analysts':       context['analysts'][:5],
            'aging_critical': context['aging_critical'][:5],
            'backlog_total':  context['backlog_total'],
            'open_p1':        context['open_p1'],
            'open_p2':        context['open_p2'],
            'monthly_trend':  context['monthly_trend'][-3:],
        }
        data_json = json.dumps(ctx_slim, ensure_ascii=False)
        log.info(f"  Contexto reduzido: {len(data_json)} chars")

    prompt = get_prompt(key, data_json, ts)

    body = json.dumps({
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,        # baixo = mais determinístico
            "num_predict": 2048,       # max tokens de resposta
            "top_p": 0.9,
        }
    }).encode('utf-8')

    req = urllib.request.Request(
        OLLAMA_URL,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    log.info(f"  Chamando Ollama [{model}] para agente '{key}'...")
    start = time.time()

    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = json.loads(resp.read().decode('utf-8'))
            text = raw.get('response', '').strip()
            elapsed = round(time.time() - start, 1)
            log.info(f"  [{key}] Ollama respondeu em {elapsed}s")

            # Limpar markdown se existir
            text = re.sub(r'^```json\s*', '', text, flags=re.MULTILINE)
            text = re.sub(r'^```\s*$',   '', text, flags=re.MULTILINE)
            text = text.strip()

            # Tentar extrair JSON válido
            # Às vezes o modelo adiciona texto antes ou depois do JSON
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                text = json_match.group()

            result = json.loads(text)
            log.info(f"  [{key}] OK — status: {result.get('status','?')}")
            return result

    except urllib.error.URLError as e:
        log.error(f"  [{key}] Ollama nao acessivel: {e}")
        log.error("  Verifique se o Ollama esta rodando: http://localhost:11434")
        return {"agent": key, "status": "error", "error": "ollama_offline"}

    except json.JSONDecodeError as e:
        log.error(f"  [{key}] JSON invalido: {e}")
        log.error(f"  Resposta raw: {text[:300] if 'text' in dir() else 'N/A'}")
        # Retornar estrutura de erro com timestamp para não quebrar o dashboard
        return {"agent": key, "status": "error", "error": "json_parse",
                "timestamp": ts, "executive_summary": "Erro ao parsear resposta do modelo."}

    except Exception as e:
        log.error(f"  [{key}] Erro: {e}")
        return {"agent": key, "status": "error", "error": str(e)[:100], "timestamp": ts}

# ── SALVAR RESULTADO ──────────────────────────────────────────────────────────
def save_result(key, result):
    """Salva o JSON do agente no diretório Resultados."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_DIR / AGENT_FILES[key]
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log.info(f"  Salvo: {out_path}")

# ── INJETAR RESULTADOS NO HTML ────────────────────────────────────────────────
def inject_into_html():
    """Lê os JSONs gerados e injeta no AI_INSIGHTS do HTML."""
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
                log.info(f"  Injetando {key}: status={ai_data[key].get('status','?')}")
            except Exception as e:
                log.warning(f"  Erro ao ler {fname}: {e}")

    if not ai_data:
        log.warning("Nenhum resultado para injetar")
        return

    new_ai_json = json.dumps(ai_data, ensure_ascii=False, separators=(',', ':'))
    new_assignment = f'var AI_INSIGHTS = {new_ai_json};'

    import re
    # Encontrar e substituir var AI_INSIGHTS = {...};
    pattern = r'var AI_INSIGHTS\s*=\s*\{.*?\};'
    if re.search(pattern, html, re.DOTALL):
        html = re.sub(pattern, new_assignment, html, flags=re.DOTALL)
        with open(HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(html)
        log.info(f"  HTML atualizado: {HTML_FILE}")
    else:
        log.warning("  Padrao AI_INSIGHTS nao encontrado no HTML")

# ── PIPELINE PRINCIPAL ────────────────────────────────────────────────────────
def run_pipeline(only=None, model=DEFAULT_MODEL):
    log.info("=" * 60)
    log.info(f"SMD Agent Ollama — {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    log.info(f"Modelo: {model}")
    log.info("=" * 60)

    # 1. Verificar Ollama
    if not check_ollama(model):
        log.error("Abortando — Ollama nao disponivel")
        return False

    # 2. Construir contexto
    context = build_context()
    if context is None:
        log.error("Abortando — falha ao ler CSV")
        return False

    log.info(f"Contexto: {context['total_tickets']} tickets | {len(context['projects'])} projetos")

    # 3. Executar agentes
    agents = [only] if only else list(AGENT_FILES.keys())
    log.info(f"Executando agentes: {agents}")
    ok = err = 0

    for key in agents:
        log.info(f"\n--- Agente: {key} ---")
        try:
            result = call_ollama(key, context, model)
            save_result(key, result)
            if result.get('status') == 'ok':
                ok += 1
                log.info(f"  Summary: {result.get('executive_summary','')[:80]}")
            else:
                err += 1
                log.warning(f"  Status: {result.get('status')} | Erro: {result.get('error','')}")
        except Exception as e:
            log.error(f"  Erro critico em {key}: {e}")
            err += 1
        time.sleep(2)  # pausa entre agentes

    # 4. Injetar no HTML
    log.info("\n--- Injetando resultados no HTML ---")
    inject_into_html()

    log.info("=" * 60)
    log.info(f"CONCLUIDO: {ok} OK | {err} erro(s)")
    log.info(f"Resultados: {RESULTS_DIR}")
    log.info(f"HTML: {HTML_FILE}")
    log.info("=" * 60)
    return err == 0

# ── SCHEDULER ─────────────────────────────────────────────────────────────────
def run_schedule(model=DEFAULT_MODEL):
    """Roda automaticamente às 07:00 e 15:00."""
    log.info(f"Modo schedule ativo. Aguardando 07:00 ou 15:00 (modelo: {model})")
    triggered = set()
    while True:
        now = datetime.now()
        key = f"{now.date()}-{now.hour}"
        if now.hour in (7, 15) and key not in triggered:
            triggered.add(key)
            log.info(f"Gatilho horario: {now.hour:02d}:00")
            run_pipeline(model=model)
            today = str(now.date())
            triggered = {k for k in triggered if k.startswith(today)}
        time.sleep(30)

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="SMD Agent Ollama — IA local para análise ITSM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python smd_agent_ollama.py                    # todos os 6 agentes
  python smd_agent_ollama.py --agent ops        # só Operations Advisor
  python smd_agent_ollama.py --model mistral    # usar Mistral
  python smd_agent_ollama.py --check            # verificar se Ollama OK
  python smd_agent_ollama.py --schedule         # modo 07:00 e 15:00
  python smd_agent_ollama.py --list-models      # ver modelos instalados
        """
    )
    parser.add_argument('--agent',      choices=list(AGENT_FILES.keys()),
                        help='Executar apenas um agente específico')
    parser.add_argument('--model',      default=DEFAULT_MODEL,
                        help=f'Modelo Ollama (padrão: {DEFAULT_MODEL})')
    parser.add_argument('--check',      action='store_true',
                        help='Verificar se Ollama está OK e sair')
    parser.add_argument('--schedule',   action='store_true',
                        help='Modo agendado: roda às 07:00 e 15:00')
    parser.add_argument('--list-models',action='store_true',
                        help='Listar modelos instalados no Ollama')
    args = parser.parse_args()

    if args.list_models:
        import urllib.request
        try:
            with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=5) as r:
                data = json.loads(r.read())
                print("Modelos instalados:")
                for m in data.get('models', []):
                    size_gb = m.get('size', 0) / 1e9
                    print(f"  {m['name']:30} {size_gb:.1f}GB")
        except:
            print("Ollama nao esta rodando.")
        sys.exit(0)

    if args.check:
        ok = check_ollama(args.model)
        sys.exit(0 if ok else 1)

    if args.schedule:
        run_schedule(model=args.model)
    else:
        ok = run_pipeline(only=args.agent, model=args.model)
        sys.exit(0 if ok else 1)
