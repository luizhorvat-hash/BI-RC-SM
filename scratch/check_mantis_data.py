import json
from pathlib import Path

data_js = Path("c:/Dashboard/data.js")
if data_js.exists():
    content = data_js.read_text(encoding="utf-8")
    if "var SMD_DATA_T =" in content:
        start = content.find("var SMD_DATA_T =") + len("var SMD_DATA_T =")
        end = content.find(";", start)
        t_json = content[start:end].strip()
        t_data = json.loads(t_json)
        rows = t_data.get("rows", [])
        
        counts = {}
        for r in rows:
            # Index 18 is y_o, 19 is m_o
            y, m = r[18], r[19]
            prj = r[17]
            key = (prj, y, m)
            counts[key] = counts.get(key, 0) + 1
            
        print("Mantis Row Counts (Prj, Year, Month):")
        for k in sorted(counts.keys()):
            print(f"{k}: {counts[k]} tickets")
