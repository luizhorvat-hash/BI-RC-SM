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
        self.anonymization_map = {} # Real -> Anon
        self.reverse_map = {}       # Anon -> Real
        
    def _get_anon_name(self, name):
        """Mapeia um nome real para um pseudônimo constante durante a sessão."""
        if not name or name == "Unknown": return name
        if name in self.anonymization_map:
            return self.anonymization_map[name]
        
        idx = len(self.anonymization_map) + 1
        anon = f"Analista_{idx}"
        self.anonymization_map[name] = anon
        self.reverse_map[anon] = name
        return anon

    def _deanonymize_text(self, text):
        """Restaura nomes reais em um texto retornado pela IA."""
        if not text or not isinstance(text, str): return text
        for anon, real in self.reverse_map.items():
            text = text.replace(anon, real)
        return text
        
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
        
        aging_mask = open_inc['Opening_DT'] < (today - pd.Timedelta(days=30)) if not open_inc.empty else pd.Series(dtype=bool)
        aging_30d = int(aging_mask.sum())
        aging_tickets = open_inc[aging_mask]['Ticket'].head(3).tolist() if not open_inc.empty else []
        
        dormant_mask = open_inc['Last_Upd_DT'] < (today - pd.Timedelta(days=7)) if not open_inc.empty else pd.Series(dtype=bool)
        dormant_7d = int(dormant_mask.sum())
        dormant_tickets = open_inc[dormant_mask]['Ticket'].head(3).tolist() if not open_inc.empty else []
        
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

        # Top categorias e analistas para Operations/Improvement
        top_apps = v['Application'].value_counts().head(5).to_dict()
        top_rcs = v['Root Cause Type'].value_counts().head(5).to_dict()
        top_staff = v[v['Status'].isin(MY_BK)]['assigned'].value_counts().head(3).to_dict()
        
        # Tickets reais que violaram SLA ou estão em risco
        breached_tickets = v[(v['Status'].isin(CLOSED)) & (pd.to_numeric(v['Resolution SLA'], errors='coerce') < 0)]['Ticket'].head(3).tolist()
        backlog_tickets = v[v['Status'].isin(MY_BK)].sort_values('Opening Date')['Ticket'].head(3).tolist()

        # --- APLICA ANONIMIZAÇÃO ---
        anon_staff = {}
        for name, count in top_staff.items():
            anon_staff[self._get_anon_name(name)] = count
        
        return {
            'total_tickets': int(len(v)),
            'summary': summary,
            'sla': sla,
            'backlog_rc': int(v['Status'].isin(MY_BK).sum()),
            'backlog_cli': int(v['Status'].isin(CLI_BK).sum()),
            'historical_weekly_volume': weekly_vol,
            'stat_forecast': forecast,
            'aging_30d': aging_30d,
            'aging_tickets': aging_tickets,
            'dormant_7d': dormant_7d,
            'dormant_tickets': dormant_tickets,
            'burn_rate': burn_rate,
            'prob_ratio': prob_ratio,
            'median_mttr_h': median_mttr_h,
            'trend_slope': round(trend_slope, 2),
            'trend_label': "CRESCENTE 📈" if trend_slope > 0.5 else ("DECRESCENTE 📉" if trend_slope < -0.5 else "ESTÁVEL 平"),
            'calculated_health': {'value': calc_hs_val, 'label': calc_hs_lbl, 'color': calc_hs_col},
            'top_apps': top_apps,
            'top_rcs': top_rcs,
            'top_staff': anon_staff,
            'breached_tickets': breached_tickets,
            'backlog_tickets': backlog_tickets,
            'timestamp': today.strftime('%Y-%m-%d %H:%M:%S')
        }

    def _extract_json(self, text):
        """Extrai e tenta reparar JSON de textos da IA (Markdown, truncamentos, vírgulas decimais)."""
        if not text or not isinstance(text, str): return {}
        
        # 1. Pré-processamento: Trata vírgulas decimais em números (ex: 0,175 -> 0.175)
        # mas apenas se estiverem entre dígitos e seguidas de dígitos (evita quebrar vírgulas de separação de campos)
        processed = re.sub(r'(\d+),(\d+)', r'\1.\2', text)
        
        # 2. Busca por blocos JSON (prioriza blocos markdown ```json ... ``` ou ``` ... ```)
        blocks = re.findall(r'```(?:json)?\s*(\{.*?\})\s*```', processed, re.DOTALL)
        if not blocks:
            # Tenta encontrar o primeiro { e o último } para capturar o objeto
            start = processed.find('{')
            end = processed.rfind('}')
            if start != -1 and end != -1 and end > start:
                blocks = [processed[start:end+1]]
            
        if not blocks: return {}
        
        # 3. Tenta parsear cada bloco, do maior para o menor
        blocks.sort(key=len, reverse=True)
        for b in blocks:
            try:
                # Remove possíveis comentários de linha no JSON que algumas IAs insistem em colocar
                b_clean = re.sub(r'//.*', '', b)
                return json.loads(b_clean)
            except json.JSONDecodeError:
                # 4. Heurística de Reparo para truncamento ou aspas faltantes
                try:
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
            f"Data: {ctx['timestamp']}\n"
            f"Tickets: {ctx['total_tickets']} total.\n"
            f"Incidents: {s['incident']['open']} abertos.\n"
            f"SLA P1: {sl.get('P1',{}).get('pct',0)}%, P2: {sl.get('P2',{}).get('pct',0)}%.\n"
            f"Aging >30d: {ctx.get('aging_30d', 0)} | Dormancy >7d: {ctx.get('dormant_7d', 0)}.\n"
            f"Burn Rate: {ctx.get('burn_rate', 0)} | Prob Ratio: {ctx.get('prob_ratio', 0):.2f}.\n"
            f"Top Apps: {ctx.get('top_apps', {})}\n"
            f"Top Root Causes: {ctx.get('top_rcs', {})}\n"
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
            top_staff_str = json.dumps(ctx.get('top_staff', {}), ensure_ascii=False)
            
            prompt = f"""PERSONA: Especialista SÊNIOR em Operações ITSM (AI_Ops_Advisor). Postura: INCISIVA, FOCO EM SLA E EFICIÊNCIA.

DADOS OPERACIONAIS:
{data_str}

SINAIS CRÍTICOS:
- Health Score: {hs_val}/100 ({hs_lbl}).
- Analistas com maior backlog (Top 3): {top_staff_str}
- Tickets que violaram SLA de Resolução: {ctx.get('breached_tickets', [])}
- Tickets críticos em backlog (Top 3): {ctx.get('backlog_tickets', [])}

TAREFA: 
1. Avalie a saúde da operação e identifique os principais "SLA Breakers".
2. Verifique se o backlog está mal distribuído entre os analistas citados.
3. Nas 'recommendations', cite NOMES de analistas e IDs de tickets específicos (ex: 'Redistribuir tickets de analista.x', 'Atacar ticket 12345').
4. Retorne APENAS JSON puro.

JSON_DATA:
{{
  "health_score": {{ "value": {hs_val}, "color": "{hs_col}", "label": "{hs_lbl}" }},
  "executive_summary": "<avaliação CRÍTICA em até 3 frases focada em produtividade e SLA>",
  "alerts": [
    {{ "level": "<ALTO|MEDIO>", "message": "<motivo da perda de performance>", "metric": "<valor>" }}
  ],
  "recommendations": [
    {{ "priority": "<P1|P2>", "area": "<Área>", "action": "<Ação nominal ou técnica específica>" }}
  ]
}}"""

        elif key == "predictive":
            trend_info = f"TENDÊNCIA ESTATÍSTICA: {ctx.get('trend_label')} (Slope: {ctx.get('trend_slope')})"
            forecast_str = json.dumps(ctx.get('stat_forecast', []), indent=2)
            top_apps_str = json.dumps(ctx.get('top_apps', {}), ensure_ascii=False)
            
            prompt = f"""PERSONA: Sênior Data Scientist (AI_Predictive_Analyst). Especialista em ITSM e análise de capacidade.

DADOS HISTÓRICOS E PREVISÃO:
{data_str}

PREVISÃO ESTATÍSTICA CALCULADA (Próximos 30 dias):
{forecast_str}

SINAIS VITAIS DA OPERAÇÃO:
- Tendência de Volume: {trend_info}
- Burn Rate (Abertos vs Fechados 7d): {ctx.get('burn_rate', 0)} (Negativo é bom, Positivo indica acúmulo)
- Tickets em Aging (>30 dias): {ctx.get('aging_30d', 0)} (Ex: {', '.join(str(x) for x in ctx.get('aging_tickets', []))})
- Tickets Dormentes (>7 dias sem atualização): {ctx.get('dormant_7d', 0)} (Ex: {', '.join(str(x) for x in ctx.get('dormant_tickets', []))})
- Top Aplicações: {top_apps_str}

TAREFA: 
1. Analise se a equipe vai suportar o volume projetado considerando o "Burn Rate" atual e o passivo de tickets ("Aging" e "Dormentes").
2. Avalie se o crescimento está focado em aplicações específicas.
3. Nas 'recommendations', SEMPRE cite IDs de tickets específicos para investigar se houver dormentes ou aging (ex: 'Investigar ticket 12345').
4. Escreva um resumo executivo DIRETO E INCISIVO (máx 3 frases).
5. Retorne APENAS um JSON válido seguindo estritamente a estrutura abaixo.

JSON_DATA:
{{
  "executive_summary": "<sua análise executiva em até 3 frases focada em risco de capacidade>",
  "prediction_risk": "<BAIXO|MEDIO|ALTO>",
  "primary_bottleneck": "<O principal gargalo projetado (ex: Acúmulo de Aging, Burn rate alto na App X)>",
  "alerts": [
    {{ "level": "<ALTO|MEDIO|BAIXO>", "message": "<alerta específico>", "metric": "<valor>" }}
  ],
  "recommendations": [
    {{ "priority": "<IMEDIATA|CURTO_PRAZO>", "area": "<área afetada>", "action": "<ação preventiva>" }}
  ]
}}"""

        elif key == "improvement":
            top_apps_str = json.dumps(ctx.get('top_apps', {}), ensure_ascii=False)
            top_rcs_str = json.dumps(ctx.get('top_rcs', {}), ensure_ascii=False)
            
            prompt = f"""PERSONA: Consultor Sênior em Melhoria Contínua (ITIL 4 CSI). Postura: ANALÍTICA, ORIENTADA A EFICIÊNCIA.

DADOS REAIS DA OPERAÇÃO:
- Top Aplicações (Frequência): {top_apps_str}
- Top Causas Raiz: {top_rcs_str}
- MTTR Médio: {ctx.get('median_mttr_h', 0)}h

TAREFA: 
1. Analise as causas raiz e aplicações citadas acima. Identifique o maior ofensor e sugira uma automação TÉCNICA real para ele.
2. Avalie a maturidade (1 a 5). Se o MTTR for alto, a maturidade é baixa.
3. Nas 'quick_wins', NUNCA use "App X" ou "gap 1". Use os nomes reais das aplicações listadas nos dados acima.
4. Se os dados estiverem vazios, sugira melhorias genéricas de processo ITIL, mas cite que os dados estão insuficientes.
5. Retorne APENAS JSON puro.

JSON_DATA (ESTRUTURA OBRIGATÓRIA):
{{
  "maturity_assessment": {{ 
    "level": <número>, 
    "label": "<Iniciante|Gerenciado|Definido|Quantitativo|Otimizado>",
    "gaps": ["descrever gap real observado", "descrever ponto de melhoria"] 
  }},
  "executive_summary": "<análise baseada nos nomes das aplicações citadas acima>",
  "quick_wins": [
    {{ "target": "<Nome da Aplicação Real>", "action": "<Ação técnica específica>", "impact": "ALTO" }}
  ],
  "recommendations": [
    {{ "priority": "P2", "area": "Processo", "action": "<Melhoria baseada na Causa Raiz real>" }}
  ]
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
            return "Erro: GEMINI_API_KEY não configurada.", {}
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={smd_config.GEMINI_API_KEY}"
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1}
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                text = data['candidates'][0]['content']['parts'][0]['text'].strip()
                # Captura uso de tokens (se disponível na API Gemini)
                usage = data.get('usageMetadata', {})
                return text, {
                    "input_tokens": usage.get('promptTokenCount', 0),
                    "output_tokens": usage.get('candidatesTokenCount', 0)
                }
        except Exception as e:
            log.error(f"Erro Gemini: {e}")
            return f"Erro Gemini: {str(e)}", {}

    def call_anthropic(self, prompt, model="claude-3-5-haiku-20241022"):
        if not smd_config.ANTHROPIC_API_KEY:
            return "Erro: ANTHROPIC_API_KEY não configurada.", {}

        url = "https://api.anthropic.com/v1/messages"
        body = json.dumps({
            "model": model,
            "max_tokens": 2048,
            "temperature": 0.1,
            "system": "Você é um especialista sênior em ITSM/ITIL com foco em análise executiva. Responda sempre em português do Brasil. Use nomes fictícios ou IDs fornecidos (ex: Analista_1) sem revelar nomes reais. Ao estruturar JSON, use aspas duplas e campos completos.",
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
                text = data['content'][0]['text'].strip()
                usage = data.get('usage', {})
                return text, {
                    "input_tokens": usage.get('input_tokens', 0),
                    "output_tokens": usage.get('output_tokens', 0)
                }
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            log.error(f"Erro Anthropic HTTP: {err}")
            return f"Erro Anthropic: {err}", {}
        except Exception as e:
            log.error(f"Erro Anthropic: {e}")
            return f"Erro Anthropic: {str(e)}", {}

    def get_structured_result(self, key, text, usage, ctx):
        """Converte a resposta em texto da IA no formato JSON esperado pelo dashboard."""
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 1. Desanonimizar a resposta bruta antes de qualquer processamento
        text = self._deanonymize_text(text)

        # 2. Extrair JSON
        structured_info = self._extract_json(text)
        if not structured_info:
            log.warning(f"Falha ao extrair JSON estruturado para {key}.")
            structured_info = {}

        # 3. FinOps: Cálculo de Custo
        costs = smd_config.AI_COST_TABLE.get(self.provider, {"input_1m":0, "output_1m":0})
        in_t = usage.get("input_tokens", 0)
        out_t = usage.get("output_tokens", 0)
        est_cost = ((in_t * costs["input_1m"]) / 1000000) + ((out_t * costs["output_1m"]) / 1000000)

        calc_hs = ctx.get('calculated_health', {})
        hs_val = calc_hs.get('value', 30)
        hs_lbl = calc_hs.get('label', 'CRÍTICO')
        hs_col = calc_hs.get('color', 'red')
        p1_pct = ctx['sla'].get('P1',{}).get('pct',0)

        # Fallback de texto se a IA falhou
        if not text or "Erro" in text or len(text) < 20:
             if key == "ops":
                 clean_text = f"Análise Automática: Saúde do projeto em {hs_val}/100 ({hs_lbl}). SLA P1 em {p1_pct}%."
             else:
                 clean_text = f"Resumo operacional baseado nos indicadores: {hs_lbl} ({hs_val}/100)."
        else:
             clean_text = re.sub(r'JSON_DATA:?.*?\{.*\}', '', text, flags=re.DOTALL).strip()
             if not clean_text or len(clean_text) < 10: clean_text = text[:300]

        result = {
            "agent": f"AI_{key.upper()}",
            "timestamp": ts,
            "status": "ok" if "Erro" not in text else "error",
            "approved": False, # Human-in-the-Loop: Pendente por padrão
            "usage_stats": {
                "provider": self.provider,
                "input_tokens": in_t,
                "output_tokens": out_t,
                "cost_usd": round(est_cost, 6)
            },
            "executive_summary": structured_info.get("executive_summary", clean_text),
            "health_score": {"value": hs_val, "label": hs_lbl, "color": hs_col},
            "alerts": structured_info.get("alerts", []),
            "recommendations": structured_info.get("recommendations", []),
            "prediction_risk": structured_info.get("prediction_risk", ""),
            "maturity_assessment": structured_info.get("maturity_assessment", {}),
            "quick_wins": structured_info.get("quick_wins", [])
        }
        
        # Desanonimizar campos específicos caso o extrator JSON tenha falhado em restaurar tudo
        result["executive_summary"] = self._deanonymize_text(result["executive_summary"])
        for rec in result["recommendations"]:
            if "action" in rec: rec["action"] = self._deanonymize_text(rec['action'])

        if key == "ops":
            result["sla_analysis"] = {"p1_pct": p1_pct, "overall_status": "OK" if p1_pct >= 95 else "EM_RISCO"}
        
        if key == "predictive":
            if "weekly_forecast" not in result or not result["weekly_forecast"]:
                result["weekly_forecast"] = ctx.get("stat_forecast", [])
                
            if "prediction_risk" not in result or not result["prediction_risk"]:
                slope = ctx.get("trend_slope", 0)
                result["prediction_risk"] = "ALTO" if slope > 1.0 else ("MEDIO" if slope > 0.5 else "BAIXO")
                
        return result

    def run_agent(self, key, ctx):
        prompt = self.generate_prompt(key, ctx)
        log.info(f"Executando agente {key} via {self.provider}...")
        
        tm = 300 if key in ["predictive", "ops", "improvement", "market", "qa", "triage"] else 60
        text = ""
        usage = {}
        
        if self.provider == "gemini":
            text, usage = self.call_gemini(prompt)
        elif self.provider == "anthropic":
            text, usage = self.call_anthropic(prompt)
        else:
            # Ollama
            text = self.call_ollama_custom(prompt, timeout=tm)
            usage = {"input_tokens": 0, "output_tokens": 0} # Ollama API local não costuma retornar uso
            
            if "Erro" in text or "Timeout" in text or len(text) < 10:
                log.warning(f"Ollama falhou para {key}. Tentando Fallback via Nuvem...")
                if smd_config.ANTHROPIC_API_KEY:
                    log.info("Usando Fallback: Anthropic")
                    text, usage = self.call_anthropic(prompt)
                elif smd_config.GEMINI_API_KEY:
                    log.info("Usando Fallback: Gemini")
                    text, usage = self.call_gemini(prompt)
        
        return self.get_structured_result(key, text, usage, ctx)
