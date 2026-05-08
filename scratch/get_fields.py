import json

path = r'c:\Dashboard\data.js'

def get_fields():
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        f.readline()
        line2 = f.readline()
        
    start = line2.find('"fields":[') + len('"fields":')
    end = line2.find(']', start) + 1
    fields_str = line2[start:end]
    fields = json.loads(fields_str)
    print(fields)

if __name__ == "__main__":
    get_fields()
