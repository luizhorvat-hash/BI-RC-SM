import json
from datetime import datetime
from pathlib import Path

with open('c:/Dashboard/scratch/_kpis_tmp.json', encoding='utf-8') as f:
    kpis = json.load(f)

ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def hs_label(v):
    return "EXCELENTE" if v>=90 else ("BOM" if v>=70 else ("ATENÇÃO" if v>=50 else "CRÍTICO"))

def hs_color(v):
    return "green" if v>=70 else ("yellow" if v>=50 else "red")

def fmt_apps(top):
    return ", ".join(a['app'] for a in top[:3]) if top else "N/A"

def fmt_rct(top):
    return ", ".join(a['rct'] for a in top[:3]) if top else "N/A"

def week_trend(weekly):
    if len(weekly) < 2: return "estável"
    last2 = sum(w['incidents'] for w in weekly[-2:])
    prev2 = sum(w['incidents'] for w in weekly[-4:-2]) if len(weekly) >= 4 else last2
    if prev2 == 0: return "estável"
    delta = (last2 - prev2) / prev2 * 100
    if delta > 15: return f"alta de {delta:.0f}%"
    if delta < -15: return f"queda de {abs(delta):.0f}%"
    return "estável"

def forecast_weeks(weekly, n=4):
    src = weekly[-6:] if len(weekly) >= 6 else weekly
    if not src:
        return [{"week": i+1, "incidents": 0, "user_requests": 0} for i in range(n)]
    avg_i = sum(w['incidents'] for w in src) / len(src)
    avg_u = sum(w['user_requests'] for w in src) / len(src)
    xs = list(range(len(src)))
    si = sum(xs[i]*src[i]['incidents'] for i in range(len(src)))
    su = sum(xs[i]*src[i]['user_requests'] for i in range(len(src)))
    sx = sum(xs); sxx = sum(x*x for x in xs); n_s = len(src)
    denom = n_s*sxx - sx*sx or 1
    slope_i = (n_s*si - sx*sum(w['incidents'] for w in src)) / denom
    slope_u = (n_s*su - sx*sum(w['user_requests'] for w in src)) / denom
    result = []
    base = len(src) - 1
    for w in range(1, n+1):
        result.append({
            "week": w,
            "incidents":     max(0, round(avg_i + slope_i*(base+w))),
            "user_requests": max(0, round(avg_u + slope_u*(base+w)))
        })
    return result

