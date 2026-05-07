
import pandas as pd

try:
    # Ler o tickets.csv atual
    df = pd.read_csv('input/tickets.csv', sep=';', encoding='utf-8-sig', low_memory=False)
    
    print("Colunas do tickets.csv:")
    print(df.columns.tolist())
    
    # Procurar o ticket 112735
    row = df[df['Ticket'].astype(str) == '112735']
    if not row.empty:
        print("\nDados do ticket 112735 no tickets.csv consolidado:")
        d = row.iloc[0].to_dict()
        for k, v in d.items():
            if pd.notna(v) and str(v).strip() != "":
                print(f"  {k}: {v}")
            else:
                print(f"  {k}: (EMPTY)")
    else:
        print("\nTicket 112735 não encontrado no tickets.csv consolidado!")

except Exception as e:
    print(f"Erro: {e}")
