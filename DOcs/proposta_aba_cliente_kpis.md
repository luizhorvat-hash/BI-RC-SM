# Validação da Aba Cliente + Proposta de KPIs

## 1. Estado atual (`buildCliente`, SM_DASH.html:5579-5660)

**Header KPIs (4 cards):**
- TOTAL ABERTOS (mês)
- TOTAL FECHADOS (mês)
- SLA P1/P2 — *bug: lê apenas `sla.P1.pct`, label promete P2*
- BACKLOG ATUAL

**Conteúdo:** 3 seções (incident, user_request, problem) × 3 charts (Open×Closed 6m, Distribuição prioridade, Backlog RC vs Cliente).

**Achado importante:** `panel-sla` está com `display:none!important` (linha 389) — a aba SLA já está oculta, então **migrar os 4 cards de SLA P1/P2/P3/P4 para a aba Cliente é o caminho natural** e elimina código órfão.

## 2. Bugs / lacunas

| # | Problema | Local |
|---|---|---|
| 1 | Card "SLA P1/P2" só mostra P1 | 5604 |
| 2 | Sem comparação MoM (delta) | 5602-5605 |
| 3 | Sem MTTR (já existe no codebase, 82 refs) | — |
| 4 | `sem_upd` (backlog sem atualização) não é exibido | D.backlog[sev].*.sem_upd |
| 5 | Sem taxa de reabertura | — |
| 6 | Mistura Incident + User Request + Problem nos KPIs do topo (não dá pra ler severidade isolada) | 5667 |

## 3. Proposta

### 3.1 Migrar SLA da aba INC para Cliente

Adicionar bloco abaixo do header, antes das 3 seções:

```html
<div class="cb" style="margin-bottom:24px">
  <div class="cbt">SLA por Prioridade — <span id="cli-sla-period"></span></div>
  <div class="sla-grid" id="cli-sla-cards"></div>
</div>
```

E reusar `buildSLA()` apontando para `cli-sla-cards` (parametrizar o ID alvo, ou criar `buildSLAInto(targetId)`). Manter `getSLAFiltered()` (já respeita filtros globais).

### 3.2 Novos KPIs (header expandido para 8 cards, 2 linhas de 4)

**Linha 1 — Volumetria (com delta MoM):**
1. **TOTAL ABERTOS** + Δ% vs mês anterior
2. **TOTAL FECHADOS** + Δ% vs mês anterior
3. **THROUGHPUT LÍQUIDO** (Fechados − Abertos) — sinal de tendência do backlog
4. **BACKLOG ATUAL** + Δ vs início do mês

**Linha 2 — Qualidade & Saúde:**
5. **MTTR MÉDIO** (horas, P1+P2) — performance de resolução
6. **BACKLOG STALE** (% sem atualização > 7d) — fonte: `sem_upd / total`
7. **AGING MÉDIO BACKLOG** (dias) — idade ponderada
8. **TAXA REABERTURA** (% reabertos / fechados) — qualidade da resolução

### 3.3 Tooltip e drilldown

Aproveitar `kpiCard(label, value, note, col, tip)` — o 5º arg habilita tooltip. Cada card de SLA já tem clique → modal (`showSLADetail`); manter esse comportamento na aba Cliente.

## 4. Plano de implementação (incremental, sem big-bang)

1. **Fix imediato:** corrigir label/valor do card "SLA P1/P2" (média ponderada P1+P2 ou apenas P1 com label correto).
2. **Migração SLA:** mover `sla-grid` para `panel-cliente` e remover/limpar `panel-sla`.
3. **Adicionar KPIs em 2 ondas:**
   - Onda A (dados já existentes): Δ MoM Abertos/Fechados, Throughput, Backlog Stale (`sem_upd`).
   - Onda B (precisa cálculo novo): MTTR médio, Aging médio, Taxa de reabertura.
4. **Não mexer** em FLT-ANO/FLT-PRJ (sem badges de contagem, conforme regra do projeto).
