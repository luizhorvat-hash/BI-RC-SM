import pandas as pd
from pathlib import Path

def inspect():
    csv_path = Path("input/tickets.csv")
    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')
        if len(df.columns) < 5:
            df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig')
        
        # Look for the row where Summary contains 106311
        matches = df[df['Summary'].astype(str).str.contains("106311", na=False)]
        if not matches.empty:
            print("Row for 106311:")
            row = matches.iloc[0]
            for col in df.columns:
                print(f"  {col}: {row[col]}")
        else:
            print("106311 not found in Summary (weird, previous script found it)")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect()
