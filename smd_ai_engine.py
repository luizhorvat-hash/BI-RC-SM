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

        return {
            'total_tickets': int(len(v)),
            'summary': summary,
            'sla': sla,
            'backlog_rc': int(v['Status'].isin(MY_BK).sum()),
            'backlog_cli': int(v['Status'].isin(CLI_BK).sum()),
            'historical_weekly_volume': weekly_vol,
            'timestamp': today.strftime('%Y-%m-%d %H:%M:%S')
        }

    def generate_prompt(self, key, ctx):
        """Monta o prompt final combinando persona e dados."""
        persona = self.prompts.get(key, "Você é um especialista em ITSM.")
        s = ctx['summary']
        sl = ctx['sla']
        
        data_str = (
            f"Dados ITSM: {ctx['total_tickets']} total. "
            f"Incidents: {s['incident']['open']} abertos. "
            f"SLA P1: {sl.get('P1',{}).get('pct',0)}%, P2: {sl.get('P2',{}).get('pct',0)}%. "
            f"Backlog RC: {ctx['backlog_rc']}, Backlog Cliente: {ctx['backlog_cli']}."
        )

        hist_str = ""
        if key == "predictive" and "historical_weekly_volume" in ctx:
            hist_str = "\nVOLUME HISTÓRICO SEMANAL (Últimos 30 dias):\n"
            hist_str += json.dumps(ctx['historical_weekly_volume'], indent=2)

        questions = {
            "ops": "Qual o status da saúde operacional e ação prioritária?",
            "predictive": "PREVISÃO: Com base no VOLUME HISTÓRICO SEMANAL, projete as próximas 4 semanas. Retorne JSON: {\"weekly_forecast\":[{\"week\":1,\"incidents\":10,\"user_requests\":15},...]}",
            "improvement": "Aponte 2 quick wins para melhorar a operação.",


            "market": "Como este SLA se compara com benchmarks de mercado?",
            "qa": "Quais os principais gaps de qualidade ou conformidade?",
            "triage": "Quais tickets precisam de revisão urgente por aging?"
        }
        
        return f"""PERSONA: {persona}
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

JSON_DATA: {{"executive_summary": "...", ...}}"""



    def call_ollama(self, prompt, model=smd_config.OLLAMA_MODEL):
        body = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 200,
                "num_ctx": 1500,
                "top_k": 10
            }
        }).encode('utf-8')
        
        req = urllib.request.Request(smd_config.OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:

                data = json.loads(resp.read())
                return data.get('response', '').strip()
        except Exception as e:
            return f"Erro Ollama: {e}"

    def call_gemini(self, prompt, model=smd_config.GEMINI_MODEL):
        if not smd_config.GEMINI_API_KEY:
            return "Erro: GEMINI_API_KEY não configurada."
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={smd_config.GEMINI_API_KEY}"
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}]
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
        
        # Tentar extrair JSON da resposta se a IA foi prolixa
        structured_info = {}
        try:
            json_match = re.search(r'(\{.*\})', text, re.DOTALL)
            if json_match:
                structured_info = json.loads(json_match.group(1))
        except Exception as e:
            log.warning(f"Falha ao extrair JSON estruturado para {key}: {e}. Resposta bruta salva em Results/debug_{key}.txt")
            (smd_config.RESULTS_DIR / f"debug_{key}.txt").write_text(text, encoding="utf-8")
            pass

        # Lógica de Health Score simplificada para a engine
        p1_pct = ctx['sla'].get('P1',{}).get('pct',0)
        hs_val = 90 if p1_pct >= 98 else (70 if p1_pct >= 95 else (50 if p1_pct >= 80 else 30))
        hs_lbl = "EXCELENTE" if hs_val >= 90 else ("BOM" if hs_val >= 70 else ("ATENÇÃO" if hs_val >= 50 else "CRÍTICO"))
        hs_col = "green" if hs_val >= 70 else ("yellow" if hs_val >= 50 else "red")

        # Template base compatível com o frontend
        # Se não houver structured_summary, usamos o texto da IA (limpando o JSON se estiver lá)
        clean_text = re.sub(r'JSON_DATA:?.*?\{.*\}', '', text, flags=re.DOTALL).strip()
        if not clean_text or len(clean_text) < 10:
             clean_text = text[:300]

        result = {
            "agent": f"AI_{key.upper()}",
            "timestamp": ts,
            "status": "ok" if "Erro" not in text else "error",
            "executive_summary": structured_info.get("executive_summary", clean_text),
            "reasoning": text,
            "health_score": {"value": hs_val, "label": hs_lbl, "color": hs_col},
            "alerts": [{"level": "MEDIO", "message": "Analise automatica", "metric": "IA"}]
        }
        
        if key == "ops":
            result["sla_analysis"] = {"p1_pct": p1_pct, "overall_status": "OK" if p1_pct >= 95 else "EM_RISCO"}
        
        if key == "predictive" and "weekly_forecast" in structured_info:
            result["weekly_forecast"] = structured_info["weekly_forecast"]
        
        return result

    def run_agent(self, key, ctx):
        prompt = self.generate_prompt(key, ctx)
        log.info(f"Executando agente {key} via {self.provider}...")
        
        if self.provider == "gemini":
            text = self.call_gemini(prompt)
        elif self.provider == "anthropic":
            text = self.call_anthropic(prompt)
        else:
            text = self.call_ollama(prompt)
            
        return self.get_structured_result(key, text, ctx)
