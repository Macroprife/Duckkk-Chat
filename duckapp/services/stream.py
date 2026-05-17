"""Duck Chat — stream collector + provider streaming helpers."""

import json
import logging
import time
import uuid
from typing import AsyncGenerator, Optional

import httpx

import db as db_mod
from duckapp.config import PROVIDERS

logger = logging.getLogger("myapi.stream")


class StreamCollector:
    """Accumulates streamed chunks and persists the final assistant message."""

    def __init__(self, conversation_id: uuid.UUID, session_id: uuid.UUID | None,
                 model_id: str, provider: str, ip: str | None = None):
        self.conversation_id = conversation_id
        self.session_id = session_id
        self.model_id = model_id
        self.provider = provider
        self.ip = ip
        self.chunks: list[str] = []
        self.start_ts = time.perf_counter()
        self.tokens_prompt: int | None = None
        self.tokens_completion: int | None = None

    def add_chunk(self, text: str):
        self.chunks.append(text)

    def finalize_tokens(self, prompt: int | None = None, completion: int | None = None):
        if prompt is not None:
            self.tokens_prompt = prompt
        if completion is not None:
            self.tokens_completion = completion

    @property
    def full_text(self) -> str:
        return "".join(self.chunks)

    @property
    def duration_ms(self) -> int:
        return int((time.perf_counter() - self.start_ts) * 1000)

    async def save(self):
        content = self.full_text
        if not content:
            logger.info("Empty assistant response — skipping persistence")
            return
        try:
            await db_mod.insert_message(
                conversation_id=self.conversation_id,
                role="assistant",
                content=content,
                tokens_prompt=self.tokens_prompt,
                tokens_completion=self.tokens_completion,
                model_id=self.model_id,
                provider=self.provider,
                duration_ms=self.duration_ms,
            )
            await db_mod.insert_usage(
                session_id=self.session_id,
                conversation_id=self.conversation_id,
                model_id=self.model_id,
                provider=self.provider,
                tokens_prompt=self.tokens_prompt or 0,
                tokens_completion=self.tokens_completion or 0,
                duration_ms=self.duration_ms,
                ip_address=self.ip,
            )
            await db_mod.touch_conversation(self.conversation_id)
        except Exception as exc:
            logger.error("Persistence failed: %s", exc)


async def stream_ollama(
    client: httpx.AsyncClient,
    model_id: str,
    message: str,
    *,
    image: str | None = None,
    collector: StreamCollector | None = None,
) -> AsyncGenerator[str, None]:
    model_name = model_id.split("/", 1)[1]
    cfg = PROVIDERS["ollama"]
    headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"
    if image:
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": message},
                {"type": "image_url", "image_url": {"url": image}},
            ]
        }]
    else:
        messages = [{"role": "user", "content": message}]
    payload = {
        "model": model_name,
        "messages": messages,
        "stream": True,
    }

    try:
        async with client.stream(
            "POST", cfg["base_url"] + "/chat/completions",
            headers=headers, json=payload,
        ) as resp:
            if resp.status_code >= 400:
                yield f"[error {resp.status_code}]"
                return
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                content = line[6:]
                if content == "[DONE]":
                    break
                try:
                    d = json.loads(content)
                    choice = d["choices"][0]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                delta = choice.get("delta", {})
                if "content" in delta:
                    tok = delta["content"]
                    yield tok
                    if collector is not None:
                        collector.add_chunk(tok)
                usage = d.get("usage")
                if usage and collector is not None:
                    collector.finalize_tokens(
                        prompt=usage.get("prompt_tokens"),
                        completion=usage.get("completion_tokens"),
                    )
    except httpx.TimeoutException:
        yield "[timeout]"
    except httpx.HTTPError as e:
        yield f"[network error: {type(e).__name__}]"
    finally:
        if collector is not None:
            try:
                await collector.save()
            except Exception as exc:
                logger.error("collector.save (ollama): %s", exc)


async def stream_claw(
    client: httpx.AsyncClient,
    model_id: str,
    message: str,
    *,
    image: str | None = None,
    collector: StreamCollector | None = None,
) -> AsyncGenerator[str, None]:
    agent = model_id.split("/", 1)[1]
    cfg = PROVIDERS["claw"]
    if image:
        messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": message},
                {"type": "image_url", "image_url": {"url": image}},
            ]
        }]
    else:
        messages = [{"role": "user", "content": message}]
    payload = {
        "model": f"openclaw/{agent}",
        "messages": messages,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }

    try:
        async with client.stream(
            "POST", cfg["base_url"] + "/v1/chat/completions",
            headers=headers, json=payload,
        ) as resp:
            if resp.status_code >= 400:
                yield f"[claw error {resp.status_code}]"
                return
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                c = line[6:]
                if c == "[DONE]":
                    break
                try:
                    d = json.loads(c)
                    choice = d["choices"][0]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
                delta = choice.get("delta", {})
                if "content" in delta:
                    tok = delta["content"]
                    yield tok
                    if collector is not None:
                        collector.add_chunk(tok)
                usage = d.get("usage")
                if usage and collector is not None:
                    collector.finalize_tokens(
                        prompt=usage.get("prompt_tokens"),
                        completion=usage.get("completion_tokens"),
                    )
    except httpx.TimeoutException:
        yield "[timeout]"
    except httpx.HTTPError as e:
        yield f"[network error: {type(e).__name__}]"
    finally:
        if collector is not None:
            try:
                await collector.save()
            except Exception as exc:
                logger.error("collector.save (claw): %s", exc)
