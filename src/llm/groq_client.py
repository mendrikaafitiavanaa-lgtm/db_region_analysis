"""
Client pour l'API Groq (Llama 3 / Mixtral ultra-rapide).

Expose call_llm(messages) et lève GroqQuotaError (sur 429 / quota épuisé)
ou GroqError en cas d'autres erreurs HTTP/réseau.
"""
import time
import requests
import random
from config import settings


class GroqError(Exception):
    pass


class GroqQuotaError(GroqError):
    pass


_SESSION = requests.Session()


def _candidate_models() -> list:
    configured = (settings.GROQ_MODEL or "").strip()
    fallback_models = [
        model.strip()
        for model in getattr(settings, "GROQ_FALLBACK_MODELS", [])
        if model and model.strip()
    ]
    ordered = []
    seen = set()
    for model in [configured] + fallback_models:
        if model and model not in seen:
            ordered.append(model)
            seen.add(model)
    return ordered or ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]


def call_llm(messages: list) -> str:
    """Retourne le texte brut de la réponse (JSON), ou lève GroqQuotaError / GroqError."""
    api_key = (settings.GROQ_API_KEY or "").strip().strip('"').strip("'")
    if not api_key:
        raise GroqQuotaError("Clé Groq non configurée ou vide dans .env")

    base_url = (settings.GROQ_BASE_URL or "https://api.groq.com/openai/v1").rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    models_to_try = _candidate_models()
    last_error = None

    for model in models_to_try:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": max(1500, settings.LLM_MAX_TOKENS_OUTPUT),
            "response_format": {"type": "json_object"},
        }

        for attempt in range(max(1, settings.LLM_MAX_RETRIES)):
            try:
                resp = _SESSION.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=settings.LLM_TIMEOUT_SECONDES,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "")
                        if content and content.strip():
                            return content.strip()
                    raise GroqError(f"Réponse Groq vide pour le modèle {model}")

                if resp.status_code == 429:
                    raise GroqQuotaError(f"Quota Groq dépassé (HTTP 429) pour le modèle {model}")

                if resp.status_code in (401, 403):
                    raise GroqQuotaError(f"Clé API Groq invalide ou non autorisée (HTTP {resp.status_code})")

                if resp.status_code in (400, 404):
                    last_error = GroqError(f"Modèle Groq non supporté ou indisponible ({model}): {resp.text[:200]}")
                    break  # Passer au modèle candidat suivant

                if resp.status_code >= 500:
                    time.sleep(1.0 + attempt * 0.5)
                    continue

                raise GroqError(f"Erreur Groq HTTP {resp.status_code}: {resp.text[:300]}")

            except (requests.Timeout, requests.ConnectionError) as net_err:
                last_error = GroqError(f"Erreur réseau Groq: {net_err}")
                time.sleep(1.0 + attempt * 0.5)
            except GroqQuotaError:
                raise
            except Exception as e:
                last_error = GroqError(f"Exception Groq inattendue: {e}")
                time.sleep(1.0)

    raise last_error or GroqError("Échec des appels à l'API Groq sur tous les modèles candidats.")
