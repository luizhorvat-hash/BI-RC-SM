# SMD Dashboard v6 — Guia de Instalação e Uso
**Arrocha ITSM | 2026**

---

## Índice

1. [O que você vai precisar](#1-o-que-você-vai-precisar)
2. [Instalar o Python](#2-instalar-o-python)
3. [Instalar as bibliotecas](#3-instalar-as-bibliotecas)
4. [Criar a estrutura de pastas](#4-criar-a-estrutura-de-pastas)
5. [Copiar os arquivos do dashboard](#5-copiar-os-arquivos-do-dashboard)
6. [Exportar os CSVs do Mantis](#6-exportar-os-csvs-do-mantis)
7. [Fazer o merge dos CSVs](#7-fazer-o-merge-dos-csvs)
8. [Gerar o dashboard](#8-gerar-o-dashboard)
9. [Abrir o dashboard](#9-abrir-o-dashboard)
10. [Configurar por projeto](#10-configurar-por-projeto)
11. [Automatizar com Task Scheduler](#11-automatizar-com-task-scheduler)
12. [Exportar o Timesheet (opcional)](#12-exportar-o-timesheet-opcional)
13. [Uso diário resumido](#13-uso-diário-resumido)
14. [Solução de problemas](#14-solução-de-problemas)

---

## 1. O que você vai precisar

### Arquivos do dashboard (receber de quem já usa)

| Arquivo | Tamanho | Função |
|---|---|---|
| `arrocha_dashboard_v6.html` | ~5.7 MB | O dashboard — abre no browser |
| `smd_build.py` | ~27 KB | Processa os CSVs e atualiza o dashboard |
| `smd_merge.py` | ~10 KB | Junta os CSVs dos projetos em um único arquivo |
| `AGENTS.md` | ~2 KB | Definição e governança dos agentes de IA |

### Programas a instalar

| Programa | Obrigatório? |
|---|---|
| **Python 3.10 ou superior** | ✅ Sim |
| **Google Chrome** ou **Microsoft Edge** | ✅ Sim (para abrir o dashboard) |

> O Python é gratuito e o único instalador necessário. O Chrome/Edge já costumam vir instalados no Windows.

---

## 2. Instalar o Python

**Passo 1** — Acessar https://python.org/downloads e baixar a versão mais recente

**Passo 2** — Executar o instalador

> ⚠️ **ATENÇÃO:** Na primeira tela do instalador, marcar obrigatoriamente a opção:
> **"Add Python to PATH"** (ou "Add python.exe to PATH")
> Se não marcar essa opção, os comandos não vão funcionar no terminal.

**Passo 3** — Clicar em **Install Now** e aguardar

**Passo 4** — Verificar se funcionou: abrir o **Prompt de Comando** (CMD) e digitar:
```cmd
python --version
```
O resultado deve ser algo como `Python 3.12.3`. Se aparecer erro, o Python não foi instalado corretamente — refazer o Passo 2 marcando "Add to PATH".

---

## 3. Instalar as bibliotecas

Com o **Prompt de Comando** (CMD) aberto, executar o comando abaixo e aguardar:

```cmd
pip install pandas openpyxl lxml
```

Vai aparecer uma sequência de downloads e instalações. Quando retornar ao prompt (`C:\>`), está pronto.

**Verificar se funcionou:**
```cmd
python -c "import pandas; print('OK')"
```
Deve aparecer `OK`. Se aparecer erro, repetir o comando do pip install.

---

## 4. Criar a estrutura de pastas

Abrir o **Prompt de Comando** e executar:

```cmd
mkdir C:\Dashboard
mkdir C:\Dashboard\input
mkdir C:\Dashboard\input\backups
mkdir C:\Dashboard\builds
```

A estrutura final ficará assim:

```
C:\Dashboard\
│
├── arrocha_dashboard_v6.html   ← o dashboard
├── smd_build.py                ← pipeline de dados
├── smd_merge.py                ← merge dos CSVs
├── smd_merge.log               ← log gerado automaticamente
├── smd_build.log               ← log gerado automaticamente
├── builds\                     ← versões anteriores (gerado automaticamente)
│
└── input\
    ├── Tickets.csv             ← gerado pelo smd_merge.py
    ├── TimesheetsCMSMonthly.xls  ← opcional (timesheet do CMS)
    └── backups\                ← backups automáticos do Tickets.csv
```

---

## 5. Copiar os arquivos do dashboard

Copiar os 3 arquivos recebidos para `C:\Dashboard\`:

```
arrocha_dashboard_v6.html  →  C:\Dashboard\arrocha_dashboard_v6.html
smd_build.py               →  C:\Dashboard\smd_build.py
smd_merge.py               →  C:\Dashboard\smd_merge.py
```

---

## 6. Exportar os CSVs do Mantis

No **Mantis**, exportar um CSV separado para cada projeto com as seguintes configurações:

- Formato: **CSV**
- Separador: **ponto e vírgula ( ; )**
- Encoding: **UTF-8**

**Padrão obrigatório do nome do arquivo:**
```
Incidents_<NomeDoProjeto><AAAA-MM-DD>.csv
```

**Exemplos de nomes corretos:**
```
Incidents_Chanel2026-04-08.csv
Incidents_Farmacia Arrocha2026-04-08.csv
Incidents_Farmatodo2026-04-08.csv
Incidents_GDN2026-04-08.csv
Incidents_Tata2026-04-08.csv
```

**Salvar todos os arquivos exportados em:**
```
C:\Users\luiz.horvat\Downloads\
```

> O script detecta automaticamente todos os arquivos nessa pasta que seguem o padrão de nome. Não é necessário renomear ou mover — basta salvar lá e rodar o script.

---

## 7. Fazer o merge dos CSVs

Abrir o **Prompt de Comando** e executar:

```cmd
python C:\Dashboard\smd_merge.py
```

O script vai:
1. Mostrar todos os arquivos encontrados na pasta Downloads
2. Pedir confirmação antes de salvar
3. Fazer backup do `Tickets.csv` anterior (se existir)
4. Juntar todos os arquivos e salvar em `C:\Dashboard\input\Tickets.csv`

**Exemplo do que aparece no terminal:**

```
📂 Arquivos encontrados em C:\Users\luiz.horvat\Downloads:

  ARQUIVO                                       PROJETO           DATA
  --------------------------------------------- ----------------- ----------
  Incidents_Chanel2026-04-08.csv                Chanel            2026-04-08
  Incidents_Farmacia Arrocha2026-04-08.csv      Farmacia Arrocha  2026-04-08
  Incidents_Farmatodo2026-04-08.csv             Farmatodo         2026-04-08
  Incidents_GDN2026-04-08.csv                   GDN               2026-04-08
  Incidents_Tata2026-04-08.csv                  Tata              2026-04-08

  Total: 5 arquivo(s)

──────────────────────────────────────────────────────────────
  Será gerado: C:\Dashboard\input\Tickets.csv

  Confirmar merge? [S/n]: S

✅ Merge concluído com sucesso!
   18234 tickets | 5 projetos
   Salvo em: C:\Dashboard\input\Tickets.csv
```

---

## 8. Gerar o dashboard

Após o merge, executar:

```cmd
python C:\Dashboard\smd_build.py --no-agents
```

O script processa o `Tickets.csv`, calcula todos os KPIs e atualiza o `arrocha_dashboard_v6.html`.

**Exemplo do que aparece:**
```
[INFO] CSV: C:\Dashboard\input\tickets.csv (4164kb)
[INFO] Reconstruindo dados no HTML...
[INFO] HTML OK: 18234 tickets | 5 projetos | anos: ['2019', ..., '2026']
```

O processo leva cerca de **10 segundos**.

---

## 9. Abrir o dashboard

Abrir o arquivo diretamente no browser:

```cmd
start C:\Dashboard\arrocha_dashboard_v6.html
```

Ou navegar até `C:\Dashboard\` pelo Explorer e dar duplo clique no arquivo `arrocha_dashboard_v6.html`.

> Se o dashboard abrir com dados antigos, pressionar **Ctrl+Shift+R** (força recarregamento sem cache).

---

## 10. Configurar por projeto

Na primeira vez que abrir o dashboard, cada projeto terá configurações padrão de SLA e Ranges. Para personalizar conforme o contrato de cada projeto:

**Passo 1** — Selecionar o projeto no filtro principal (ex: `GDN`)

**Passo 2** — Clicar na aba **Config**

**Passo 3** — Ajustar conforme o contrato:

| Seção | O que configurar |
|---|---|
| **Limites de SLA** | Tempo máximo (minutos) e meta (%) por prioridade P1/P2/P3/P4 |
| **Faixas de Volume (Man-Days)** | Até 8 faixas de volume de tickets e seu esforço em dias |
| **Alertas KPI** | Thresholds para alertas automáticos na aba Atenção |
| **Dias sem atualização** | Quantos dias sem update considera um ticket em alerta |

**Passo 4** — Clicar em **Salvar** em cada seção alterada

> ⚠️ As configurações ficam salvas **no browser deste computador** (localStorage). Se abrir em outro computador, precisará configurar novamente.

---

## 11. Automatizar com Task Scheduler

Para que o dashboard seja atualizado automaticamente todo dia sem precisar rodar os scripts manualmente.

**Opção A — Merge + Build automático (recomendado)**

Abrir o **Prompt de Comando como Administrador** e executar:

```cmd
schtasks /create /tn "SMD Merge+Build 07h" /tr "cmd /c python C:\Dashboard\smd_merge.py --auto && python C:\Dashboard\smd_build.py --no-agents" /sc daily /st 07:00 /f

schtasks /create /tn "SMD Merge+Build 15h" /tr "cmd /c python C:\Dashboard\smd_merge.py --auto && python C:\Dashboard\smd_build.py --no-agents" /sc daily /st 15:00 /f
```

> O `--auto` no merge pula a confirmação. O `&&` faz o build rodar apenas se o merge tiver sucesso.

**Pré-requisito para funcionar:** os CSVs do Mantis precisam ser exportados e salvos na pasta Downloads **antes** do horário agendado (07h ou 15h).

**Opção B — Só o Build automático (se o merge for manual)**

```cmd
schtasks /create /tn "SMD Build 07h" /tr "python C:\Dashboard\smd_build.py --no-agents" /sc daily /st 07:00 /f
schtasks /create /tn "SMD Build 15h" /tr "python C:\Dashboard\smd_build.py --no-agents" /sc daily /st 15:00 /f
```

**Verificar tarefas criadas:**
```cmd
schtasks /query /tn "SMD Merge+Build 07h"
```

**Remover uma tarefa (se precisar):**
```cmd
schtasks /delete /tn "SMD Merge+Build 07h" /f
```

---

## 12. Exportar o Timesheet (opcional)

O Timesheet ativa as seções de **Horas por Ticket** e **Analistas** nas abas de Incident, User Request e Problem.

**Passo 1** — No sistema CMS, exportar o relatório `TimesheetsCMSMonthly`

**Passo 2** — Salvar o arquivo como:
```
C:\Dashboard\input\TimesheetsCMSMonthly.xls
```

**Passo 3** — Rodar o build normalmente:
```cmd
python C:\Dashboard\smd_build.py --no-agents
```

O script detecta o arquivo automaticamente e injeta os dados no dashboard.

> Se o arquivo não existir, o dashboard funciona normalmente — apenas as seções de timesheet ficam vazias.

---

## 13. Uso diário resumido

### Rotina completa (com exportação manual dos CSVs)

```
1. Exportar CSVs do Mantis → salvar em C:\Users\luiz.horvat\Downloads\
2. Exportar TimesheetsCMSMonthly.xls → salvar em C:\Dashboard\input\  (opcional)
3. Abrir CMD e executar:

   python C:\Dashboard\smd_merge.py --auto && python C:\Dashboard\smd_build.py --no-agents

4. Abrir/recarregar C:\Dashboard\arrocha_dashboard_v6.html no browser
```

### Comandos de referência

| Comando | Quando usar |
|---|---|
| `python C:\Dashboard\smd_merge.py` | Merge interativo com confirmação |
| `python C:\Dashboard\smd_merge.py --auto` | Merge sem confirmação |
| `python C:\Dashboard\smd_merge.py --dry-run` | Ver quais arquivos seriam processados sem salvar |
| `python C:\Dashboard\smd_build.py --no-agents` | Gerar/atualizar o dashboard |
| `python C:\Dashboard\smd_build.py --validate` | Verificar se o CSV está correto sem gerar |

---

## 14. Solução de problemas

| Problema | Causa | Solução |
|---|---|---|
| `python` não reconhecido no CMD | Python não instalado ou não está no PATH | Reinstalar Python marcando **"Add Python to PATH"** |
| `ModuleNotFoundError: pandas` | Bibliotecas não instaladas | Executar `pip install pandas openpyxl lxml` |
| Nenhum arquivo encontrado pelo merge | CSVs com nome errado ou na pasta errada | Verificar se o nome segue `Incidents_Projeto2026-04-08.csv` e se está em `C:\Users\luiz.horvat\Downloads\` |
| `CSV nao encontrado` no build | Merge não foi executado | Executar `smd_merge.py` primeiro |
| Dashboard abre com dados antigos | Cache do browser | Pressionar **Ctrl+Shift+R** no browser |
| Timesheet não aparece | XLS ausente ou nome errado | Verificar se está em `C:\Dashboard\input\TimesheetsCMSMonthly.xls` (exatamente esse nome) |
| Erro de encoding no CSV | Mantis exportou em formato diferente | Verificar nas opções de exportação do Mantis se está em UTF-8 com separador `;` |
| Configurações do projeto sumiram | Outro browser ou computador | Reconfigurar na aba Config — cada máquina salva suas próprias configurações |
| Build demora mais de 2 minutos | CSV muito grande ou computador lento | Normal para CSVs acima de 50.000 tickets — aguardar |

---

*SMD Dashboard v6 — Arrocha ITSM*
*Última atualização: 08/04/2026*
