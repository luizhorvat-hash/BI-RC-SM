import json
import re

def audit():
    try:
        with open('data.js', 'r', encoding='utf-8') as f:
            content = f.read()
            
        start_tag = 'var SMD_DATA_D ='
        if start_tag not in content:
            start_tag = 'var SMD_DATA_D='
        
        end_tag = ';var SMD_DATA_T'
        if end_tag not in content:
            end_tag = '; var SMD_DATA_T'

        
        start = content.find(start_tag) + len(start_tag)
        end = content.find(end_tag)
        
        if start < 20 or end < start:
            print("Could not find SMD_DATA_D in data.js")
            return
            
        d = json.loads(content[start:end])
        ts = d.get('timesheet', {})
        print(f"Total entries in timesheet: {len(ts)}")
        
        # Audit years and months
        dist = {}
        for k, v in ts.items():
            y = v.get('y')
            m = v.get('m')
            key = f"{y}-{m}"
            dist[key] = dist.get(key, 0) + 1
            
        print("\n--- Year-Month Distribution ---")
        for k in sorted(dist.keys()):
            print(f"  {k}: {dist[k]} entries")

        # Audit projects for 2026-4
        if "2026-4" in dist:
             print("\n--- Projects in 2026-4 ---")
             prjs = {}
             for k, v in ts.items():
                 if f"{v.get('y')}-{v.get('m')}" == "2026-4":
                     p = v.get('prj')
                     prjs[p] = prjs.get(p, 0) + 1
             for p, c in sorted(prjs.items(), key=lambda x: x[1], reverse=True):
                 print(f"  {p}: {c}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    audit()
