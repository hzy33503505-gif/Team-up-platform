from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from types import SimpleNamespace
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
LOCAL_CONFIG = BASE_DIR / "data" / "llm_config.local.json"
EXAMPLE_CONFIG = BASE_DIR / "data" / "llm_config.example.json"


PROVIDER_DEFAULTS = {
    "deepseek": {
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "label": "DeepSeek V4 云端增强",
        "allowed_models": ["deepseek-v4-flash", "deepseek-v4-pro"],
    },
}


def ensure_example_config() -> None:
    EXAMPLE_CONFIG.parent.mkdir(exist_ok=True)
    if EXAMPLE_CONFIG.exists():
        return
    payload = {
        "provider": "deepseek",
        "api_key": "",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "notes": "默认不再依赖本地 Qwen/Ollama。自训练模型优先回答；需要云端增强时填写 DeepSeek API Key，或设置 DEEPSEEK_API_KEY 环境变量。",
    }
    EXAMPLE_CONFIG.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_local_config() -> dict[str, Any]:
    ensure_example_config()
    if not LOCAL_CONFIG.exists():
        return {}
    try:
        data = json.loads(LOCAL_CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def get_llm_config() -> dict[str, Any]:
    local = _read_local_config()
    raw_provider = (
        os.getenv("LLM_PROVIDER")
        or local.get("provider")
        or "deepseek"
    ).strip().lower()
    provider = "deepseek" if raw_provider not in PROVIDER_DEFAULTS else raw_provider
    defaults = PROVIDER_DEFAULTS[provider]
    api_key = (
        (os.getenv(defaults["api_key_env"]) if defaults.get("api_key_env") else "")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("LLM_API_KEY")
        or local.get("api_key")
        or ""
    ).strip()
    if api_key.startswith("把你的") or api_key.lower() in {"ollama", "none", "null"}:
        api_key = ""

    model = os.getenv("LLM_MODEL") or local.get("model") or defaults["model"]
    if model not in defaults.get("allowed_models", []):
        model = defaults["model"]

    return {
        "provider": provider,
        "label": defaults["label"],
        "api_key_env": defaults["api_key_env"],
        "api_key_configured": bool(api_key),
        "api_key_optional": False,
        "api_key": api_key,
        "base_url": os.getenv("LLM_BASE_URL") or local.get("base_url") or defaults["base_url"],
        "model": model,
        "allowed_models": defaults.get("allowed_models", []),
        "config_path": str(LOCAL_CONFIG),
        "example_path": str(EXAMPLE_CONFIG),
    }


def llm_server_available(config: dict[str, Any], timeout: float = 1.5) -> bool:
    if not config["api_key_configured"]:
        return False
    url = config["base_url"].rstrip("/") + "/models"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {config['api_key']}",
            "Accept": "application/json",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return 200 <= response.status < 500
    except (OSError, urllib.error.URLError):
        return False


class OpenAICompatibleClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._chat_completions_create))

    def _chat_completions_create(self, **payload):
        url = f"{self.base_url}/chat/completions"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        message = data["choices"][0]["message"]
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=message.get("content", ""))
                )
            ]
        )


def get_llm_client() -> tuple[OpenAICompatibleClient | None, dict[str, Any]]:
    config = get_llm_config()
    if not config["api_key_configured"]:
        config["server_available"] = False
        return None, config
    config["server_available"] = True
    client = OpenAICompatibleClient(api_key=config["api_key"], base_url=config["base_url"])
    return client, config


def save_deepseek_config(api_key: str = "", model: str = "deepseek-v4-flash", base_url: str = "https://api.deepseek.com") -> dict[str, Any]:
    defaults = PROVIDER_DEFAULTS["deepseek"]
    safe_model = model if model in defaults["allowed_models"] else defaults["model"]
    payload = {
        "provider": "deepseek",
        "api_key": (api_key or "").strip(),
        "base_url": (base_url or defaults["base_url"]).strip().rstrip("/"),
        "model": safe_model,
        "notes": "自训练模型优先回答；DeepSeek V4 只作为云端增强接口，不再依赖本地 Qwen/Ollama。",
    }
    LOCAL_CONFIG.parent.mkdir(exist_ok=True)
    LOCAL_CONFIG.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return get_llm_config()


def public_llm_status() -> dict[str, Any]:
    config = get_llm_config()
    server_available = llm_server_available(config)
    return {
        "provider": config["provider"],
        "label": config["label"],
        "model": config["model"],
        "base_url": config["base_url"],
        "api_key_configured": config["api_key_configured"],
        "api_key_optional": config["api_key_optional"],
        "server_available": server_available,
        "api_key_env": config["api_key_env"],
        "allowed_models": config["allowed_models"],
        "config_path": config["config_path"],
        "example_path": config["example_path"],
    }
