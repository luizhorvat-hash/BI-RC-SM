import pandas as pd
from pathlib import Path

csv_path = Path(r"c:\Dashboard\input\tickets.csv")
df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig', low_memory=False)

# Normalizar colunas
df.columns = [str(c).strip() for c in df.columns]
df['Severity'] = df['Severity'].fillna('unknown').astype(str).str.lower().str.strip()
df['Project Name'] = df['Project Name'].fillna('Unknown').astype(str).str.strip()
df['Status'] = df['Status'].fillna('unknown').astype(str).str.lower().str.strip()

# Filtro Farmatodo
farmatodo = df[df['Project Name'] == 'Farmatodo'].copy()

# Status de "aberto" (não fechado, não resolvido, não rejeitado)
OPEN_STATUSES_NEG = {"closed", "resolved", "rejected"}
farmatodo['Is_Open'] = ~farmatodo['Status'].isin(OPEN_STATUSES_NEG)

# Encontrar Problems abertos
open_problems = farmatodo[(farmatodo['Severity'] == 'problem') & (farmatodo['Is_Open'])]

print(f"Total de tickets Farmatodo: {len(farmatodo)}")
print(f"Total de Problems abertos Farmatodo: {len(open_problems)}")

if len(open_problems) > 0:
    print("\nProblems Abertos e Incidentes vinculados:")
    for _, p in open_problems.iterrows():
        pid = str(int(p['Ticket'])).lstrip('0')
        # Buscar incidentes vinculados a este problema
        # Nota: Incidentes podem estar em outros projetos se forem vinculados, 
        # mas geralmente buscamos no mesmo contexto.
        linked_incidents = df[(df['Severity'] == 'incident') & (df['Problem'].astype(str).str.lstrip('0') == pid)]
        print(f"- Problem {pid} (Status: {p['Status']}): {len(linked_incidents)} incidentes vinculados")
        if len(linked_incidents) > 0:
            for _, inc in linked_incidents.iterrows():
                 print(f"  * Incident {inc['Ticket']} (Status: {inc['Status']})")
else:
    # Talvez existam problemas FECHADOS com incidentes?
    closed_problems = farmatodo[(farmatodo['Severity'] == 'problem')]
    print(f"\nTotal de Problems (todos status) Farmatodo: {len(closed_problems)}")
    for _, p in closed_problems.head(10).iterrows():
        pid = str(int(p['Ticket'])).lstrip('0')
        linked_incidents = df[(df['Severity'] == 'incident') & (df['Problem'].astype(str).str.lstrip('0') == pid)]
        if len(linked_incidents) > 0:
            print(f"- Problem {pid} (Status: {p['Status']}): {len(linked_incidents)} incidentes vinculados")
