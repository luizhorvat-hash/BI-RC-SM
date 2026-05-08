import json
import re

path = r'c:\Dashboard\data.js'

target_ids = [
    111005, 111025, 111035, 111050, 111070, 111105, 111126, 111199, 111269, 111357,
    111360, 111361, 111375, 111376, 111379, 111386, 111401, 111408, 111439, 111511,
    111575, 111638, 111679, 111680, 111699, 111715, 111759, 111785, 111791, 111956,
    111982, 111985, 112019, 112068, 112109, 112185, 112287, 112306, 112366, 112410,
    112411, 112412, 112413, 112414, 110198, 110200, 110545, 110603, 110610, 110629,
    110633, 110693, 110748, 110751, 110810, 110862, 110884, 110955, 110956, 110957,
    110958, 110976, 110978, 110986, 110995
]

def find_tickets():
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    # Extrair os fields de SMD_DATA_T
    start_t = content.find('var SMD_DATA_T =')
    if start_t == -1:
        print("SMD_DATA_T não encontrado")
        return
    
    fields_match = re.search(r'"fields":\s*(\[.*?\])', content[start_t:])
    if not fields_match:
        print("Fields não encontrados")
        return
    
    fields = json.loads(fields_match.group(1))
    prj_i = fields.index('prj')
    tk_i = fields.index('k')
    st_i = fields.index('st')
    su_i = fields.index('su')
    eid_i = fields.index('eid')

    # Regex para capturar cada linha da array "rows"
    # rows é [[...],[...],...]
    rows_start = content.find('"rows":', start_t)
    # A partir daqui, as linhas são separadas por ],[
    
    chanel_tickets = {}
    
    # Busca por ID específico: [ID,
    for tid in target_ids:
        # Padrão: [TID,"EXT_ID","PRI","SV","ST","OP","RES","AP","EN","SUMMARY",...
        # Como o ID é o primeiro campo (k), ele começa com [TID,
        pattern = r'\[' + str(tid) + r',.*?\]'
        match = re.search(pattern, content[rows_start:])
        if match:
            try:
                row_str = match.group(0)
                # Parse robusto da linha
                row = json.loads(row_str)
                if row[prj_i] == "Chanel":
                    chanel_tickets[tid] = {
                        "id": tid,
                        "ext_id": row[eid_i],
                        "status": row[st_i],
                        "summary": row[su_i],
                        "project": row[prj_i]
                    }
            except:
                pass

    # Organizar por Abertos e Fechados
    o_ids = [111005, 111025, 111035, 111050, 111070, 111105, 111126, 111199, 111269, 111357, 111360, 111361, 111375, 111376, 111379, 111386, 111401, 111408, 111439, 111511, 111575, 111638, 111679, 111680, 111699, 111715, 111759, 111785, 111791, 111956, 111982, 111985, 112019, 112068, 112109, 112185, 112287, 112306, 112366, 112410, 112411, 112412, 112413, 112414]
    c_ids = [110198, 110200, 110545, 110603, 110610, 110629, 110633, 110693, 110748, 110751, 110810, 110862, 110884, 110955, 110956, 110957, 110958, 110976, 110978, 110986, 110995, 111005, 111025, 111035, 111050, 111070, 111105, 111126, 111199, 111357, 111361, 111375, 111376, 111379, 111386, 111401, 111408, 111439, 111511, 111638, 111679, 111680, 111699, 111785, 111791, 112410, 112411, 112412, 112413, 112414]

    opened_chanel = [chanel_tickets[tid] for tid in o_ids if tid in chanel_tickets]
    closed_chanel = [chanel_tickets[tid] for tid in c_ids if tid in chanel_tickets]

    print(json.dumps({
        "project": "Chanel",
        "month": "Abril 2026",
        "opened_incidents": opened_chanel,
        "closed_incidents": closed_chanel
    }, indent=2))

if __name__ == "__main__":
    find_tickets()
