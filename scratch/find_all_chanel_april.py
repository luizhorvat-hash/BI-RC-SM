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
    # As rows são separadas por ],[
    # No entanto, strings podem conter ],[ (improvável mas possível)
    # Vamos usar uma abordagem mais segura: split por "],["
    rows_list = rows_str.split("],[")
    
    chanel_april_opened = []
    chanel_april_closed = []
    
    # Corrigir a primeira e última row (remover colchetes extras se houver)
    # Na verdade, o split já lidou com o miolo.
    
    for r_str in rows_list:
        # Reconstruir o JSON da row
        # Como o split removeu ],[, precisamos garantir que a string seja um array válido
        if not r_str.startswith("["): r_str = "[" + r_str
        if not r_str.endswith("]"): r_str = r_str + "]"
        
        if '"Chanel"' in r_str:
            try:
                row = json.loads(r_str)
                # indices: k(0), prj(13), y_o(15), m_o(16), y_c(18), m_c(19)
                
                # Abertos em Abril 2026
                if row[15] == 2026 and row[16] == 4:
                    chanel_april_opened.append({
                        "id": row[0],
                        "ext_id": row[1],
                        "status": row[4],
                        "summary": row[9],
                        "sv": row[3]
                    })
                
                # Fechados em Abril 2026
                if row[18] == 2026 and row[19] == 4:
                    chanel_april_closed.append({
                        "id": row[0],
                        "ext_id": row[1],
                        "status": row[4],
                        "summary": row[9],
                        "sv": row[3]
                    })
            except:
                pass

    print(json.dumps({
        "opened": chanel_april_opened,
        "closed": chanel_april_closed
    }, indent=2))

if __name__ == "__main__":
    search_all_chanel()