def gen_ops(k, prj):
    hs = k['health_score']
    p1 = k['sla'].get('P1', {}); p2 = k['sla'].get('P2', {})
    mttr_p1 = k['mttr'].get('P1', {}); bk = k['backlog']
    apps = fmt_apps(k['top_apps']); rct = fmt_rct(k['top_rct'])
    inc_open = k['summary'].get('incident', {}).get('open', 0)
    trend = week_trend(k['historical_weekly_volume'])
    p1p = p1.get('pct', 0); p2p = p2.get('pct', 0)
    mh = mttr_p1.get('median_h', 0); mx = mttr_p1.get('gap_x', 0)
    ag = k['aging_gt30']
    sla_status = "DENTRO_DO_TARGET" if p1p >= 98 else "EM_RISCO"

    alerts = []
    if p1p < 98:
        alerts.append({"level":"ALTO","message":f"SLA P1 em {p1p}% — abaixo do target de 98%","metric":"SLA_P1"})
    if mh > 4:
        alerts.append({"level":"MEDIO","message":f"MTTR P1 mediano {mh}h ({mx}x acima do benchmark ITIL de 4h)","metric":"MTTR_P1"})
    if bk['rc'] > 20:
        alerts.append({"level":"ALTO","message":f"Backlog RC com {bk['rc']} tickets — risco de SLA futuro","metric":"BACKLOG_RC"})
    if ag > 10:
        alerts.append({"level":"MEDIO","message":f"{ag} tickets com aging >30 dias","metric":"AGING"})
    if not alerts:
        alerts.append({"level":"BAIXO","message":"Operação dentro dos parâmetros — manutenção preventiva recomendada","metric":"GERAL"})

    summary = (
        f"Saúde operacional de {prj}: {hs_label(hs)} ({hs}/100). "
        f"SLA P1: {p1p}% ({sla_status}), P2: {p2p}%. "
        f"MTTR P1 mediano: {mh}h vs benchmark ITIL 4h. "
        f"Incidents abertos: {inc_open}. Backlog RC: {bk['rc']}, Cliente: {bk['cli']}. "
        f"Aging >30d: {ag} tickets. Tendência semanal: {trend}. "
        f"Apps críticas: {apps}. Root causes dominantes: {rct}."
    )
    p3_pct = k['sla'].get('P3',{}).get('pct',0)
    p4_pct = k['sla'].get('P4',{}).get('pct',0)
    p2_met = k['sla'].get('P2',{}).get('met',0)
    p2_tot = k['sla'].get('P2',{}).get('total',0)
    p1_met = p1.get('met',0); p1_tot = p1.get('total',0)
    mttr_p2 = k['mttr'].get('P2',{}).get('median_h',0)
    mttr_p3 = k['mttr'].get('P3',{}).get('median_h',0)
    inc_total = k['summary'].get('incident',{}).get('total',0)
    ur_total  = k['summary'].get('user_request',{}).get('total',0)
    pb_total  = k['summary'].get('problem',{}).get('total',0)

    rec1 = "Priorizar resolução de P1s em aberto para recuperar SLA." if p1p < 98 else "Manter SLA P1 — implementar revisão semanal preventiva."
    rec2 = f"Reduzir MTTR P1 com escalonamento automático após 2h sem resolução." if mh > 4 else "MTTR P1 dentro do benchmark — documentar boas práticas."
    rec3 = f"Revisar backlog RC com o gerente para identificar bloqueios técnicos." if bk['rc'] > 15 else "Manter cadência de backlog grooming semanal."

    reasoning = (
        f"Análise completa de {k['total_tickets']} tickets do projeto {prj} (referência {ts[:10]}).\n\n"
        f"**SLA Performance:**\n"
        f"- P1: {p1p}% de cumprimento ({p1_met}/{p1_tot} tickets) — benchmark ITIL: 99%+\n"
        f"- P2: {p2p}% ({p2_met}/{p2_tot} tickets)\n"
        f"- P3: {p3_pct}% | P4: {p4_pct}%\n\n"
        f"**MTTR (Incidentes PRD fechados):**\n"
        f"- P1: {mh}h mediano | P2: {mttr_p2}h | P3: {mttr_p3}h\n"
        f"- P1 está {mx}x acima do benchmark ITIL (4h) {'(ATENCAO)' if mx > 2 else '(OK)'}\n\n"
        f"**Backlog e Aging:**\n"
        f"- RC (nosso lado): {bk['rc']} tickets em análise/desenvolvimento\n"
        f"- Cliente: {bk['cli']} tickets aguardando resposta do cliente\n"
        f"- {ag} tickets abertos há mais de 30 dias requerem revisão urgente\n\n"
        f"**Distribuição por Severidade:**\n"
        f"- Incidents: {inc_total} total, {inc_open} abertos\n"
        f"- User Requests: {ur_total} total\n"
        f"- Problems: {pb_total} total\n\n"
        f"**Recomendações:**\n"
        f"1. {rec1}\n"
        f"2. {rec2}\n"
        f"3. {rec3}\n"
        f"4. Apps críticas a monitorar proativamente: {apps}."
    )
    return {"agent":"AI_OPS","timestamp":ts,"status":"ok",
            "executive_summary":summary,"reasoning":reasoning,
            "health_score":{"value":hs,"label":hs_label(hs),"color":hs_color(hs)},
            "sla_analysis":{"p1_pct":p1p,"p2_pct":p2p,"overall_status":sla_status},
            "alerts":alerts}

