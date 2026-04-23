import re
import json

try:
    content = open('data.js', encoding='utf-8').read()
    # Tenta capturar o objeto completo de SMD_DATA_D
    m = re.search(r'var SMD_DATA_D\s*=\s*(\{.*?\});', content, re.DOTALL)
    if m:
        data = json.loads(m.group(1))
        ts = data.get('timesheet', {})
        print(f"Projetos no Timesheet: {list(ts.keys())}")
        if 'Farmacia Arrocha' in ts:
            print(f"Anos em Farmacia Arrocha: {list(ts['Farmacia Arrocha'].keys())}")
            for year in ts['Farmacia Arrocha']:
                print(f"  Meses em {year}: {list(ts['Farmacia Arrocha'][year].keys())}")
        else:
            print("Farmacia Arrocha não encontrado no objeto timesheet.")
    else:
        print("Variável SMD_DATA_D não encontrada.")
except Exception as e:
    print(f"Erro: {e}")
