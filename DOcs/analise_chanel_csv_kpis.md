# Análise Chanel.csv vs Dashboard Atual + Novos KPIs

## 1. Schema do CSV

**Colunas:** `Project Name, Ticket, Priority, Severity, Category, Status, Opening Date, Date of Resolution, Acknowledge SLA, Resolution SLA, Application, Environment, MD's, Problem, Country, Close Date, Closed Admin, SM Audit`

**Volumetria (334 tickets):** 169 incidents · 105 problems · 46 user_requests · 7 CRs · 6 internal · **154,74 MDs totais**.

## 2. ⚠️ Gap crítico: dados não capturados

| Coluna CSV | Estado no dashboard | Impacto |
|---|---|---|
| **`Problem`** (ID parent) | ❌ Não lido em `smd_build.py` | Sem visão de Problem Management |
| **`MD's`** (esforço real) | ❌ Não lido — dashboard usa estimativa por ranges em `effort_mds` | Simulador roda em estimativa, não em real |
| `Country` | ❌ Não lido | Sem split geo |
| `Closed Admin` | ❌ Não lido | Não distingue fechamento administrativo |
| `SM Audit` | ❌ Não lido | Sem visão de auditoria |

**Bug de normalização identificado:** Problem IDs nos incidents vêm sem zeros (`84849`); nos próprios problems vêm com (`0084849`). Precisa `lstrip('0')` no merge.

## 3. Achados quantitativos (CSV real)

### Problem Management
- **Cobertura:** 110/169 incidents (65,1%) têm Problem vinculado
- **8 incidents** apontam para Problem inexistente — data quality
- **15 problems órfãos** (abertos sem incident)
- **Ratio Problem/Incident effort = 66%** — bem acima do benchmark ITIL (20-30%); investimento alto em RC analysis vs resolução
- **TOP recorrência:** Problem `0084849` (RCIB) — 7 incidents · 5,47 MDs · ainda em `waiting_client_tests`
- **TOP esforço:** Problem `0111582` (Xstore) — 6,78 MDs (4,75 self + 2,03 inc)

### Esforço (MDs reais)
- **Por severidade:** Incident 0,42 · Problem 0,45 · **CR 3,43** (8x mais caro) · UR 0,26
- **Por priority:** P1=0,27 · P2=0,50 · P3=0,38 · **P4=0,74** (P4 consome mais que P1!)
- **Por app:** Xstore 0,55 · RCIB 0,50 · XOffice 0,38
- **57 tickets (17%) com 0 MD** — proxy de fechamento sem trabalho
- **Distribuição:** p50=0,22 · p95=1,31 · max=12,22 (super skewed)

## 4. Novos KPIs propostos

### 4.1 Cluster Problem Management (nova seção na aba Cliente)

| KPI | Fórmula | Target | Cor crítica |
|---|---|---|---|
| **Problem Coverage** | inc_com_problem / total_inc | ≥70% | <50% red |
| **Effort Ratio P/I** | MD_problems / MD_incidents | 20-30% | >50% red (sobre-investimento em RC) |
| **Top Recurrent Problem** | max(#incidents por problem) | <5 | ≥5 amber |
| **Problems Stale** | problems abertos >30d | ≤2 | >5 red |
| **Problems Órfãos** | problems sem incident | ≤5% | >15% amber |
| **MD por Recorrência** | MD_total_problem / #incidents | menor é melhor | — |

**Tabela acompanhante** "TOP 5 Problems críticos":
- Coluna: Problem ID · App · #Incidents · MD Self · MD Inc · MD Total · Status
- Ordenação: MD Total desc OU #Incidents desc (toggle)

### 4.2 Cluster Esforço Real (header da Cliente — opcional substituir simulador)

| KPI | Fórmula |
|---|---|
| **MDs Totais (mês)** | sum(MD's) no período |
| **MD/Ticket Médio** | total_md / total_tickets |
| **% Tickets sem MD** | tickets_md_zero / total |
| **MD Real vs Planejado** | (real_md − estimated_md) / estimated_md (delta do simulador) |

### 4.3 Cluster Quality (oportunidades secundárias)

- **% Closed Admin** — proxy de retrabalho/erro de classificação
- **CR Burn** — MDs gastos em change_requests vs orçamento (se houver)
- **MD por App por Mês** — heatmap para identificar app degradante

## 5. Plano de implementação

**Pré-requisito (smd_build.py):**
1. Capturar `Problem` (string normalizada — `lstrip('0')`) e `MD's` (float, parse `,` → `.`) em `_TF`/`_ROWS`.
2. Capturar `Country` e `Closed Admin` se quiser cluster Geo/Quality.
3. Pré-computar índice `D.problems[pid] = {self_md, status, incidents:[{ticket,md,pri,app}]}` para evitar varrer `_ROWS` no client.

**Frontend (SM_DASH.html, aba Cliente):**
1. Adicionar seção **"Problem Management"** com 6 KPIs + tabela TOP 5.
2. Adicionar seção **"Esforço (MDs)"** ao lado dos atuais 8 KPIs (ou nova linha 3).
3. Reusar `kpiCard` + cores semânticas (já padrão).

**Helpers JS:**
- `getProblemCoverage(prj, y, m)` → {linked, total, pct}
- `getProblemEffortRatio(prj, y, m)` → {prob_md, inc_md, ratio}
- `getTopRecurrentProblems(prj, y, m, n)` → array
- `getMDStats(prj, y, m)` → {total, avg, zero_pct, real_vs_planned}

**Sugestão de priorização:**
1. **Onda 1 (alto valor, baixo custo):** Problem Coverage + Top Recurrent table + Effort Ratio. São 1 seção que justifica a maior parte do valor.
2. **Onda 2:** MDs reais + MD/ticket por severidade.
3. **Onda 3:** Country/Closed Admin (se aplicável a outros projetos além de Chanel).
