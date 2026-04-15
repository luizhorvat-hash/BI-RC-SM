# 🚀 Guia de Migração do Service Management Dashboard (SMD)

Este guia contém os passos para configurar o Dashboard no seu computador pessoal.

## 1. Pré-requisitos
Instale os seguintes componentes no seu PC novo:
- **Python 3.10+**: [Download aqui](https://www.python.org/downloads/)
- **Git**: [Download aqui](https://git-scm.com/downloads)
- **Ollama**: [Download aqui](https://ollama.com/) (Após instalar, rode o comando `ollama run llama3.2`)

## 2. Preparação dos Arquivos
### Via GitHub (Código)
1. Abra o terminal (PowerShell ou CMD).
2. Clone o repositório:
   ```bash
   git clone https://github.com/luizhorvat-hash/SM-Dashboard
   cd SM-Dashboard
   ```

### Via Transferência Manual (Dados Sensíveis)
Como o GitHub ignora dados sensíveis, você precisa copiar manualmente do PC antigo para o novo:
1.  **Pasta `input/`**: Copie os arquivos `tickets.csv` e `TimesheetsCMSMonthly.xls`.
2.  **Arquivo `.env`**: Copie este arquivo para a raiz do projeto (contém suas chaves de API).

## 3. Instalação de Dependências
No terminal, dentro da pasta do projeto, execute:
```bash
pip install pandas schedule requests xlrd
```

## 4. Executando o Dashboard
Para atualizar os dados e gerar novos insights de IA:
```bash
python smd_agent.py
```
O arquivo `data.js` será gerado/atualizado. Depois, basta abrir o `SM_DASH.html` no seu navegador favorito.

---
## Dicas de Performance
- O agendador está configurado no arquivo `smd_build.py` (ou via comandos no dashboard).
- Se a IA local (Ollama) estiver lenta, o sistema usará automaticamente sua chave da Anthropic como backup (fallback).
