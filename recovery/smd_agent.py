#!/usr/bin/env python3
"""
smd_agent.py — Interface CLI para execução dos Agentes de IA do SMD.
Alinhado com as instruções do dashboard.
"""

import sys
import json
import logging
import argparse
import re
import pandas as pd
from pathlib import Path
from datetime import datetime
import concurrent.futures

import smd_config
from smd_ai_engine import SMDAIEngine
from smd_build import process_tickets_data

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(smd_config.BASE_DIR / "smd_agent.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)

def run_agents(selected_agent=None, skip_dashboard=False):
    log.info("=" * 60)
    log.info(f"SMD AI AGENT — Iniciando execução em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    log.info("=" * 60)

    # 1. Carregar Dados
    D, T, df_raw = process_tickets_data()
    if df_raw is None or df_raw.empty:
        log.error("Não foi possível carregar os tickets para análise.")
        return

    # 2. Inicializar Motor de IA
    engine = SMDAIEngine()
    
    projects = ["Todos"] + sorted(df_raw["Project Name"].dropna().unique().tolist())
    
    # 3. Determinar quais agentes executar
    available_agents = ["ops", "predictive", "improvement", "market", "qa", "triage"]
    agents_to_run = [selected_agent] if selected_agent in available_agents else available_agents
    
    ai_insights = {}
    
    # Carregar insights existentes se não estiver rodando todos (para não sobrescrever)
    if selected_agent and smd_config.DATA_JS.exists():
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
        except:
            pass

    # 4. Executar Agentes por Projeto
    for prj in projects:
        log.info(f"Gerando contexto para: {prj}")
        if prj == "Todos":
            df_prj = df_raw.copy()
        else:
            df_prj = df_raw[df_raw["Project Name"] == prj].copy()

        if df_prj.empty:
            continue
            
        ctx = engine.build_context_data(df_prj)
        
        if prj not in ai_insights:
            ai_insights[prj] = {}
        
        def run_single_agent(agent):
            safe_prj = prj.replace(" ", "_")
            res_file = smd_config.RESULTS_DIR / f"insight_{agent}_{safe_prj}.json"
            
            # CACHE: Se já existe e não é erro, pula
            if res_file.exists():
                try:
                    cached = json.loads(res_file.read_text(encoding="utf-8"))
                    if cached and cached.get("status") == "ok":
                        log.info(f"[{prj}] Usando cache para {agent.upper()}")
                        return agent, cached
                except:
                    pass

            try:
                log.info(f"[{prj}] Executando agente {agent.upper()} [Thread]")
                if agent == "predictive" and "historical_weekly_volume" in ctx:
                    vol_summary = ", ".join([f"W{v['week_iso']}:{v['incidents']}inc" for v in ctx["historical_weekly_volume"]])
                    log.info(f"[{prj}] Contexto Preditivo (Vol Histórico): {vol_summary}")
                
                res = engine.run_agent(agent, ctx)
                
                # Salvar resultado individual para debug/auditoria
                res_file.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
                return agent, res
            except Exception as e:
                log.error(f"Falha no agente {agent} ({prj}): {e}")
                return agent, None

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_agent = {executor.submit(run_single_agent, a): a for a in agents_to_run}
            for future in concurrent.futures.as_completed(future_to_agent):
                agent, res = future.result()
                if res is not None:
                    ai_insights[prj][agent] = res

    # 5. Atualizar data.js (se não houver flag skip)
    if not skip_dashboard:
        log.info(f"Atualizando {smd_config.DATA_JS.name} com novos insights...")
        try:
            lines = smd_config.DATA_JS.read_text(encoding="utf-8").splitlines()
            new_lines = []
            found = False
            for line in lines:
                if line.startswith("var AI_INSIGHTS ="):
                    new_lines.append(f"var AI_INSIGHTS = {json.dumps(ai_insights, ensure_ascii=False, separators=(',',':'))};")
                    found = True
                else:
                    new_lines.append(line)
            
            if not found:
                new_lines.append(f"var AI_INSIGHTS = {json.dumps(ai_insights, ensure_ascii=False, separators=(',',':'))};")
            
            smd_config.DATA_JS.write_text("\n".join(new_lines), encoding="utf-8")
            log.info("Dashboard atualizado com sucesso.")
        except Exception as e:
            log.error(f"Erro ao atualizar data.js: {e}")

    log.info("Processo concluído.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SMD AI Agent CLI")
    parser.add_argument("--agent", type=str, choices=["ops", "predictive", "improvement", "market", "qa", "triage"], help="Executar apenas um agente específico")
    parser.add_argument("--no-dashboard", action="store_true", help="Não atualizar o data.js")
    parser.add_argument("--schedule", action="store_true", help="Modo scheduler (loop infinito)")
    
    args = parser.parse_args()
    
    if args.schedule:
        log.info("Modo SCHEDULER ativado (Agendado para 07:00 e 15:00)")
        # Simulação simples de scheduler para o script
        import schedule
        import time
        
        schedule.every().day.at("07:00").do(run_agents)
        schedule.every().day.at("15:00").do(run_agents)
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    else:
        run_agents(selected_agent=args.agent, skip_dashboard=args.no_dashboard)
