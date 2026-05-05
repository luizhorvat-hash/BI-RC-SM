import time
import subprocess
import sys

def benchmark():
    print("Iniciando benchmark do smd_build.py (sem agentes)...")
    start = time.time()
    
    # Rodar com --no-agents para focar no ETL
    result = subprocess.run([sys.executable, "smd_build.py", "--no-agents"], 
                            capture_output=True, text=True)
    
    end = time.time()
    duration = end - start
    
    if result.returncode == 0:
        print(f"Build concluído com sucesso em {duration:.2f} segundos.")
    else:
        print(f"Build falhou com código {result.returncode}.")
        print(result.stderr)
    
    return duration

if __name__ == "__main__":
    benchmark()
