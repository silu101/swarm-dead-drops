"""OpenRouter chat client: provider pinning, retry/backoff, spend ledger, budget stop.

Standard library only. Reads OPENROUTER_API_KEY from the environment or .env.
Every call is appended to results/spend.jsonl (flushed and fsynced), and the
client refuses to make a call once total spend reaches the stop limit.
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_LEDGER = ROOT / "results" / "spend.jsonl"
DEFAULT_STOP_USD = 45.0  # PREREG stopping rule


class BudgetExceeded(RuntimeError):
    pass


class LLMError(RuntimeError):
    pass


def load_env(path: Path = ROOT / ".env") -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


class SpendLedger:
    def __init__(self, path: Path = DEFAULT_LEDGER, stop_usd: float | None = None):
        self.path = Path(path)
        self.stop_usd = float(os.environ.get("BUDGET_STOP_USD", DEFAULT_STOP_USD)) if stop_usd is None else stop_usd
        self._total = self._read_total()
        self._lock = threading.Lock()

    def _read_total(self) -> float:
        if not self.path.exists():
            return 0.0
        total = 0.0
        for line in self.path.read_text().splitlines():
            try:
                total += float(json.loads(line).get("cost_usd") or 0.0)
            except (ValueError, json.JSONDecodeError):
                pass
        return total

    @property
    def total(self) -> float:
        return self._total

    def check(self) -> None:
        with self._lock:
            over = self._total >= self.stop_usd
        if over:
            raise BudgetExceeded(f"spend ${self._total:.2f} reached stop limit ${self.stop_usd:.2f}")

    def record(self, entry: dict) -> None:
        with self._lock:
            self._total += float(entry.get("cost_usd") or 0.0)
            append_jsonl(self.path, entry)


@dataclass
class ChatResult:
    message: dict  # assistant message (role, content, tool_calls, reasoning?)
    usage: dict
    cost_usd: float
    provider: str | None
    model: str
    latency_s: float
    finish_reason: str | None


class OpenRouterClient:
    def __init__(
        self,
        model: str,
        provider: str | None = None,
        max_tokens: int = 1500,
        temperature: float | None = None,
        ledger: SpendLedger | None = None,
        extra: dict | None = None,
        max_retries: int = 6,
        timeout_s: float = 120.0,
    ):
        load_env()
        self.api_key = os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise LLMError("OPENROUTER_API_KEY not set (put it in .env, no spaces around =)")
        self.model = model
        self.provider = provider
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.ledger = ledger or SpendLedger()
        self.extra = extra or {}
        self.max_retries = max_retries
        self.timeout_s = timeout_s

    def _body(self, messages, tools) -> dict:
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "usage": {"include": True},  # OpenRouter returns the call's cost
        }
        if tools:
            body["tools"] = tools
        if self.temperature is not None:
            body["temperature"] = self.temperature
        if self.provider:
            body["provider"] = {"order": [self.provider], "allow_fallbacks": False}
        body.update(self.extra)
        return body

    def chat(self, messages: list[dict], tools: list[dict] | None = None, tag: dict | None = None) -> ChatResult:
        self.ledger.check()
        data = json.dumps(self._body(messages, tools)).encode()
        last_err = None
        for attempt in range(self.max_retries):
            req = urllib.request.Request(
                API_URL,
                data=data,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-Title": "swarm-dead-drops",
                },
            )
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                    resp = json.loads(r.read())
            except urllib.error.HTTPError as e:
                body = e.read().decode(errors="replace")[:500]
                last_err = f"HTTP {e.code}: {body}"
                if e.code in (408, 409, 425, 429) or e.code >= 500:
                    self._sleep(attempt)
                    continue
                raise LLMError(last_err) from e
            except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError) as e:
                last_err = f"{type(e).__name__}: {e}"
                self._sleep(attempt)
                continue
            if "error" in resp and not resp.get("choices"):
                last_err = f"API error: {json.dumps(resp['error'])[:500]}"
                self._sleep(attempt)
                continue
            if not resp.get("choices"):
                last_err = "empty choices"
                self._sleep(attempt)
                continue
            choice = resp["choices"][0]
            usage = resp.get("usage") or {}
            cost = float(usage.get("cost") or 0.0)
            result = ChatResult(
                message=choice.get("message") or {},
                usage=usage,
                cost_usd=cost,
                provider=resp.get("provider"),
                model=resp.get("model", self.model),
                latency_s=round(time.time() - t0, 2),
                finish_reason=choice.get("finish_reason"),
            )
            self.ledger.record(
                {
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "model": result.model,
                    "provider": result.provider,
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "cost_usd": cost,
                    "attempts": attempt + 1,
                    **(tag or {}),
                }
            )
            return result
        raise LLMError(f"gave up after {self.max_retries} attempts: {last_err}")

    @staticmethod
    def _sleep(attempt: int) -> None:
        time.sleep(min(60.0, 2.0 ** attempt) + random.random())
