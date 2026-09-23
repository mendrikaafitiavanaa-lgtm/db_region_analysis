"""
Client pour l'API NVIDIA (NVIDIA NIM / integrate.api.nvidia.com).

Expose call_llm(messages) et lève NvidiaQuotaError (sur 429 / quota épuisé)
ou NvidiaError en cas d'autres erreurs HTTP/réseau.
"""
import time
import requests
import logging
from config import settings

logger = logging.getLogger("scraper_logger")


class NvidiaError(Exception):
    pass


class NvidiaQuotaError(NvidiaError):
    pass


_SESSION = requests.Session()


def _candidate_models() -> list:
    configured = (settings.NVIDIA_MODEL or "").strip()
    fallback_models = [
        model.strip()
        for model in getattr(settings, "NVIDIA_FALLBACK_MODELS", [])
        if model and model.strip()
    ]
    ordered = []
    seen = set()
    for model in [configured] + fallback_models:
        if model and model not in seen:
            ordered.append(model)
            seen.add(model)
    return ordered or [
        "deepseek-ai/deepseek-v4.1-flash",
        "meta/llama-3.3-70b-instruct",
        "mistralai/mistral-large-2-instruct",
        "deepseek-ai/deepseek-r1",
    ]


def call_llm(messages: list) -> str:
    """Retourne le texte brut de la réponse (JSON), ou lève NvidiaQuotaError / NvidiaError."""
    api_key = (settings.NVIDIA_API_KEY or "").strip().strip('"').strip("'")
    if not api_key:
        raise NvidiaQuotaError("Clé NVIDIA non configurée ou vide dans .env")

    base_url = (settings.NVIDIA_BASE_URL or "https://integrate.api.nvidia.com/v1").rstrip("/")
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

        max_retries = max(1, settings.LLM_MAX_RETRIES)
        for attempt in range(max_retries):
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
                        msg = choices[0].get("message", {})
                        content = msg.get("content") or ""
                        if not content and msg.get("reasoning_content"):
                            content = msg.get("reasoning_content") or ""
                        if content and str(content).strip():
                            return str(content).strip()
                    raise NvidiaError(f"Réponse NVIDIA vide pour le modèle {model}")

                if resp.status_code in (402, 429):
                    if attempt < max_retries - 1:
                        sleep_s = 2.0 + attempt * 2.0
                        time.sleep(sleep_s)
                        continue
                    last_error = NvidiaQuotaError(f"Quota NVIDIA dépassé (HTTP {resp.status_code}) pour le modèle {model}: {resp.text[:200]}")
                    break

                if resp.status_code in (401, 403):
                    raise NvidiaQuotaError(f"Clé API NVIDIA invalide ou non autorisée (HTTP {resp.status_code})")

                if resp.status_code in (400, 404):
                    last_error = NvidiaError(f"Modèle NVIDIA non supporté ou indisponible ({model}): {resp.text[:200]}")
                    break  # Passer au modèle candidat suivant

                if resp.status_code >= 500:
                    time.sleep(1.0 + attempt * 0.5)
                    continue

                raise NvidiaError(f"Erreur NVIDIA HTTP {resp.status_code}: {resp.text[:300]}")

            except (requests.Timeout, requests.ConnectionError) as net_err:
                last_error = NvidiaError(f"Erreur réseau NVIDIA: {net_err}")
                time.sleep(1.0 + attempt * 0.5)
            except NvidiaQuotaError:
                raise
            except Exception as e:
                last_error = NvidiaError(f"Exception NVIDIA inattendue: {e}")
                time.sleep(1.0)

    if last_error and isinstance(last_error, NvidiaQuotaError):
        raise last_error
    raise last_error or NvidiaError("Échec des appels à l'API NVIDIA sur tous les modèles candidats.")
