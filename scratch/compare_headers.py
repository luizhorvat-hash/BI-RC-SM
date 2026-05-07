
import pandas as pd

def check_file(path):
    try:
        df = pd.read_csv(path, sep=';', encoding='utf-8-sig', nrows=0)
    except:
        df = pd.read_csv(path, sep=';', encoding='latin-1', nrows=0)
    return df.columns.tolist()

files = [
    'input/tickets.csv',
    'downloads/processed/Incidents_Chanel2026-05-07.csv',
    'downloads/processed/Farmacia_Arrocha.csv'
]

for f in files:
    print(f"\n{f}:")
    cols = check_file(f)
    print(cols)
