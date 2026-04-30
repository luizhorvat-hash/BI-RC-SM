$path = 'c:\Dashboard\SM_DASH.html'
$content = [System.IO.File]::ReadAllText($path)

# 1. Corrigir a mistura de exportSummary e engine (caso ainda exista)
$pattern1 = '(?s)body_html \+= ''<div class=\"ai\">'' \+.*?agg\.headcount = Object\.keys\(agg\.staff\)\.length;'
$replacement1 = 'body_html += ''<div class="ai">'' + esc(txt.trim().slice(0,120)) + ''</div>'';
    });
    body_html += ''</div>'';
  }

  body_html += ''<div class="ft">Service Management Dashboard &nbsp;|&nbsp; Arrocha &nbsp;|&nbsp; '' + dateStr + ''</div>'';

  var win = window.open('''', ''_blank'', ''width=820,height=640'');
  if (!win) { alert(''Permita popups para exportar.''); return; }
  win.document.write(''<!DOCTYPE html><html><head><meta charset="utf-8"><title>SMD Resumo '' + dateStr + ''</title>'' +
    ''<style>'' + css + ''</style></head><body>'' + body_html + ''</body></html>'');
  win.document.close();
  win.focus();
  setTimeout(function(){ win.print(); }, 300);
}

// ── TIMESHEET ENGINE ────────────────────────────────────────────────────────
var _tsData = (typeof SMD_TIMESHEET !== ''undefined'') ? SMD_TIMESHEET : {};

function getTSData() {
  var prj = selProject || ''Todos'';
  var src = _tsData[prj] || _tsData[''Todos''] || {};
  if (selYear) {
    var filtered = {}; filtered[String(selYear)] = src[String(selYear)] || {}; return filtered;
  }
  return src;
}

function getTSMonth() {
  var src = getTSData();
  var result = {};
  Object.keys(src).forEach(function(yr) {
    Object.keys(src[yr]).forEach(function(mo) {
      if (selMonth && parseInt(mo) !== selMonth) return;
      var key = yr + ''-'' + mo;
      result[key] = src[yr][mo];
    });
  });
  return result;
}

function getTSAgg() {
  var months = getTSMonth();
  var agg = { total_h:0, total_days:0, overtime_h:0, headcount_set:{},
               staff:{}, tasks:{}, subs:{}, grades:{}, grade_details:{}, sub_projects:{}, weekly:[], weekly_map:{} };
  Object.values(months).forEach(function(b) {
    agg.total_h    += b.total_h    || 0;
    agg.total_days += b.total_days || 0;
    agg.overtime_h += b.overtime_h || 0;
    (b.top_staff||[]).forEach(function(s){ agg.staff[s.name] = (agg.staff[s.name]||0) + s.h; });
    (b.top_tasks||[]).forEach(function(t){ agg.tasks[t.task] = (agg.tasks[t.task]||0) + t.h; });
    Object.keys(b.by_subsidiary||{}).forEach(function(s){ agg.subs[s] = (agg.subs[s]||0) + (b.by_subsidiary[s]||0); });
    Object.keys(b.by_career_grade||{}).forEach(function(g){ agg.grades[g] = (agg.grades[g]||0) + (b.by_career_grade[g]||0); });
    Object.keys(b.grade_details||{}).forEach(function(g){
      if(!agg.grade_details[g]) agg.grade_details[g] = {};
      b.grade_details[g].forEach(function(d){
        if(!agg.grade_details[g][d.name]) agg.grade_details[g][d.name] = { h:0, d:0, sub:d.sub };
        agg.grade_details[g][d.name].h += d.h;
        agg.grade_details[g][d.name].d += d.d;
      });
    });
    (b.sub_projects||[]).forEach(function(p){ agg.sub_projects[p.name] = (agg.sub_projects[p.name]||0) + p.h; });
    (b.weekly||[]).forEach(function(w){
      if(!agg.weekly_map[w.week]) {
        agg.weekly_map[w.week] = { week:w.week, h:0 };
        agg.weekly.push(agg.weekly_map[w.week]);
      }
      agg.weekly_map[w.week].h += w.h;
    });
  });
  agg.headcount = Object.keys(agg.staff).length;'

# 2. Corrigir buildTimesheet (lógica de MDs)
$pattern2 = '(?s)var tKey = tY \+ ''-'' \+ String\(tM\)\.padStart\(2,''0''\);.*?var consumedMD = 0;.*?prjList\.forEach\(function\(p\) \{.*?consumedMD \+= tsPrj\[tY\]\[String\(tM\)\.padStart\(2,''0''\)\]\.total_days \|\| 0;.*?\}\);'
$replacement2 = 'var tKey = tY + ''-'' + String(tM).padStart(2,''0'');

  var consumedMD = 0;
  var prjList = selProject ? [selProject] : (D.projects || []);
  prjList.forEach(function(p) {
    var tsPrj = (typeof SMD_TIMESHEET !== ''undefined'' ? SMD_TIMESHEET[p] : null);
    if (tsPrj && tsPrj[tY] && tsPrj[tY][String(tM).padStart(2,''0'')]) {
      consumedMD += tsPrj[tY][String(tM).padStart(2,''0'')].total_days || 0;
    }
  });

  // ── CÁLCULO DE MDs POR CATEGORIA (Severidade/Prioridade/Complexidade) ────────
  var sevMD = { INCIDENT:0, USER_REQUEST:0, PROBLEM:0, CHANGE_REQUEST:0, INTERNAL:0, UNKNOWN:0 };
  var priMD = { P1:0, P2:0, P3:0, P4:0 };
  var appMD = {}; // Para Matriz de Complexidade
  var linkedTotalMD = 0;
  var counted = 0;

  Object.keys(ts).forEach(function(tid) {
    var d = ts[tid];
    if (selProject && d.prj !== selProject) return;
    
    var tMD = 0;
    var filterKey = (selYear && selMonth) ? (selYear + ''-'' + String(selMonth).padStart(2,''0'')) : null;
    
    Object.keys(d.periods || {}).forEach(function(pk) {
      if (filterKey) { if (pk === filterKey) tMD += d.periods[pk].d || 0; }
      else if (selYear) { if (pk.startsWith(selYear)) tMD += d.periods[pk].d || 0; }
      else tMD += d.periods[pk].d || 0;
    });

    if (tMD > 0) {
      counted++;
      linkedTotalMD += tMD;
      // Severidade
      var s = (d.sv || ''unknown'').toUpperCase();
      if (sevMD[s] !== undefined) sevMD[s] += tMD;
      else sevMD.UNKNOWN += tMD;
      
      // Prioridade
      var p = (d.pr || ''P4'').toUpperCase();
      if (priMD[p] !== undefined) priMD[p] += tMD;
      
      // Complexidade
      var t = getTix(tid);
      var app = (t ? (t.ap || ''N/A'') : ''N/A'');
      if (!appMD[app]) appMD[app] = { tix:0, md:0, mttrSum:0, closed:0 };
      appMD[app].md += tMD;
      appMD[app].tix++;
      if (t && t.st === ''closed'' && t.op && t.cl) {
        var d1 = new Date(t.op), d2 = new Date(t.cl);
        var diff = (d2 - d1) / (1000 * 3600);
        if (diff >= 0) { appMD[app].mttrSum += diff; appMD[app].closed++; }
      }
    }
  });

  // Esforço não vinculado a tickets (Internal/Outros)
  var internalMD = Math.max(0, consumedMD - linkedTotalMD);
  sevMD.INTERNAL += internalMD;'

$newContent = [System.Text.RegularExpressions.Regex]::Replace($content, $pattern1, $replacement1)
$newContent = [System.Text.RegularExpressions.Regex]::Replace($newContent, $pattern2, $replacement2)
[System.IO.File]::WriteAllText($path, $newContent, [System.Text.Encoding]::UTF8)
