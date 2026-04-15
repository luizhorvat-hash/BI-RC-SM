import xml.etree.ElementTree as ET
import re

def peek_xls_dates():
    try:
        content = open('downloads/TimesheetsCMSMonthly.xls', 'r', encoding='utf-8').read()
        # Look for DateTime patterns
        dates = re.findall(r'<Data ss:Type=\"DateTime\">(.*?)</Data>', content)
        print(f"Total timestamps found: {len(dates)}")
        print(f"First 20 unique timestamps: {sorted(list(set(dates)))[:20]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    peek_xls_dates()
