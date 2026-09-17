"""
Wrapper LLM avec basculement automatique (failover) multi-fournisseurs.

Supporte :
- Mode 'auto' : essaie le premier fournisseur disponible dans LLM_PROVIDER_ORDER
  (par défaut: google -> openrouter). En cas d'erreur de quota (429/402/exhaution),
  bascule automatiquement sur le fournisseur suivant sans interrompre le traitement.
- Mode direct ('google' ou 'openrouter').
"""
import logging
from typing import List, Tuple
from config import settings
from src.llm import cooldown_manager
from src.llm.rate_limiter import global_rate_limiter
from src.llm import token_budget
from src.llm import openrouter_client
from src.llm import google_client

logger = logging.getLogger("scraper_logger")


class LLMError(Exception):
    pass


def _get_provider_pipeline() -> List[Tuple[str, callable]]:
    """Retourne la liste ordonnée des fournisseurs à essayer selon la configuration."""
    pipeline = []
    order = settings.LLM_PROVIDER_ORDER if settings.LLM_PROVIDER == "auto" else [settings.LLM_PROVIDER]

    for p in order:
        p_clean = p.strip().lower()
        if p_clean in ("google", "google_aistudio", "aistudio"):
            pipeline.append(("google", google_client.call_llm))
        elif p_clean == "openrouter":
            pipeline.append(("openrouter", openrouter_client.call_llm))

    if not pipeline:
        # Fallback par défaut si mal configuré
        pipeline = [("google", google_client.call_llm), ("openrouter", openrouter_client.call_llm)]

    return pipeline


def call_llm(messages: list) -> str:
    # 1. Estimation tokens prompt
    prompt_tokens = token_budget.estimate_tokens_for_messages(messages)

    # 2. Vérification budget journalier si configuré
    if settings.LLM_TOKEN_BUDGET_DAILY and settings.LLM_TOKEN_BUDGET_DAILY > 0:
        consumed = token_budget.get_consumed_today()
        remaining = settings.LLM_TOKEN_BUDGET_DAILY - consumed
        reserved_estimate = prompt_tokens + int(settings.LLM_MAX_TOKENS_OUTPUT)
        if remaining <= 0:
            raise token_budget.BudgetExceeded("Budget journalier de tokens atteint. Arrêt des appels LLM.")
        if reserved_estimate > remaining:
            raise token_budget.BudgetExceeded(
                f"Budget journalier insuffisant (nécessite ~{reserved_estimate} tokens, reste {remaining})."
            )

    # 3. Rate limiter
    try:
        global_rate_limiter.acquire()
    except Exception:
        pass

    pipeline = _get_provider_pipeline()

    # Filtrer les fournisseurs disponibles selon le statut de cooldown
    available_providers = [
        (name, fn) for name, fn in pipeline
        if cooldown_manager.is_provider_available(name)
    ]

    # Si tous les fournisseurs sont actuellement bloqués par un cooldown actif
    if not available_providers:
        status_details = []
        for name, _ in pipeline:
            rem = cooldown_manager.get_remaining_cooldown_seconds(name)
            rem_str = cooldown_manager.format_remaining_time(rem)
            status_details.append(f"{name.upper()} (cooldown restant: {rem_str})")
        details_str = ", ".join(status_details)
        raise LLMError(
            f"Tous les fournisseurs LLM sont actuellement bloqués par un cooldown. [{details_str}]. "
            f"Attendez la fin du cooldown ou réinitialisez le statut si vous avez changé de clé API."
        )

    last_exc = None

    for provider_name, call_fn in available_providers:
        try:
            raw = call_fn(messages)

            # Enregistrer consommation tokens
            try:
                resp_tokens = token_budget.estimate_tokens_from_text(raw)
                token_budget.add_consumed(prompt_tokens + resp_tokens)
            except Exception:
                pass

            return raw

        except (google_client.GoogleQuotaError, openrouter_client.OpenRouterQuotaError) as quota_err:
            # Active un cooldown uniquement si la configuration le permet
            cooldown_manager.mark_cooldown(
                provider_name=provider_name,
                reason=str(quota_err),
                duration_hours=settings.LLM_COOLDOWN_HOURS,
            )
            logger.warning(
                f"⚠️ [FAILOVER] Quota/Limite 429 atteinte sur '{provider_name.upper()}'. "
                f"Durée active du cooldown: {settings.LLM_COOLDOWN_HOURS}h. Basculement automatique..."
            )
            last_exc = quota_err
            continue

        except Exception as exc:
            # Si erreur générique LLM, tenter aussi le fallback si d'autres fournisseurs disponibles
            if settings.LLM_PROVIDER == "auto" and len(available_providers) > 1:
                logger.warning(
                    f"⚠️ [FAILOVER] Erreur sur '{provider_name.upper()}': {exc}. "
                    f"Tentative de basculement vers fournisseur suivant..."
                )
                last_exc = exc
                continue
            raise LLMError(f"[{provider_name}] {exc}") from exc

    raise LLMError(f"Tous les fournisseurs LLM disponibles ont échoué. Dernière erreur: {last_exc}")


def get_error_class():
    return LLMError

