import pandas as pd
import re
import xml.etree.ElementTree as ET
from pathlib import Path

def debug_mapping():
    csv_path = Path("input/tickets.csv")
    xls_path = Path("downloads/TimesheetsCMSMonthly.xls")
    
    # 1. Inspect CSV Tickets
    print("--- CSV TICKETS SAMPLE ---")
    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')
        if len(df.columns) < 5:
            df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig')
        
        tickets = df['Ticket'].dropna().astype(str).tolist()
        print(f"Total CSV Tickets: {len(tickets)}")
        print(f"Sample: {tickets[:10]}")
        # Check lengths
        lens = [len(t) for t in tickets]
        print(f"ID Lengths: min={min(lens)}, max={max(lens)}")
    except Exception as e:
        print(f"CSV Error: {e}")

    # 2. Inspect XLS Comments
    print("\n--- XLS COMMENTS SAMPLE ---")
    ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    comments_found = []
    try:
        context = ET.iterparse(str(xls_path), events=('end',))
        for event, elem in context:
            if elem.tag == '{urn:schemas-microsoft-com:office:spreadsheet}Row':
                cells = elem.findall('{urn:schemas-microsoft-com:office:spreadsheet}Cell', ns)
                current_idx = 1
                for cell in cells:
                    idx_attr = cell.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                    if idx_attr: current_idx = int(idx_attr)
                    
                    if current_idx == 20:
                        data_elem = cell.find('{urn:schemas-microsoft-com:office:spreadsheet}Data', ns)
                        if data_elem is not None and data_elem.text:
                            comments_found.append(data_elem.text)
                        
                    merge = int(cell.get('{urn:schemas-microsoft-com:office:spreadsheet}MergeAcross', 0))
                    current_idx += 1 + merge
                elem.clear()
        
        print(f"Total Comments Found: {len(comments_found)}")
        for i, c in enumerate(comments_found[:30]):
            print(f"  [{i}] {c}")
            
    except Exception as e:
        print(f"XLS Error: {e}")

if __name__ == "__main__":
    debug_mapping()
