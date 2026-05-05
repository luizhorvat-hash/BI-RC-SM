import os
from pathlib import Path

# Configurações de Diretório
BASE_DIR = Path(__file__).parent.absolute()
INPUT_DIR = BASE_DIR / "input"
RESULTS_DIR = BASE_DIR / "Resultados"
BUILDS_DIR = BASE_DIR / "builds"

# Arquivos
TICKETS_CSV = INPUT_DIR / "tickets.csv"
DOWNLOADS_DIR = BASE_DIR / "downloads"
DASHBOARD_HTML = BASE_DIR / "SM_DASH.html"
DATA_JS = BASE_DIR / "data.js"
AGENTS_MD = BASE_DIR / "AGENTS.md"

# Carregamento Simples de .env
def load_dotenv(path):
    env_path = Path(path)
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

load_dotenv(BASE_DIR / ".env")

# IA Config (Preferência por .env)
DEFAULT_AI_PROVIDER = os.environ.get("DEFAULT_AI_PROVIDER", "ollama")  # ollama | gemini | anthropic
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Carregamento da Chave Anthropic de arquivo ou .env
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
API_KEY_FILE = BASE_DIR / "api_key.txt"
if API_KEY_FILE.exists():
    key_found = API_KEY_FILE.read_text(encoding="utf-8").strip()
    if key_found.startswith("sk-ant") and not ANTHROPIC_API_KEY:
        ANTHROPIC_API_KEY = key_found
        print(f"[SMD-CONFIG] Chave Anthropic carregada (provedor ativo: {DEFAULT_AI_PROVIDER})")
    elif key_found and not key_found.startswith("sk-ant") and not GEMINI_API_KEY:
        # Chave Gemini detectada — provider gratuito
        GEMINI_API_KEY = key_found
        if not os.environ.get("DEFAULT_AI_PROVIDER"):
            DEFAULT_AI_PROVIDER = "gemini"
        print(f"[SMD-CONFIG] Chave Gemini detectada — provedor ativo: {DEFAULT_AI_PROVIDER}")

# --- MAPEAMENTOS DE PROJETOS ---
PROJECTS_CONFIG_FILE = BASE_DIR / "smd_projects.json"
DE_PARA_PROJETOS = {}
TIMESHEET_PROJECT_MAP = {}
MANUAL_RESOURCE_FIXES = {}

if PROJECTS_CONFIG_FILE.exists():
    try:
        import json
        with open(PROJECTS_CONFIG_FILE, "r", encoding="utf-8") as f:
            pdata = json.load(f)
            DE_PARA_PROJETOS = pdata.get("DE_PARA_PROJETOS", {})
            TIMESHEET_PROJECT_MAP = pdata.get("TIMESHEET_PROJECT_MAP", {})
            MANUAL_RESOURCE_FIXES = pdata.get("MANUAL_RESOURCE_FIXES", {})
            print(f"[SMD-CONFIG] Mapeamentos de projetos carregados ({len(TIMESHEET_PROJECT_MAP)} itens)")
    except Exception as e:
        print(f"[SMD-CONFIG] Erro ao carregar {PROJECTS_CONFIG_FILE.name}: {e}")

# Arquivos de Suporte
RESOURCE_LEVEL_FILE = BASE_DIR / "DOcs" / "Resource Level.xlsx"

# Criar diretórios se não existirem
for d in [INPUT_DIR, RESULTS_DIR, BUILDS_DIR, DOWNLOADS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def get_env_var(name, default=None):
    return os.environ.get(name, default)

# Benchmarks de Mercado (ITIL / HDI)
MTTR_BENCHMARK_H = {
    "P1": 4,   # 4 horas (Crítico)
    "P2": 8,   # 8 horas (Alta)
    "P3": 24,  # 1 dia (Média)
    "P4": 48   # 2 dias (Baixa)
}
# --- CONFIGURAÇÕES DE CUSTO (FINOPS) ---
AI_COST_TABLE = {
    "gemini": {
        "input_1m": 0.10,   # USD por 1M tokens
        "output_1m": 0.40
    },
    "anthropic": {
        "input_1m": 0.25,
        "output_1m": 1.25
    },
    "ollama": {
        "input_1m": 0.0,
        "output_1m": 0.0
    }
}

