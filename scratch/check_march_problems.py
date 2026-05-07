
import json
import re

def main():
    with open(r'c:\Dashboard\data.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    start = content.find('{')
    end = content.rfind('}')
    if start == -1 or end == -1:
        print("Could not find JSON object in data.js")
        return
    
    json_str = content[start:end+1]
    data = json.loads(json_str)
    
    rows = data.get('rows', {})
    idx = data.get('idx', {})
    
    # Indices
    k_idx = idx.get('k')
    prj_idx = idx.get('prj')
    sev_idx = idx.get('sev')
    y_c_idx = idx.get('y_c')
    m_c_idx = idx.get('m_c')
    
    chanel_problems_closed_march = []
    
    for tid, row in rows.items():
        if row[prj_idx] == 'Chanel' and row[sev_idx] == 'problem':
            if row[y_c_idx] == 2026 and row[m_c_idx] == 3:
                chanel_problems_closed_march.append(tid)
    
    print(f"Total Chanel Problems closed in March 2026: {len(chanel_problems_closed_march)}")
    # print(chanel_problems_closed_march)

if __name__ == "__main__":
    main()
