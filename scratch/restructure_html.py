import sys
import re

file_path = r'c:\Dashboard\SM_DASH.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update CSS - ONLY FIRST OCCURRENCE
css_additions = """
/* --- NOVO LAYOUT CLAUDE DESIGN --- */
html,body { overflow: hidden; }
.app-layout { display: flex; height: 100vh; width: 100vw; overflow: hidden; }
.sidebar { width: 260px; background: var(--glass-surf); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border-right: 1px solid var(--glass-border); display: flex; flex-direction: column; padding: 24px 0; z-index: 200; flex-shrink: 0; box-shadow: 4px 0 24px var(--glass-shadow); }
.sidebar .logo { padding: 0 24px; margin-bottom: 32px; font-size: 16px; color: var(--text); }
.sidebar .nav { display: flex; flex-direction: column; border: none; background: transparent; padding: 0; overflow-y: auto; overflow-x: hidden; }
.sidebar .ntab { padding: 12px 24px; border-radius: 0; border: none; border-left: 4px solid transparent; margin-bottom: 4px; font-size: 11px; font-weight: 600; text-transform: none; letter-spacing: normal; color: var(--dim); white-space: normal; }
.sidebar .ntab:hover { background: rgba(255,255,255,0.03); color: var(--text); }
.sidebar .ntab.active { background: rgba(255,255,255,0.08); box-shadow: inset 20px 0 20px -20px rgba(0,0,0,0.2); font-size: 11px; color: var(--text); }
.main-content { flex: 1; display: flex; flex-direction: column; overflow-y: auto; overflow-x: hidden; }
.main-content .hdr { background: transparent; backdrop-filter: none; border-bottom: none; box-shadow: none; padding: 24px 32px 12px 32px; height: auto; position: relative; }
.panels-container { padding: 0 12px 24px 12px; display: flex; flex-direction: column; flex: 1; }
/* --------------------------------- */
</style>
"""
content = content.replace('</style>', css_additions, 1)

# 2. Update HTML Structure
html_search = """<body>
<div class="bg-orbs"><div class="orb orb-1"></div><div class="orb orb-2"></div></div>

<div class="hdr">
  <div class="logo"><div class="dot"></div>SERVICE MANAGEMENT DASHBOARD</div>
  <div class="hchips"><span class="chip" id="chip-prj">-</span><span class="chip">27/03/2026</span></div>
</div>

<div class="fbar">"""

html_replace = """<body>
<div class="bg-orbs"><div class="orb orb-1"></div><div class="orb orb-2"></div></div>

<div class="app-layout">
  <aside class="sidebar">
    <div class="logo"><div class="dot"></div>Retail Consult</div>
    <div class="nav" id="nav">
      <!-- nav será movido pra cá -->
    </div>
  </aside>
  
  <main class="main-content">
    <div class="hdr">
      <div>
        <div style="font-family:var(--ft);font-size:18px;font-weight:700;color:var(--text);letter-spacing:0.05em">EXECUTIVE DASHBOARD</div>
        <div style="font-size:11px;color:var(--muted);margin-top:4px">Service Management Analytics</div>
      </div>
      <div class="hchips"><span class="chip" id="chip-prj">-</span><span class="chip">27/03/2026</span></div>
    </div>

    <div class="fbar">"""

content = content.replace(html_search, html_replace)

# 3. Move the .nav items
nav_search = """<div class="nav" id="nav">
  <div class="ntab t-hoje active" data-view="hoje">&#128197; Hoje</div>
  <div class="ntab t-inc" data-sev="incident">Incident</div>
  <div class="ntab t-ur"  data-sev="user_request">User Request</div>
  <div class="ntab t-prb" data-sev="problem">Problem</div>
  <div class="ntab t-cr"  data-sev="change_request">Change Request</div>
  <div class="ntab t-int" data-sev="internal">Internal</div>
  <div class="ntab t-attn" data-view="attn">&#9888; Atencao</div>
  <div class="ntab t-cfg"  data-view="config">&#9881; Config</div>
  <div class="ntab t-ai" data-view="ai">&#129302; AI Insights</div>
  <div class="ntab t-cmp" data-view="comp">&#128200; Comparativo</div>
  <div class="ntab t-cli" data-view="cliente">&#128200; Cliente</div>
  <div class="ntab t-ts"  data-view="timesheet">&#128336; Timesheet</div>
  <div class="ntab t-comp-ts" data-view="comp_timesheet">&#128203; Comparativo TS</div>
  <div class="ntab t-exec" data-view="exec_summary">&#128196; Resumo Executivo</div>
  <div class="ntab t-sim" data-view="simulador">&#128202; Simulador</div>
</div>"""

# Extract the inner items
nav_items_match = re.search(r'<div class="nav" id="nav">(.*?)</div>', nav_search, re.DOTALL)
if nav_items_match:
    nav_items = nav_items_match.group(1)
    # Replace the empty placeholder we inserted
    content = content.replace('<div class="nav" id="nav">\n      <!-- nav será movido pra cá -->\n    </div>', f'<div class="nav" id="nav">{nav_items}</div>')
    # Remove the OLD nav completely by replacing it with the start of our new panels-container wrapper
    content = content.replace(nav_search, '<div class="panels-container">')

# 4. Close the tags at the END of the file (using rpartition to target the LAST </body>)
before, sep, after = content.rpartition('</body>')
if sep:
    content = before + '</div></main></div>\n</body>' + after

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("HTML Restructure Complete (Fixed!).")
