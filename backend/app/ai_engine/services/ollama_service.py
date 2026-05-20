"""
Ollama Service – async HTTP client for the local Ollama LLM server.

Responsibilities:
  - POST /api/generate  : send a prompt and receive a completion
  - GET  /api/tags      : health check + available model listing
  - JSON extraction     : parse structured JSON from raw model output
  - Timeout handling    : configurable per-request timeout
  - Fallback safety     : all errors return None so callers can degrade gracefully

Requires: httpx (async HTTP client)

Ollama API docs: https://github.com/ollama/ollama/blob/main/docs/api.md
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config.settings import settings

logger = logging.getLogger(__name__)


class OllamaService:
    """
    Thin async wrapper around the Ollama REST API.

    The service is intentionally silent on errors — it logs warnings and
    returns None so that the RecommendationService can fall back to
    rule-only output without propagating exceptions to the API layer.
    """

    def __init__(self) -> None:
        self._base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self._model = settings.OLLAMA_MODEL
        self._timeout = float(settings.OLLAMA_TIMEOUT)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def generate(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Send a prompt to Ollama and return the parsed JSON response dict.

        The prompt is expected to instruct the model to respond with pure JSON.
        This method extracts and parses that JSON automatically.

        Args:
            prompt: Fully formatted prompt string from a templates.py builder.

        Returns:
            Parsed dict on success, None on any error (connection, timeout, parse).
        """
        if not settings.OLLAMA_ENABLED:
            logger.debug("Ollama disabled in settings — skipping LLM call.")
            return None

        payload: Dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.15,   # low temperature → deterministic structured output
                "num_predict": 1024,   # max output tokens
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
        except Exception as exc:  # noqa: BLE001
            logger.error("OllamaService: unexpected error: %s", exc, exc_info=True)

        return None

    async def health_check(self) -> Dict[str, Any]:
        """
        Check Ollama server reachability and model availability.

        Returns a dict with:
            available      : bool — is the Ollama server reachable?
            model_loaded   : bool — is the configured model available?
            model          : str  — configured model name
            base_url       : str  — configured Ollama base URL
            available_models: list — all models found on the server
            error          : str | None — human-readable error if any
        """
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
        except Exception as exc:  # noqa: BLE001
            return {
                "available": False,
                "model_loaded": False,
                "model": self._model,
                "base_url": self._base_url,
                "available_models": [],
                "error": str(exc),
            }

    async def list_models(self) -> List[str]:
        """Return a list of model names available on the Ollama server."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/api/tags")
                resp.raise_for_status()
                return [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception:  # noqa: BLE001
            return []

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Extract a JSON object from raw model output.

        Handles three common Ollama response patterns:
          1. Pure JSON string (ideal case)
          2. JSON wrapped in markdown code fences (```json ... ```)
          3. JSON embedded somewhere inside a longer prose response
        """
        if not text:
            return None

        # Attempt 1: direct parse
        try:
            return json.loads(text.strip())
        except (json.JSONDecodeError, ValueError):
            pass

        # Attempt 2: strip markdown code fences
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

        # Attempt 3: find first '{' … last '}' substring
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start: end + 1])
            except (json.JSONDecodeError, ValueError):
                pass

        return None


# ---------------------------------------------------------------------------
# Module-level singleton — imported by RecommendationService
# ---------------------------------------------------------------------------

ollama_service = OllamaService()
