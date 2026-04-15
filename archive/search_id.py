import pandas as pd
from pathlib import Path

def search():
    csv_path = Path("input/tickets.csv")
    targets = ["106311", "106320", "106501", "106387", "106393", "106033"]
    
    try:
        df = pd.read_csv(csv_path, sep=';', encoding='utf-8-sig')
        if len(df.columns) < 5:
            df = pd.read_csv(csv_path, sep=',', encoding='utf-8-sig')
        
        print(f"Columns: {df.columns.tolist()}")
        
        for t in targets:
            print(f"\nSearching for {t}...")
            # Search in all columns
            found = False
            for col in df.columns:
                matches = df[df[col].astype(str).str.contains(t, na=False)]
                if not matches.empty:
                    print(f"  FOUND in column '{col}':")
                    print(f"    Project: {matches['Project Name'].values[0]}")
                    found = True
            if not found:
                print("  NOT FOUND in ANY column.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    search()
