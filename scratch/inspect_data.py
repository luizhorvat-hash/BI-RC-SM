import json
from pathlib import Path

data_js = Path("data.js")
if not data_js.exists():
    print("data.js not found")
    exit()

content = data_js.read_text(encoding="utf-8")
ai_insights = None
for line in content.splitlines():
    if line.startswith("var AI_INSIGHTS ="):
        json_str = line.replace("var AI_INSIGHTS =", "").strip().rstrip(";")
        try:
            ai_insights = json.loads(json_str)
            print(f"AI_INSIGHTS found. Keys: {list(ai_insights.keys())}")
            for k, v in ai_insights.items():
                print(f"  {k}: {list(v.keys())}")
        except Exception as e:
            print(f"Error parsing AI_INSIGHTS JS: {e}")
        break

timesheet = None
for line in content.splitlines():
    if line.startswith("var SMD_TIMESHEET ="):
        json_str = line.replace("var SMD_TIMESHEET =", "").strip().rstrip(";")
        try:
            timesheet = json.loads(json_str)
            print(f"SMD_TIMESHEET found. Keys: {list(timesheet.keys())}")
            if "status" in timesheet:
                 print(f"  Status: {timesheet['status']}")
            if "projects" in timesheet:
                 print(f"  Projects: {list(timesheet['projects'].keys())}")
        except Exception as e:
            print(f"Error parsing SMD_TIMESHEET JS: {e}")
        break

if ai_insights is None:
    print("AI_INSIGHTS variable not found in data.js")
