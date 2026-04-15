import json
import re

def get_months():
    with open('data.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract timesheet part using regex
    match = re.search(r'"timesheet":(\{.*?\})', content)
    if not match:
        print("Timesheet section not found")
        return
    
    ts_str = match.group(1)
    # Manually parsing the first few items to see the dates
    # Since it's a huge JSON, we can't load it all easily if it's broken
    # But let's try to find patterns like "y":2026,"m":4
    
    from collections import Counter
    ym_pairs = re.findall(r'"y":(\d+),"m":(\d+)', ts_str)
    counts = Counter(ym_pairs)
    
    print("\n--- Year-Month Distribution ---")
    for (y, m), count in sorted(counts.items()):
        print(f"  {y}-{m}: {count} entries")


if __name__ == "__main__":
    get_months()
