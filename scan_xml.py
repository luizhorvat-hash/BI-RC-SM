import xml.etree.ElementTree as ET
import sys

path = 'input/TimesheetsCMSMonthly.xls'
ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
tag_row = '{urn:schemas-microsoft-com:office:spreadsheet}Row'
tag_cell = '{urn:schemas-microsoft-com:office:spreadsheet}Cell'
tag_data = '{urn:schemas-microsoft-com:office:spreadsheet}Data'
tag_index = '{urn:schemas-microsoft-com:office:spreadsheet}Index'

print(f"Escaneando {path}...")
try:
    context = ET.iterparse(path, events=('end',))
    count = 0
    for event, elem in context:
        if elem.tag == tag_row:
            cells = elem.findall(tag_cell)
            row_data = {}
            cur_idx = 1
            for cell in cells:
                idx_attr = cell.get(tag_index)
                if idx_attr: cur_idx = int(idx_attr)
                d = cell.find(tag_data)
                row_data[cur_idx] = d.text if d is not None else ""
                cur_idx += 1
            
            # Procura por uma linha que pareça ter dados de projeto
            row_str = str(row_data)
            if 'Farmatodo' in row_str or 'Chanel' in row_str or 'Arrocha' in row_str:
                print(f"\nLinha de dados encontrada (Linha {count}):")
                for idx, val in sorted(row_data.items()):
                    if val:
                        print(f"  Coluna {idx}: {val}")
                break
            
            count += 1
            if count > 2000: # Limite para não demorar
                print("\nNenhuma linha de dados encontrada nos primeiros 2000 registros.")
                break
            elem.clear()
except Exception as e:
    print(f"Erro: {e}")
