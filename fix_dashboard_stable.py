import sys

file_path = r'c:\Dashboard\SM_DASH.html'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Vamos localizar e substituir todo o bloco do Resumo Executivo por uma versão ultra-estável
start_idx = 7610
end_idx = 7845 # Abrangendo até o fim de _renderAdvancedExecTable e utilitários relacionados

new_code = """/**
 * ENGINE EXECUTIVO ULTRA-ESTÁVEL (VLAEG)
 * Projetado para resiliência total contra dados inconsistentes.
 */
function buildExecutiveSummary() {
  const VIEW_ID = 'exec-summary-body';
  const b = document.getElementById(VIEW_ID);
  if (!b) return;

  // 1. Verificação de Contexto
  const prj = typeof selProject !== 'undefined' ? selProject : null;
  if (!prj || strPrj(prj) === 'todos') {
    b.innerHTML = '<div style="padding:100px;text-align:center;color:var(--dim);font-size:12px;">' +
                  '<div style="font-size:30px;margin-bottom:15px;">📊</div>' +
                  'POR FAVOR, SELECIONE UM PROJETO ESPECÍFICO PARA GERAR O RELATÓRIO ESTRATÉGICO.</div>';
    return;
  }

  b.innerHTML = '<div style="padding:100px; text-align:center; color:var(--dim); font-size:12px;">' +
                '<div class="spinner" style="margin:0 auto 15px"></div>' +
                'PROCESSANDO INTELIGÊNCIA EXECUTIVA...</div>';

  setTimeout(function() {
    try {
      // 2. Extração Segura de Parâmetros
      const filterY = typeof selYear !== 'undefined' ? +selYear : new Date().getFullYear();
      const filterM = typeof selMonth !== 'undefined' ? +selMonth : null;
      const periodLabel = (filterM && typeof MPT !== 'undefined' ? MPT[filterM] : "Acumulado") + " " + filterY;
      
      const rawData = (window.SMD_DATA_T && window.SMD_DATA_T.rows) ? window.SMD_DATA_T.rows : [];
      if (rawData.length === 0) {
        b.innerHTML = '<div style="padding:100px;text-align:center;color:var(--dim);">AGUARDANDO CARREGAMENTO DE DADOS (SMD_DATA_T)...</div>';
        return;
      }

      // 3. MAPEAMENTO DE CABEÇALHOS (FAIL-SAFE)
      const _I = (key) => typeof _TF !== 'undefined' ? _TF.indexOf(key) : -1;
      const idx = {
        prj: _I('prj'), yo: _I('y_o'), mo: _I('m_o'), st: _I('st'), sv: _I('sv'), 
        md: _I('md'), yc: _I('y_c'), mc: _I('m_c'), app: _I('app'), rc: _I('root_cause'), upd: _I('days_upd')
      };

      if (idx.prj === -1) throw new Error("Mapeamento de colunas (_TF) inválido.");

      // 4. MOTOR DE PROCESSAMENTO ÚNICO (SINGLE PASS)
      const matStats = { inc: 0, prob: 0, urTotal: 0, urOnTime: 0, aging: 0, closed: 0, noRC: 0 };
      let tOpened = 0, tClosed = 0;
      const monthlyVol = {};

      rawData.forEach(r => {
        if (strPrj(r[idx.prj]) !== strPrj(prj)) return;
        
        const rYO = +r[idx.yo], rMO = +r[idx.mo], rYC = +r[idx.yc], rMC = +r[idx.mc];
        const st = String(r[idx.st]||'').toLowerCase();
        const sev = String(r[idx.sv]||'').toLowerCase();
        const app = String(r[idx.app]||'').toLowerCase();
        const isClosed = ['closed','resolved'].indexOf(st) !== -1;

        // Filtro de Período (Abertura)
        if (rYO === filterY && (!filterM || rMO === filterM)) {
          tOpened++;
          if (app !== 'internal' && st !== 'rejected') {
            if (sev.indexOf('incident') !== -1) matStats.inc++;
            if (sev.indexOf('problem') !== -1) matStats.prob++;
          }
          if (sev.indexOf('request') !== -1) {
            matStats.urTotal++;
            if (isClosed && (r[idx.md] * 8) <= 4) matStats.urOnTime++;
          }
          if (!isClosed && st !== 'rejected' && (r[idx.upd] || 0) > 15) matStats.aging++;
        }

        // Filtro de Período (Fechamento/Produção)
        if (rYC === filterY && (!filterM || rMC === filterM) && isClosed) {
          tClosed++;
          if (app !== 'internal' && (sev.indexOf('incident')!==-1 || sev.indexOf('problem')!==-1)) {
            matStats.closed++;
            if (!r[idx.rc] || r[idx.rc].trim() === '') matStats.noRC++;
          }
        }

        // Acúmulo Mensal para MoM (Apenas ano filtrado)
        if (rYO === filterY) {
          monthlyVol[rMO] = (monthlyVol[rMO] || 0) + 1;
        }
      });

      // 5. CÁLCULO DE PERFORMANCE E RANGES
      const projectCfg = typeof _loadProjectCFG === 'function' ? _loadProjectCFG(prj) : null;
      const cfgRanges = (projectCfg && projectCfg.ranges) ? projectCfg.ranges.filter(r => r.max > 0) : [];
      const tsData = (typeof SMD_TIMESHEET !== 'undefined') ? SMD_TIMESHEET : {};

      const monthAnalysis = [];
      for (let m = 1; m <= 12; m++) {
        const vol = monthlyVol[m] || 0;
        if (vol === 0 && m > new Date().getMonth() + 1 && filterY >= new Date().getFullYear()) continue;

        let mantisMD = 0;
        rawData.forEach(r => { 
          if (strPrj(r[idx.prj]) === strPrj(prj) && r[idx.yc] === filterY && r[idx.mc] === m) 
            mantisMD += (+r[idx.md] || 0); 
        });

        let tsMD = 0;
        const prjKey = Object.keys(tsData).find(k => strPrj(k) === strPrj(prj));
        if (prjKey && tsData[prjKey][String(filterY)] && tsData[prjKey][String(filterY)][String(m).padStart(2,'0')]) {
          tsMD = tsData[prjKey][String(filterY)][String(m).padStart(2,'0')].total_days || 0;
        }

        let expectedMD = 0;
        cfgRanges.forEach(rg => { if (vol >= rg.min && vol <= rg.max) expectedMD = rg.effort_mds; });
        if (expectedMD === 0 && cfgRanges.length && vol > cfgRanges[cfgRanges.length-1].max) {
          expectedMD = (Math.ceil(vol / 10) * 10) * 0.07;
        }

        if (vol > 0 || tsMD > 0 || mantisMD > 0) {
          monthAnalysis.push({ 
            m: m, label: typeof MPT !== 'undefined' ? MPT[m] : m, vol: vol, 
            actual: tsMD, expected: expectedMD, mantis: mantisMD 
          });
        }
      }

      // 6. MÉTRICAS CONSOLIDADAS
      const incPmRatio = matStats.inc > 0 ? (matStats.prob / matStats.inc * 100) : 0;
      const urSlaRatio = matStats.urTotal > 0 ? (matStats.urOnTime / matStats.urTotal * 100) : 100;
      const kedbRatio = matStats.closed > 0 ? ((matStats.closed - matStats.noRC) / matStats.closed * 100) : 100;

      const totalExpected = monthAnalysis.reduce((a,m) => a + m.expected, 0);
      const totalActual = monthAnalysis.reduce((a,m) => a + m.actual, 0);
      const globalEff = totalExpected > 0 ? (totalActual / totalExpected) * 100 : 0;

      // 7. RENDERIZAÇÃO SEGURA
      const headerHtml = `
        <div style="margin-bottom:30px; border-bottom:2px solid #fb923c; padding-bottom:15px; display:flex; justify-content:space-between; align-items:flex-end;">
          <div>
            <h2 style="margin:0; font-size:22px; color:#f1f5f9;">Resumo Executivo: ${prj.toUpperCase()}</h2>
            <div style="font-size:12px; color:#fb923c; margin-top:4px; letter-spacing:1px;">${periodLabel} | GOVERNANÇA VLAEG</div>
          </div>
          <div style="text-align:right; font-size:10px; color:var(--muted);">Gerado em: ${new Date().toLocaleString()}</div>
        </div>`;

      const scorecardHtml = `
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:20px 0;">
          ${buildMatCard("Vínculo Inc/PM", incPmRatio.toFixed(1) + "%", incPmRatio >= 100 ? "#34d399" : "#f87171", "Meta: 100% paridade")}
          ${buildMatCard("Agilidade UR (4h)", urSlaRatio.toFixed(1) + "%", urSlaRatio >= 95 ? "#34d399" : "#fbbf24", "User Requests no prazo")}
          ${buildMatCard("Aging Crítico", matStats.aging, matStats.aging > 5 ? "#f87171" : "#34d399", "Tickets parados > 15d")}
          ${buildMatCard("Higiene KEDB", kedbRatio.toFixed(0) + "%", "#60a5fa", "Causa Raiz preenchida")}
        </div>`;

      const analysisHtml = `
        <div style="background:rgba(255,255,255,0.02); padding:20px; border-radius:12px; border:1px solid rgba(255,255,255,0.05); margin-bottom:25px;">
          <h3 style="margin-top:0; color:#f1f5f9; font-size:14px; text-transform:uppercase; letter-spacing:1px; border-left:3px solid #fb923c; padding-left:10px;">1. Diagnóstico de Performance Global</h3>
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:40px; margin-top:15px;">
            <div>
              <p style="font-size:12px; color:var(--dim); line-height:1.6;">
                A operação apresenta uma eficiência financeira global de <b style="color:${globalEff <= 100 ? '#34d399' : '#f87171'}">${globalEff.toFixed(1)}%</b>. 
                Isso significa um consumo de <b>${totalActual.toFixed(1)} MDs</b> frente a um planejamento contratual de <b>${totalExpected.toFixed(1)} MDs</b> para o volume processado.
              </p>
            </div>
            <div style="text-align:right;">
               <div style="font-size:10px; color:var(--muted); margin-bottom:5px;">STATUS DA CONTA</div>
               <div style="font-size:24px; font-weight:700; color:${globalEff <= 100 ? '#34d399' : '#fbbf24'};">${globalEff <= 100 ? 'OPERANDO EM MARGEM' : 'ALERTA DE COMPLEXIDADE'}</div>
            </div>
          </div>
        </div>`;

      b.innerHTML = `
        <style>
          #exec-summary-body h3 { color:#f1f5f9; font-size:13px; margin-top:30px; text-transform:uppercase; letter-spacing:1px; }
          .exec-table th { padding:12px; color:var(--muted); font-size:10px; text-transform:uppercase; text-align:right; border-bottom:1px solid rgba(255,255,255,0.1); }
          .exec-table td { padding:12px; color:var(--dim); font-size:11px; text-align:right; border-bottom:1px solid rgba(255,255,255,0.03); }
          .exec-table tr:hover { background: rgba(255,255,255,0.02); }
        </style>
        ${headerHtml}
        ${analysisHtml}
        <h3>2. Maturidade Operacional (KPIs)</h3>
        ${scorecardHtml}
        <h3>3. Detalhamento de Produção MoM (Mantis vs Timesheet vs Range)</h3>
        ${_renderStableTable(monthAnalysis)}
      `;

      // 8. Integração Prescritiva
      if (typeof _addPrescriptiveBudget === 'function') _addPrescriptiveBudget(prj);

    } catch (err) {
      console.error("CRITICAL DASHBOARD ERROR:", err);
      b.innerHTML = `
        <div style="padding:60px; text-align:center; background:rgba(248,113,113,0.05); border-radius:15px; border:1px solid rgba(248,113,113,0.2);">
          <div style="font-size:40px; margin-bottom:20px;">⚠️</div>
          <h3 style="color:#f87171; margin-bottom:10px;">Falha na Geração do Resumo Executivo</h3>
          <p style="color:var(--dim); font-size:12px;">Ocorreu um erro ao processar os indicadores deste projeto.<br>Detalhe técnico: ${err.message}</p>
          <button onclick="buildExecutiveSummary()" style="margin-top:20px; padding:8px 20px; background:#1e293b; border:1px solid #f87171; color:#f87171; border-radius:6px; cursor:pointer;">Tentar Novamente</button>
        </div>`;
    }
  }, 50);
}

function _renderStableTable(data) {
  if (!data || data.length === 0) return '<p style="color:var(--muted); padding:20px;">Sem dados para detalhamento.</p>';
  
  let html = `<div style="overflow-x:auto;"><table class="exec-table" style="width:100%; border-collapse:collapse; margin-top:10px;"><thead><tr>` +
    `<th style="text-align:left;">Mês</th>` +
    `<th>Vol. Tickets</th>` +
    `<th>MD Planejado (Range)</th>` +
    `<th>MD Produção (Mantis)</th>` +
    `<th style="color:#34d399;">MD Real (TS)</th>` +
    `<th>Eficiência</th></tr></thead><tbody>`;

  data.forEach(d => {
    const eff = d.expected > 0 ? (d.actual / d.expected) * 100 : 0;
    const effCol = eff <= 100 ? '#34d399' : (eff <= 110 ? '#fbbf24' : '#f87171');
    
    html += `<tr>` +
      `<td style="text-align:left; font-weight:700; color:#f1f5f9;">${d.label}</td>` +
      `<td>${d.vol}</td>` +
      `<td>${d.expected.toFixed(2)}</td>` +
      `<td>${d.mantis.toFixed(2)}</td>` +
      `<td style="font-weight:700; color:#34d399;">${d.actual.toFixed(2)}</td>` +
      `<td style="font-weight:700; color:${effCol};">${d.expected > 0 ? eff.toFixed(0) + '%' : 'N/A'}</td>` +
      `</tr>`;
  });

  return html + `</tbody></table></div>`;
}

function buildMatCard(title, val, color, sub) {
  return `<div style="background:rgba(255,255,255,0.02); padding:15px; border-radius:10px; border:1px solid rgba(255,255,255,0.05); text-align:center;">
    <div style="font-size:9px; color:var(--muted); text-transform:uppercase; margin-bottom:10px;">${title}</div>
    <div style="font-size:20px; font-weight:700; color:${color};">${val}</div>
    <div style="font-size:9px; color:var(--dim); margin-top:5px;">${sub}</div>
  </div>`;
}
"""

# Substituir o bloco antigo pela nova versão blindada
lines[start_idx:end_idx+1] = [new_code + "\\n"]

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Stable Professional Engine applied successfully.")
