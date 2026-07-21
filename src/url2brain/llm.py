from __future__ import annotations

import json
import re
import threading
from typing import Any

import requests

from .config import Settings


class BrainError(RuntimeError):
    pass


def extract_json_object(text: str) -> dict[str, Any]:
    value = str(text or "").strip()
    value = re.sub(r"^```(?:json)?\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*```$", "", value).strip()
    try:
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(value[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    raise BrainError(f"model did not return a valid JSON object: {value[:200]}")


class ArticleBrain:
    """url2brainのLLM呼び出し層。ollama/deepseekを選択式で切替える(kcbrainのCryptoBrainと同型)。"""

    def __init__(self, config: Settings) -> None:
        self.config = config
        self._lock = threading.Lock()

    def health(self) -> dict[str, Any]:
        if self.config.llm_provider == "deepseek":
            return self._deepseek_health()
        try:
            response = requests.get(f"{self.config.ollama_url}/api/tags", timeout=4)
            response.raise_for_status()
            names = {str(item.get("name") or "") for item in response.json().get("models", [])}
            return {
                "provider": "ollama",
                "reachable": True,
                "model_available": self.config.ollama_model in names,
                "models": sorted(names),
            }
        except Exception as exc:
            return {"provider": "ollama", "reachable": False, "model_available": False, "error": str(exc)[:200]}

    def _deepseek_headers(self) -> dict[str, str]:
        if not self.config.deepseek_api_key:
            raise BrainError("URL2BRAIN_DEEPSEEK_API_KEY is not configured")
        return {
            "Accept": "application/json",
            "Authorization": f"Bearer {self.config.deepseek_api_key}",
            "Content-Type": "application/json",
        }

    def _deepseek_health(self) -> dict[str, Any]:
        try:
            response = requests.get(
                f"{self.config.deepseek_base_url}/models",
                headers=self._deepseek_headers(),
                timeout=min(self.config.deepseek_timeout, 10),
            )
            response.raise_for_status()
            names = {str(item.get("id") or "") for item in response.json().get("data", [])}
            return {
                "provider": "deepseek",
                "reachable": True,
                "model_available": self.config.deepseek_model in names,
                "models": sorted(names),
            }
        except Exception as exc:
            return {"provider": "deepseek", "reachable": False, "model_available": False, "error": str(exc)[:200]}

    @property
    def model(self) -> str:
        return self.config.active_model

    def model_for(self, provider: str = "") -> str:
        provider = provider or self.config.llm_provider
        return self.config.deepseek_model if provider == "deepseek" else self.config.ollama_model

    def generate_json(self, prompt: str, max_tokens: int = 2200, provider: str = "") -> dict[str, Any]:
        # provider省略時はconfig既定(url2pub WebアプリはローカルGemma4のまま)。x402ゲートウェイは
        # 有料コールに対して常にprovider="deepseek"を注入し、ローカルGPUをKurage本番系と
        # 競合させずに済ませる(2026-07-21方針)。
        provider = provider or self.config.llm_provider
        if len(prompt) > self.config.max_input_chars:
            raise BrainError(f"input exceeds {self.config.max_input_chars} characters")
        if provider == "deepseek":
            content = self._chat_deepseek(prompt, max_tokens)
            return extract_json_object(content)
        if provider != "ollama":
            raise BrainError("provider must be ollama or deepseek")
        payload = {
            "model": self.config.ollama_model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "format": "json",
            "options": {"temperature": 0.4, "num_predict": max_tokens},
        }
        try:
            with self._lock:
                response = requests.post(
                    f"{self.config.ollama_url}/api/generate",
                    json=payload,
                    timeout=self.config.ollama_timeout,
                )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            raise BrainError(f"Ollama request failed: {exc}") from exc
        raw = str(body.get("response") or "").strip()
        if not raw:
            reason = str(body.get("done_reason") or "unknown")
            raise BrainError(f"Ollama returned an empty response (done_reason={reason})")
        return extract_json_object(raw)

    def _chat_deepseek(self, prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self.config.deepseek_model,
            "messages": [
                {"role": "system", "content": "Return exactly one valid JSON object and no commentary or markdown."},
                {"role": "user", "content": prompt},
            ],
            "thinking": {"type": "disabled"},
            "stream": False,
            "temperature": 0.4,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            response = requests.post(
                f"{self.config.deepseek_base_url}/chat/completions",
                headers=self._deepseek_headers(),
                json=payload,
                timeout=self.config.deepseek_timeout,
            )
            response.raise_for_status()
            body = response.json()
        except requests.RequestException as exc:
            raise BrainError(f"DeepSeek request failed: {exc}") from exc
        choices = body.get("choices") or []
        content = str(((choices[0] if choices else {}).get("message") or {}).get("content") or "").strip()
        if not content:
            finish_reason = str((choices[0] if choices else {}).get("finish_reason") or "unknown")
            raise BrainError(f"DeepSeek returned an empty response (finish_reason={finish_reason})")
        return content
