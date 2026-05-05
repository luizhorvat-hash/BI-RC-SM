import json
from pathlib import Path

def list_projects_robust():
    data_js = Path("c:/Dashboard/data.js")
    if not data_js.exists(): 
        print("data.js não existe")
        return
        
    with open(data_js, "r", encoding="utf-8") as f:
        line1 = f.readline()
        if not line1.startswith("var SMD_DATA_D ="):
            print("Linha 1 não contém SMD_DATA_D")
            return
            
        json_str = line1[len("var SMD_DATA_D ="):].strip().rstrip(";")
        data_d = json.loads(json_str)
        
        rows = data_d.get("rows", [])
        if not rows:
            print("Chave 'rows' não encontrada ou vazia no SMD_DATA_D")
            # Tentar ver se rows está em SMD_DATA_T (outra variável)
            return

        projects = sorted(list(set([str(r[17]).strip() for r in rows])))
        print("\n=== PROJETOS NO DASHBOARD ===")
        for p in projects:
            if "FARMA" in p.upper():
                print(f"[!] {p}")
            else:
                print(p)

if __name__ == "__main__":
    list_projects_robust()
