#!/usr/bin/env python3
"""
smd_merge.py — Merge de CSVs do Mantis → Tickets.csv
Arrocha ITSM | 2026

FUNÇÃO:
  Varre C:\\Users\\luiz.horvat\\Downloads procurando arquivos no padrão:
    Incidents_<Projeto><AAAA-MM-DD>.csv
  Junta todos em um único Tickets.csv e salva em C:\\Dashboard\\input\\

EXEMPLOS DE NOMES ACEITOS:
  Incidents_Chanel2026-04-08.csv
  Incidents_Farmacia Arrocha2026-04-08.csv
  Incidents_Farmatodo2026-04-08.csv
  Incidents_GDN2026-04-08.csv
  Incidents_Tata2026-04-08.csv

USO:
  python C:\\Dashboard\\smd_merge.py              # merge + confirma
  python C:\\Dashboard\\smd_merge.py --dry-run    # só lista arquivos, não salva
  python C:\\Dashboard\\smd_merge.py --auto       # sem confirmação (para agendamento)
  python C:\\Dashboard\\smd_merge.py --source "C:\\OutraPasta"  # pasta diferente

FLUXO COMPLETO (recomendado):
  python C:\\Dashboard\\smd_merge.py && python C:\\Dashboard\\smd_build.py --no-agents
"""

import os
import re
import sys
import shutil
import logging
import argparse
import smd_config
from pathlib import Path
from datetime import datetime

# ── CONFIG ────────────────────────────────────────────────────────────────────
SOURCE_DIR  = smd_config.DOWNLOADS_DIR
OUTPUT_DIR  = smd_config.INPUT_DIR
OUTPUT_FILE = smd_config.TICKETS_CSV
BACKUP_DIR  = OUTPUT_DIR / "backups"
LOG_FILE    = smd_config.BASE_DIR / "smd_merge.log"

# Padrão de nome do arquivo exportado pelo Mantis
# Aceita: Incidents_Projeto2026-04-08.csv  (com ou sem espaços no projeto)
FILE_PATTERN = re.compile(
    r'^Incidents_(.+?)(\d{4}-\d{2}-\d{2})\.csv$',
    re.IGNORECASE
)

# Colunas obrigatórias que todo CSV do Mantis deve ter
REQUIRED_COLS = [
    'Project Name', 'Ticket', 'Status', 'Severity',
    'Priority', 'Opening Date', 'Application', 'Root Cause Type',
    'Resolution SLA', 'Date of Resolution'
]

# Separador e encoding do Mantis
CSV_SEP      = ';'
CSV_ENCODING = 'utf-8-sig'

# ── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger(__name__)


# ── FUNÇÕES ───────────────────────────────────────────────────────────────────

def find_csv_files(source_dir: Path) -> list[dict]:
    """
    Varre source_dir e retorna lista de arquivos que batem com FILE_PATTERN.
    Retorna: [{'path': Path, 'project': str, 'date': str}, ...]
    """
    if not source_dir.exists():
        log.error(f"Pasta não encontrada: {source_dir}")
        return []

    found = []
    for f in sorted(source_dir.iterdir()):
        if not f.is_file():
            continue
        m = FILE_PATTERN.match(f.name)
        if m:
            project = m.group(1).strip().rstrip('_')
            date    = m.group(2)
            found.append({'path': f, 'project': project, 'date': date})

    return found


def validate_csv(path: Path, project: str) -> tuple[bool, str, object]:
    """
    Valida se o CSV tem as colunas obrigatórias e dados legíveis.
    Retorna: (ok, mensagem, dataframe_ou_None)
    """
    try:
        import pandas as pd
        df = pd.read_csv(path, sep=CSV_SEP, encoding=CSV_ENCODING, low_memory=False)
    except UnicodeDecodeError:
        try:
            import pandas as pd
            df = pd.read_csv(path, sep=CSV_SEP, encoding='latin-1', low_memory=False)
            log.warning(f"  {path.name}: encoding latin-1 (não UTF-8)")
        except Exception as e:
            return False, f"Erro de leitura: {e}", None
    except Exception as e:
        return False, f"Erro: {e}", None

    # Verificar colunas obrigatórias
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        return False, f"Colunas faltando: {missing}", None

    if len(df) == 0:
        return False, "Arquivo vazio", None

    # Verificar se Project Name bate com o nome do arquivo
    projects_no_csv = df['Project Name'].dropna().unique()
    if len(projects_no_csv) > 0:
        csv_prj = str(projects_no_csv[0])
        if csv_prj.lower() != project.lower() and project.lower() not in csv_prj.lower():
            log.warning(f"  {path.name}: projeto no arquivo ({csv_prj!r}) ≠ nome do arquivo ({project!r})")

    return True, f"{len(df)} linhas | {len(df.columns)} colunas", df


