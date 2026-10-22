"""Print the OpenRouter key's spend so far (never the key itself).

    .venv/bin/python tools/key_usage.py
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.embed import api_key  # noqa: E402

req = urllib.request.Request("https://openrouter.ai/api/v1/key", headers={"Authorization": "Bearer " + api_key()})
with urllib.request.urlopen(req, timeout=30) as resp:
    d = json.load(resp)["data"]
print(f"usage ${float(d.get('usage') or 0):.4f}  limit_remaining {d.get('limit_remaining')}")
