import xml.etree.ElementTree as ET
import re

def find_comment_col():
    path = 'downloads/TimesheetsCMSMonthly.xls'
    ns = {'ss': 'urn:schemas-microsoft-com:office:spreadsheet'}
    
    try:
        context = ET.iterparse(path, events=('end',))
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
                    idx += 1 + int(c.get('{urn:schemas-microsoft-com:office:spreadsheet}MergeAcross', 0))
                
                # Search for a 7-digit ID (Mantis pattern) in any column
                for col_idx, val in row_data.items():
                    if val and re.search(r'\d{7}', str(val)):
                        print(f"Potential ID Found in Col {col_idx}: {val}")
                        # If we find it, print the whole row for context
                        print(f"Full row context: {row_data}")
                        return
                        
                elem.clear()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    find_comment_col()
