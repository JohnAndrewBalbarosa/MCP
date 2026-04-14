from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Semaphore
from typing import Dict, List

try:
    from huggingface_hub import InferenceClient
except ImportError:  # pragma: no cover - handled at runtime if dependency is missing
    InferenceClient = None

from mcp_servers.llm_server.libraries.types.contracts import ProviderRuntime


def _as_text(response: object) -> str:
    if isinstance(response, str):
        return response.strip()
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()
    choices = getattr(response, "choices", None)
    if choices:
        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        if message is not None:
            content = getattr(message, "content", None)
            if isinstance(content, str) and content.strip():
                return content.strip()
        content = getattr(first_choice, "content", None)
        if isinstance(content, str) and content.strip():
            return content.strip()
    return str(response).strip()


class QwenClientPool:
    def __init__(self, runtime: ProviderRuntime) -> None:
        if InferenceClient is None:
            raise RuntimeError("Install huggingface_hub to enable the Qwen provider backend")

        client_count = max(1, runtime.max_parallel_instances)
        model_ref = runtime.model
        self._runtime = runtime
        self._clients = [
            InferenceClient(model=model_ref, token=runtime.api_key or None)
            for _ in range(client_count)
        ]
        self._client_lock = Lock()
        self._semaphore = Semaphore(client_count)
        self._index = 0

    def _next_client(self):
        with self._client_lock:
            client = self._clients[self._index]
            self._index = (self._index + 1) % len(self._clients)
            return client

    def generate(self, prompt: str) -> str:
        with self._semaphore:
            client = self._next_client()
            response = client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=self._runtime.model,
                max_tokens=self._runtime.max_output_tokens,
                temperature=self._runtime.temperature,
                top_p=self._runtime.top_p,
            )
            return _as_text(response)

    def generate_many(self, prompts: List[str]) -> List[str]:
        if not prompts:
            return []
        max_workers = min(len(prompts), len(self._clients))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            return list(pool.map(self.generate, prompts))


_QWEN_POOLS: Dict[str, QwenClientPool] = {}
_QWEN_POOLS_LOCK = Lock()


def _qwen_pool_key(runtime: ProviderRuntime) -> str:
    return "|".join(
        [
            runtime.provider_id,
            runtime.model,
            runtime.api_key,
            str(runtime.max_parallel_instances),
            str(runtime.max_output_tokens),
            str(runtime.temperature),
            str(runtime.top_p),
        ]
    )


def get_pool(runtime: ProviderRuntime) -> QwenClientPool:
    key = _qwen_pool_key(runtime)
    with _QWEN_POOLS_LOCK:
        pool = _QWEN_POOLS.get(key)
        if pool is None:
            pool = QwenClientPool(runtime)
            _QWEN_POOLS[key] = pool
        return pool


def generate_text(runtime: ProviderRuntime, prompt: str) -> str:
    return get_pool(runtime).generate(prompt)


def generate_texts(runtime: ProviderRuntime, prompts: List[str]) -> List[str]:
    return get_pool(runtime).generate_many(prompts)