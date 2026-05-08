import json
import os

# Caminho para o data.js
data_js_path = r'c:\Dashboard\data.js'

def inspect_data():
    if not os.path.exists(data_js_path):
        print("data.js não encontrado")
        return

    with open(data_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extrair SMD_DATA_T
    # var SMD_DATA_T = {...};
    start_marker = "var SMD_DATA_T ="
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("SMD_DATA_T não encontrado")
        return
    
    start_idx += len(start_marker)
    end_idx = content.find(";", start_idx)
    json_str = content[start_idx:end_idx].strip()
    
    data_t = json.loads(json_str)
    fields = data_t['fields']
    rows = data_t['rows']

    prj_i = fields.index('prj')
    y_o_i = fields.index('y_o')
    m_o_i = fields.index('m_o')
    y_c_i = fields.index('y_c')
    m_c_i = fields.index('m_c')
    tk_i = fields.index('k')
    sv_i = fields.index('sv')

    target_prj = "Chanel"
    target_year = 2026
    target_month = 4

    opened_count = 0
    closed_count = 0
    opened_ids = []
    closed_ids = []

    for r in rows:
        if r[prj_i] != target_prj:
            continue
        
        # Abertos em Abril 2026
        if r[y_o_i] == target_year and r[m_o_i] == target_month:
            opened_count += 1
            opened_ids.append(r[tk_i])
        
        # Fechados em Abril 2026
        if r[y_c_i] == target_year and r[m_c_i] == target_month:
            closed_count += 1
            closed_ids.append(r[tk_i])

    print(f"Projeto: {target_prj} | Período: {target_month}/{target_year}")
    print(f"Abertos (Data): {opened_count}")
    print(f"IDs Abertos: {opened_ids}")
    print(f"Fechados (Data): {closed_count}")
    print(f"IDs Fechados: {closed_ids}")

if __name__ == "__main__":
    inspect_data()
