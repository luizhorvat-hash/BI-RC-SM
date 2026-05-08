import json
import os

path = r'c:\Dashboard\data.js'

def check():
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
    
    print(f"Total size: {len(content)}")
    print(f"Chanel count: {content.count('\"Chanel\"')}")
    
    # Verificando os IDs de Abril
    o_ids = [111005, 111025, 111035, 111050, 111070, 111105, 111126, 111199, 111269, 111357, 111360, 111361, 111375, 111376, 111379, 111386, 111401, 111408, 111439, 111511, 111575, 111638, 111679, 111680, 111699, 111715, 111759, 111785, 111791, 111956, 111982, 111985, 112019, 112068, 112109, 112185, 112287, 112306, 112366, 112410, 112411, 112412, 112413, 112414]
    
    found_any = False
    for tid in o_ids:
        if str(tid) in content:
            # Pega um pedaço ao redor
            idx = content.find(str(tid))
            print(f"ID {tid} found at {idx}: {content[idx:idx+200]}")
            found_any = True
            break
    if not found_any:
        print("Nenhum ID de Abril encontrado no arquivo!")

if __name__ == "__main__":
    check()
