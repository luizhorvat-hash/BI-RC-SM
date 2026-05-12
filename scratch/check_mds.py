import pandas as pd
df = pd.read_csv('input/tickets.csv', sep=';', encoding='utf-8-sig', low_memory=False)
tids = ['112590', '112638', '112764']
# Filtro por ticket
subset = df[df['Ticket'].astype(str).str.lstrip('0').isin(tids)]
print(subset[['Ticket', "MD's", 'Severity', 'Problem']])
