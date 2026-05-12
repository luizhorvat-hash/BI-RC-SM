import pandas as pd
df = pd.read_csv('input/tickets.csv', sep=';', encoding='utf-8-sig', low_memory=False)
# Mostra os 20 tickets com maior MD
top = df.copy()
top["MD_num"] = pd.to_numeric(top["MD's"].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
print(top[top["MD_num"] > 0][["Ticket", "Project Name", "MD's", "MD_num", "Opening Date"]].sort_values("MD_num", ascending=False).head(20))
