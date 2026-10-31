from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .agent import CaseRunner
from .config import Settings
from .memory.embedding import EmbeddingError
from .protocol import RunRequest, SeedRequest, SeedResponse
from .store import Store


class AsciiJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(content, ensure_ascii=True, allow_nan=False, indent=None, separators=(",", ":")).encode("ascii")


def build_app(settings: Settings | None = None, http: httpx.AsyncClient | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = settings
        app.state.store = Store(settings.db_path)
        app.state.http = http or httpx.AsyncClient(limits=httpx.Limits(max_connections=64, max_keepalive_connections=16))
        app.state.runner = CaseRunner(settings, app.state.store, app.state.http)
        try:
            yield
        finally:
            await app.state.http.aclose()
            app.state.store.close()

    app = FastAPI(lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/seed")
    async def seed(request: Request) -> AsciiJSONResponse:
        try:
            body = SeedRequest.model_validate(await request.json())
        except Exception as exc:
            logging.getLogger("harness").error("malformed seed request: %s", exc)
            return AsciiJSONResponse({"error": f"malformed seed request: {exc}"[:500]}, status_code=400)
        pairs, subjects, links = app.state.store.upsert_seed(body.user_id, body.pairs, body.subjects, body.links)
        try:
            await app.state.runner.embed_pairs(body.user_id, body.pairs)
        except EmbeddingError as exc:
            logging.getLogger("harness").warning("seed embedding unavailable, records stay searchable by words and are embedded when a case needs them: %s", exc)
        return AsciiJSONResponse(SeedResponse(pairs=pairs, subjects=subjects, links=links).model_dump())

    @app.post("/run")
    async def run(request: Request) -> AsciiJSONResponse:
        try:
            req = RunRequest.model_validate(await request.json())
        except Exception as exc:
            logging.getLogger("harness").error("malformed run request: %s", exc)
            return AsciiJSONResponse({"error": f"malformed run request: {exc}"[:500]}, status_code=400)
        try:
            response = await app.state.runner.run(req)
        except Exception as exc:
            logging.getLogger("harness").error("run request failed: %s", exc)
            return AsciiJSONResponse({"error": f"run request failed: {exc}"[:500]}, status_code=500)
        return AsciiJSONResponse(response.wire())

    return app


app = build_app()
