import pandas as pd
import os

res_path = r"c:\Dashboard\DOcs\Resource Level.xlsx"
if os.path.exists(res_path):
    df = pd.read_excel(res_path)
    # Procurar por Joao Manuel Soares Barbosa
    target = "Joao Manuel Soares Barbosa"
    match = df[df['Name'].str.contains("Joao Manuel Soares Barbosa", case=False, na=False)]
    if not match.empty:
        print(f"Encontrado: {match[['Name', 'Career Grade']].to_dict('records')}")
    else:
        # Tentar busca parcial
        match2 = df[df['Name'].str.contains("Barbosa", case=False, na=False)]
        print(f"Busca parcial 'Barbosa': {match2[['Name', 'Career Grade']].to_dict('records')}")
else:
    print("Arquivo não encontrado")
