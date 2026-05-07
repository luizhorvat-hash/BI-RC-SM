
import pandas as pd

try:
    df = pd.read_csv('input/tickets.csv', sep=';', encoding='latin1')
    
    closed_status = ['closed', 'resolved', 'rejected', 'rejeitado', 'fechado', 'resolvido']
    open_tix = df[~df['Status'].str.lower().isin(closed_status)]
    
    print(f"Total de tickets abertos: {len(open_tix)}")
    
    if not open_tix.empty:
        print("\nStatus vs Assigned em tickets ABERTOS:")
        # Mostrar contagem de tickets por Status e se tem 'assigned' preenchido
        open_tix['has_assigned'] = open_tix['assigned'].notna() & (open_tix['assigned'] != 'nan')
        summary = open_tix.groupby(['Status', 'has_assigned']).size().unstack(fill_value=0)
        print(summary)
        
        print("\nExemplo de tickets abertos com 'assigned' preenchido:")
        print(open_tix[open_tix['has_assigned']][['Ticket', 'Status', 'assigned', 'Severity']].head(10))
    
except Exception as e:
    print(f"Erro: {e}")
