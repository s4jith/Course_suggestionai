
import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)

class OllamaService:

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL
        self._timeout = float(settings.OLLAMA_TIMEOUT)

    async def generate(self, prompt: str) -> Optional[Dict[str, Any]]:
        if not settings.OLLAMA_ENABLED:
            logger.debug("Ollama disabled in settings — skipping LLM call.")
            return None

        payload: Dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.15,
                "num_predict": 1024,
                "top_p": 0.9,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                raw_text: str = data.get("response", "")
                parsed = self._extract_json(raw_text)
                if parsed is None:
                    logger.warning(
                        "OllamaService: could not parse JSON from model response "
                        "(first 300 chars): %s",
                        raw_text[:300],
                    )
                return parsed

        except httpx.TimeoutException:
            logger.warning(
                "OllamaService: request timed out after %.0fs — falling back to rules.",
                self._timeout,
            )
        except httpx.ConnectError:
            logger.warning(
                "OllamaService: cannot connect to Ollama at %s — "
                "ensure `ollama serve` is running.",
                self._base_url,
            )
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "OllamaService: HTTP %d from Ollama: %s",
                exc.response.status_code,
                exc.response.text[:300],
            )
        except Exception as exc:
            logger.error("OllamaService: unexpected error: %s", exc, exc_info=True)

        return None

    async def health_check(self) -> Dict[str, Any]:
        if not settings.OLLAMA_ENABLED:
            return {
                "available": False,
                "model_loaded": False,
                "model": self._model,
                "base_url": self._base_url,
                "available_models": [],
                "error": "Ollama integration is disabled (OLLAMA_ENABLED=false).",
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                tags_data = resp.json()
                models: List[str] = [m.get("name", "") for m in tags_data.get("models", [])]
                model_loaded = any(self._model in m for m in models)
                return {
                    "available": True,
                    "model_loaded": model_loaded,
                    "model": self._model,
                    "base_url": self._base_url,
                    "available_models": models,
                    "error": (
                        None
                        if model_loaded
                        else f"Model '{self._model}' not found. Run: ollama pull {self._model}"
                    ),
                }

        except httpx.ConnectError:
            return {
                "available": False,
                "model_loaded": False,
                "model": self._model,
                "base_url": self._base_url,
                "available_models": [],
                "error": (
                    f"Cannot connect to Ollama at {self._base_url}. "
                    "Ensure the Ollama server is running (`ollama serve`)."
                ),
            }
        except Exception as exc:
            return {
                "available": False,
                "model_loaded": False,
                "model": self._model,
                "base_url": self._base_url,
                "available_models": [],
                "error": str(exc),
            }

    async def list_models(self) -> List[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                return [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception:
            return []

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        if not text:
            return None

        try:
            return json.loads(text.strip())
        except (json.JSONDecodeError, ValueError):
            pass

        cleaned = text.strip()
        for fence in ("```json\n", "```json", "```\n", "```"):
            if cleaned.startswith(fence):
                cleaned = cleaned[len(fence):]
                break
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

        try:
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError):
            pass

        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start: end + 1])
            except (json.JSONDecodeError, ValueError):
                pass

        return None

ollama_service = OllamaService()
