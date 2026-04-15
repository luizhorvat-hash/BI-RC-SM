import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path

def diagnose():
    csv_path = Path("input/tickets.csv")
    xls_path = Path("downloads/TimesheetsCMSMonthly.xls")
    
    # 1. CSV Projects
    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')
        if len(df.columns) < 5:
            df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig')
        csv_projs = sorted(df['Project Name'].dropna().unique().tolist())
        print(f"--- CSV PROJECTS ({len(csv_projs)}) ---")
        for p in csv_projs: print(f"  [CSV] {p}")
    except Exception as e:
        print(f"CSV Error: {e}")
        return

    # 2. XLS Projects
    xls_projs = set()
    ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    try:
        context = ET.iterparse(str(xls_path), events=('end',))
        for event, elem in context:
            if elem.tag == '{urn:schemas-microsoft-com:office:spreadsheet}Row':
                # Try finding Index 2 explicitly or just the second cell
                # We use a more generic approach: list all cells and find the one at index 2
                cells = elem.findall('{urn:schemas-microsoft-com:office:spreadsheet}Cell', ns)
                current_idx = 1
                for cell in cells:
                    idx_attr = cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                    if idx_attr: current_idx = int(idx_attr)
                    
                    if current_idx == 2:
                        data_elem = cell.find('{urn:schemas-microsoft-com:office:spreadsheet}Data', ns)
                        if data_elem is not None and data_elem.text:
                            xls_projs.add(data_elem.text)
                        break
                    
                    merge = int(cell.get('{urn:schemas-microsoft-com:office:spreadsheet}MergeAcross', 0))
                    current_idx += 1 + merge
                elem.clear()
        
        xls_proj_list = sorted(list(xls_projs))
        print(f"\n--- XLS PROJECTS ({len(xls_proj_list)}) ---")
        for p in xls_proj_list: print(f"  [XLS] {p}")
        
    except Exception as e:
        print(f"XLS Error: {e}")

if __name__ == "__main__":
    diagnose()
