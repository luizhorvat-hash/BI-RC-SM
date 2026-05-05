# Guia de Instalação: SMD Dashboard v2.0

Este guia descreve como instalar e configurar o Service Management Dashboard em um novo ambiente.

## 1. Pré-requisitos

- **Python 3.10+** instalado (Certifique-se de marcar "Add Python to PATH").
- **Instalação Automática**: Basta executar o arquivo `install_deps.bat` incluído no pacote.
- **Instalação Manual**:
  ```bash
  pip install pandas openpyxl lxml
  ```
- (Opcional) **Ollama** instalado localmente se desejar usar as funcionalidades de IA local.

## 2. Estrutura de Pastas

O projeto deve seguir esta estrutura básica:
- `/input`: Onde o arquivo `Tickets.csv` será gerado.
- `/downloads`: Onde você deve colocar os exports do Mantis.
- `/Resultados`: Onde os dados processados serão salvos.
- `/DOcs`: Documentação e arquivos de suporte (ex: `Resource Level.xlsx`).

## 3. Configuração de Projetos

O Dashboard é genérico. Para mapear os nomes dos projetos do Mantis para nomes amigáveis ou consolidar projetos do Timesheet, edite o arquivo:
**`smd_projects.json`**

### Exemplo de Configuração:
```json
{
  "DE_PARA_PROJETOS": {
    "NOME_NO_MANTIS": "Nome Exibido"
  },
  "TIMESHEET_PROJECT_MAP": {
    "PROJETO_TS_1": "Projeto Final",
    "PROJETO_TS_2": "Projeto Final"
  },
  "MANUAL_RESOURCE_FIXES": {
    "nome do analista": "Career Grade"
  }
}
```

## 4. Fluxo de Uso

1. **Exportar Dados**: Baixe os CSVs do Mantis e coloque na pasta `downloads`.
2. **Mesclar Dados**:
   ```bash
   python smd_merge.py
   ```
   Isso criará o arquivo `input/Tickets.csv` consolidado.
3. **Gerar Dashboard**:
   ```bash
   python smd_build.py --no-agents
   ```
   Isso processará os dados e atualizará o arquivo `data.js`.
4. **Visualizar**: Abra o arquivo `SM_DASH.html` em qualquer navegador moderno.

## 5. IA e Insights (Opcional)

Se tiver configurado o Ollama ou uma chave de API do Gemini no arquivo `.env`, você pode rodar os agentes de IA para obter insights:
```bash
python smd_build.py
```

## 6. Ferramentas de Análise (BI)

Para gerar relatórios detalhados de esforço e crescimento por projeto (Top Tickets e Resumo Mensal), utilize:
```bash
python smd_analyze_project.py "Nome do Projeto"
```
Exemplo: `python smd_analyze_project.py "Arrocha"`

---
*Versão Portátil 3.1 | Arrocha ITSM*
