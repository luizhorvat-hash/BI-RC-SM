import json
import os

# Caminho para o data.js
data_js_path = r'c:\Dashboard\data.js'

def get_chanel_april_incidents():
    if not os.path.exists(data_js_path):
        print("data.js não encontrado")
        return

    with open(data_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extrair SMD_DATA_T
    start_marker = "var SMD_DATA_T ="
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("SMD_DATA_T não encontrado")
        return
    
    start_idx += len(start_marker)
    end_idx = content.find(";", start_idx)
    json_str = content[start_idx:end_idx].strip()
    
    # Tentativa de parse robusto (removendo possíveis problemas de caracteres)
    try:
        data_t = json.loads(json_str)
    except Exception as e:
        print(f"Erro ao parsear JSON: {e}")
        # Tenta pegar apenas uma parte ou usar regex se for muito grande
        return

    fields = data_t['fields']
    rows = data_t['rows']

    prj_i = fields.index('prj')
    y_o_i = fields.index('y_o')
    m_o_i = fields.index('m_o')
    y_c_i = fields.index('y_c')
    m_c_i = fields.index('m_c')
    tk_i = fields.index('k')
    sv_i = fields.index('sv')
    st_i = fields.index('st')
    su_i = fields.index('su')

    target_prj = "Chanel"
    target_year = 2026
    target_month = 4

    opened_incidents = []
    closed_incidents = []

    for r in rows:
        if r[prj_i] != target_prj:
            continue
        
        if r[sv_i] != 'incident':
            continue

        # Abertos em Abril 2026
        if r[y_o_i] == target_year and r[m_o_i] == target_month:
            opened_incidents.append({
                "id": r[tk_i],
                "status": r[st_i],
                "summary": r[su_i]
            })
        
        # Fechados em Abril 2026
        if r[y_c_i] == target_year and r[m_c_i] == target_month:
            closed_incidents.append({
                "id": r[tk_i],
                "status": r[st_i],
                "summary": r[su_i]
            })

    print(json.dumps({
        "opened": opened_incidents,
        "closed": closed_incidents
    }, indent=2))

if __name__ == "__main__":
    get_chanel_april_incidents()
