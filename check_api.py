import urllib.request
import json

url = "http://localhost:8000/openapi.json"
with urllib.request.urlopen(url) as resp:
    data = json.load(resp)

for path in data.get("paths", {}).keys():
    print(path)