import logging
import requests

from app.config import settings

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str = None, timeout: int = None):
        self._base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self._timeout = timeout or settings.LLM_TRANSLATION_TIMEOUT_SECONDS

    def generate(self, model: str, prompt: str, system: str = None) -> str:
        payload = {"model": model, "prompt": prompt, "stream": False}
        if system is not None:
            payload["system"] = system
        try:
            response = requests.post(
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout,
            )
        except requests.ConnectionError as e:
            raise RuntimeError(f"Ollama unreachable: {e}") from e
        if response.status_code != 200:
            raise RuntimeError(f"Ollama returned {response.status_code}: {response.text}")
        return response.json()["response"]
