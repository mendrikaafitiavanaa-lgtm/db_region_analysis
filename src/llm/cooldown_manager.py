"""
Gestionnaire de cooldown persistant (Circuit Breaker) pour les fournisseurs LLM.

Le cooldown est désactivé par défaut afin d'éviter de bloquer un fournisseur pendant 24h
à cause d'un ancien fichier checkpoint ou d'un changement de clé API. Si un quota est
rencontré, l'option LLM_COOLDOWN_HOURS peut être utilisée pour réactiver un blocage temporaire.
L'état est persisté sur disque dans .checkpoint/provider_cooldown.json.
"""
import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from config import settings

logger = logging.getLogger("scraper_logger")

COOLDOWN_FILE = os.path.join(settings.CHECKPOINT_DIR, "provider_cooldown.json")


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
    """Retourne True si le fournisseur n'est pas sous cooldown de quota."""
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

    cooldown_until = info.get("cooldown_until", 0)
    now = time.time()
    if now < cooldown_until:
        return False
    return True


def get_remaining_cooldown_seconds(provider_name: str) -> float:
    """Retourne le nombre de secondes restantes de cooldown (0 si disponible)."""
    provider_name = provider_name.strip().lower()
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