def backup_existing(output_file: Path, backup_dir: Path):
    """Faz backup do Tickets.csv atual antes de sobrescrever."""
    if not output_file.exists():
        return
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
    dst = backup_dir / f"tickets_{ts}.csv"
    shutil.copy2(output_file, dst)
    log.info(f"Backup salvo: {dst}")


def archive_files(csv_list: list[dict], source_dir: Path):
    """Move arquivos processados para uma subpasta 'processed'."""
    archive_dir = source_dir / "processed"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    for item in csv_list:
        try:
            p = item['path']
            dst = archive_dir / p.name
            if dst.exists():
                dst.unlink() # remover se já existir versão anterior
            shutil.move(str(p), str(dst))
            log.info(f"Arquivado: {p.name}")
        except Exception as e:
            log.error(f"Erro ao arquivar {item['path'].name}: {e}")



def merge_files(csv_list: list[dict], existing_file: Path = None) -> object:
    """
    Junta histórico existente com novos DataFrames, removendo duplicatas.
    A prioridade é sempre o dado do arquivo com data de exportação mais recente.
    """
    import pandas as pd
    frames = []
    
    # 1. Carregar histórico existente (se houver)
    if existing_file and existing_file.exists():
        try:
            df_old = pd.read_csv(existing_file, sep=CSV_SEP, encoding=CSV_ENCODING, low_memory=False)
            df_old['_export_date'] = '1900-01-01' # data base para histórico antigo sem marcação
            frames.append(df_old)
            log.info(f"Histórico carregado: {len(df_old)} tickets")
        except Exception as e:
            log.error(f"Erro ao carregar histórico: {e}")

    # 2. Carregar novos arquivos
    total_new_raw = 0
    for item in csv_list:
        ok, msg, df = validate_csv(item['path'], item['project'])
        if not ok:
            log.error(f"  IGNORADO {item['path'].name}: {msg}")
            continue
        
        # Marcar com a data de exportação do nome do arquivo
        df['_export_date'] = item['date']
        frames.append(df)
        total_new_raw += len(df)
        log.info(f"  OK  {item['path'].name}: {msg}")

    if not frames:
        return None

    # 3. Concatenar tudo
    merged = pd.concat(frames, ignore_index=True)
    log.info(f"\nTotal bruto (histórico + novos): {len(merged)} linhas")

    # 4. Remover duplicatas pelo número do ticket (manter a exportação mais RECENTE)
    # Primeiro garantimos que Ticket é string para comparação
    merged['Ticket'] = merged['Ticket'].astype(str)
    
    # Ordenar por data de exportação decrescente
    merged = merged.sort_values('_export_date', ascending=False)
    
    before_dedup = len(merged)
    merged = merged.drop_duplicates(subset=['Ticket'], keep='first')
    
    # Remover coluna auxiliar
    merged = merged.drop(columns=['_export_date'])
    
    # Voltar a ordem por ID de ticket (crescente)
    merged['_tk_num'] = pd.to_numeric(merged['Ticket'], errors='coerce')
    merged = merged.sort_values('_tk_num', ascending=True)
    merged = merged.drop(columns=['_tk_num'])

    dupes = before_dedup - len(merged)
    log.info(f"Tickets atualizados/desduplicados: {dupes}")
    log.info(f"Total final consolidado: {len(merged)} tickets únicos")

    # Verificar projetos presentes
    projects = sorted(merged['Project Name'].dropna().unique())
    log.info(f"Projetos no banco: {projects}")

    return merged



