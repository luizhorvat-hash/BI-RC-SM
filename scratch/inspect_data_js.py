
import json
import re

try:
    with open('data.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encontrar a definição de D.rows ou _ROWS
    # No dashboard parece ser _ROWS ou D.rows
    match = re.search(r'(_ROWS|D\.rows)\s*=\s*(\[.*?\]);', content, re.DOTALL)
    if match:
        var_name = match.group(1)
        rows_json = match.group(2)
        # Tentar carregar como JSON (pode precisar de ajustes se não for JSON puro)
        # Mas vamos apenas pegar os últimos 500 caracteres para ver a estrutura
        print(f"Variável encontrada: {var_name}")
        print("Final do array:")
        print(rows_json[-500:])
        
        # Tentar pegar os nomes das colunas (_TF)
        tf_match = re.search(r'(_TF|D\.tf)\s*=\s*(\[.*?\]);', content, re.DOTALL)
        if tf_match:
            print("\nColunas (_TF):")
            print(tf_match.group(2))
    else:
        print("Não foi possível encontrar _ROWS ou D.rows")
        # Mostrar o início do arquivo
        print("\nInício do arquivo (primeiros 500 caracteres):")
        print(content[:500])

except Exception as e:
    print(f"Erro: {e}")
