
found = False
with open('input/tickets.csv', 'r', encoding='utf-8-sig') as f:
    header = f.readline()
    print("Header Count:", len(header.split(';')))
    for line in f:
        if ';112735;' in line:
            print("Linha encontrada:")
            print(line.strip())
            fields = line.split(';')
            print(f"Número de campos na linha: {len(fields)}")
            found = True
            break
if not found:
    print("Ticket 112735 não encontrado!")
