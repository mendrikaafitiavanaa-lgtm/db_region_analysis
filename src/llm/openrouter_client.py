import time
import requests
import random
from config import settings


class OpenRouterError(Exception):
    pass


class OpenRouterQuotaError(OpenRouterError):
    pass


_SESSION = requests.Session()


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
    payload = {
        "model": settings.OPENROUTER_MODEL,
        "messages": messages,
        "max_tokens": settings.LLM_MAX_TOKENS_OUTPUT,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }

    last_error = None
    for attempt in range(settings.LLM_MAX_RETRIES + 1):
        try:
            resp = _SESSION.post(
                url,
                headers=headers,
                json=payload,
                timeout=settings.LLM_TIMEOUT_SECONDES,
            )
            if resp.status_code in (402, 429):
                err_msg = f"HTTP {resp.status_code}: {resp.text[:250]}"
                # Si 402 (Payment required / credits exhausted) ou 429 persistant
                if resp.status_code == 402 or "quota" in resp.text.lower() or "credits" in resp.text.lower():
                    raise OpenRouterQuotaError(err_msg)
                last_error = OpenRouterError(err_msg)
                backoff = min(6, 1.0 * (2 ** attempt))
                time.sleep(backoff + random.uniform(0, 0.5))
                continue
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

    if last_error and ("429" in str(last_error) or "quota" in str(last_error).lower()):
        raise OpenRouterQuotaError(str(last_error))
    raise last_error or OpenRouterError("Échec inconnu de l'appel OpenRouter")