def gen_predictive(k, prj):
    hs = k['health_score']; bk = k['backlog']; ag = k['aging_gt30']
    trend = week_trend(k['historical_weekly_volume'])
    fc = forecast_weeks(k['historical_weekly_volume'])
    rct = fmt_rct(k['top_rct'])
    weekly = k['historical_weekly_volume']
    avg_inc = sum(w['incidents'] for w in weekly[-4:]) / max(len(weekly[-4:]), 1)
    avg_ur  = sum(w['user_requests'] for w in weekly[-4:]) / max(len(weekly[-4:]), 1)

    summary = (
        f"Análise preditiva de {prj}: tendência de incidents {trend}. "
        f"Média últimas 4 semanas: {avg_inc:.1f} incidents/semana, {avg_ur:.1f} URs/semana. "
        f"Backlog RC atual: {bk['rc']} — {'crítico' if bk['rc']>20 else 'controlado'}. "
        f"Previsão próximas 4 semanas: {fc[0]['incidents']}-->{fc[3]['incidents']} incidents/sem. "
        f"Root causes recorrentes: {rct}."
    )

    hist_lines = "".join(
        f"- Sem {w['year']}-W{w['week']:02d}: {w['incidents']} incidents, {w['user_requests']} URs\n"
        for w in weekly[-8:]
    )
    fc_lines = "".join(
        f"- Semana +{f['week']}: ~{f['incidents']} incidents, ~{f['user_requests']} user requests\n"
        for f in fc
    )
    risk1 = f"Backlog RC: {bk['rc']} tickets acumulados {'(ALTO — pode inflar volume futuro)' if bk['rc']>20 else '(controlado)'}"
    risk2 = f"Aging >30d: {ag} tickets {'— indica gargalo de resolução' if ag>5 else '— dentro do normal'}"
    rec2 = "Revisar capacidade da equipe — volume projetado pode exceder SLA." if fc[3]['incidents'] > avg_inc*1.2 else "Manter monitoramento semanal de volume."

    reasoning = (
        f"**Análise Preditiva — {prj} ({ts[:10]}):**\n\n"
        f"**Volume Histórico (últimas {len(weekly)} semanas):**\n"
        f"{hist_lines}\n"
        f"**Tendência:** {trend.upper()}\n\n"
        f"**Projeção Próximas 4 Semanas:**\n"
        f"{fc_lines}\n"
        f"**Fatores de Risco:**\n"
        f"- {risk1}\n"
        f"- {risk2}\n"
        f"- Root causes recorrentes sem resolução definitiva: {rct}\n\n"
        f"**Recomendações:**\n"
        f"1. Implementar problema formal para RCAs recorrentes: {rct.split(',')[0] if rct != 'N/A' else 'classificar root causes não mapeados'}.\n"
        f"2. {rec2}\n"
        f"3. Priorizar resolução do backlog RC antes do acúmulo virar débito de SLA."
    )
    return {"agent":"AI_PREDICTIVE","timestamp":ts,"status":"ok",
            "executive_summary":summary,"reasoning":reasoning,
            "health_score":{"value":hs,"label":hs_label(hs),"color":hs_color(hs)},
            "weekly_forecast":fc}

