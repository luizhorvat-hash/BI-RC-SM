import json, urllib.request

url = 'http://localhost:11434/api/generate'
prompt = 'ITSM data: 4607 tickets. SLA P1=99.8%. In 2 sentences: what are the main data quality issues?'
body = json.dumps({
    'model': 'llama3.2:1b',
    'prompt': prompt,
    'stream': True,
    'options': {'temperature': 0.1, 'num_predict': 200}
}).encode()

req = urllib.request.Request(url, data=body,
      headers={'Content-Type': 'application/json'}, method='POST')
parts = []
with urllib.request.urlopen(req, timeout=60) as r:
    while True:
        line = r.readline()
        if not line: break
        line = line.decode().strip()
        if not line: continue
        chunk = json.loads(line)
        parts.append(chunk.get('response', ''))
        if chunk.get('done'): break

resposta = ''.join(parts)
print("RESPOSTA COMPLETA:")
print(repr(resposta))
print(f"\nTamanho: {len(resposta)} chars")
