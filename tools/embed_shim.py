"""Local stand-in for the validators' Ollama-compatible embedding gateway.

The harness calls POST {OLLAMA_BASE_URL}/api/embed with {"model": ..., "input": [...]}.
Validators answer that with OpenRouter's embeddings API on the pinned profile
(perplexity/pplx-embed-v1-0.6b, 768 dims, float; see ditto-subnet
services/model-relay/internal/config/config.go). This does the same locally.

    OPENROUTER_API_KEY=... python3 embed_shim.py --port 11500
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

UPSTREAM = "https://openrouter.ai/api/v1/embeddings"
MODEL = "perplexity/pplx-embed-v1-0.6b"
DIMS = 768


def embed(texts, key, attempts=4):
    body = json.dumps({"model": MODEL, "input": texts, "dimensions": DIMS,
                       "encoding_format": "float"}).encode()
    for attempt in range(attempts):
        req = urllib.request.Request(UPSTREAM, data=body, method="POST", headers={
            "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)["data"]
            return [row["embedding"] for row in sorted(data, key=lambda r: r["index"])]
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError):
            if attempt == attempts - 1:
                raise
            time.sleep(2 * (attempt + 1))


class Handler(BaseHTTPRequestHandler):
    key = ""

    def log_message(self, *args):
        pass

    def reply(self, code, payload):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self.reply(200, {"status": "ok"} if self.path in ("/", "/api/version", "/health")
                   else {"error": "not found"})

    def do_POST(self):
        if self.path not in ("/api/embed", "/api/embeddings"):
            self.reply(404, {"error": "not found"})
            return
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            texts = req.get("input", req.get("prompt", []))
            single = isinstance(texts, str)
            vectors = embed([texts] if single else list(texts), self.key)
        except Exception as e:  # report upstream failures to the harness as a 502
            self.reply(502, {"error": f"{type(e).__name__}: {e}"[:300]})
            return
        if self.path == "/api/embeddings":
            self.reply(200, {"embedding": vectors[0]})
        else:
            self.reply(200, {"model": req.get("model", MODEL), "embeddings": vectors})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=11500)
    args = ap.parse_args()
    Handler.key = os.environ["OPENROUTER_API_KEY"]
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
