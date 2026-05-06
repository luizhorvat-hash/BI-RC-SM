import os
from pathlib import Path
import json

data_js = Path("c:/Dashboard/data.js")
if data_js.exists():
    with open(data_js, "r", encoding="utf-8") as f:
        content = f.read()
        
        # Extract SMD_DATA_T
        start = content.find("var SMD_DATA_T =") + len("var SMD_DATA_T =")
        end = content.find(";", start)
        t_data = json.loads(content[start:end].strip())
        rows = t_data.get("rows", [])
        
        # Check for Chanel tickets in 2026
        # Index 17: prj, 21: y_c, 22: m_c
        for r in rows:
            if "Chanel" in str(r[17]) and r[21] == 2026:
                print(f"Chanel Ticket {r[0]} | Closed: {r[21]}-{r[22]} | MDs: {r[26]}")
