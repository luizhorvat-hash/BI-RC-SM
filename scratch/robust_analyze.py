import json
import re

path = r'c:\Dashboard\data.js'

def analyze(tid):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        f.readline()
        line2 = f.readline()
        
    start_pos = line2.find('"rows":[[')
    idx = line2.find(f"[{tid},", start_pos)
    if idx == -1: idx = line2.find(f",{tid},", start_pos)
    
    if idx != -1:
        # Pega um pedaço grande o suficiente para conter toda a row
        snippet = line2[idx:idx+1000]
        # Tenta encontrar o fim real da row (padrão ],[ ou ]])
        match = re.search(r'\[.*?\],\[', snippet)
        if not match: match = re.search(r'\[.*?\]\]', snippet)
        
        if match:
            row_str = match.group(0)
            if row_str.endswith(",["): row_str = row_str[:-2]
            if row_str.endswith("]]"): row_str = row_str[:-1]
            
            print(f"Row for {tid}: {row_str}")
            
            # Como o JSON pode estar quebrado devido a aspas não escapadas ou algo assim,
            # vamos tentar dar um parse mais "sujo"
            # Na verdade, se o JSON.loads falhou, é porque há aspas dentro da string sem escape.
            
            # Vamos usar uma regex para extrair os campos entre aspas ou números
            parts = re.findall(r'("(?:\\.|[^"\\])*"|[^,\[\]]+)', row_str)
            
            print(f"Parsed parts for {tid}:")
            fields = ['k', 'eid', 'pr', 'sv', 'st', 'op', 'res', 'cl', 'ap', 'en', 'su', 'upd', 'ass', 'sl', 'rc', 'rct', 'rs', 'prj', 'y_o', 'm_o', 'd_o', 'y_c', 'm_c', 'd_c', 'sev', 'pid', 'md', 'co', 'ca', 'svl']
            for i, p in enumerate(parts):
                val = p.strip('"')
                if i < len(fields):
                    print(f"  {i}: {fields[i]} = {val}")

if __name__ == "__main__":
    import sys
    tid = sys.argv[1] if len(sys.argv) > 1 else 110633
    analyze(tid)
