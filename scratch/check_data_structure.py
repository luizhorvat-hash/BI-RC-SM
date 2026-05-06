import json
import os
from pathlib import Path

# Mock a simple version of the build to see how keys are generated
def test_keys():
    dy = "2026"
    dm = f"{3:02d}" # March
    print(f"Key generated in Python: [{dy}][{dm}]")

test_keys()

# If data.js exists, let's try to peek at it
data_js = Path("c:/Dashboard/data.js")
if data_js.exists():
    content = data_js.read_text(encoding="utf-8")
    print("Found data.js")
    # Peek at SMD_TIMESHEET structure
    if "var SMD_TIMESHEET =" in content:
        start = content.find("var SMD_TIMESHEET =") + len("var SMD_TIMESHEET =")
        end = content.find(";", start)
        ts_json = content[start:end].strip()
        try:
            ts = json.loads(ts_json)
            prj = list(ts.keys())[0]
            years = list(ts[prj].keys())
            print(f"Project: {prj}")
            print(f"Years: {years}")
            if years:
                months = list(ts[prj][years[0]].keys())
                print(f"Months for {years[0]}: {months}")
        except:
            print("Could not parse SMD_TIMESHEET JSON")