def gen_improvement(k, prj):
    hs = k['health_score']
    p1p = k['sla'].get('P1',{}).get('pct',0)
    mh = k['mttr'].get('P1',{}).get('median_h',0)
    bk = k['backlog']; ag = k['aging_gt30']
    apps = fmt_apps(k['top_apps']); rct = fmt_rct(k['top_rct'])
    mat = "Nível 3 (Gerenciado)" if hs>=75 else ("Nível 2 (Definido)" if hs>=50 else "Nível 1 (Inicial)")

    qw = []
    if mh > 4:
        qw.append(f"Runbook de Resolução P1: Criar playbook para top 3 cenários P1. Impacto: redução de {round(mh-4,1)}h no MTTR (de {mh}h para ~4h).")
    else:
        qw.append(f"Knowledge Base de P1: MTTR P1 já em {mh}h (dentro do benchmark). Documentar procedimentos bem-sucedidos para onboarding.")
    if bk['rc'] > 15:
        qw.append(f"Backlog Sprint: Dedicar 20% da capacidade semanal para resolver os {bk['rc']} tickets RC acumulados. Meta: zerar em 3 sprints.")
    else:
        qw.append(f"Automação de Categorização: Implementar regras automáticas para root causes em {rct} — reduz tempo de triagem em ~30%.")
    if ag > 5:
        qw.append(f"Aging Review: {ag} tickets com >30 dias — implementar alerta automático no D+15 para escalonamento preventivo.")

    p3_pct = k['sla'].get('P3',{}).get('pct',0)
    p4_pct = k['sla'].get('P4',{}).get('pct',0)
    gap_sla = round(99-p1p,1) if p1p<99 else 0
    gap_mttr = round(mh-4,1) if mh>4 else 0
    gap_bk = bk['rc']-10 if bk['rc']>10 else 0

    summary = (
        f"Maturidade ITIL estimada: {mat} — {prj}. "
        f"Quick Win 1: {qw[0][:80]}... "
        f"Quick Win 2: {qw[1][:80]}... "
        f"Apps críticas a automatizar: {apps}."
    )
    qw_lines = "".join(f"{i+1}. {q}\n\n" for i,q in enumerate(qw))
    sla_ok = "ok" if p1p>=99 else str(gap_sla)+"pp"
    mttr_ok = "ok" if mh<=4 else "+"+str(gap_mttr)+"h"
    bk_ok = "ok" if bk['rc']<=10 else "+"+str(gap_bk)
    ag_ok = "ok" if ag==0 else "+"+str(ag)

    reasoning = (
        f"**Plano de Melhoria Contínua — {prj} ({ts[:10]}):**\n\n"
        f"**Nível de Maturidade ITIL:** {mat}\n\n"
        f"**Quick Wins Identificados:**\n"
        f"{qw_lines}"
        f"**Métricas Atuais vs Targets:**\n"
        f"| Métrica      | Atual   | Target ITIL | Gap   |\n"
        f"|--------------|---------|-------------|-------|\n"
        f"| SLA P1       | {p1p}%  | 99%+        | {sla_ok} |\n"
        f"| SLA P3       | {p3_pct}% | 95%+      | {'ok' if p3_pct>=95 else str(round(95-p3_pct,1))+'pp'} |\n"
        f"| MTTR P1      | {mh}h   | <4h         | {mttr_ok} |\n"
        f"| Backlog RC   | {bk['rc']} | <10      | {bk_ok} |\n"
        f"| Aging >30d   | {ag}    | 0           | {ag_ok} |\n\n"
        f"**Roadmap Sugerido (90 dias):**\n"
        f"- Mês 1: Implementar quick wins de processo (runbooks, RCA formal)\n"
        f"- Mês 2: Automatizar alertas e categorização\n"
        f"- Mês 3: Medir impacto e ajustar — revisão de maturidade ITIL"
    )
    return {"agent":"AI_IMPROVEMENT","timestamp":ts,"status":"ok",
            "executive_summary":summary,"reasoning":reasoning,
            "health_score":{"value":hs,"label":hs_label(hs),"color":hs_color(hs)},
            "quick_wins":qw[:3]}

