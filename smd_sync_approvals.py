import os
import json
import re
import sys

# ─────────────────────────────────────────────────────────────────────────────
# SMD SYNC APPROVALS (HITL Governance)
# Este script sincroniza as decisões de curadoria humana (Aprovado/Rejeitado)
# do Dashboard de volta para o arquivo data.js.
# ─────────────────────────────────────────────────────────────────────────────

DATA_FILE = r'C:\Dashboard\data.js'
DECISIONS_FILE = r'C:\Dashboard\smd_ai_decisions.json'

def sync():
    print("🚀 Iniciando sincronização de governança (HITL)...")

    if not os.path.exists(DECISIONS_FILE):
        print(f"❌ Erro: Arquivo de decisões não encontrado: {DECISIONS_FILE}")
        print("💡 No Dashboard, exporte as decisões para este arquivo antes de rodar o script.")
        return

    try:
        with open(DECISIONS_FILE, 'r', encoding='utf-8') as f:
            decisions = json.load(f)
    except Exception as e:
        print(f"❌ Erro ao ler decisões: {e}")
        return

    if not os.path.exists(DATA_FILE):
        print(f"❌ Erro: data.js não encontrado em {DATA_FILE}")
        return

    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    updated = False
    new_lines = []
    
    # Regex para identificar a linha do AI_INSIGHTS
    # Exemplo: var AI_INSIGHTS = {...};
    ai_pattern = re.compile(r'^var AI_INSIGHTS\s*=\s*(.*);')

    for line in lines:
        match = ai_pattern.match(line.strip())
        if match:
            try:
                ai_data = json.loads(match.group(1))
                
                # Aplicar decisões
                for agent_key, status in decisions.items():
                    if agent_key in ai_data:
                        # Converte status (approved/rejected) para booleano no campo 'approved'
                        # E mantém o campo 'status' como 'ok' se estiver ok
                        is_approved = (status == 'approved')
                        ai_data[agent_key]['approved'] = is_approved
                        print(f"✅ Agente '{agent_key}': Status definido como {'APROVADO' if is_approved else 'REJEITADO'}")
                
                new_line = f"var AI_INSIGHTS = {json.dumps(ai_data, ensure_ascii=False)};\n"
                new_lines.append(new_line)
                updated = True
            except Exception as e:
                print(f"⚠️ Erro ao processar JSON da linha AI_INSIGHTS: {e}")
                new_lines.append(line)
        else:
            new_lines.append(line)

    if updated:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print(f"✨ Sincronização concluída com sucesso! {len(decisions)} decisões aplicadas ao data.js.")
    else:
        print("⚠️ Aviso: A variável AI_INSIGHTS não foi encontrada ou não pôde ser atualizada no data.js.")

if __name__ == "__main__":
    sync()
