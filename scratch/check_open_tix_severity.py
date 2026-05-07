
import pandas as pd

try:
    df = pd.read_csv('input/tickets.csv', sep=';', encoding='latin1')
    
    closed_status = ['closed', 'resolved', 'rejected', 'rejeitado', 'fechado', 'resolvido']
    open_tix = df[~df['Status'].str.lower().isin(closed_status)]
    
    print("Distribuição de Severity para tickets ABERTOS:")
    print(open_tix['Severity'].value_counts())
    
    # Detalhar status dos Incidents abertos
    print("\nStatus dos INCIDENTS abertos:")
    incidents = open_tix[open_tix['Severity'] == 'incident']
    if not incidents.empty:
        print(incidents['Status'].value_counts())
        print("\nAnalistas atribuídos aos Incidents abertos:")
        print(incidents['assigned'].value_counts())
    else:
        print("Nenhum Incident aberto.")

    # Detalhar status dos User Requests abertos
    print("\nStatus dos USER_REQUESTS abertos:")
    urs = open_tix[open_tix['Severity'] == 'user_request']
    if not urs.empty:
        print(urs['Status'].value_counts())
    else:
        print("Nenhuma User Request aberta.")

except Exception as e:
    print(f"Erro: {e}")
