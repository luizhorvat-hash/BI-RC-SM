import json

path = r'c:\Dashboard\data.js'

def find_specific_row(tid):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        f.readline()
        line2 = f.readline()
        
    start_pos = line2.find('"rows":[[')
    idx = line2.find(f"[{tid},", start_pos)
    if idx == -1:
        idx = line2.find(f",{tid},", start_pos)
        
    if idx != -1:
        end_idx = line2.find("]", idx)
        row_str = line2[idx:end_idx+1]
        if row_str.startswith(","): row_str = row_str[1:]
        print(f"Row for {tid}: {row_str}")
        try:
            row = json.loads(row_str)
            print(f"Fields mapping for {tid}:")
            fields = ['k', 'eid', 'pr', 'sv', 'st', 'op', 'res', 'cl', 'ap', 'en', 'su', 'upd', 'ass', 'sl', 'rc', 'rct', 'rs', 'prj', 'y_o', 'm_o', 'd_o', 'y_c', 'm_c', 'd_c', 'sev', 'pid', 'md', 'co', 'ca', 'svl']
            for i, f_name in enumerate(fields):
                if i < len(row):
                    print(f"  {i}: {f_name} = {row[i]}")
        except Exception as e:
            print(f"Error parsing: {e}")

if __name__ == "__main__":
    find_specific_row(110633)
