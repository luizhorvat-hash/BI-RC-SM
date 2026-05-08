import json
import re

path = r'c:\Dashboard\data.js'

def extract_chanel_april():
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # IDs que sabemos ser de Abril/2026 (Total de Incidentes)
    o_ids = [111005, 111025, 111035, 111050, 111070, 111105, 111126, 111199, 111269, 111357, 111360, 111361, 111375, 111376, 111379, 111386, 111401, 111408, 111439, 111511, 111575, 111638, 111679, 111680, 111699, 111715, 111759, 111785, 111791, 111956, 111982, 111985, 112019, 112068, 112109, 112185, 112287, 112306, 112366, 112410, 112411, 112412, 112413, 112414]
    c_ids = [110198, 110200, 110545, 110603, 110610, 110629, 110633, 110693, 110748, 110751, 110810, 110862, 110884, 110955, 110956, 110957, 110958, 110976, 110978, 110986, 110995, 111005, 111025, 111035, 111050, 111070, 111105, 111126, 111199, 111357, 111361, 111375, 111376, 111379, 111386, 111401, 111408, 111439, 111511, 111638, 111679, 111680, 111699, 111785, 111791, 112410, 112411, 112412, 112413, 112414]

    # Localizar o início das rows
    rows_pos = content.find('"rows":[[')
    if rows_pos == -1:
        print("Rows não encontradas")
        return
    
    rows_part = content[rows_pos:]
    
    # Campos (ordem baseada na análise prévia)
    # ["k","eid","pr","sv","st","op","res","ap","en","su","upd","ass","sl","prj",...]
    # prj_i = 13
    # k_i = 0
    
    def get_ticket_info(tid):
        # Busca por [TID,
        search_str = f"[{tid},"
        idx = rows_part.find(search_str)
        if idx == -1: return None
        
        # Encontrar o fim do array ]
        end_idx = rows_part.find("]", idx)
        row_str = rows_part[idx : end_idx+1]
        
        try:
            row = json.loads(row_str)
            if row[13] == "Chanel":
                return {
                    "id": row[0],
                    "ext_id": row[1],
                    "status": row[4],
                    "summary": row[9]
                }
        except:
            pass
        return None

    opened_chanel = []
    for tid in o_ids:
        info = get_ticket_info(tid)
        if info: opened_chanel.append(info)

    closed_chanel = []
    for tid in c_ids:
        info = get_ticket_info(tid)
        if info: closed_chanel.append(info)

    print(json.dumps({
        "opened": opened_chanel,
        "closed": closed_chanel
    }, indent=2))

if __name__ == "__main__":
    extract_chanel_april()
