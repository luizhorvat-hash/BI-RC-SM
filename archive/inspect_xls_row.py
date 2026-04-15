import xml.etree.ElementTree as ET

def inspect_row():
    path = 'downloads/TimesheetsCMSMonthly.xls'
    ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    
    try:
        context = ET.iterparse(path, events=('end',))
        row_count = 0
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
                        row_data[idx] = (d.text, d.get('{urn:schemas-microsoft-com:office:spreadsheet}Type'))
                    m = int(c.get('{urn:schemas-microsoft-com:office:spreadsheet}MergeAcross', 0))
                    idx += 1 + m
                
                # Check if it's a data row (has hours in index 22-ish)
                if 22 in row_data:
                    print(f"\n--- Data Row Found (Row index approx {row_count}) ---")
                    for k in sorted(row_data.keys()):
                        print(f"  Col {k}: {row_data[k]}")
                    
                    # Stop after 2 data rows
                    if row_count > 50: # wait for a few rows
                         break
                
                row_count += 1
                elem.clear()
                if row_count > 500: break # don't loop forever
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_row()
