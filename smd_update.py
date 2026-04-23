#!/usr/bin/env python3
"""
smd_update.py — Comando único para atualizar o Dashboard (Merge + Build)
Arrocha | 2026

USO:
  python smd_update.py          # Atualização rápida (sem IA)
  python smd_update.py --ai     # Atualização completa (com Agentes de IA)
"""

import sys
import subprocess
import time
from pathlib import Path

# Configurações de caminhos
BASE_DIR = Path(__file__).parent.absolute()
MERGE_SCRIPT = BASE_DIR / "smd_merge.py"
BUILD_SCRIPT = BASE_DIR / "smd_build.py"

def run_command(cmd_list, description):
    print(f"\n[>>>] {description}...")
    start_time = time.time()
    try:
        # Executa o sub-processo e redireciona a saída para o terminal atual
        process = subprocess.run(
            [sys.executable] + cmd_list,
            check=True,
            text=True
        )
        elapsed = time.time() - start_time
        print(f"[OK] {description} concluído em {elapsed:.1f}s")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[X] ERRO em: {description}")
        print(f"    Código de saída: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n[X] Erro inesperado: {e}")
        return False

def main():
    use_ai = "--ai" in sys.argv
    
    print("=" * 60)
    print(" SMD - ATUALIZAÇÃO RÁPIDA DE DADOS ")
    print("=" * 60)
    
    # 1. Passo: Merge (Sincronização de novos arquivos de Downloads -> Tickets.csv)
    # Usamos --auto para não pedir confirmação
    if not run_command([str(MERGE_SCRIPT), "--auto"], "Integração de novos CSVs (Merge)"):
        print("\nO processo foi interrompido devido a um erro no Merge.")
        sys.exit(1)

    # 2. Passo: Build (Geração do data.js para o Dashboard)
    # Por padrão, pulamos os agentes por velocidade, a menos que --ai seja passado
    build_args = [str(BUILD_SCRIPT)]
    if not use_ai:
        build_args.append("--no-agents")
        msg = "Gerando Dashboard (Modo Rápido)"
    else:
        msg = "Gerando Dashboard (Modo Completo com IA)"

    if not run_command(build_args, msg):
        print("\nO processo foi interrompido devido a um erro no Build.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print(" [✓] SUCESSO: Dashboard atualizado e pronto para uso!")
    print("=" * 60)
    print(" Próximos passos:")
    print(" 1. Abra (ou recarregue) o arquivo SM_DASH.html")
    print(" 2. Use 'python smd_update.py --ai' se precisar de novas análises detalhadas.")
    print("=" * 60)

if __name__ == "__main__":
    main()
