"""
Client minimal pour Google AI Studio (endpoint configurable).

Expose call_llm(messages) et lève LLMError ou GoogleQuotaError en cas d'échec.
"""
import time
import requests
import random
from config import settings


class LLMError(Exception):
    pass


class GoogleQuotaError(LLMError):
    pass


_SESSION = requests.Session()


def call_llm(messages: list) -> str:
    """Retourne le texte brut de la réponse via l'endpoint v1beta/models/{model}:generateContent."""
    api_key = (settings.GOOGLE_AI_API_KEY or "").strip().strip('"').strip("'")
    if not api_key:
        raise GoogleQuotaError("Clé Google AI Studio non configurée ou vide")

    headers = {"Content-Type": "application/json"}
    if api_key.startswith("ya29.") or api_key.startswith("ya29_"):
        headers["Authorization"] = f"Bearer {api_key}"

    # Construire le prompt textuel à partir des messages
    prompt_parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            prompt_parts.append(f"INSTRUCTIONS:\n{content}")
        else:
            prompt_parts.append(f"{content}")
    prompt = "\n\n".join(prompt_parts)

    base = settings.GOOGLE_AI_BASE_URL.rstrip("/")
    primary_model = settings.GOOGLE_AI_MODEL or "gemini-flash-lite-latest"
    model_candidates = [primary_model]
    for m in ("gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"):
        if m not in model_candidates:
            model_candidates.append(m)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": max(1500, settings.LLM_MAX_TOKENS_OUTPUT),
            "responseMimeType": "application/json",
        },
    }

    def _extract_text(data: dict) -> str:
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception:
            for path in (
                ("candidates", 0, "output"),
                ("candidates", 0, "text"),
                ("output",),
                ("choices", 0, "message", "content"),
            ):
                try:
                    val = data
                    for key in path:
                        val = val[key]
                    if isinstance(val, str):
                        return val
                    if isinstance(val, dict) and "content" in val:
                        return val["content"]
                except Exception:
                    continue
        raise KeyError("No text candidate found in Google AI response")

    last_error = None
    for attempt in range(settings.LLM_MAX_RETRIES + 1):
        for model in model_candidates:
            call_url = f"{base}/v1beta/models/{model}:generateContent"
            if api_key and not headers.get("Authorization"):
                sep = "&" if "?" in call_url else "?"
                call_url = f"{call_url}{sep}key={api_key}"

            try:
                resp = _SESSION.post(
                    call_url,
                    headers=headers,
                    json=payload,
                    timeout=settings.LLM_TIMEOUT_SECONDES,
                )
                if resp.status_code == 429 or "RESOURCE_EXHAUSTED" in resp.text:
                    err_msg = f"HTTP {resp.status_code}: {resp.text[:250]}"
                    if "quota" in resp.text.lower() or "resource_exhausted" in resp.text.lower():
                        raise GoogleQuotaError(err_msg)
                    last_error = LLMError(err_msg)
                    backoff = min(4, 0.5 * (2 ** attempt))
                    time.sleep(backoff + random.uniform(0, 0.5))
                    continue

                if resp.status_code in (400, 404):
                    last_error = LLMError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                    continue

                if resp.status_code >= 500:
                    last_error = LLMError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                    time.sleep(min(2, 0.25 * (2 ** attempt)))
                    continue

                resp.raise_for_status()
                data = resp.json()
                return _extract_text(data)
            except GoogleQuotaError:
                raise
            except (requests.RequestException, KeyError, IndexError) as exc:
                last_error = LLMError(str(exc))
                time.sleep(min(1, 0.1 * (2 ** attempt)))
                continue

    if last_error and ("429" in str(last_error) or "quota" in str(last_error).lower() or "resource_exhausted" in str(last_error).lower()):
        raise GoogleQuotaError(str(last_error))
    raise last_error or LLMError("Échec de l'appel Google AI Studio")

