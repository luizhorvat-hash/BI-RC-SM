
import pandas as pd

try:
    df = pd.read_csv('input/tickets.csv', sep=';', encoding='latin1')
    print("Colunas:", df.columns.tolist())
    
    # Verificar distribuição de status
    if 'Status' in df.columns:
        print("\nDistribuição de Status:")
        print(df['Status'].value_counts())
    
    # Verificar campo 'assigned'
    if 'assigned' in df.columns:
        print("\nTop 10 Analistas (assigned):")
        print(df['assigned'].value_counts().head(10))
        
    # Verificar cruzamento status vs assigned para tickets não fechados
    closed_status = ['closed', 'resolved', 'rejected', 'rejeitado', 'fechado', 'resolvido']
    open_tix = df[~df['Status'].str.lower().isin(closed_status)]
    
    print("\nDistribuição de Status para Tickets ABERTOS:")
    if not open_tix.empty:
        print(open_tix['Status'].value_counts())
    else:
        print("Nenhum ticket aberto encontrado!")
    
except Exception as e:
    print(f"Erro: {e}")
