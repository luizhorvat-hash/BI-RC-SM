import json
from pathlib import Path

def debug_data_structure():
    data_js = Path("c:/Dashboard/data.js")
    with open(data_js, "r", encoding="utf-8") as f:
        f.readline()
        line2 = f.readline()
    
    json_str = line2[len("var SMD_DATA_T ="):].strip().rstrip(";")
    rows = json.loads(json_str)
    
    print(f"Total rows: {len(rows)}")
    if len(rows) > 0:
        first = rows[0]
        print(f"Type of first row: {type(first)}")
        print(f"Content of first row: {first}")
        if isinstance(first, list):
            print(f"Length of first row: {len(first)}")

if __name__ == "__main__":
    debug_data_structure()