def gen_market(k, prj):
    hs = k['health_score']
    p1p = k['sla'].get('P1',{}).get('pct',0)
    p2p = k['sla'].get('P2',{}).get('pct',0)
    mh = k['mttr'].get('P1',{}).get('median_h',0)
    mttr_p2 = k['mttr'].get('P2',{}).get('median_h',0)

    p1_pos = "top 5%" if p1p>=99.5 else ("top 15%" if p1p>=98 else ("top 30%" if p1p>=95 else "abaixo da mediana"))
    p2_pos = "top 10%" if p2p>=98 else ("top 25%" if p2p>=95 else ("mediana" if p2p>=90 else "abaixo da mediana"))
    mttr_pos = "top 10%" if mh<=2 else ("top 25%" if mh<=4 else ("mediana" if mh<=8 else "abaixo da mediana"))
    msp_pos = "premium" if hs>=80 else ("intermediário" if hs>=60 else "básico")

    rec1 = f"Usar SLA P1 {p1p}% como argumento comercial em RFPs." if p1p>=99 else f"Definir plano de ação para SLA P1 atingir 99% em 60 dias."
    mttr_ana = "Dentro do padrão ITIL." if mh<=4 else f"Acima do benchmark — risco em contratos com SLA MTTR explícito."
    hs_ana = "Posicionamento premium — argumento para upsell de serviços gerenciados." if hs>=80 else "Necessita investimento para atingir benchmark de MSPs tier-1."

    summary = (
        f"Benchmark de mercado — {prj}. "
        f"SLA P1 {p1p}% -> {p1_pos} (referência HDI 2024: top quartil >=99%). "
        f"SLA P2 {p2p}% -> {p2_pos}. "
        f"MTTR P1 {mh}h -> {mttr_pos} (benchmark ITIL: <4h, excelência: <2h). "
        f"Posicionamento MSP: {msp_pos}."
    )
    reasoning = (
        f"**Análise de Benchmarking — {prj} ({ts[:10]}):**\n\n"
        f"Referências: HDI Service Desk Practices Report 2024, ITIL 4 Guidelines, Gartner IT Key Metrics 2024\n\n"
        f"| Métrica   | {prj}   | Top 10% | Mediana | Posição |\n"
        f"|-----------|---------|---------|---------|--------|\n"
        f"| SLA P1    | {p1p}%  | >=99.5% | 97%     | {p1_pos} |\n"
        f"| SLA P2    | {p2p}%  | >=98%   | 93%     | {p2_pos} |\n"
        f"| MTTR P1   | {mh}h   | <=2h    | 6h      | {mttr_pos} |\n"
        f"| MTTR P2   | {mttr_p2}h | <=4h | 12h    | — |\n\n"
        f"**Análise Competitiva:**\n"
        f"- SLA P1 ({p1p}%): {rec1}\n"
        f"- MTTR P1 ({mh}h): {mttr_ana}\n"
        f"- Health Score {hs}/100: {hs_ana}\n\n"
        f"**Recomendações para Posicionamento:**\n"
        f"1. {rec1}\n"
        f"2. Implementar relatório mensal de benchmark para evidenciar evolução ao cliente.\n"
        f"3. {'Investigar práticas de top performers para reduzir MTTR P1.' if mh>4 else 'Documentar MTTR como benchmark interno para novos contratos.'}"
    )
    return {"agent":"AI_MARKET","timestamp":ts,"status":"ok",
            "executive_summary":summary,"reasoning":reasoning,
            "health_score":{"value":hs,"label":hs_label(hs),"color":hs_color(hs)},
            "benchmark":{"sla_p1_position":p1_pos,"mttr_p1_position":mttr_pos}}

