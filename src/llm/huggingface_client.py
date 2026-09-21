"""
Client pour l'API Hugging Face Serverless / Inference Router.

Expose call_llm(messages) et lève HuggingFaceQuotaError (sur 429 / quota épuisé)
ou HuggingFaceError en cas d'autres erreurs.
"""
import time
import requests
import random
from config import settings


class HuggingFaceError(Exception):
    pass


class HuggingFaceQuotaError(HuggingFaceError):
    pass


_SESSION = requests.Session()


def _candidate_models() -> list:
    configured = (settings.HUGGINGFACE_MODEL or "").strip()
    fallback_models = [
        model.strip()
        for model in getattr(settings, "HUGGINGFACE_FALLBACK_MODELS", [])
        if model and model.strip()
    ]
    ordered = []
    seen = set()
    for model in [configured] + fallback_models:
        if model and model not in seen:
            ordered.append(model)
            seen.add(model)
    return ordered or ["Qwen/Qwen2.5-72B-Instruct", "meta-llama/Llama-3.3-70B-Instruct"]


def call_llm(messages: list) -> str:
    """Retourne le texte brut de la réponse (JSON), ou lève HuggingFaceQuotaError / HuggingFaceError."""
    api_key = (settings.HUGGINGFACE_API_KEY or "").strip().strip('"').strip("'")
    if not api_key:
        raise HuggingFaceQuotaError("Clé Hugging Face non configurée ou vide dans .env")

    base_url = (settings.HUGGINGFACE_BASE_URL or "https://router.huggingface.co/hf-inference/v1").rstrip("/")
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
                    raise HuggingFaceError(f"Réponse Hugging Face vide pour le modèle {model}")

                if resp.status_code in (429, 402):
                    raise HuggingFaceQuotaError(f"Quota Hugging Face dépassé (HTTP {resp.status_code}) pour le modèle {model}")

                if resp.status_code in (401, 403):
                    raise HuggingFaceQuotaError(f"Clé API Hugging Face invalide ou non autorisée (HTTP {resp.status_code})")

                if resp.status_code == 503:
                    # Modèle en cours de chargement sur Hugging Face
                    time.sleep(2.0 + attempt * 1.5)
                    continue

                if resp.status_code in (400, 404):
                    last_error = HuggingFaceError(f"Modèle HF non supporté ou indisponible ({model}): {resp.text[:200]}")
                    break

                if resp.status_code >= 500:
                    time.sleep(1.0 + attempt * 0.5)
                    continue

                raise HuggingFaceError(f"Erreur Hugging Face HTTP {resp.status_code}: {resp.text[:300]}")

            except (requests.Timeout, requests.ConnectionError) as net_err:
                last_error = HuggingFaceError(f"Erreur réseau Hugging Face: {net_err}")
                time.sleep(1.0 + attempt * 0.5)
            except HuggingFaceQuotaError:
                raise
            except Exception as e:
                last_error = HuggingFaceError(f"Exception Hugging Face inattendue: {e}")
                time.sleep(1.0)

    raise last_error or HuggingFaceError("Échec des appels à l'API Hugging Face sur tous les modèles candidats.")
