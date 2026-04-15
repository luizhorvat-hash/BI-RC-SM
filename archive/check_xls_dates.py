import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime

def check_xls_dates():
    ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    dates = []
    
    try:
        context = ET.iterparse('downloads/TimesheetsCMSMonthly.xls', events=('end',))
        for event, elem in context:
            if elem.tag == '{urn:schemas-microsoft-com:office:spreadsheet}Row':
                cells = elem.findall('{urn:schemas-microsoft-com:office:spreadsheet}Cell', ns)
                row_data = {}
                idx = 1
                for c in cells:
                    i = c.get('{urn:schemas-microsoft-com:office:spreadsheet}Index')
                    if i: idx = int(i)
                    d = c.find('{urn:schemas-microsoft-com:office:spreadsheet}Data', ns)
                    if d is not None:
                        row_data[idx] = d.text
                    m = int(c.get('{urn:schemas-microsoft-com:office:spreadsheet}MergeAcross', 0))
                    idx += 1 + m
                
                # Week index is 7
                week_iso = row_data.get(7)
                if week_iso and 'T' in week_iso:
                    try:
                        dt = datetime.fromisoformat(week_iso[:10])
                        dates.append(f"{dt.year}-{dt.month:02d}")
                    except:
                        pass
                elem.clear()
        
        counts = Counter(dates)
        print("\n--- XLS Date Distribution (Year-Month) ---")
        for ym, count in sorted(counts.items()):
            print(f"  {ym}: {count} rows")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_xls_dates()
