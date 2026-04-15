import json
from pathlib import Path

def check_coverage():
    data_js = Path("data.js")
    if not data_js.exists():
        print("data.js not found")
        return

    content = data_js.read_text(encoding='utf-8')
    start_tag = "var SMD_DATA_D="
    if start_tag not in content:
        start_tag = "var SMD_DATA_D = "
        
    end_tag = ";var SMD_DATA_T"
    
    start_idx = content.find(start_tag) + len(start_tag)
    end_idx = content.find(end_tag)

    
    if start_idx == -1 or end_idx == -1:
        print("Could not parse data.js structure")
        return
        
    data_str = content[start_idx:end_idx]
    data = json.loads(data_str)
    ts = data.get('timesheet', {})
    
    print(f"Total entries in timesheet: {len(ts)}")
    
    # 1. Date Distribution
    date_dist = {}
    # 2. Severity Distribution for April 2026
    sev_dist_apr_26 = {}
    # 3. Project Distribution for April 2026
    prj_dist_apr_26 = {}

    for k, v in ts.items():
        y = v.get('y')
        m = v.get('m')
        sv = v.get('sv')
        prj = v.get('prj')
        
        ym = f"{y}-{m}"
        date_dist[ym] = date_dist.get(ym, 0) + 1
        
        if ym == "2026-4":
            sev_dist_apr_26[sv] = sev_dist_apr_26.get(sv, 0) + 1
            prj_dist_apr_26[prj] = prj_dist_apr_26.get(prj, 0) + 1

    print("\n--- Date Distribution ---")
    for k in sorted(date_dist.keys()):
        print(f"  {k}: {date_dist[k]} entries")

    print("\n--- April 2026 Severities ---")
    for k, count in sev_dist_apr_26.items():
        print(f"  {k}: {count}")

    print("\n--- April 2026 Projects (Top 10) ---")
    sorted_prjs = sorted(prj_dist_apr_26.items(), key=lambda x: x[1], reverse=True)
    for k, count in sorted_prjs[:10]:
        print(f"  {k}: {count}")

if __name__ == "__main__":
    check_coverage()