def save_output(df, output_file: Path):
    """Salva o DataFrame como Tickets.csv com o formato correto."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, sep=CSV_SEP, encoding=CSV_ENCODING, index=False)
    size_kb = output_file.stat().st_size // 1024
    log.info(f"\nSalvo: {output_file} ({size_kb}kb)")


def print_summary(csv_list: list[dict], source_dir: Path):
    """Mostra resumo dos arquivos encontrados."""
    if not csv_list:
        print("\n[X] Nenhum arquivo encontrado.")
        print(f"   Pasta verificada: {source_dir}")
        print(f"   Padrão esperado:  Incidents_<Projeto><AAAA-MM-DD>.csv")
        print(f"   Exemplo:          Incidents_GDN2026-04-08.csv")
        return

    print(f"\nArquivos encontrados em {source_dir}:\n")
    print(f"  {'ARQUIVO':<45} {'PROJETO':<25} {'DATA'}")
    print(f"  {'-'*45} {'-'*25} {'-'*10}")
    for item in csv_list:
        print(f"  {item['path'].name:<45} {item['project']:<25} {item['date']}")
    print(f"\n  Total: {len(csv_list)} arquivo(s)")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run(source_dir: Path, dry_run: bool = False, auto: bool = False):
    log.info("=" * 60)
    log.info("smd_merge.py — Início")
    log.info(f"Pasta fonte:  {source_dir}")
    log.info(f"Arquivo saída: {OUTPUT_FILE}")
    log.info("=" * 60)

    # 1. Encontrar arquivos
    csv_list = find_csv_files(source_dir)
    print_summary(csv_list, source_dir)

    if not csv_list:
        sys.exit(1)

    # 2. Dry-run: apenas listar
    if dry_run:
        print("\n[!] Modo --dry-run: nenhum arquivo foi salvo.")
        sys.exit(0)

    # 3. Confirmar (a menos que --auto)
    if not auto:
        print(f"\n{'-'*60}")
        print(f"  Será gerado: {OUTPUT_FILE}")
        if OUTPUT_FILE.exists():
            size_kb = OUTPUT_FILE.stat().st_size // 1024
            print(f"  Arquivo atual: {size_kb}kb — será substituído (backup automático)")
        resp = input("\n  Confirmar merge? [S/n]: ").strip().lower()
        if resp not in ('', 's', 'sim', 'y', 'yes'):
            print("  Cancelado.")
            sys.exit(0)

    # 4. Backup
    backup_existing(OUTPUT_FILE, BACKUP_DIR)

    # 5. Merge
    print(f"\n{'-'*60}")
    log.info("Processando integração aditiva (Upsert)...")
    df = merge_files(csv_list, existing_file=OUTPUT_FILE)

    if df is None or len(df) == 0:
        log.error("Nenhum dado válido para salvar.")
        sys.exit(1)

    # 6. Salvar
    save_output(df, OUTPUT_FILE)

    # 7. Arquivamento
    if not dry_run:
        print(f"\n{'-'*60}")
        log.info("Arquivando arquivos processados...")
        archive_files(csv_list, source_dir)

    print(f"\n{'-'*60}")

    print(f"[*] Merge concluído com sucesso!")
    print(f"   {len(df)} tickets | {len(df['Project Name'].dropna().unique())} projetos")
    print(f"   Salvo em: {OUTPUT_FILE}")
    print(f"\n Sugestão:")
    print(f"   python C:\\Dashboard\\smd_build.py --no-agents")

    log.info("smd_merge.py — Concluído")
    return True


if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="Merge de CSVs do Mantis em Tickets.csv",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python smd_merge.py                                    # merge interativo
  python smd_merge.py --dry-run                          # só lista, não salva
  python smd_merge.py --auto                             # sem confirmação
  python smd_merge.py --source "D:\\Exports"             # pasta diferente
  python smd_merge.py --auto && python smd_build.py --no-agents  # merge + build

Padrão de nome aceito:
  Incidents_<Projeto><AAAA-MM-DD>.csv
  Incidents_GDN2026-04-08.csv
  Incidents_Farmacia Arrocha2026-04-08.csv
        """
    )
    p.add_argument('--dry-run',  action='store_true', help='Só lista arquivos, não salva')
    p.add_argument('--auto',     action='store_true', help='Sem confirmação (para agendamento)')
    p.add_argument('--source',   type=str,            help=f'Pasta fonte (padrão: {SOURCE_DIR})')
    args = p.parse_args()

    source = Path(args.source) if args.source else SOURCE_DIR
    run(source_dir=source, dry_run=args.dry_run, auto=args.auto)
