"""
Gestionnaire de cooldown persistant (Circuit Breaker) pour les fournisseurs LLM.

Le cooldown est désactivé par défaut (ou paramétrable via LLM_COOLDOWN_HOURS).
Si une clé API est modifiée dans .env, le cooldown est IMMÉDIATEMENT levé pour ce
fournisseur, même si la période de blocage n'était pas terminée.
L'état est persisté sur disque dans .checkpoint/provider_cooldown.json.
"""
import os
import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import hashlib
from config import settings

logger = logging.getLogger("scraper_logger")

COOLDOWN_FILE = os.path.join(settings.CHECKPOINT_DIR, "provider_cooldown.json")


def _get_api_key(provider_name: str) -> str:
    """Récupère la clé API configurée pour un fournisseur donné (avec support des alias)."""
    p = (provider_name or "").strip().lower()
    if p in ("google", "google_aistudio", "aistudio", "gemini"):
        return (getattr(settings, "GOOGLE_AI_API_KEY", "") or "").strip()
    elif p in ("cerebras", "cerebras_ai"):
        return (getattr(settings, "CEREBRAS_API_KEY", "") or "").strip()
    elif p in ("openrouter", "open_router"):
        return (getattr(settings, "OPENROUTER_API_KEY", "") or "").strip()
    elif p in ("nvidia", "nvdia", "nvidia_nim", "nim"):
        return (getattr(settings, "NVIDIA_API_KEY", "") or "").strip()
    elif p in ("groq", "grok"):
        return (getattr(settings, "GROQ_API_KEY", "") or "").strip()
    elif p in ("huggingface", "hf", "hugginface"):
        return (getattr(settings, "HUGGINGFACE_API_KEY", "") or "").strip()
    return ""


def _current_key_fingerprint(provider_name: str) -> str:
    """Génère une empreinte unique (hash SHA256 tronqué) de la clé API active."""
    key = _get_api_key(provider_name)
    if not key:
        return "no_key"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _ensure_dir():
    os.makedirs(settings.CHECKPOINT_DIR, exist_ok=True)


def _load_state() -> Dict[str, Any]:
    _ensure_dir()
    if not os.path.exists(COOLDOWN_FILE):
        return {}
    try:
        with open(COOLDOWN_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save_state(state: Dict[str, Any]):
    _ensure_dir()
    try:
        with open(COOLDOWN_FILE, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
    except Exception as exc:
        logger.warning(f"Impossible de sauvegarder le cooldown LLM : {exc}")


def is_provider_available(provider_name: str) -> bool:
    """
    Vérifie si un fournisseur est disponible pour être appelé.
    Lève automatiquement le cooldown si :
    1. LLM_COOLDOWN_HOURS <= 0
    2. La clé API dans .env a changé (empreinte différente)
    3. L'ancien enregistrement n'avait pas d'empreinte de clé
    4. Le délai de cooldown est expiré
    """
    provider_name = provider_name.strip().lower()

    if float(getattr(settings, "LLM_COOLDOWN_HOURS", 0.0)) <= 0:
        state = _load_state()
        if provider_name in state:
            state.pop(provider_name, None)
            _save_state(state)
        return True

    state = _load_state()
    info = state.get(provider_name)
    if not info:
        return True

    current_fp = _current_key_fingerprint(provider_name)
    stored_fp = info.get("key_fingerprint")

    # Si aucune empreinte enregistrée (ancien format) ou clé modifiée -> lever immédiatement
    if not stored_fp or stored_fp != current_fp:
        state.pop(provider_name, None)
        _save_state(state)
        logger.info(
            f"🔄 [CIRCUIT BREAKER] Clé API modifiée ou rafraîchie pour '{provider_name.upper()}', cooldown levé immédiatement."
        )
        return True

    cooldown_until = info.get("cooldown_until", 0)
    if time.time() >= cooldown_until:
        state.pop(provider_name, None)
        _save_state(state)
        return True

    return False


def get_remaining_cooldown_seconds(provider_name: str) -> float:
    """
    Retourne le nombre de secondes restantes de cooldown (0 si disponible ou si clé changée).
    """
    provider_name = provider_name.strip().lower()
    # is_provider_available purge l'état si la clé a changé ou si le temps est écoulé
    if is_provider_available(provider_name):
        return 0.0

    state = _load_state()
    info = state.get(provider_name)
    if not info:
        return 0.0

    cooldown_until = info.get("cooldown_until", 0)
    return max(0.0, cooldown_until - time.time())


def format_remaining_time(seconds: float) -> str:
    """Formate une durée en heures et minutes lisibles."""
    if seconds <= 0:
        return "0m"
    hours = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    if hours > 0:
        return f"{hours}h {mins:02d}m"
    return f"{mins}m"


def mark_cooldown(provider_name: str, reason: str, duration_hours: Optional[float] = None):
    """Met un fournisseur en pause pour une durée donnée si le cooldown est activé."""
    provider_name = provider_name.strip().lower()
    if duration_hours is None:
        duration_hours = getattr(settings, "LLM_COOLDOWN_HOURS", 0.0)

    if float(duration_hours) <= 0:
        state = _load_state()
        if provider_name in state:
            state.pop(provider_name, None)
            _save_state(state)
        logger.info(f"[CIRCUIT BREAKER] Cooldown désactivé pour '{provider_name.upper()}'; aucun blocage persistant appliqué.")
        return

    now = time.time()
    cooldown_until = now + (float(duration_hours) * 3600)
    until_dt = datetime.fromtimestamp(cooldown_until).strftime("%Y-%m-%d %H:%M:%S")

    state = _load_state()
    state[provider_name] = {
        "cooldown_until": cooldown_until,
        "cooldown_until_iso": until_dt,
        "duration_hours": duration_hours,
        "disabled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "reason": str(reason)[:300],
        "key_fingerprint": _current_key_fingerprint(provider_name),
    }
    _save_state(state)

    logger.warning(
        f"⛔ [CIRCUIT BREAKER] Fournisseur '{provider_name.upper()}' mis en pause pour {duration_hours}h "
        f"(jusqu'à {until_dt}) suite à un dépassement de quota."
    )


def reset_cooldown(provider_name: Optional[str] = None):
    """Réinitialise le cooldown pour un ou tous les fournisseurs."""
    state = _load_state()
    if provider_name:
        p = provider_name.strip().lower()
        if p in state:
            del state[p]
            _save_state(state)
            logger.info(f"[CIRCUIT BREAKER] Cooldown réinitialisé pour '{p.upper()}'.")
    else:
        _save_state({})
        logger.info("[CIRCUIT BREAKER] Tous les cooldowns LLM ont été réinitialisés.")

