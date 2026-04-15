import os
import re
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime

def audit_processing():
    tickets_csv = 'input/tickets.csv'
    timesheet_xls = 'downloads/TimesheetsCMSMonthly.xls'
    
    # 1. Load tickets for mapping
    df = pd.read_csv(tickets_csv, low_memory=False, sep=None, engine='python')
    tickets_map = {}

    for _, row in df.iterrows():
        tid = str(row.get('Ticket', ''))
        prj = str(row.get('Project Name', '')).strip().lower()
        if tid:
            tickets_map[tid] = prj

    matches = []
    
            # 2. Parse XLS
            ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
            context = ET.iterparse(timesheet_xls, events=('end',))
            for event, elem in context:
                if elem.tag == '{urn:schemas-microsoft-com:office:spreadsheet}Row':
                    cells = elem.findall('{urn:schemas-microsoft-com:office:spreadsheet}Cell', ns)
                    row_data = {}
                    idx = 1
                    for c in cells:
                        i = c.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                        if i: idx = int(i)
                        d = c.find('{urn:schemas-microsoft-com:office:spreadsheet}Data', ns)
                        if d is not None: row_data[idx] = d.text
                        m = int(c.get('{urn:schemas-microsoft-com:office:spreadsheet}MergeAcross', 0))
                        idx += 1 + m
                    
                    week_iso = row_data.get(7, "")
                    if '2026-03' in week_iso:
                        comm = row_data.get(20, "") # Comments
                        ids = re.findall(r'(\d{4,7})', str(comm))
                        
                        if ids:
                            for tid in ids:
                                if tid in tickets_map:
                                    matches.append(tickets_map[tid])
                        else:
                            prj_xls = row_data.get(2, "Internal")
                            matches.append(f"UNMATCHED_{prj_xls}")
                    
                    elem.clear()


    from collections import Counter
    print("\n--- Project Distribution of Ticket-ID Matches ---")
    counts = Counter(matches)
    for prj, count in counts.most_common(20):
        print(f"  {prj}: {count}")

if __name__ == "__main__":
    audit_processing()
