import json

path = r'c:\Dashboard\data.js'

def check_c_ids():
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        f.readline()
        line2 = f.readline()
    
    # IDs do D.monthly para Abril
    april_c_ids = [92198, 93410, 104332, 106897, 108136, 108137, 108520, 108697, 108717, 108773, 108775, 108778, 108944, 109183, 109716, 110980]
    
    chanel_ids = []
    
    for tid in april_c_ids:
        idx = line2.find(f"[{tid},")
        if idx == -1: idx = line2.find(f",{tid},")
        if idx != -1:
            end = line2.find("]", idx)
            row_str = line2[idx:end+1]
            if row_str.startswith(","): row_str = row_str[1:]
            if '"Chanel"' in row_str:
                chanel_ids.append(tid)
                
    print(f"IDs da Chanel no D.monthly de Abril: {chanel_ids}")
    print(f"Total: {len(chanel_ids)}")

if __name__ == "__main__":
    check_c_ids()
