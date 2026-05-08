import json

path = r'c:\Dashboard\data.js'

def analyze_problems():
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        f.readline()
        line2 = f.readline()
    
    start_pos = line2.find('"rows":[[') + len('"rows":[[')
    end_pos = line2.find(']],"idx"')
    rows_list = line2[start_pos:end_pos].split("],[")
    
    # Indices: k(0), sv(3), st(4), op(5), res(6), su(10), prj(17), y_o(18), m_o(19), y_c(21), m_c(22)
    
    problems_april_opened = []
    problems_april_closed = []
    
    for r_str in rows_list:
        if not r_str.startswith("["): r_str = "[" + r_str
        if not r_str.endswith("]"): r_str = r_str + "]"
        
        if '"Chanel"' in r_str and '"problem"' in r_str:
            try:
                row = json.loads(r_str)
                if row[17] == "Chanel" and row[3] == "problem":
                    # Abertos em Abril
                    if row[18] == 2026 and row[19] == 4:
                        problems_april_opened.append({"id": row[0], "res": row[6], "st": row[4]})
                    
                    # Fechados/Resolvidos (Pela lógica do Dashboard: Status closed/resolved + ResDate em Abril)
                    res_date = row[6]
                    yc, mc = row[21], row[22]
                    if res_date and len(res_date) >= 7:
                        yc = int(res_date[:4])
                        mc = int(res_date[5:7])
                    
                    is_closed_status = row[4] in ["closed", "resolved"]
                    
                    if yc == 2026 and mc == 4 and is_closed_status:
                        problems_april_closed.append({"id": row[0], "res": row[6], "st": row[4]})
            except: pass

    print(json.dumps({
        "opened_count": len(problems_april_opened),
        "closed_count": len(problems_april_closed),
        "opened": problems_april_opened,
        "closed": problems_april_closed
    }, indent=2))

if __name__ == "__main__":
    analyze_problems()
