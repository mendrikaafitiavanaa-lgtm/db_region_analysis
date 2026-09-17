import time
import requests
import random
from config import settings


class OpenRouterError(Exception):
    pass


class OpenRouterQuotaError(OpenRouterError):
    pass


_SESSION = requests.Session()


def _candidate_models() -> list[str]:
    configured = (settings.OPENROUTER_MODEL or "").strip()
    fallback_models = [
        model.strip()
        for model in getattr(settings, "OPENROUTER_FALLBACK_MODELS", [])
        if model and model.strip()
    ]
    ordered = []
    seen = set()
    for model in [configured] + fallback_models:
        model = model.strip()
        if model and model not in seen:
            ordered.append(model)
            seen.add(model)
    return ordered or ["openai/gpt-oss-20b:free"]


def _looks_like_missing_model(resp_text: str) -> bool:
    text = (resp_text or "").lower()
    return (
        "model not found" in text
        or "model doesn't exist" in text
        or "no model" in text
        or "unavailable" in text
        or "not available" in text
        or "slug instead" in text
        or ("not found" in text and "model" in text)
    )


def call_llm(messages: list) -> str:
    """Retourne le texte brut de la réponse (JSON), ou lève OpenRouterError/OpenRouterQuotaError."""
    api_key = (settings.OPENROUTER_API_KEY or "").strip().strip('"').strip("'")
    if not api_key:
        raise OpenRouterQuotaError("Clé OpenRouter non configurée ou vide")

    url = f"{settings.OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com",
        "X-Title": "ScrapingCorse",
    }

    last_error = None
    for attempt in range(settings.LLM_MAX_RETRIES + 1):
        for model_name in _candidate_models():
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": settings.LLM_MAX_TOKENS_OUTPUT,
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            }
            try:
                resp = _SESSION.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=settings.LLM_TIMEOUT_SECONDES,
                )

                if resp.status_code in (402, 429):
                    err_msg = f"HTTP {resp.status_code}: {resp.text[:250]}"
                    if resp.status_code == 402 or "quota" in resp.text.lower() or "credits" in resp.text.lower():
                        raise OpenRouterQuotaError(err_msg)
                    last_error = OpenRouterError(err_msg)
                    backoff = min(6, 1.0 * (2 ** attempt))
                    time.sleep(backoff + random.uniform(0, 0.5))
                    continue

                if resp.status_code == 404 or (resp.status_code == 400 and _looks_like_missing_model(resp.text)):
                    err_msg = f"HTTP {resp.status_code} ({model_name}): {resp.text[:250]}"
                    last_error = OpenRouterError(err_msg)
                    # Essayer le modèle de fallback suivant
                    continue

                if resp.status_code == 400:
                    err_msg = f"HTTP {resp.status_code}: {resp.text[:250]}"
                    last_error = OpenRouterError(err_msg)
                    break

                if resp.status_code >= 500:
                    last_error = OpenRouterError(f"HTTP {resp.status_code}: {resp.text[:200]}")
                    time.sleep(min(4, 0.5 * (2 ** attempt)))
                    continue

                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except OpenRouterQuotaError:
                raise
            except (requests.RequestException, KeyError, IndexError) as exc:
                last_error = OpenRouterError(str(exc))
                time.sleep(min(2, 0.25 * (2 ** attempt)))

        if last_error and any(token in str(last_error).lower() for token in ("429", "quota", "credits")):
            raise OpenRouterQuotaError(str(last_error))

        if last_error and _looks_like_missing_model(str(last_error)):
            time.sleep(min(2, 0.5 * (2 ** attempt)))
            continue

        if last_error:
            break

    if last_error and ("429" in str(last_error) or "quota" in str(last_error).lower()):
        raise OpenRouterQuotaError(str(last_error))
    raise last_error or OpenRouterError("Échec inconnu de l'appel OpenRouter")

