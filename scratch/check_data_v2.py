
with open(r'c:\Dashboard\data.js', 'r', encoding='utf-8') as f:
    c = f.read()
    print(f"Chanel: {'Chanel' in c}")
    print(f"CHANEL: {'CHANEL' in c}")
    print(f"Farmatodo: {'Farmatodo' in c}")
    
    # Let's count Problems in March 2026 for Chanel
    # Pattern: [tid, ..., "problem", ..., "Chanel", 2026, 3, ...]
    # We need to be more precise.
    # Looking at the 'rows' structure:
    # 2818: tid: r[i.k], prj: r[i.prj], sev: r[i.sev], st: r[i.st],
    # 2819: y_o: r[i.y_o], m_o: r[i.m_o], y_c: r[i.y_c], m_c: r[i.m_c],
    
    import json
    
    # Find SMD_DATA_T
    start = c.find('var SMD_DATA_T =')
    if start == -1: start = c.find('SMD_DATA_T =')
    
    if start != -1:
        start = c.find('{', start)
        # We need the end of THIS object. 
        # Since it's big, we'll look for the next variable or end of file.
        next_var = c.find('var ', start + 1)
        if next_var == -1: end = c.rfind('}')
        else: end = c.rfind('}', start, next_var) + 1
        
        json_part = c[start:end]
        try:
            data = json.loads(json_part)
            idx = data['idx']
            rows = data['rows']
            
            prj_idx = idx['prj']
            sev_idx = idx['sev']
            y_c_idx = idx['y_c']
            m_c_idx = idx['m_c']
            
            count = 0
            ids = []
            for tid, r in rows.items():
                if r[prj_idx] == 'Chanel' and r[sev_idx] == 'problem':
                    if r[y_c_idx] == 2026 and r[m_c_idx] == 3:
                        count += 1
                        ids.append(tid)
            print(f"Indices: {idx}")
            print(f"Chanel Problems Closed March 2026: {count}")
            if count > 0:
                print(f"Sample IDs: {ids[:10]}")
        except Exception as e:
            print(f"Error parsing SMD_DATA_T: {e}")
    else:
        print("SMD_DATA_T not found")


