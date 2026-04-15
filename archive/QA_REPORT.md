# SMD Dashboard — Relatório de QA (v1.0)
**Arrocha ITSM | Abril 2026**

Este relatório apresenta os resultados da auditoria de qualidade realizada no projeto, cobrindo segurança, performance, mantenabilidade e funcionalidade.

## 1. Segurança (Crítico)
> [!CAUTION]
> **Risco Identificado:** Chave de API exposta.
> O arquivo `smd_agent.py` (linha 44) contém uma chave de API (`sk-ant-...`) hardcoded no código. Esta prática é insegura e viola as políticas de governança.
> **Ação:** A chave será removida e movida para o arquivo `api_key.txt`.

## 2. Performance e Escalabilidade
- **Tamanho do Dashboard:** O arquivo `arrocha_dashboard_v6.html` possui aproximadamente **5.9 MB**. Isso ocorre devido à injeção direta de todo o histórico de tickets (`json-T`) no HTML.
- **Impacto:** O carregamento pode ser lento em navegadores mobile ou máquinas com pouca RAM.
- **Recomendação:** Considerar o desacoplamento do banco de dados em um arquivo `data.js` separado para melhorar o cache e a velocidade de carregamento.

## 3. Qualidade de Código e Mantenabilidade
- **Versonamento de IA:** Existem três scripts principais para agentes (`smd_agent.py`, `smd_agent_ollama.py`, `smd_agent_ollama_backup.py`). Há uma sobreposição de lógica.
- **Integridade:** O script `smd_agent.py` parece estar truncado ou incompleto ao final do arquivo.
- **Hardcoding:** O caminho `C:/Dashboard` está definido de forma estática em múltiplos arquivos, dificultando a portabilidade para outros diretórios ou servidores.

## 4. Funcionalidade
- **Build Pipeline:** O arquivo `smd_build.py` está bem estruturado e possui validações robustas para os CSVs do Mantis.
- **Agentes:** A lógica de agentes no Ollama é modular e bem definida, com suporte a streaming e recuperação de JSON inválido.

## 5. Próximos Passos
1. Implementar a governança via `AGENTS.md`.
2. Sanitizar `smd_agent.py`.
3. Validar a integração final dos insights de IA no Dashboard.
