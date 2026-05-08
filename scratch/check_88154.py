import json
import re

def check_problem():
    try:
        with open('c:/Dashboard/data.js', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extrair SMD_DATA_D
        match = re.search(r'var SMD_DATA_D = (\{.*?\});', content, re.DOTALL)
        if not match:
            print("SMD_DATA_D não encontrado")
            return
            
        data = json.loads(match.group(1))
        problems = data.get('problems', {})
        
        # Extrair SMD_TIMESHEET
        ts_match = re.search(r'var SMD_TIMESHEET = (\{.*?\});', content, re.DOTALL)
        ts_data = json.loads(ts_match.group(1)) if ts_match else {}
        
        target = "88154"
        if target in problems:
            p = problems[target]
            print(f"Problem #{target} encontrado:")
            print(f"  App: {p.get('app')}")
            print(f"  Status: {p.get('status')}")
            print(f"  Is Open: {p.get('is_open')}")
            print(f"  Self MD (Mantis): {p.get('self_md')}")
            
            # Checar esforço no Timesheet para o ticket do problema
            print(f"  Timesheet Effort (Self):")
            found_ts = False
            for prj in ts_data:
                for y in ts_data[prj]:
                    for m in ts_data[prj][y]:
                        if 'tix' in ts_data[prj][y][m] and target in ts_data[prj][y][m]['tix']:
                            print(f"    - {prj} ({y}-{m}): {ts_data[prj][y][m]['tix'][target]} MDs")
                            found_ts = True
            if not found_ts: print("    - Nenhum lançamento encontrado no Timesheet para o problema.")

            print(f"  Incidents linked: {len(p.get('incidents', []))}")
            for inc in p.get('incidents', []):
                itk = inc['ticket']
                print(f"    - Inc #{itk} (Mantis MD: {inc['md']})")
                # Checar TS para o incidente
                for prj in ts_data:
                    for y in ts_data[prj]:
                        for m in ts_data[prj][y]:
                            if 'tix' in ts_data[prj][y][m] and itk in ts_data[prj][y][m]['tix']:
                                print(f"      [TS] {prj} ({y}-{m}): {ts_data[prj][y][m]['tix'][itk]} MDs")
        else:
            print(f"Problem #{target} NÃO encontrado no index. Chaves disponíveis (amostra): {list(problems.keys())[:10]}")
            
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    check_problem()
