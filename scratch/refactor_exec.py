import sys
import re

file_path = r'c:\Dashboard\SM_DASH.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Locate the exact block to replace
start_str = "function buildExecutiveSummary() {"
end_str = "function strPrj(s) { return String(s || '').split(' ')[0].toLowerCase(); }"

start_idx = content.find(start_str)
end_idx = content.find(end_str)

if start_idx == -1 or end_idx == -1:
    print("Could not find block bounds!")
    sys.exit(1)

# New Implementation
new_code = """function buildExecutiveSummary() {
  var b = document.getElementById('panel-exec_summary');
  if (!b) return;
  var prj = selProject || 'Todos os Projetos';
  
  if (prj === 'Todos os Projetos') {
    b.innerHTML = '<div style="padding:100px;text-align:center;color:var(--dim);font-size:12px;letter-spacing:1px">POR FAVOR, SELECIONE UM PROJETO ESPECÍFICO PARA GERAR O RELATÓRIO ESTRATÉGICO.</div>';
    return;
  }

  // ── MOTOR DE CÁLCULO DINÂMICO ──────────────────
  var rows = (window.SMD_DATA_T && window.SMD_DATA_T.rows) ? window.SMD_DATA_T.rows : [];
  var tsData = (typeof SMD_TIMESHEET !== 'undefined') ? SMD_TIMESHEET : {};
  
  var totalMantis = 0;
  var totalTimesheet = 0;
  var tOpened = 0;
  var tClosed = 0;

  var months = [ { label: "Jan", y: 2026, m: 1 }, { label: "Fev", y: 2026, m: 2 }, { label: "Mar", y: 2026, m: 3 }, { label: "Abr", y: 2026, m: 4 } ];
  var dynamicData = months.map(function(mo) {
    var mMD = 0;
    rows.forEach(function(r) {
      if (strPrj(r[17]) === strPrj(prj) && r[21] === mo.y && r[22] === mo.m) {
        mMD += (r[26] || 0);
      }
    });
    var tsMD = 0;
    var prjKey = Object.keys(tsData).find(function(k) { return k === prj || strPrj(k) === strPrj(prj); });
    if (prjKey) {
      var yK = String(mo.y);
      var mK = String(mo.m).padStart(2, '0');
      if (tsData[prjKey][yK] && tsData[prjKey][yK][mK]) {
        tsMD = tsData[prjKey][yK][mK].total_days || 0;
      }
    }
    totalMantis += mMD;
    totalTimesheet += tsMD;
    return { m: mo.label, md: mMD, mdf: tsMD };
  });

  // Throughput (Abertos vs Fechados YTD)
  rows.forEach(function(r) {
    if (strPrj(r[17]) === strPrj(prj) && r[18] === 2026) {
      tOpened++;
      var st = String(r[21] || '').toLowerCase();
      if (['closed','resolved'].indexOf(st) !== -1) tClosed++;
    }
  });

  // SLA
  var slaInfo = getSLAFiltered ? getSLAFiltered() : { met:0, count:0 };
  var slaPct = slaInfo.count > 0 ? (slaInfo.met / slaInfo.count) * 100 : 0;

  // ── REGRAS DE NEGÓCIO (THRESHOLDS) ──────────────────
  var rMargem = "Sem Dados";
  var cMargem = "var(--dim)";
  var margemRatio = totalTimesheet > 0 ? totalMantis / totalTimesheet : (totalMantis > 0 ? 999 : 0);
  if (totalTimesheet > 0 || totalMantis > 0) {
    if (margemRatio <= 1.10) { rMargem = "Saudável"; cMargem = "#34d399"; }
    else if (margemRatio <= 1.30) { rMargem = "Atenção"; cMargem = "#fbbf24"; }
    else { rMargem = "Crítico"; cMargem = "#f87171"; }
  }

  var rVazao = "Sem Dados";
  var cVazao = "var(--dim)";
  if (tOpened > 0 || tClosed > 0) {
    if (tClosed >= tOpened) { rVazao = "Vazão Positiva"; cVazao = "#34d399"; }
    else { rVazao = "Gargalo Operacional"; cVazao = "#f87171"; }
  }

  var rSla = "Sem Dados";
  var cSla = "var(--dim)";
  if (slaInfo.count > 0) {
    if (slaPct >= 95) { rSla = "Blindado (>95%)"; cSla = "#34d399"; }
    else if (slaPct >= 90) { rSla = "Vulnerável (90-95%)"; cSla = "#fbbf24"; }
    else { rSla = "Crítico (<90%)"; cSla = "#f87171"; }
  }

  // Narrativa Inteligente
  var narrativa = "";
  if (margemRatio <= 1.10 && tClosed >= tOpened && slaPct >= 95) {
    narrativa = "A operação apresenta estabilidade de Margem (Saudável), com SLA blindado (>95%) e vazão positiva (Fechados superam Abertos). O projeto está rentável e operando em máxima eficiência técnica.";
  } else if (margemRatio > 1.30 || tClosed < tOpened) {
    var overhead = margemRatio > 1.0 ? ((margemRatio-1)*100).toFixed(1) : 0;
    narrativa = "O projeto requer atenção imediata. " + (tClosed < tOpened ? "Apresenta Gargalo Operacional ("+tOpened+" abertos vs "+tClosed+" fechados). " : "") + 
                (margemRatio > 1.30 ? "O esforço técnico total ("+totalMantis.toFixed(0)+" MDs) está "+overhead+"% superior ao faturamento aprovado, indicando perda de margem de lucro." : "");
  } else {
    narrativa = "A operação se mantém estável, porém requer acompanhamento da evolução de SLAs e volumetria para evitar pressão de margem no médio prazo.";
  }

  // ── HTML RENDER (GLASSMORPHISM CARDS) ──────────────────
  var html = '<div style="padding:12px; max-width:1200px; margin:0 auto; font-family:\\'Inter\\',sans-serif;">' +
    '<div style="margin-bottom:30px; border-bottom:1px solid var(--glass-border); padding-bottom:15px; display:flex; justify-content:space-between; align-items:flex-end">' +
      '<div><h1 style="font-size:24px; margin:0; color:var(--text); letter-spacing:-0.5px">Relatório de Gestão Estratégica</h1>' +
      '<h2 style="font-size:14px; margin:5px 0 0; color:var(--open); font-weight:400">' + prj.toUpperCase() + ' (YTD 2026)</h2></div>' +
      '<div style="text-align:right; font-size:10px; color:var(--dim)">SMD ALGORITHMIC ANALYSIS</div>' +
    '</div>' +

    '<!-- CARD VISÃO GERAL -->' +
    '<div style="background:var(--glass-surf); backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px); padding:24px; border-radius:12px; border:1px solid var(--glass-border); margin-bottom:20px; box-shadow:0 10px 30px var(--glass-shadow)">' +
      '<div style="font-size:12px; font-weight:700; color:var(--muted); margin-bottom:15px; letter-spacing:1px">1. VISÃO GERAL E CONDIÇÃO DO CONTRATO</div>' +
      '<p style="font-size:14px; color:var(--text); line-height:1.6; margin-bottom:24px; padding-left:12px; border-left:4px solid var(--open)"><i>"'+narrativa+'"</i></p>' +
      '<div style="display:grid; grid-template-columns:repeat(3,1fr); gap:15px">' +
        '<div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:8px; border:1px solid var(--glass-border)">' +
          '<div style="font-size:10px; color:var(--dim); margin-bottom:5px">BALANÇO DE ESFORÇO</div>' +
          '<div style="font-size:15px; font-weight:700; color:'+cMargem+'">'+rMargem+'</div>' +
        '</div>' +
        '<div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:8px; border:1px solid var(--glass-border)">' +
          '<div style="font-size:10px; color:var(--dim); margin-bottom:5px">TEMPERATURA OPERACIONAL</div>' +
          '<div style="font-size:15px; font-weight:700; color:'+cVazao+'">'+rVazao+'</div>' +
        '</div>' +
        '<div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:8px; border:1px solid var(--glass-border)">' +
          '<div style="font-size:10px; color:var(--dim); margin-bottom:5px">SAÚDE DE SLA (GLOBAL)</div>' +
          '<div style="font-size:15px; font-weight:700; color:'+cSla+'">'+rSla+'</div>' +
        '</div>' +
      '</div>' +
    '</div>' +

    '<!-- CARD TABELA MENSAL -->' +
    '<div style="background:var(--glass-surf); backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px); padding:24px; border-radius:12px; border:1px solid var(--glass-border); margin-bottom:20px; box-shadow:0 10px 30px var(--glass-shadow)">' +
      '<div style="font-size:12px; font-weight:700; color:var(--muted); margin-bottom:15px; letter-spacing:1px">2. CONCILIAÇÃO DE ESFORÇO (YTD)</div>' +
      '<table style="width:100%; border-collapse:collapse; background:rgba(255,255,255,0.01); border-radius:8px; overflow:hidden">' +
        '<thead style="background:var(--glass-surf); text-align:left">' +
          '<tr>' +
            '<th style="padding:12px;font-size:10px;color:var(--muted); border-bottom:1px solid var(--glass-border)">MÊS</th>' +
            '<th style="padding:12px;font-size:10px;color:var(--muted);text-align:right; border-bottom:1px solid var(--glass-border)">MD TÉCNICO (Mantis)</th>' +
            '<th style="padding:12px;font-size:10px;color:#34d399;text-align:right; border-bottom:1px solid var(--glass-border)">MD FATURÁVEL (Timesheet)</th>' +
            '<th style="padding:12px;font-size:10px;color:var(--open);text-align:right; border-bottom:1px solid var(--glass-border)">OVERHEAD / DELTA</th>' +
          '</tr>' +
        '</thead><tbody>' +
        dynamicData.map(function(d) {
          var delta = d.md - d.mdf;
          var dCol = delta > 5 ? "#f87171" : (delta > 0 ? "var(--open)" : "var(--dim)");
          return '<tr style="border-bottom:1px solid var(--glass-border)">' +
            '<td style="padding:12px; font-weight:700; color:var(--text)">'+d.m+'</td>' +
            '<td style="padding:12px; text-align:right; color:var(--dim)">'+d.md.toFixed(2)+'</td>' +
            '<td style="padding:12px; text-align:right; font-weight:700; color:#34d399">'+d.mdf.toFixed(2)+'</td>' +
            '<td style="padding:12px; text-align:right; font-weight:700; color:'+dCol+'">'+(delta>0?'+':'')+delta.toFixed(2)+'</td>' +
          '</tr>';
        }).join('') +
      '</tbody></table>' +
    '</div>' +
  '</div>';

  b.innerHTML = html;
}
"""

content = content[:start_idx] + new_code + content[end_idx:]

# Additionally, the original panel had an inner div with hardcoded CSS. We must strip that in HTML so the JS populates purely inside panel.
# We replace `<div id="panel-exec_summary" class="panel">...</div>` with a clean one.
html_panel_search = re.compile(r'<div id="panel-exec_summary" class="panel">.*?</div>\s*</div>\s*</div>', re.DOTALL)
content = html_panel_search.sub('<div id="panel-exec_summary" class="panel" style="padding:10px; overflow-y:auto"></div>', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Executive Summary Refactored.")
