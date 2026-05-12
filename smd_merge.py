#!/usr/bin/env python3
"""
smd_merge.py — Merge de CSVs do Mantis → Tickets.csv
Arrocha ITSM | 2026

FUNÇÃO:
  Varre a pasta de Downloads procurando arquivos no padrão:
    Incidents_<Projeto><AAAA-MM-DD>.csv
  Junta todos em um único Tickets.csv e salva na pasta input.

EXEMPLOS DE NOMES ACEITOS:
  projeto_a.csv
  projeto_b.csv
  Incidents_ProjetoA2026-04-08.csv

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
import numpy as np
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

# Colunas críticas para o funcionamento básico
REQUIRED_COLS = [
    'Project Name', 'Ticket', 'Status', 'Severity',
    'Priority', 'Opening Date'
]

# Separador e encoding do Mantis
CSV_SEP      = ';'
CSV_ENCODING = 'utf-8-sig'

# Colunas que devem ser "fundidas" (se estiver vazio em uma, tenta pegar da outra)
COALESCE_COLS = [
    "MD's", "Opening Date", "Summary", "Application", "Status", "Resolution SLA", 
    "Acknowledge SLA", "Problem", "assigned", "Priority", "Severity", "Environment"
]

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

def find_csv_files(source_dir: Path, is_volatile: bool = True) -> list[dict]:
    """
    Varre source_dir e retorna lista de arquivos que batem com os padrões.
    Retorna: [{'path': Path, 'project': str, 'date': str, 'volatile': bool}, ...]
    """
    if not source_dir.exists():
        log.warning(f"Pasta não encontrada: {source_dir}")
        return []

    p_with_date = re.compile(r'^(?:Incidents_|Tickets_)?(.+?)_?(\d{4}-\d{2}-\d{2})\.csv$', re.IGNORECASE)
    p_simple    = re.compile(r'^(.+)\.csv$', re.IGNORECASE)
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    found = []
    
    for f in sorted(source_dir.iterdir()):
        if not f.is_file():
            continue
        
        if f.name.lower() in ('tickets.csv', 'smd_merge.log', 'api_key.txt'):
            continue

        m1 = p_with_date.match(f.name)
        if m1:
            project = m1.group(1).strip().strip('_')
            date    = m1.group(2)
            found.append({'path': f, 'project': project, 'date': date, 'volatile': is_volatile})
            continue
            
        m2 = p_simple.match(f.name)
        if m2:
            project = m2.group(1).strip()
            found.append({'path': f, 'project': project, 'date': today_str, 'volatile': is_volatile})

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
        if csv_prj.lower() != project.lower() and project.lower() not in csv_prj.lower() and csv_prj.lower() not in project.lower():
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


def archive_files(csv_list: list[dict]):
    """Move apenas arquivos voláteis para a subpasta 'processed' do seu diretório de origem."""
    for item in csv_list:
        if not item.get('volatile', True):
            continue
            
        try:
            p = item['path']
            archive_dir = p.parent / "processed"
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            dst = archive_dir / p.name
            if dst.exists():
                dst.unlink()
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
    
    # 2. Carregar novos arquivos
    frames = []
    total_new_raw = 0
    for item in csv_list:
        ok, msg, df = validate_csv(item['path'], item['project'])
        if not ok:
            log.warning(f"  PULADO: {msg}")
            continue
        
        df['_export_date'] = datetime.now()
        df['_priority'] = 1  # Maior prioridade
        frames.append(df)

    # 3. Carregar arquivo existente (se houver) como base de BAIXA prioridade (ao final)
    if existing_file and existing_file.exists():
        try:
            df_old = pd.read_csv(existing_file, sep=CSV_SEP, encoding=CSV_ENCODING, low_memory=False)
            df_old['_export_date'] = datetime.fromtimestamp(existing_file.stat().st_mtime)
            df_old['_priority'] = 2
            frames.append(df_old)
            log.info(f"Base antiga carregada: {len(df_old)} tickets (será usada apenas para preencher lacunas)")
        except Exception as e:
            log.error(f"Erro ao carregar base antiga: {e}")

    if not frames:
        return None

    # 4. Concatenar tudo (Novos Primeiro!)
    merged = pd.concat(frames, ignore_index=True)
    log.info(f"\nTotal bruto para processamento: {len(merged)} linhas")

    # 4. Normalização PRÉ-CONSOLIDAÇÃO
    log.info(f"Normalizando dados de {len(merged)} linhas...")
    
    # Datas
    for date_col in ['Opening Date', 'Close Date', 'Last Updated Date', 'Date of Resolution']:
        if date_col in merged.columns:
            merged[date_col] = pd.to_datetime(merged[date_col], dayfirst=True, errors='coerce')
            
    # MD's (converter para float tratando a vírgula brasileira)
    if "MD's" in merged.columns:
        merged["MD's"] = pd.to_numeric(merged["MD's"].astype(str).str.replace(',', '.'), errors='coerce')

    # 5. Consolidação Inteligente (Coalesce)
    # Primeiro, normalizamos vazios e strings de espaço para NaN para que o .first() funcione
    merged = merged.replace(r'^\s*$', np.nan, regex=True)
    
    # Ordenamos para que o dado de maior prioridade (1=Novo) e data mais recente fique no topo
    merged = merged.sort_values(['_priority', '_export_date'], ascending=[True, False])
    
    # Agrupamos por Ticket e pegamos o primeiro valor NÃO NULO de cada coluna (Coalesce)
    # Isso garante que se o arquivo novo vier com campos vazios (ex: MD's), ele busque no histórico.
    before_dedup = len(merged)
    merged['Ticket'] = merged['Ticket'].astype(str).str.lstrip('0')
    
    # Consolidar: o .first() do pandas em um dataframe ordenado pega o primeiro valor não-nulo
    merged = merged.groupby('Ticket', as_index=False, sort=False).first()
    
    # Remover colunas auxiliares
    merged = merged.drop(columns=['_export_date', '_priority'])
    
    # Voltar a ordem por ID de ticket (crescente)
    merged['_tk_num'] = pd.to_numeric(merged['Ticket'], errors='coerce')
    merged = merged.sort_values('_tk_num', ascending=True)
    merged = merged.drop(columns=['_tk_num'])

    dupes = before_dedup - len(merged)
    log.info(f"Tickets consolidados (duplicatas fundidas): {dupes}")
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


def print_summary(csv_list: list[dict]):
    """Mostra resumo dos arquivos encontrados."""
    if not csv_list:
        print("\n[X] Nenhum arquivo encontrado nas pastas configuradas.")
        return

    print(f"\nArquivos encontrados:\n")
    print(f"  {'ARQUIVO':<45} {'PROJETO':<25} {'TIPO'}")
    print(f"  {'-'*45} {'-'*25} {'-'*10}")
    for item in csv_list:
        tipo = "Volátil" if item.get('volatile') else "Histórico"
        print(f"  {item['path'].name:<45} {item['project']:<25} {tipo}")
    print(f"\n  Total: {len(csv_list)} arquivo(s)")


# ── MAIN ──────────────────────────────────────────────────────────────────────

def run(source_dir: Path = None, dry_run: bool = False, auto: bool = False):
    log.info("=" * 60)
    log.info("smd_merge.py — Início")
    log.info(f"Arquivo saída: {OUTPUT_FILE}")
    log.info("=" * 60)
 
    # 1. Encontrar arquivos (Downloads + Histórico)
    csv_list = []
    if source_dir:
        # Se o usuário passou uma pasta via CLI, usamos apenas ela
        csv_list.extend(find_csv_files(source_dir, is_volatile=True))
    else:
        # Padrão: buscar em downloads e em histórico
        csv_list.extend(find_csv_files(SOURCE_DIR, is_volatile=True))
        csv_list.extend(find_csv_files(smd_config.TT_HISTORY_DIR, is_volatile=False))
        
    print_summary(csv_list)

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
        
        # if not skip_confirm:
        #     conf = input(f"\n  Confirmar merge? [S/n]: ").strip().lower()
        #     if conf != 's' and conf != '':
        #         print("  Cancelado.")
        #         return None, None

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
        log.info("Arquivando arquivos voláteis...")
        archive_files(csv_list)

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
  chanel.csv, farmatodo.csv, etc.
  Incidents_<Projeto><AAAA-MM-DD>.csv
  Incidents_GDN2026-04-08.csv
        """
    )
    p.add_argument('--dry-run',  action='store_true', help='Só lista arquivos, não salva')
    p.add_argument('--auto',     action='store_true', help='Sem confirmação (para agendamento)')
    p.add_argument('--source',   type=str,            help=f'Pasta fonte (padrão: {SOURCE_DIR})')
    args = p.parse_args()

    source = Path(args.source) if args.source else None
    run(source_dir=source, dry_run=args.dry_run, auto=args.auto)
