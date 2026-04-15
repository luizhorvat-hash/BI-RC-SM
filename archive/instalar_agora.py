#!/usr/bin/env python3
"""
instalar_agora.py
Coloca o build mais recente diretamente em C:\\Dashboard\\builds\\
Uso: python C:\\Users\\luiz.horvat\\Downloads\\instalar_agora.py
"""
import shutil, sys, os
from pathlib import Path
from datetime import datetime

BUILDS = Path("C:/Dashboard/builds")
DOWNLOADS = Path.home() / "Downloads"

# Criar pasta builds se não existir
BUILDS.mkdir(parents=True, exist_ok=True)

# Encontrar builds no Downloads
builds_found = sorted(
    DOWNLOADS.glob("arrocha_dashboard_v6_build_*.html"),
    key=lambda f: f.stat().st_mtime,
    reverse=True
)

if not builds_found:
    print("ERRO: Nenhum build encontrado em Downloads")
    print(f"  Pasta verificada: {DOWNLOADS}")
    input("Pressione Enter para sair...")
    sys.exit(1)

# Copiar todos os builds novos
copied = []
for src in builds_found:
    dst = BUILDS / src.name
    if not dst.exists():
        shutil.copy2(src, dst)
        copied.append(dst)
        print(f"[OK] Copiado: {src.name}")
    else:
        print(f"[JA EXISTE] {src.name}")

if copied:
    latest = copied[0]
    print(f"\nAbrindo: {latest.name}")
    os.startfile(str(latest))
else:
    # Abrir o mais recente que já existe
    existing = sorted(BUILDS.glob("arrocha_dashboard_v6_build_*.html"),
                      key=lambda f: f.stat().st_mtime, reverse=True)
    if existing:
        print(f"\nAbrindo mais recente existente: {existing[0].name}")
        os.startfile(str(existing[0]))

print("\nBuilds em C:\\Dashboard\\builds\\:")
for f in sorted(BUILDS.glob("*.html"), reverse=True)[:5]:
    size = round(f.stat().st_size/1024)
    print(f"  {f.name} ({size}kb)")

input("\nPressione Enter para fechar...")
