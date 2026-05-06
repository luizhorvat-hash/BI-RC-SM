import os
from pathlib import Path

# Use a streaming approach or just read the first few thousand characters
data_js = Path("c:/Dashboard/data.js")
if data_js.exists():
    with open(data_js, "r", encoding="utf-8") as f:
        content = f.read(2000000) # Read first 2MB
        
        # Check SMD_TIMESHEET structure
        if "SMD_TIMESHEET" in content:
            print("SMD_TIMESHEET found in first 2MB")
            # Look for 2026-01, 2026-02, etc.
            for m in ["01", "02", "03", "04"]:
                if f'"{m}"' in content:
                    print(f"Month {m} key found in first 2MB")
                else:
                    print(f"Month {m} key NOT found in first 2MB")

        # Check SMD_DATA_T indices
        # We know index 21 is y_c and 22 is m_c
        # Let's see if we find rows with 2026 and 1, 2, or 3
        import re
        # Find something like ..., 2026, 1, ...
        jan = re.search(r",\s*2026,\s*1,\s*", content)
        feb = re.search(r",\s*2026,\s*2,\s*", content)
        mar = re.search(r",\s*2026,\s*3,\s*", content)
        apr = re.search(r",\s*2026,\s*4,\s*", content)
        
        if jan: print("January Mantis data found")
        if feb: print("February Mantis data found")
        if mar: print("March Mantis data found")
        if apr: print("April Mantis data found")
