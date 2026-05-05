#!/usr/bin/env python3
"""
smd_analyze_project.py — Analise Dinamica de Projetos para o SMD Dashboard
Este script gera um relatorio de crescimento e esforco para qualquer projeto
baseado nos dados consolidados do dashboard.

Uso:
  python smd_analyze_project.py "Nome do Projeto"
"""

import json
import sys
import argparse
import pandas as pd
from pathlib import Path

# Tentar importar configuracoes locais
try:
    import smd_config
    DATA_JS = smd_config.DATA_JS
except ImportError:
    DATA_JS = Path("c:/Dashboard/data.js")

def analyze_project(project_name):
    if not DATA_JS.exists():
        print(f"[ERRO] Arquivo de dados nao encontrado em: {DATA_JS}")
        return

    print(f"[*] Analisando projeto: {project_name}...")
    
    try:
        content = DATA_JS.read_text(encoding="utf-8")
        # Extrair SMD_DATA_D (Contem os dados de timesheet granular)
        start_marker = "var SMD_DATA_D ="
        end_marker = "};"
        start_idx = content.find(start_marker) + len(start_marker)
        # Encontra o proximo }; apos o inicio dos dados
        end_idx = content.find(end_marker, start_idx) + 1
        
        json_str = content[start_idx:end_idx].strip()
        data_d = json.loads(json_str)
    except Exception as e:
        print(f"[ERRO] Falha ao ler ou processar data.js: {e}")
        return

    ts_granular = data_d.get("timesheet", {})
    if not ts_granular:
        print("[AVISO] Nao foram encontrados dados de timesheet granular no dashboard.")
        return

    rows = []
    project_upper = project_name.strip().upper()
    
    for tid, info in ts_granular.items():
        # Verifica se o projeto bate (Case Insensitive)
        if info.get("prj", "").strip().upper() == project_upper:
            periods = info.get("periods", {})
            for p, pdata in periods.items():
                rows.append({
                    "ticket": tid,
                    "month": p,
                    "hours": pdata.get("h", 0),
                    "days": pdata.get("d", 0),
                    "severity": info.get("sv", "unknown"),
                    "status": info.get("st", "unknown"),
                    "staff_count": len(pdata.get("staff", {}))
                })
    
    df = pd.DataFrame(rows)
    if df.empty:
        print(f"\n[!] Nenhum dado encontrado para o projeto '{project_name}'.")
        print("    Dica: Verifique se o nome esta escrito exatamente como aparece no Dashboard.")
        return

    # Ordenar por mes
    df = df.sort_values("month")
    
    # Agregacao Mensal
    summary = df.groupby("month").agg({
        "hours": "sum",
        "ticket": "nunique",
        "staff_count": "mean"
    }).rename(columns={"ticket": "distinct_tickets", "staff_count": "avg_staff_per_ticket"})
    
    print("\n" + "="*60)
    print(f" RESUMO ESTRATEGICO: {project_name.upper()}")
    print("="*60)
    print(summary)
    
    print("\n" + "="*60)
    print(" TOP 5 TICKETS POR MES (MAIOR ESFORCO)")
    print("="*60)
    
    for m in sorted(df["month"].unique()):
        print(f"\n>>> COMPETENCIA: {m}")
        top = df[df["month"] == m].sort_values("hours", ascending=False).head(5)
        for _, r in top.iterrows():
            print(f"  [{r['ticket']}] {r['hours']:>6.1f}h | {r['severity']:<15} | Status: {r['status']}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analise Dinamica de Projetos SMD")
    parser.add_argument("project", type=str, help="Nome do projeto para analise (ex: Chanel)")
    
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(1)
        
    args = parser.parse_args()
    analyze_project(args.project)