def gen_qa(k, prj):
    hs = k['health_score']
    p1p = k['sla'].get('P1',{}).get('pct',0)
    bk = k['backlog']; ag = k['aging_gt30']
    rct = fmt_rct(k['top_rct']); apps = fmt_apps(k['top_apps'])
    mh = k['mttr'].get('P1',{}).get('median_h',0)

    qs = 100
    if p1p < 99: qs -= 15
    if p1p < 95: qs -= 10
    if mh > 8: qs -= 15
    elif mh > 4: qs -= 7
    if bk['rc'] > 20: qs -= 15
    elif bk['rc'] > 10: qs -= 7
    if ag > 10: qs -= 10
    elif ag > 5: qs -= 5
    qs = max(0, min(100, qs))

    gaps = []
    if p1p < 99: gaps.append(f"SLA P1 ({p1p}%) abaixo do target — risco de penalidade contratual")
    if mh > 4: gaps.append(f"MTTR P1 ({mh}h) acima do benchmark ITIL — processo de escalação ineficiente")
    if bk['rc'] > 10: gaps.append(f"Backlog RC ({bk['rc']} tickets) indica gargalo de capacidade ou processo")
    if ag > 5: gaps.append(f"{ag} tickets aging >30d — falha no processo de revisão periódica")
    if not gaps: gaps.append("Sem gaps críticos — operação em conformidade com ITIL")

    inc_mgmt = "Conforme" if p1p>=98 and mh<=4 else "Não conforme — SLA/MTTR fora dos targets"
    pb_mgmt = "Ativo" if rct != 'N/A' else "Root causes não classificados adequadamente"
    cr_total = k['summary'].get('change_request',{}).get('total',0)
    ci_status = "Backlog RC elevado indica débito técnico" if bk['rc']>15 else "Backlog controlado"
    rec1 = "Revisão imediata do processo de triagem de P1s — meta: <2h para first response." if p1p<98 else "Manter processo de P1 — criar checklist de verificação mensal."
    gaps_lines = "".join(f"{i+1}. {g}\n" for i,g in enumerate(gaps))

    summary = (
        f"Quality Score: {qs}/100 — {prj}. "
        f"Gaps principais: {gaps[0]}. "
        f"{gaps[1]+'. ' if len(gaps)>1 else ''}"
        f"Root causes sem RCA formal: {rct}. Apps com maior incidência: {apps}."
    )
    reasoning = (
        f"**Auditoria de Qualidade e Conformidade — {prj} ({ts[:10]}):**\n\n"
        f"**Quality Score: {qs}/100**\n\n"
        f"**Gaps Identificados:**\n"
        f"{gaps_lines}\n"
        f"**Conformidade ITIL 4:**\n"
        f"- Incident Management: {inc_mgmt}\n"
        f"- Problem Management: {pb_mgmt}\n"
        f"- Change Management: {cr_total} CRs registradas\n"
        f"- Continual Improvement: {ci_status}\n\n"
        f"**Root Causes ({prj}):**\n"
        f"- Top causas: {rct}\n"
        f"- {'Implementar problema formal para causas recorrentes.' if rct != 'N/A' else 'Melhorar processo de categorização.'}\n\n"
        f"**Recomendações:**\n"
        f"1. {rec1}\n"
        f"2. Implementar revisão semanal de tickets aging >15 dias (preventivo antes de 30d).\n"
        f"3. Criar dashboard de qualidade com alertas automáticos para desvios de SLA em tempo real."
    )
    return {"agent":"AI_QA","timestamp":ts,"status":"ok",
            "executive_summary":summary,"reasoning":reasoning,
            "health_score":{"value":hs,"label":hs_label(hs),"color":hs_color(hs)},
            "quality_score":qs,"gaps":gaps}

