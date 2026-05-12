# Diretrizes de Automação e Engenharia (SMD Dashboard)

Este arquivo define os padrões de atuação da IA e de engenharia para o projeto Service Management Dashboard, integrando os princípios de Simplicidade e Precisão.

## 1. Princípios de Engenharia (Inspirado em Karpathy)
- **Pense Antes de Codar:** Antes de qualquer modificação, explicitar premissas, trade-offs e potenciais impactos. Validar se a solução resolve a causa raiz ou apenas o sintoma.
- **Simplicidade Radical:** Priorizar a solução com o menor volume de código e menor complexidade cognitiva. Evitar abstrações prematuras, bibliotecas desnecessárias ou "flexibilidade" não solicitada.
- **Mudanças Cirúrgicas:** Modificar apenas o que é estritamente necessário para o objetivo da tarefa. Proibido refatorar código adjacente ou alterar formatação de arquivos fora do escopo do ticket, a menos que solicitado explicitamente.
- **Execução Orientada a Objetivos:** Transformar pedidos imperativos em metas declarativas com critérios de sucesso claros. Sempre validar o resultado final contra o objetivo inicial antes de encerrar a tarefa.

## 2. Governança e Dados (VLAEG)
- **Integridade YTD:** O processamento de dados deve sempre buscar o consolidado desde 01/01 do ano corrente para garantir a precisão dos KPIs anuais.
- **Determinismo:** O pipeline de dados (Merge -> Build) deve ser determinístico e auditável via logs.
- **Surgical Diffs:** Ao atualizar o Dashboard (`SM_DASH.html`), manter a integridade da estrutura CSS/JS existente, aplicando mudanças apenas nos blocos funcionais afetados.

## 3. Documentação de Decisões
- Toda mudança técnica não-trivial em scripts de processamento (`smd_merge.py`, `smd_build.py`) deve ser acompanhada de uma justificativa no comentário do código, explicando o "porquê" da escolha.

## 4. Design System (VLAEG Crystal View)
O padrão visual oficial para componentes de indicadores é o **VLAEG Crystal View**. Dentro deste sistema, o componente principal de visualização de métricas é denominado **"BOX KPI"**.

### Especificações Técnicas do "BOX KPI":
Para garantir a consistência executiva e o efeito *Premium Glass*, todo **BOX KPI** deve seguir rigorosamente:

1.  **Visual Core (Glassmorphism):**
    *   **Background:** Translúcido (`rgba(255, 255, 255, 0.03)`).
    *   **Filtro:** `backdrop-filter: blur(40px) saturate(180%)`.
    *   **Borda (Rim Light):** 1px sólido `rgba(255, 255, 255, 0.08)` para simular reflexo de luz.
2.  **Sistema de Iluminação (Glow):**
    *   Todo BOX KPI deve emanar um brilho suave de fundo (*Colored Shadow*) baseado no seu status.
    *   **Configuração Padrão:** `box-shadow: 0 0 35px [COR_STATUS] (15% opacity), 0 12px 30px rgba(0, 0, 0, 0.40)`.
3.  **Semântica de Cores (Status):**
    *   🟢 **Sucesso (Verde - `#22c55e`):** Meta atingida, saúde operacional perfeita.
    *   🟡 **Atenção (Laranja - `#f97316`):** Risco identificado ou aging em crescimento.
    *   🔴 **Crítico (Vermelho - `#ef4444`):** Bloqueio operacional ou meta não atingida.
4.  **Atmosfera (Background Orbs):**
    *   Uso obrigatório de esferas de brilho orgânicas atrás dos componentes para gerar contraste e vivacidade.
    *   **Configuração:** Opacidade de 35% e `blur(100px)`.

### Hierarquia Tipográfica:
Para garantir o contraste entre impacto executivo e legibilidade técnica, o sistema utiliza:
1.  **Eixo Executivo (Montserrat):** Títulos de cartões, valores de KPIs e cabeçalhos de seção. Transmite autoridade e modernidade.
2.  **Eixo Técnico (Inter):** Conteúdo de tabelas, subtextos e descrições. Otimizado para leitura densa de dados.

### Estrutura de Conteúdo:
*   **Topo (Header):** Título em Montserrat 700 Uppercase (`muted`) e Badge de status com ícone.
*   **Centro (Value):** Valor principal em Montserrat 300 ou 500 (em destaque) com cor vinculada ao status.
*   **Base (Footer):** Subtexto contextual ou descrição da meta em Inter 400 (`dim`).
