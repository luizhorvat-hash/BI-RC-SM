import urllib.request, os, shutil
from pathlib import Path

DEST = Path("C:/Dashboard/smd_agent_ollama.py")
BACKUP = Path("C:/Dashboard/smd_agent_ollama_backup.py")

# Fazer backup do antigo
if DEST.exists():
    shutil.copy(DEST, BACKUP)
    print(f"Backup: {BACKUP}")

# Verificar se o novo já está no Downloads ou Desktop
search_dirs = [
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path("C:/Dashboard"),
]
found = None
for d in search_dirs:
    candidate = d / "smd_agent_ollama.py"
    if candidate.exists():
        size = candidate.stat().st_size
        # Verificar se é o novo (tem build_result_from_text)
        content = candidate.read_text(encoding="utf-8", errors="ignore")
        if "build_result_from_text" in content:
            found = candidate
            print(f"Arquivo novo encontrado em: {candidate} ({size} bytes)")
            break
        else:
            print(f"Arquivo ANTIGO em: {candidate} ({size} bytes) — ignorando")

if found:
    shutil.copy(found, DEST)
    print(f"Instalado com sucesso: {DEST}")
    # Verificar
    content = DEST.read_text(encoding="utf-8")
    print(f"Verificacao: build_result_from_text={'build_result_from_text' in content}")
else:
    print("ERRO: arquivo novo nao encontrado em Downloads ou Desktop")
    print("Certifique-se de ter baixado o smd_agent_ollama.py do chat")