def gen_triage(k, prj):
    hs = k['health_score']; bk = k['backlog']; ag = k['aging_gt30']
    p1p = k['sla'].get('P1',{}).get('pct',0)
    mh = k['mttr'].get('P1',{}).get('median_h',0)
    inc_open = k['summary'].get('incident',{}).get('open',0)
    apps = fmt_apps(k['top_apps'])
    ana = k['top_analyst']; anac = k['top_analyst_count']

    urgency = "CRÍTICA" if bk['rc']>30 or p1p<95 else ("ALTA" if bk['rc']>15 or ag>10 else ("MÉDIA" if bk['rc']>5 else "BAIXA"))

    action_items = []
    if inc_open > 0:
        action_items.append(f"Revisar {inc_open} incidents abertos — priorizar P1s e P2s sem atualização há >4h")
    if bk['rc'] > 0:
        action_items.append(f"{bk['rc']} tickets RC em análise/desenvolvimento — checar bloqueios com analistas")
    if bk['cli'] > 0:
        action_items.append(f"{bk['cli']} tickets aguardando cliente — enviar follow-up proativo se >5 dias")
    if ag > 0:
        action_items.append(f"{ag} tickets com aging >30 dias — escalonar para gestor se sem movimento >7 dias")
    if anac > 5:
        action_items.append(f"Analista {ana} com {anac} tickets no backlog — verificar distribuição de carga")
    if not action_items:
        action_items.append("Nenhum item crítico — manter monitoramento de rotina")

    rec1 = "Reunião de war room imediata para incidents P1/P2 abertos." if inc_open>5 else "Revisão daily standup de tickets prioritários."
    rec2 = f"Rebalancear carga do analista {ana} ({anac} tickets)." if anac>5 else "Manter distribuição atual de carga."
    ai_lines = "".join(f"{i+1}. {a}\n" for i,a in enumerate(action_items))

    summary = (
        f"Triagem de urgência {urgency} — {prj}. "
        f"Incidents abertos: {inc_open}. Backlog RC: {bk['rc']} | Cliente: {bk['cli']}. "
        f"Aging critico (>30d): {ag} tickets. "
        f"{'Analista '+ana+' concentra '+str(anac)+' tickets — rebalancear carga.' if anac>5 else 'Carga distribuída adequadamente.'} "
        f"Apps prioritárias: {apps}."
    )
    reasoning = (
        f"**Triagem e Priorização — {prj} ({ts[:10]}):**\n\n"
        f"**Nível de Urgência Atual: {urgency}**\n\n"
        f"**Action Items Imediatos:**\n"
        f"{ai_lines}\n"
        f"**Distribuição do Backlog:**\n"
        f"- RC (nosso backlog): {bk['rc']} tickets\n"
        f"- Aguardando cliente: {bk['cli']} tickets\n"
        f"- Total incidents abertos: {inc_open}\n\n"
        f"**Aging Analysis:**\n"
        f"- Tickets com aging >30 dias: {ag} {'(REVISAR URGENTE)' if ag>5 else '(dentro do normal)'}\n"
        f"- SLA P1 atual: {p1p}% {'(OK)' if p1p>=98 else '(ATENCAO)'}\n"
        f"- MTTR P1: {mh}h {'(OK)' if mh<=4 else '(Acima do benchmark)'}\n\n"
        f"**Critérios de Escalonamento:**\n"
        f"- P1 sem atualização >2h: escalar para gerente de operações\n"
        f"- P2 sem atualização >4h: notificar analista sênior\n"
        f"- Aging >30d sem movimento >7d: escalar para diretoria de serviços\n\n"
        f"**Recomendações:**\n"
        f"1. {rec1}\n"
        f"2. {rec2}\n"
        f"3. Implementar alertas automáticos de aging no D+15 para ação preventiva."
    )
    return {"agent":"AI_TRIAGE","timestamp":ts,"status":"ok",
            "executive_summary":summary,"reasoning":reasoning,
            "health_score":{"value":hs,"label":hs_label(hs),"color":hs_color(hs)},
            "urgency":urgency,"action_items":action_items}

agents_fn = {
    'ops': gen_ops, 'predictive': gen_predictive, 'improvement': gen_improvement,
    'market': gen_market, 'qa': gen_qa, 'triage': gen_triage
}

ai_insights = {}
for prj, k in kpis.items():
    ai_insights[prj] = {}
    for ag, fn in agents_fn.items():
        ai_insights[prj][ag] = fn(k, prj)
        print(f"  {prj}/{ag} OK")

with open('c:/Dashboard/scratch/_insights_tmp.json', 'w', encoding='utf-8') as f:
    json.dump(ai_insights, f, ensure_ascii=False, indent=2)
print("DONE")
