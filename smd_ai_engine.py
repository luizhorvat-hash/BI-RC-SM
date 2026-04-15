#!/usr/bin/env python3
"""
smd_ai_engine.py — Motor de IA Unificado para o SMD
Suporta múltiplos provedores (Ollama, Gemini) e 6 agentes especialistas.
"""

import os
import json
import logging
import time
import re
import urllib.request
import urllib.error
import socket
from datetime import datetime
from pathlib import Path
import smd_config

log = logging.getLogger(__name__)

class SMDAIEngine:
    def __init__(self, provider=None):
        self.provider = provider or smd_config.DEFAULT_AI_PROVIDER
        self.prompts = self._load_agent_prompts()
        
    def _load_agent_prompts(self):
        """Carrega personas e instruções do AGENTS.md."""
        prompts = {}
        if not smd_config.AGENTS_MD.exists():
            log.warning(f"AGENTS.md não encontrado em {smd_config.AGENTS_MD}. Usando fallbacks.")
            return prompts

        content = smd_config.AGENTS_MD.read_text(encoding="utf-8")
        # Regex simples para capturar System Prompts
        matches = re.findall(r"System Prompt: \"(.*?)\"", content)
        keys = ["ops", "predictive", "improvement", "market", "qa", "triage"]
        for i, key in enumerate(keys):
            if i < len(matches):
                prompts[key] = matches[i]
        return prompts

    def build_context_data(self, df):
        """Transforma o DataFrame de tickets em um contexto resumido para a IA."""
        import pandas as pd
        
        def safe(v): return '' if pd.isna(v) else str(v).strip()
        
        CLOSED = {'closed', 'resolved', 'rejected'}
        MY_BK = {'acknowledged', 'assigned_for_analysis', 'assigned_for_dev', 'assigned_for_testing', 'pending_required_fields'}
        CLI_BK = {'waiting_client_feedback', 'waiting_client_prd_inst', 'waiting_client_tests', 'waiting_client_tst_inst', 'waiting_oracle_feedback'}
        
        # Filtros básicos
        v = df.copy()
        v['Severity'] = v['Severity'].fillna('unknown').str.lower().str.replace(' ', '_')
        v['Status'] = v['Status'].fillna('unknown').str.lower().str.replace(' ', '_')
        
        # Resumo
        summary = {}
        for sv in ['incident', 'user_request', 'problem', 'change_request']:
            m = v['Severity'] == sv
            summary[sv] = {
                'total': int(m.sum()),
                'open': int((m & ~v['Status'].isin(CLOSED)).sum()),
                'bk_rc': int((m & v['Status'].isin(MY_BK)).sum()),
                'bk_cli': int((m & v['Status'].isin(CLI_BK)).sum()),
            }
            
        # SLA
        inc_prd = v[(v['Severity'] == 'incident') & (v['Environment'].str.upper().isin(['PRD', 'PROD'])) & (v['Status'].isin(CLOSED))]
        sla = {}
        for p in ['P1', 'P2', 'P3', 'P4']:
            t = inc_prd[inc_prd['Priority'] == p]
            met = t[pd.to_numeric(t['Resolution SLA'], errors='coerce') >= 0]
            sla[p] = {'pct': round(len(met)/len(t)*100, 1) if len(t) > 0 else 0}

        # Volume Histórico (Últimos 30 dias) consolidado por semana
        today = datetime.now()
        start_date = today - pd.Timedelta(days=30)
        hist_df = v[v['Opening Date'] >= start_date].copy()
        
        weekly_vol = []
        if not hist_df.empty:
            hist_df['week'] = hist_df['Opening Date'].dt.isocalendar().week
            for w, g in hist_df.groupby('week'):
                weekly_vol.append({
                    "week_iso": int(w),
                    "incidents": int((g['Severity'] == 'incident').sum()),
                    "user_requests": int((g['Severity'] == 'user_request').sum())
                })

        # Aging, MTTR, Burn Rate, Dormancy
        open_inc = v[(v['Severity'] == 'incident') & (~v['Status'].isin(CLOSED))].copy()
        open_inc['Opening_DT'] = pd.to_datetime(open_inc['Opening Date'], errors='coerce')
        open_inc['Last_Upd_DT'] = pd.to_datetime(open_inc['Last Updated Date'], errors='coerce')
        
        aging_30d = int((open_inc['Opening_DT'] < (today - pd.Timedelta(days=30))).sum()) if not open_inc.empty else 0
        dormant_7d = int((open_inc['Last_Upd_DT'] < (today - pd.Timedelta(days=7))).sum()) if not open_inc.empty else 0
        
        median_mttr_days = inc_prd['Days to Close'].astype(float).median() if not inc_prd.empty else 0
        if pd.isna(median_mttr_days):
            median_mttr_days = 0
        median_mttr_h = int(median_mttr_days * 24)

        # CÁLCULO DE TENDÊNCIA ESTATÍSTICA (Regressão Linear Simples)
        trend_slope = 0
        if len(weekly_vol) >= 2:
            x = list(range(len(weekly_vol)))
            y = [v['incidents'] + v['user_requests'] for v in weekly_vol]
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(xi*yi for xi, yi in zip(x, y))
            sum_xx = sum(xi*xi for xi in x)
            denom = (n * sum_xx - sum_x**2)
            trend_slope = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else 0

        start_7d = today - pd.Timedelta(days=7)
        opened_7d = len(v[(v['Severity'] == 'incident') & (pd.to_datetime(v['Opening Date'], errors='coerce') >= start_7d)])
        closed_7d = len(v[(v['Severity'] == 'incident') & (v['Status'].isin(CLOSED)) & (pd.to_datetime(v['Close Date'], errors='coerce') >= start_7d)])
        burn_rate = opened_7d - closed_7d

        open_probs = len(v[(v['Severity'] == 'problem') & (~v['Status'].isin(CLOSED))])
        prob_ratio = open_probs / len(open_inc) if not open_inc.empty else 1.0

        # Algoritmo Determinístico de Health Score
        hs = 0
        p1 = sla.get('P1',{}).get('pct',0)
        p2 = sla.get('P2',{}).get('pct',0)
        
        if p1 >= 98: hs += 25
        elif p1 >= 95: hs += 10
        if p2 >= 95: hs += 15
        elif p2 >= 90: hs += 5
        
        if dormant_7d == 0: hs += 25
        elif dormant_7d <= 5: hs += 10
        
        if burn_rate <= 0: hs += 20
        elif burn_rate <= 10: hs += 10
        
        if prob_ratio >= 0.02: hs += 15
        elif prob_ratio > 0: hs += 5

        calc_hs_val = hs
        calc_hs_col = "green" if hs >= 75 else ("yellow" if hs >= 50 else "red")
        calc_hs_lbl = "SAUDÁVEL" if hs >= 75 else ("ATENÇÃO" if hs >= 50 else "CRÍTICO")

        # PREVISÃO MATEMÁTICA PARA AS PRÓXIMAS 4 SEMANAS
        forecast = []
        if len(weekly_vol) > 0:
            last_inc = weekly_vol[-1]['incidents']
            last_req = weekly_vol[-1]['user_requests']
            for i in range(1, 5):
                forecast.append({
                    "week": i,
                    "incidents": max(0, int(last_inc + (trend_slope * i))),
                    "user_requests": max(0, int(last_req + (trend_slope * 0.5 * i))) # Reqs tendem a seguir mas com menos volatilidade
                })

        return {
            'total_tickets': int(len(v)),
            'summary': summary,
            'sla': sla,
            'backlog_rc': int(v['Status'].isin(MY_BK).sum()),
            'backlog_cli': int(v['Status'].isin(CLI_BK).sum()),
            'historical_weekly_volume': weekly_vol,
            'stat_forecast': forecast,
            'aging_30d': aging_30d,
            'dormant_7d': dormant_7d,
            'burn_rate': burn_rate,
            'prob_ratio': prob_ratio,
            'median_mttr_h': median_mttr_h,
            'trend_slope': round(trend_slope, 2),
            'trend_label': "CRESCENTE 📈" if trend_slope > 0.5 else ("DECRESCENTE 📉" if trend_slope < -0.5 else "ESTÁVEL 平"),
            'calculated_health': {'value': calc_hs_val, 'label': calc_hs_lbl, 'color': calc_hs_col},
            'timestamp': today.strftime('%Y-%m-%d %H:%M:%S')
        }

    def _extract_json(self, text):
        """Extrai e tenta reparar JSON de textos da IA (Markdown, truncamentos, vírgulas decimais)."""
        if not text or not isinstance(text, str): return {}
        
        # 1. Pré-processamento: Trata vírgulas decimais em números (ex: 0,175 -> 0.175)
        processed = re.sub(r'(\d+),(\d+)', r'\1.\2', text)
        
        # 2. Busca por blocos JSON (prioriza blocos markdown ```json ... ```)
        blocks = re.findall(r'```json\s*(\{.*?\})\s*```', processed, re.DOTALL)
        if not blocks:
            # Tenta encontrar qualquer coisa entre { e }
            blocks = re.findall(r'(\{.*\})', processed, re.DOTALL)
            
        if not blocks: return {}
        
        # 3. Tenta parsear cada bloco, do maior para o menor
        blocks.sort(key=len, reverse=True)
        for b in blocks:
            try:
                return json.loads(b)
            except json.JSONDecodeError:
                # 4. Heurística de Reparo para truncamento
                try:
                    # Se termina abruptamente, tenta fechar as estruturas básicas
                    repaired = b.strip()
                    if not repaired.endswith('}'):
                        if repaired.count('{') > repaired.count('}'): repaired += '}'
                    return json.loads(repaired)
                except:
                    continue
        return {}

    def generate_prompt(self, key, ctx):
        """Monta o prompt final combinando persona e dados."""
        persona = self.prompts.get(key, "Você é um especialista em ITSM.")
        s = ctx['summary']
        sl = ctx['sla']
        
        data_str = (
            f"Dados ITSM: {ctx['total_tickets']} total.\n"
            f"Incidents: {s['incident']['open']} abertos.\n"
            f"SLA P1: {sl.get('P1',{}).get('pct',0)}%, P2: {sl.get('P2',{}).get('pct',0)}%.\n"
            f"Tickets Aging >30d: {ctx.get('aging_30d', 0)} | Tickets Ociosos (Dormancy >7d sem atu.): {ctx.get('dormant_7d', 0)}.\n"
            f"Burn Rate 7d (Abertos-Fechados): {ctx.get('burn_rate', 0)}.\n"
            f"Proporção Problem/Incident: {ctx.get('prob_ratio', 0):.2f}.\n"
            f"MTTR Mediano P1 (estimado): {ctx.get('median_mttr_h', 0)}h.\n"
        )

        hist_str = ""
        if key == "predictive" and "historical_weekly_volume" in ctx:
            hist_str = "\nVOLUME HISTÓRICO SEMANAL (Últimos 30 dias):\n"
            hist_str += json.dumps(ctx['historical_weekly_volume'], indent=2)

        questions = {
            "improvement": "Quais automações ou Quick Wins você sugere para reduzir o volume recorrente?",
            "market": "Como nosso MTTR e SLA se comparam aos benchmarks ITIL/HDI fornecidos?",
            "qa": "Existem inconsistências de preenchimento ou falhas de conformidade no processo?",
            "triage": "Identifique tickets com aging excessivo ou que precisam de escalonamento urgente."
        }

        prompt = ""
        
        if key == "ops":
            hs_val = ctx.get('calculated_health', {}).get('value', 0)
            hs_lbl = ctx.get('calculated_health', {}).get('label', 'CRÍTICO')
            hs_col = ctx.get('calculated_health', {}).get('color', 'red')
            
            prompt = f"""PERSONA: Especialista SÊNIOR em ITSM (AI_Ops_Advisor). Postura: INCISIVA, CRÍTICA.

DADOS:
{data_str}

REGRAS:
- Health Score: {hs_val}/100 ({hs_lbl}).
- Alerta ALTO (Crítico): SLA P1 < 95%, Burn Rate > 15, Dormancy > 20, ou MTTR P1 > 8h.
- Alerta MÉDIO (Atenção): SLA P1 < 98%, Burn Rate > 5, ou MTTR P1 > 4h.

TAREFA: Retorne JSON puro (sem markdown).
JSON_DATA:
{{
  "health_score": {{ "value": {hs_val}, "color": "{hs_col}", "label": "{hs_lbl}" }},
  "executive_summary": "<avaliação CRÍTICA e DIRETA em 3 frases citando riscos>",
  "alerts": [
    {{ "level": "<ALTO|MEDIO>", "message": "<causa da perda de nota>", "metric": "<valor>" }}
  ],
  "recommendations": [
    {{ "priority": "P1", "area": "<Área>", "action": "<Ação estratégica>" }}
  ]
}}"""

        elif key == "predictive":
            trend_info = f"TENDÊNCIA ESTATÍSTICA: {ctx.get('trend_label')} (Slope: {ctx.get('trend_slope')})"
            forecast_str = json.dumps(ctx.get('stat_forecast', []), indent=2)
            
            prompt = f"""PERSONA: Sênior Data Scientist (AI_Predictive_Analyst).
            
PREVISÃO ESTATÍSTICA CALCULADA (Próximos 30 dias):
{forecast_str}

TENDÊNCIA ATUAL: {trend_info}
CAPACIDADE (Burn Rate): {ctx.get('burn_rate', 0)}

TAREFA: Escreva um resumo executivo de no MÁXIMO 2 frases comentando se a equipe vai suportar este volume ou se há risco de saturação.
Retorne JSON puro.

JSON_DATA:
{{
  "executive_summary": "<sua analise em 2 frases>",
  "prediction_risk": "<BAIXO|MEDIO|ALTO>",
  "alerts": [{{ "level": "MEDIO", "message": "Analise baseada em tendencia estatistica", "metric": "{ctx.get('trend_slope')}" }}]
}}"""

        else:
            prompt = f"""PERSONA: {persona}
{data_str}{hist_str}

TAREFA:
1. Escreva uma análise detalhada em PORTUGUÊS (Brasil) sobre o ponto central da pergunta abaixo.
   - Identifique os principais riscos e oportunidades com base nos dados.
   - Inclua recomendações acionáveis numeradas.
   - Cite métricas específicas dos dados fornecidos.
2. No final da resposta, inclua um bloco JSON com os dados estruturados.

PERGUNTA: {questions.get(key, 'Analise os dados.')}

RESPOSTA ESPERADA:
[Sua análise em português aqui]

JSON_DATA: {{"executive_summary": "...", "alerts": [{{ "level": "INF", "message": "Analise concluida", "metric": "IA" }}]}}"""

        if self.provider == 'ollama':
            prompt += "\n\nCRITICAL: Return ONLY a valid JSON object. No preamble, no explanation outside JSON."
            
        return prompt

    def call_ollama(self, prompt):
        body = json.dumps({
            "model": smd_config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1024,
                "num_ctx": 1500,
                "top_k": 10
            }
        }).encode('utf-8')
        
        req = urllib.request.Request(smd_config.OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read())
                return data.get('response', '').strip()
        except Exception as e:
            return f"Erro Ollama (Timeout/Falha): {e}"

    def call_ollama_custom(self, prompt, timeout=45):
        """Versão customizada do call_ollama com suporte a timeout dinâmico."""
        body = json.dumps({
            "model": smd_config.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "num_predict": 1024,
                "num_ctx": 1500,
                "top_k": 10
            }
        }).encode('utf-8')
        
        req = urllib.request.Request(smd_config.OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
                return data.get('response', '').strip()
        except Exception as e:
            return f"Erro Ollama (Timeout {timeout}s): {e}"

    def call_gemini(self, prompt, model=smd_config.GEMINI_MODEL):
        if not smd_config.GEMINI_API_KEY:
            return "Erro: GEMINI_API_KEY não configurada."
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={smd_config.GEMINI_API_KEY}"
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data['candidates'][0]['content']['parts'][0]['text'].strip()
        except Exception as e:
            log.error(f"Erro Gemini: {e}")
            return f"Erro Gemini: {str(e)}"

    def call_anthropic(self, prompt, model="claude-haiku-4-5-20251001"):
        if not smd_config.ANTHROPIC_API_KEY:
            return "Erro: ANTHROPIC_API_KEY não configurada."

        url = "https://api.anthropic.com/v1/messages"
        body = json.dumps({
            "model": model,
            "max_tokens": 2048,
            "temperature": 0.1,
            "system": "Você é um especialista sênior em ITSM/ITIL com foco em análise executiva. Responda sempre em português do Brasil. Seja detalhado, direto e orientado a dados. Ao estruturar JSON, use aspas duplas e campos completos.",
            "messages": [{"role": "user", "content": prompt}]
        }).encode('utf-8')
        
        headers = {
            "x-api-key": smd_config.ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        req = urllib.request.Request(url, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read())
                return data['content'][0]['text'].strip()
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            log.error(f"Erro Anthropic HTTP: {err}")
            return f"Erro Anthropic: {err}"
        except Exception as e:
            log.error(f"Erro Anthropic: {e}")
            return f"Erro Anthropic: {str(e)}"

    def get_structured_result(self, key, text, ctx):
        """Converte a resposta em texto da IA no formato JSON esperado pelo dashboard."""
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Tentar extrair JSON da resposta usando o novo extrator resiliente
        structured_info = self._extract_json(text)
        if not structured_info:
            log.warning(f"Falha ao extrair JSON estruturado para {key}. Resposta bruta salva em Results/debug_{key}.txt")
            (smd_config.RESULTS_DIR / f"debug_{key}.txt").write_text(text, encoding="utf-8")
            structured_info = {}

        # Lógica de Health Score conectada diretamente ao Backend de Negócio
        calc_hs = ctx.get('calculated_health', {})
        hs_val = calc_hs.get('value', 30)
        hs_lbl = calc_hs.get('label', 'CRÍTICO')
        hs_col = calc_hs.get('color', 'red')
        
        # P1 SLA
        p1_pct = ctx['sla'].get('P1',{}).get('pct',0)

        # PLANO B: Fallback determinístico se a IA falhou ou deu timeout
        if not text or "Erro" in text or len(text) < 20:
             if key == "ops":
                 clean_text = f"Análise Automática: Saúde do projeto em {hs_val}/100 ({hs_lbl}). SLA P1 atual em {p1_pct}%. Backlog RC: {ctx.get('backlog_rc',0)}. Backlog Cliente: {ctx.get('backlog_cli',0)}."
             elif key == "predictive":
                 clean_text = f"Previsão Baseada em Histórico: O projeto apresenta um volume total de {ctx.get('total_tickets',0)} tickets analisados. Tendência atual de burn-rate: {ctx.get('burn_rate',0)} (Abertos-Fechados 7d)."
             else:
                 clean_text = f"Resumo operacional baseado nos indicadores: {hs_lbl} ({hs_val}/100). SLA P1: {p1_pct}%. Backlog total detectado."
        else:
             # Se houver structured_summary, usamos o texto da IA (limpando o JSON se estiver lá)
             clean_text = re.sub(r'JSON_DATA:?.*?\{.*\}', '', text, flags=re.DOTALL).strip()
             if not clean_text or len(clean_text) < 10:
                  clean_text = text[:300]

        result = {
            "agent": f"AI_{key.upper()}",
            "timestamp": ts,
            "status": "ok" if "Erro" not in text else "error",
            "executive_summary": structured_info.get("executive_summary", clean_text),
            "reasoning": text if len(text) > 10 else clean_text,
            "health_score": {"value": hs_val, "label": hs_lbl, "color": hs_col},
            "alerts": structured_info.get("alerts", [{"level": "INF", "message": "Analise automatica (AI Fallback)", "metric": "IA"}])
        }
        
        if key == "ops":
            result["sla_analysis"] = {"p1_pct": p1_pct, "overall_status": "OK" if p1_pct >= 95 else "EM_RISCO"}
        
        if key == "predictive":
            # PRIORIDADE: Usar a previsão estatística do Python se a IA não gerou uma válida
            if "weekly_forecast" not in result or not result["weekly_forecast"]:
                result["weekly_forecast"] = ctx.get("stat_forecast", [])
            
            if "prediction_risk" not in result or not result["prediction_risk"]:
                slope = ctx.get("trend_slope", 0)
                result["prediction_risk"] = "ALTO" if slope > 1.0 else ("MEDIO" if slope > 0.5 else "BAIXO")
                
        return result

    def run_agent(self, key, ctx):
        prompt = self.generate_prompt(key, ctx)
        log.info(f"Executando agente {key} via {self.provider}...")
        
        # TIMEOUT DINÂMICO
        tm = 120 if key == "predictive" else 45
        text = ""
        
        if self.provider == "gemini":
            text = self.call_gemini(prompt)
        elif self.provider == "anthropic":
            text = self.call_anthropic(prompt)
        else:
            # Tenta Ollama primeiro
            text = self.call_ollama_custom(prompt, timeout=tm)
            
            # FALLBACK AUTOMÁTICO PARA CLOUD (Se configurado e falhar localmente no Preditivo)
            if key == "predictive" and ("Erro" in text or "Timeout" in text):
                log.warning(f"Ollama falhou para Preditivo. Tentando Fallback via Nuvem (Anthropic)...")
                if smd_config.ANTHROPIC_API_KEY:
                    text = self.call_anthropic(prompt)
                elif smd_config.GEMINI_API_KEY:
                    text = self.call_gemini(prompt)
            
        return self.get_structured_result(key, text, ctx)
