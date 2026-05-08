import os

path = r'c:\Dashboard\data.js'

def find_row():
    # IDs de Abril
    o_ids = [111005, 111025, 111035, 111050, 111070, 111105, 111126, 111199, 111269, 111357, 111360, 111361, 111375, 111376, 111379, 111386, 111401, 111408, 111439, 111511, 111575, 111638, 111679, 111680, 111699, 111715, 111759, 111785, 111791, 111956, 111982, 111985, 112019, 112068, 112109, 112185, 112287, 112306, 112366, 112410, 112411, 112412, 112413, 112414]
    
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        # Pular o SMD_DATA_D (linha 1)
        line1 = f.readline()
        # SMD_DATA_T é a linha 2
        line2 = f.readline()
    
    print(f"Line 2 length: {len(line2)}")
    
    # Vamos buscar os IDs um por um
    chanel_tix = []
    for tid in o_ids:
        tid_str = str(tid)
        # No SMD_DATA_T, as rows são [[...],[...]]
        # Cada row começa com [ID,
        # Mas pode ser a primeira da lista: [[ID, ou não: ,[ID,
        idx = line2.find(f"[{tid_str},")
        if idx == -1:
            idx = line2.find(f",{tid_str},") # Fallback
            
        if idx != -1:
            # Encontrar o fim da row
            end_idx = line2.find("]", idx)
            row_snippet = line2[idx:end_idx+1]
            if '"Chanel"' in row_snippet:
                chanel_tix.append(row_snippet)
    
    print(f"Found {len(chanel_tix)} Chanel tickets in April opened list.")
    for t in chanel_tix:
        print(t)

if __name__ == "__main__":
    find_row()
