#!/usr/bin/env python3
import urllib.request
import json

# Test register
url = "http://localhost:8000/api/auth/register"
data = json.dumps({"name": "test-gui-agent"}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req) as resp:
        print("register:", resp.read().decode())
except Exception as e:
    print("register error:", e)

# Test init
url2 = "http://localhost:8000/api/auth/init"
data2 = json.dumps({"name": "test-gui-agent", "device_id": "test123"}).encode()
req2 = urllib.request.Request(url2, data=data2, headers={"Content-Type": "application/json"})
try:
    with urllib.request.urlopen(req2) as resp:
        print("init:", resp.read().decode())
except Exception as e:
    print("init error:", e)