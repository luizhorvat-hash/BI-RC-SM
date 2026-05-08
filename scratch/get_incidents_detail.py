import json
import re

path = r'c:\Dashboard\data.js'

def extract():
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Busca por SMD_DATA_D
    match_d = re.search(r'var SMD_DATA_D\s*=\s*(\{.*?\});\s*var', content, re.DOTALL)
    if not match_d:
        print("Não encontrei SMD_DATA_D com regex simples")
        # Tenta pegar do início até a próxima variável
        start = content.find('=') + 1
        end = content.find('; var SMD_DATA_T')
        json_str = content[start:end].strip()
    else:
        json_str = match_d.group(1)

    try:
        data_d = json.loads(json_str)
        inc_april = data_d['monthly']['incident'].get('2026-04', {})
        
        # Agora buscar detalhes desses IDs em SMD_DATA_T para filtrar por PROJETO
        # (Lembrando que o usuário quer saber da Chanel, provavelmente)
        
        start_t = content.find('var SMD_DATA_T =') + len('var SMD_DATA_T =')
        end_t = content.find(';', start_t)
        json_t_str = content[start_t:end_t].strip()
        data_t = json.loads(json_t_str)
        
        fields = data_t['fields']
        rows = data_t['rows']
        
        prj_i = fields.index('prj')
        tk_i = fields.index('k')
        st_i = fields.index('st')
        su_i = fields.index('su')
        eid_i = fields.index('eid')

        all_tix = {r[tk_i]: r for r in rows}
        
        target_prj = "Chanel"
        
        opened_chanel = []
        for tid in inc_april.get('o_ids', []):
            t = all_tix.get(tid)
            if t and t[prj_i] == target_prj:
                opened_chanel.append({
                    "id": tid,
                    "ext_id": t[eid_i],
                    "status": t[st_i],
                    "summary": t[su_i]
                })

        closed_chanel = []
        for tid in inc_april.get('c_ids', []):
            t = all_tix.get(tid)
            if t and t[prj_i] == target_prj:
                closed_chanel.append({
                    "id": tid,
                    "ext_id": t[eid_i],
                    "status": t[st_i],
                    "summary": t[su_i]
                })

        result = {
            "project": target_prj,
            "period": "2026-04",
            "opened_count": len(opened_chanel),
            "closed_count": len(closed_chanel),
            "opened_tickets": opened_chanel,
            "closed_tickets": closed_chanel
        }
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    extract()
