import json

path = r'c:\Dashboard\data.js'

def search_all_chanel():
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        f.readline() # Skip SMD_DATA_D
        line2 = f.readline()
    
    # Encontrar "rows":[[
    start_pos = line2.find('"rows":[[') + len('"rows":[[')
    end_pos = line2.find(']],"idx"')
    
    rows_str = line2[start_pos:end_pos]
    rows_list = rows_str.split("],[")
    
    chanel_april_opened = []
    chanel_april_closed = []
    
    # Indices corrigidos:
    # k(0), eid(1), sv(3), st(4), op(5), res(6), su(10), prj(17), y_o(18), m_o(19), y_c(21), m_c(22)
    
    for r_str in rows_list:
        if not r_str.startswith("["): r_str = "[" + r_str
        if not r_str.endswith("]"): r_str = r_str + "]"
        
        if '"Chanel"' in r_str:
            try:
                row = json.loads(r_str)
                # Garantir que é um incidente (sv)
                severity = row[3]
                project = row[17]
                
                if project == "Chanel" and severity == "incident":
                    # Abertos em Abril 2026 (y_o=18, m_o=19)
                    if row[18] == 2026 and row[19] == 4:
                        chanel_april_opened.append({
                            "id": row[0],
                            "status": row[4],
                            "opened": row[5],
                            "summary": row[10]
                        })
                    
                    # Fechados em Abril 2026 (y_c=21, m_c=22)
                    if row[21] == 2026 and row[22] == 4:
                        chanel_april_closed.append({
                            "id": row[0],
                            "status": row[4],
                            "closed": row[6],
                            "summary": row[10]
                        })
            except:
                pass

    print(json.dumps({
        "project": "Chanel",
        "month": "Abril 2026",
        "opened_incidents_count": len(chanel_april_opened),
        "closed_incidents_count": len(chanel_april_closed),
        "opened_incidents": chanel_april_opened,
        "closed_incidents": chanel_april_closed
    }, indent=2))

if __name__ == "__main__":
    search_all_chanel()
