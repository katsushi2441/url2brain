from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Settings:
    host: str
    port: int
    api_token: str
    allowed_client_ips: frozenset[str]
    ollama_url: str
    ollama_model: str
    ollama_timeout: int
    max_input_chars: int
    oss2api_url: str
    fetch_timeout: int
    llm_provider: str = "ollama"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout: int = 600

    @property
    def active_model(self) -> str:
        if self.llm_provider == "deepseek":
            return self.deepseek_model
        return self.ollama_model


def load_settings() -> Settings:
    allowed = {
        value.strip()
        for value in os.getenv("URL2BRAIN_ALLOWED_CLIENT_IPS", "127.0.0.1,::1,157.7.188.210").split(",")
        if value.strip()
    }
    provider = os.getenv("URL2BRAIN_LLM_PROVIDER", "ollama").strip().lower()
    return Settings(
        host=os.getenv("URL2BRAIN_HOST", "0.0.0.0"),
        port=int(os.getenv("URL2BRAIN_PORT", "18332")),
        api_token=os.getenv("URL2BRAIN_API_TOKEN", "").strip(),
        allowed_client_ips=frozenset(allowed),
        ollama_url=os.getenv("URL2BRAIN_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/"),
        ollama_model=os.getenv("URL2BRAIN_OLLAMA_MODEL", "gemma4:12b-it-qat").strip(),
        ollama_timeout=int(os.getenv("URL2BRAIN_OLLAMA_TIMEOUT", "600")),
        max_input_chars=int(os.getenv("URL2BRAIN_MAX_INPUT_CHARS", "80000")),
        # oss2apiのurl/analyzeを内部で叩いて素材(title/description/headings/content)を取得する。
        # url2brainは二重にスクレイパーを持たない(AGENTS.md参照)。
        oss2api_url=os.getenv("URL2BRAIN_OSS2API_URL", "http://127.0.0.1:8015").rstrip("/"),
        fetch_timeout=int(os.getenv("URL2BRAIN_FETCH_TIMEOUT", "30")),
        llm_provider=provider,
        deepseek_base_url=os.getenv("URL2BRAIN_DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_api_key=os.getenv("URL2BRAIN_DEEPSEEK_API_KEY", "").strip(),
        deepseek_model=os.getenv("URL2BRAIN_DEEPSEEK_MODEL", "deepseek-v4-flash").strip(),
        deepseek_timeout=int(os.getenv("URL2BRAIN_DEEPSEEK_TIMEOUT", "600")),
    )


settings = load_settings()
