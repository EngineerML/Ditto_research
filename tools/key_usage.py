"""Print the OpenRouter key's spend so far and the account's balance (never the key itself).

The key's limit_remaining is only the spending cap set on the key; the money left is the account
balance, total_credits - total_usage, shared by every key on the account.

    .venv/bin/python tools/key_usage.py          # one line
    .venv/bin/python tools/key_usage.py --need 3 # exit 1 when the balance is under $3
"""
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.embed import api_key  # noqa: E402


def get(path: str) -> dict:
    req = urllib.request.Request("https://openrouter.ai/api/v1/" + path, headers={"Authorization": "Bearer " + api_key()})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)["data"]


key, account = get("key"), get("credits")
balance = float(account["total_credits"]) - float(account["total_usage"])
print(f"key usage ${float(key.get('usage') or 0):.4f}  account balance ${balance:.4f}")
if "--need" in sys.argv and balance < float(sys.argv[sys.argv.index("--need") + 1]):
    sys.exit(1)
